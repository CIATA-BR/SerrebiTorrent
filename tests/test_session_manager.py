import pytest
import sys
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def mock_libtorrent_environment():
    """
    Setup a mocked libtorrent environment for all tests in this module.
    Restores the original environment afterwards.
    """
    # Save original modules
    original_lt = sys.modules.get('libtorrent')
    original_sm = sys.modules.get('session_manager')
    
    # Create Mock
    mock_lt = MagicMock()
    # Setup Enums
    mock_lt.proxy_type_t = MagicMock()
    mock_lt.proxy_type_t.none = 0
    mock_lt.proxy_type_t.socks4 = 1
    mock_lt.proxy_type_t.socks5 = 2
    mock_lt.proxy_type_t.socks5_pw = 3
    mock_lt.proxy_type_t.http = 4
    mock_lt.proxy_type_t.http_pw = 5

    mock_lt.alert = MagicMock()
    mock_lt.alert.category_t = MagicMock()
    mock_lt.alert.category_t.status_notification = 1
    mock_lt.alert.category_t.storage_notification = 2
    mock_lt.alert.category_t.error_notification = 4

    mock_lt.resume_data_flags_t = MagicMock()
    mock_lt.resume_data_flags_t.flush_disk_cache = 1
    mock_lt.session.return_value.wait_for_alert.return_value = False
    mock_lt.session.return_value.pop_alerts.return_value = []
    
    # Patch
    sys.modules['libtorrent'] = mock_lt
    # Remove session_manager so it gets re-imported with the mock
    if 'session_manager' in sys.modules:
        del sys.modules['session_manager']
        
    yield mock_lt
    
    # Cleanup
    if original_lt:
        sys.modules['libtorrent'] = original_lt
    else:
        del sys.modules['libtorrent']
        
    if original_sm:
        sys.modules['session_manager'] = original_sm
    elif 'session_manager' in sys.modules:
        del sys.modules['session_manager']

@pytest.fixture
def session_manager(mock_libtorrent_environment):
    from session_manager import SessionManager
    
    # Reset singleton
    SessionManager._instance = None
    
    # Reset mock_lt session calls
    mock_libtorrent_environment.session.return_value.reset_mock()
    
    with patch('session_manager.get_state_dir', return_value='.'):
        with patch('os.path.exists', return_value=False):
            with patch('session_manager.ConfigManager') as MockCM:
                MockCM.return_value.get_preferences.return_value = {}
                with patch('os.listdir', return_value=[]):
                    sm = SessionManager.get_instance()
                    sm.ses.reset_mock()
                    yield sm
                    sm.running = False
                    sm.alert_thread.join(timeout=1)
                    SessionManager._instance = None

def test_singleton(session_manager):
    from session_manager import SessionManager
    sm2 = SessionManager.get_instance()
    assert session_manager is sm2

def test_apply_preferences(session_manager):
    prefs = {
        'dl_limit': 1000,
        'ul_limit': 2000,
        'max_connections': 50,
        'listen_port': 7001,
    }
    session_manager.apply_preferences(prefs)
    
    # Check if ses.apply_settings was called
    session_manager.ses.apply_settings.assert_called_once()
    call_args = session_manager.ses.apply_settings.call_args[0][0]
    
    assert call_args['download_rate_limit'] == 1000
    assert call_args['upload_rate_limit'] == 2000
    assert call_args['connections_limit'] == 50
    assert call_args['listen_interfaces'] == '0.0.0.0:7001,[::]:7001'


def test_apply_preferences_maps_upload_slots_and_unlimited_limits(session_manager):
    prefs = {
        'dl_limit': -1,
        'ul_limit': -1,
        'max_uploads': 12,
    }
    session_manager.apply_preferences(prefs)

    call_args = session_manager.ses.apply_settings.call_args[0][0]

    assert call_args['download_rate_limit'] == 0
    assert call_args['upload_rate_limit'] == 0
    assert call_args['unchoke_slots_limit'] == 12


def test_apply_preferences_treats_zero_upload_slots_as_unlimited(session_manager):
    session_manager.apply_preferences({'max_uploads': 0})

    call_args = session_manager.ses.apply_settings.call_args[0][0]

    assert call_args['unchoke_slots_limit'] == -1


def test_qbittorrent_identity_matches_the_reported_version():
    import session_manager as sm

    # The version is looked up from qBittorrent's releases, so pin one here
    # rather than asserting on whatever today's is.
    with patch.object(sm, 'qbittorrent_version', return_value=(5, 2, 3)):
        user_agent, fingerprint = sm.qbittorrent_identity()

    assert user_agent == "qBittorrent/5.2.3"
    assert fingerprint == b"-qB5230-"


def test_qbittorrent_version_falls_back_when_the_lookup_fails(tmp_path):
    import session_manager as sm

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)), \
            patch.object(sm, '_fetch_latest_qbittorrent', return_value=None):
        assert sm.qbittorrent_version() == sm._parse_version(
            sm.QBITTORRENT_FALLBACK_VERSION)


def test_qbittorrent_version_is_remembered_between_lookups(tmp_path):
    import session_manager as sm

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)), \
            patch.object(sm, '_fetch_latest_qbittorrent',
                         return_value=(9, 9, 9)) as fetch:
        assert sm.qbittorrent_version() == (9, 9, 9)
        # Second call inside the same day is answered from the state file.
        assert sm.qbittorrent_version() == (9, 9, 9)

    assert fetch.call_count == 1


def test_qbittorrent_version_offline_never_calls_out(tmp_path):
    import session_manager as sm

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)), \
            patch.object(sm, '_fetch_latest_qbittorrent',
                         side_effect=AssertionError("looked up")):
        assert sm.qbittorrent_version(allow_network=False) == sm._parse_version(
            sm.QBITTORRENT_FALLBACK_VERSION)

def test_add_magnet(session_manager, mock_libtorrent_environment):
    magnet = "magnet:?xt=urn:btih:abcdef"
    save_path = "/tmp"
    
    mock_params = MagicMock()
    mock_params.info_hashes.v1 = "abcdef"
    mock_params.info_hashes.has_v1.return_value = True
    
    mock_libtorrent_environment.parse_magnet_uri.return_value = mock_params
    
    with patch.object(session_manager, '_find_handle', return_value=None):
         session_manager.add_magnet(magnet, save_path)
    
    session_manager.ses.add_torrent.assert_called()
    assert "abcdef" in session_manager.torrents_db
    assert session_manager.torrents_db["abcdef"]['save_path'] == save_path
    assert session_manager.torrents_db["abcdef"]['magnet_uri'] == magnet

def test_remove_torrent(session_manager, mock_libtorrent_environment):
    info_hash = "abcdef"
    session_manager.torrents_db[info_hash] = {'save_path': '/tmp'}
    
    mock_handle = MagicMock()
    with patch.object(session_manager, '_find_handle', return_value=mock_handle):
         mock_libtorrent_environment.remove_flags_t = MagicMock()
         mock_libtorrent_environment.remove_flags_t.delete_files = 1
         
         session_manager.remove_torrent(info_hash)
         
         session_manager.ses.remove_torrent.assert_called()
         assert info_hash not in session_manager.torrents_db


class FakeHash:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def to_string(self):
        return bytes.fromhex(self.value)


class FakeInfoHashes:
    def __init__(self, v1, v2):
        self.v1 = FakeHash(v1)
        self.v2 = FakeHash(v2)

    def has_v1(self):
        return True

    def has_v2(self):
        return True


class FakeHybridHandle:
    def __init__(self, v1, v2):
        self._hashes = FakeInfoHashes(v1, v2)
        self._legacy_hash = FakeHash(v2[:40])

    def info_hashes(self):
        return self._hashes

    def info_hash(self):
        return self._legacy_hash


def test_find_handle_accepts_hybrid_v2_display_hash(session_manager):
    v1 = "0ecb0b05fa9334995a9b71373c4a31ed519ab5ff"
    v2 = "45e8ad4452fc70825ac06a07369d26f711e384ae89a382bd2e3d77d0166496b6"
    handle = FakeHybridHandle(v1, v2)
    session_manager.ses.get_torrents.return_value = [handle]

    assert session_manager._handle_hash_key(handle) == v1
    assert session_manager._find_handle(v2[:40]) is handle
    assert session_manager._find_handle(v2) is handle


def test_remove_hybrid_display_hash_cleans_v1_state(session_manager):
    v1 = "0ecb0b05fa9334995a9b71373c4a31ed519ab5ff"
    v2 = "45e8ad4452fc70825ac06a07369d26f711e384ae89a382bd2e3d77d0166496b6"
    handle = FakeHybridHandle(v1, v2)
    session_manager.ses.get_torrents.return_value = [handle]
    session_manager.torrents_db[v1] = {'save_path': '/tmp'}

    with patch('os.path.exists', return_value=False):
        session_manager.remove_torrent(v2[:40])

    session_manager.ses.remove_torrent.assert_called_once()
    assert v1 not in session_manager.torrents_db


def test_remove_cleans_known_state_even_without_handle(session_manager):
    info_hash = "2" * 40
    session_manager.ses.get_torrents.return_value = []
    session_manager.torrents_db[info_hash] = {'save_path': '/tmp'}

    with patch('os.path.exists', return_value=False):
        session_manager.remove_torrent(info_hash)

    session_manager.ses.remove_torrent.assert_not_called()
    assert info_hash not in session_manager.torrents_db


def test_save_resume_keeps_pending_on_write_failure(session_manager, tmp_path):
    info_hash = "3" * 40
    session_manager.state_dir = str(tmp_path)
    session_manager.pending_saves.add(info_hash)
    alert = SimpleNamespace(params=SimpleNamespace(info_hashes=info_hash, save_path=""))

    with patch('session_manager._write_resume_data_bytes', side_effect=OSError("boom")):
        session_manager._handle_save_resume(alert)

    assert info_hash in session_manager.pending_saves
    assert not (tmp_path / f"{info_hash}.resume").exists()


def test_save_resume_discards_pending_after_atomic_write(session_manager, tmp_path):
    info_hash = "4" * 40
    session_manager.state_dir = str(tmp_path)
    session_manager.pending_saves.add(info_hash)
    alert = SimpleNamespace(params=SimpleNamespace(info_hashes=info_hash, save_path=""))

    with patch('session_manager._write_resume_data_bytes', return_value=b"resume-data"):
        session_manager._handle_save_resume(alert)

    assert info_hash not in session_manager.pending_saves
    assert (tmp_path / f"{info_hash}.resume").read_bytes() == b"resume-data"
    assert list(tmp_path.glob("*.tmp")) == []


def test_cleanup_torrent_state_removes_db_key_files_when_called_with_alias(session_manager, tmp_path):
    db_key = "5" * 40
    alias = "6" * 40
    session_manager.state_dir = str(tmp_path)
    session_manager.torrents_db[db_key] = {"hashes": {"v1": alias}, "save_path": "/tmp"}
    session_manager.pending_saves.update({db_key, alias})

    with patch('os.path.exists', return_value=True), patch('os.remove') as remove_file:
        with patch.object(session_manager, '_save_torrents_db'):
            session_manager._cleanup_torrent_state([alias])

    removed = {os.path.basename(call.args[0]) for call in remove_file.call_args_list}
    assert f"{alias}.torrent" in removed
    assert f"{alias}.resume" in removed
    assert f"{db_key}.torrent" in removed
    assert f"{db_key}.resume" in removed
    assert db_key not in session_manager.torrents_db
    assert db_key not in session_manager.pending_saves
    assert alias not in session_manager.pending_saves


def test_handle_has_metadata_across_libtorrent_versions():
    from session_manager import _handle_has_metadata

    class LegacyHandle:
        def __init__(self, metadata):
            self._metadata = metadata

        def has_metadata(self):
            return self._metadata

    class V21Handle:
        def __init__(self, metadata):
            self._metadata = metadata

        def status(self):
            return SimpleNamespace(has_metadata=self._metadata)

    assert _handle_has_metadata(LegacyHandle(True)) is True
    assert _handle_has_metadata(LegacyHandle(False)) is False
    assert _handle_has_metadata(V21Handle(True)) is True
    assert _handle_has_metadata(V21Handle(False)) is False


def test_get_status_uses_session_status_when_available(session_manager):
    session_manager.get_status()
    session_manager.ses.status.assert_called_once()


def test_get_status_falls_back_to_summed_rates_without_session_status(session_manager):
    """libtorrent 2.1 removed session.status(); rates are summed per torrent."""
    del session_manager.ses.status  # simulate libtorrent 2.1

    handle = MagicMock()
    handle.is_valid.return_value = True
    st = MagicMock()
    st.download_payload_rate = 1000
    st.upload_payload_rate = 500
    handle.status.return_value = st
    session_manager.ses.get_torrents.return_value = [handle, handle]

    status = session_manager.get_status()

    assert status.payload_download_rate == 2000
    assert status.payload_upload_rate == 1000



def test_load_torrents_db_preserves_corrupt_file(tmp_path):
    from session_manager import SessionManager

    db_path = tmp_path / "torrents.json"
    corrupt = "{broken json"
    db_path.write_text(corrupt, encoding="utf-8")

    manager = SessionManager.__new__(SessionManager)
    manager.torrents_db_path = str(db_path)

    assert manager._load_torrents_db() == {}
    assert db_path.read_text(encoding="utf-8") == corrupt
    assert (tmp_path / "torrents.json.corrupt").read_text(encoding="utf-8") == corrupt


def test_load_torrents_db_rejects_non_object_root(tmp_path):
    from session_manager import SessionManager

    db_path = tmp_path / "torrents.json"
    db_path.write_text('["unexpected"]', encoding="utf-8")

    manager = SessionManager.__new__(SessionManager)
    manager.torrents_db_path = str(db_path)

    assert manager._load_torrents_db() == {}
    assert (tmp_path / "torrents.json.corrupt").read_text(encoding="utf-8") == '["unexpected"]'



def test_qbittorrent_version_cache_ignores_non_object_json(tmp_path):
    import session_manager as sm

    state_path = tmp_path / sm._VERSION_STATE_FILE
    state_path.write_text('["unexpected"]', encoding="utf-8")

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)):
        assert sm._read_version_state() == (None, 0.0)


def test_qbittorrent_version_cache_ignores_invalid_checked_value(tmp_path):
    import session_manager as sm

    state_path = tmp_path / sm._VERSION_STATE_FILE
    state_path.write_text(
        json.dumps({"version": "9.9.9", "checked": "not-a-number"}),
        encoding="utf-8",
    )

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)):
        assert sm._read_version_state() == (None, 0.0)


def test_qbittorrent_version_cache_write_is_atomic(tmp_path):
    import session_manager as sm

    with patch.object(sm, 'get_state_dir', return_value=str(tmp_path)):
        sm._write_version_state((9, 9, 9))

    state_path = tmp_path / sm._VERSION_STATE_FILE
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["version"] == "9.9.9"
    assert isinstance(payload["checked"], float)
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_torrents_db_restricts_permissions_on_posix(tmp_path, monkeypatch):
    from session_manager import SessionManager
    import session_manager as sm

    manager = SessionManager.__new__(SessionManager)
    manager.torrents_db_path = str(tmp_path / "torrents.json")
    manager.torrents_db = {"abc": {"save_path": "/tmp"}}
    monkeypatch.setattr(sm.os, "name", "posix", raising=False)
    chmods = []
    monkeypatch.setattr(sm.os, "chmod", lambda p, mode, **_kw: chmods.append((str(p), mode)))

    manager._save_torrents_db()

    db_path = tmp_path / "torrents.json"
    assert (str(db_path), 0o600) in chmods


def test_corrupt_torrents_db_backup_restricts_permissions_on_posix(tmp_path, monkeypatch):
    from session_manager import SessionManager
    import session_manager as sm

    db_path = tmp_path / "torrents.json"
    db_path.write_text("{broken json", encoding="utf-8")
    db_path.chmod(0o644)
    monkeypatch.setattr(sm.os, "name", "posix", raising=False)
    chmods = []
    monkeypatch.setattr(sm.os, "chmod", lambda p, mode, **_kw: chmods.append((str(p), mode)))

    manager = SessionManager.__new__(SessionManager)
    manager.torrents_db_path = str(db_path)

    assert manager._load_torrents_db() == {}
    backup = tmp_path / "torrents.json.corrupt"
    assert backup.exists()
    assert (str(backup), 0o600) in chmods
