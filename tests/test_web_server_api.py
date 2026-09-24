
import pytest
import sys
import os
import json
import io
import time
import hashlib
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import web_server

@pytest.fixture
def client():
    web_server.app.config['TESTING'] = True
    web_server.app.config['SECRET_KEY'] = 'test'
    with web_server.app.test_client() as client:
        yield client

@pytest.fixture
def auth_failures():
    """Keep throttle state out of the shared module-level cache."""
    with web_server._auth_lock:
        original = dict(web_server._auth_failures)
        web_server._auth_failures.clear()
    yield web_server._auth_failures
    with web_server._auth_lock:
        web_server._auth_failures.clear()
        web_server._auth_failures.update(original)

@pytest.fixture
def auth_client(client):
    # Perform login
    client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
    return client


def csrf_headers(client):
    with client.session_transaction() as session:
        return {'X-CSRF-Token': session['csrf_token']}


def test_compromised_web_secret_is_rotated(tmp_path, monkeypatch):
    import app_paths

    key_path = tmp_path / 'web_secret.key'
    compromised = b'published session key'
    key_path.write_bytes(compromised)
    monkeypatch.setattr(app_paths, 'get_data_dir', lambda: str(tmp_path))
    monkeypatch.setattr(
        web_server,
        '_COMPROMISED_SECRET_KEY_SHA256',
        hashlib.sha256(compromised).hexdigest(),
    )

    key = web_server._load_or_create_secret_key()

    assert len(key) == 32
    assert key != compromised
    assert key_path.read_bytes() == key

def test_login(client):
    rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
    assert b"Ok." in rv.data
    assert rv.status_code == 200
    
    rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'wrong'})
    assert rv.status_code == 403


def test_session_invalidates_after_credentials_change(client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG.update({'username': 'admin', 'password': 'password'})
        rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
        assert rv.status_code == 200

        web_server.WEB_CONFIG.update({'password': 'new-secret'})
        rv = client.get('/api/v2/auth/csrf')

        assert rv.status_code == 403
        with client.session_transaction() as session:
            assert 'logged_in' not in session
            assert 'auth_fingerprint' not in session
    finally:
        web_server.WEB_CONFIG.update(original)


def test_web_ui_does_not_start_with_default_password(monkeypatch):
    original = web_server.WEB_CONFIG.copy()
    original_thread = web_server.server_thread
    thread_ctor = MagicMock()
    try:
        web_server.WEB_CONFIG.update({'password': 'password', 'enabled': True})
        web_server.server_thread = None
        monkeypatch.setattr(web_server.threading, 'Thread', thread_ctor)

        web_server.start_web_ui()

        thread_ctor.assert_not_called()
        assert web_server.server_thread is None
    finally:
        web_server.WEB_CONFIG.update(original)
        web_server.server_thread = original_thread

def test_profiles_endpoint(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {'p1': {'name': 'Profile 1'}}
    mock_app.current_profile_id = 'p1'
    
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/profiles')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'p1' in data['profiles']
    assert data['current_id'] == 'p1'

def test_torrents_info_endpoint(auth_client):
    mock_app = MagicMock()
    torrents_list = [
        {'hash': 'abc', 'name': 'Test', 'size': 1000, 'done': 500, 'state': 1}
    ]
    mock_app.all_torrents = torrents_list
    mock_app.get_all_torrents_safe.return_value = torrents_list
    
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/torrents/info')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert len(data['torrents']) == 1
    assert data['stats']['All'] == 1
    assert data['stats']['Downloading'] == 1

def test_torrents_add_endpoint(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client
    
    rv = auth_client.post(
        '/api/v2/torrents/add',
        data={'urls': 'magnet:?foo', 'savepath': '/tmp'},
        headers=csrf_headers(auth_client),
    )
    assert rv.status_code == 200
    mock_client.add_torrent_url.assert_called_with('magnet:?foo', sp='/tmp')

def test_torrents_delete_endpoint_uses_bulk_remove(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': 'h1|h2', 'deleteFiles': 'true'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    mock_client.remove_torrents.assert_called_once_with(['h1', 'h2'], True)

def test_torrents_delete_endpoint_reports_remove_errors(auth_client):
    mock_client = MagicMock()
    mock_client.remove_torrents.side_effect = RuntimeError("still present")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': 'h1', 'deleteFiles': 'false'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to remove torrent(s)." in rv.data
    assert b"still present" not in rv.data

def test_rss_feeds_endpoint(auth_client):
    mock_app = MagicMock()
    mock_app.rss_panel.manager.feeds = {'http://feed': {'alias': 'Test'}}
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/rss/feeds')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'http://feed' in data


def test_translation_catalogs_are_public_before_login(client):
    response = client.get('/locales/index.json')
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload.get('languages'), list)


def test_non_locale_static_assets_remain_protected_before_login(client):
    response = client.get('/app.js')
    assert response.status_code in (301, 302)
    assert response.headers['Location'].endswith('/login.html')


def _fail_login(client, attempts):
    for _ in range(attempts):
        assert client.post(
            '/api/v2/auth/login',
            data={'username': 'admin', 'password': 'wrong'},
        ).status_code == 403


def test_lockout_reports_retry_after_and_not_invalid_credentials(client, auth_failures):
    _fail_login(client, web_server._AUTH_FAIL_LIMIT)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 429
    assert b"Too many failed attempts. Try again later." in response.data
    retry_after = int(response.headers['Retry-After'])
    assert 0 < retry_after <= web_server._AUTH_LOCK_SECONDS


def test_successful_login_clears_throttle_state(client, auth_failures):
    _fail_login(client, web_server._AUTH_FAIL_LIMIT - 1)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 200
    assert web_server._auth_failures == {}


def test_expired_throttle_record_is_pruned_on_read(client, auth_failures):
    stale = time.time() - web_server._AUTH_LOCK_SECONDS - 1
    with web_server._auth_lock:
        web_server._auth_failures['10.0.0.1'] = (web_server._AUTH_FAIL_LIMIT, stale)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 200
    assert '10.0.0.1' not in web_server._auth_failures


def test_throttle_cache_is_bounded_and_evicts_oldest(monkeypatch, auth_failures):
    monkeypatch.setattr(web_server, '_AUTH_MAX_TRACKED_IPS', 4)
    now = time.time()
    with web_server._auth_lock:
        for index in range(4):
            web_server._auth_failures[f'10.0.0.{index}'] = (1, now - 10 + index)

    web_server._record_auth_failure('10.0.0.9')

    assert len(web_server._auth_failures) == 4
    assert '10.0.0.0' not in web_server._auth_failures
    assert '10.0.0.9' in web_server._auth_failures


def test_baseline_security_headers_are_sent(client):
    response = client.get('/login.html')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=()'
    assert response.headers['Cache-Control'] == 'no-store'


def test_api_responses_are_not_cached(client, auth_failures):
    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.headers['Cache-Control'] == 'no-store'


def test_torrent_action_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.post(
            '/api/v2/torrents/pause',
            data={'hashes': 'h1'},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_recheck_reports_partial_failures(auth_client):
    mock_client = MagicMock()
    mock_client.recheck_torrent.side_effect = [None, RuntimeError("boom")]
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/recheck',
        data={'hashes': 'h1|h2'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to recheck one or more torrents." in rv.data
    assert mock_client.recheck_torrent.call_count == 2


def test_openfolder_reports_missing_download_path(auth_client):
    mock_client = MagicMock()
    mock_client.get_torrent_save_path.return_value = ''
    web_server.WEB_CONFIG['client'] = mock_client
    web_server.WEB_CONFIG['app'] = MagicMock()

    rv = auth_client.post(
        '/api/v2/torrents/openfolder',
        data={'hashes': 'h1'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"Download folder is unavailable." in rv.data


def test_torrents_delete_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.post(
            '/api/v2/torrents/delete',
            data={'hashes': 'h1', 'deleteFiles': 'false'},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_delete_requires_selection(auth_client):
    web_server.WEB_CONFIG['client'] = MagicMock()

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': '', 'deleteFiles': 'false'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"No torrents selected." in rv.data


def test_profile_switch_rejects_unknown_profile(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {
        'local': {'name': 'Local', 'type': 'local'}
    }
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/switch',
        data={'id': 'missing'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"Profile not found." in rv.data
    mock_app.connect_profile.assert_not_called()


def test_profile_switch_requires_profile_id(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {
        'local': {'name': 'Local', 'type': 'local'}
    }
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/switch',
        data={'id': ''},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Profile id is required." in rv.data
    mock_app.connect_profile.assert_not_called()


def test_profile_add_rejects_unknown_type(auth_client):
    mock_app = MagicMock()
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/add',
        data={
            'name': 'Broken',
            'type': 'not-a-client',
            'url': 'http://example.invalid',
        },
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Unsupported profile type." in rv.data
    mock_app.config_manager.add_profile.assert_not_called()


def test_profile_add_rejects_whitespace_only_required_fields(auth_client):
    mock_app = MagicMock()
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/add',
        data={
            'name': '   ',
            'type': 'rtorrent',
            'url': '   ',
        },
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Missing data" in rv.data
    mock_app.config_manager.add_profile.assert_not_called()


def test_profile_add_normalizes_supported_type(auth_client):
    mock_app = MagicMock()
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/add',
        data={
            'name': ' Remote ',
            'type': ' QBITTORRENT ',
            'url': ' http://127.0.0.1:8080 ',
            'user': 'user',
            'password': 'secret',
        },
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    mock_app.config_manager.add_profile.assert_called_once_with(
        'Remote',
        'qbittorrent',
        'http://127.0.0.1:8080',
        'user',
        'secret',
    )


def test_profile_add_reports_persistence_failure(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.add_profile.side_effect = OSError("disk full")
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/add',
        data={
            'name': 'Remote',
            'type': 'qbittorrent',
            'url': 'http://127.0.0.1:8080',
        },
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to create profile." in rv.data
    assert b"disk full" not in rv.data


def test_torrents_peers_returns_client_data(auth_client):
    mock_client = MagicMock()
    mock_client.get_peers.return_value = [
        {
            'address': '203.0.113.10:51413',
            'client': 'ExampleClient',
            'progress': 0.75,
            'down_rate': 2048,
            'up_rate': 1024,
        }
    ]
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/peers?hash=abc123')

    assert rv.status_code == 200
    assert rv.get_json() == mock_client.get_peers.return_value
    mock_client.get_peers.assert_called_once_with('abc123')


def test_torrents_peers_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.get('/api/v2/torrents/peers?hash=abc123')

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_peers_requires_hash(auth_client):
    web_server.WEB_CONFIG['client'] = MagicMock()

    rv = auth_client.get('/api/v2/torrents/peers')

    assert rv.status_code == 400
    assert b"Torrent hash is required." in rv.data


def test_torrents_peers_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.get_peers.side_effect = RuntimeError("secret backend detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/peers?hash=abc123')

    assert rv.status_code == 500
    assert b"Failed to load torrent peers." in rv.data
    assert b"secret backend detail" not in rv.data


def test_torrents_trackers_returns_client_data(auth_client):
    mock_client = MagicMock()
    mock_client.get_trackers.return_value = [
        {
            'url': 'https://tracker.example/announce',
            'status': 'Working',
            'peers': 42,
            'message': '',
        }
    ]
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/trackers?hash=abc123')

    assert rv.status_code == 200
    assert rv.get_json() == mock_client.get_trackers.return_value
    mock_client.get_trackers.assert_called_once_with('abc123')


def test_torrents_trackers_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.get('/api/v2/torrents/trackers?hash=abc123')

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_trackers_requires_hash(auth_client):
    web_server.WEB_CONFIG['client'] = MagicMock()

    rv = auth_client.get('/api/v2/torrents/trackers')

    assert rv.status_code == 400
    assert b"Torrent hash is required." in rv.data


def test_torrents_trackers_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.get_trackers.side_effect = RuntimeError("secret tracker detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/trackers?hash=abc123')

    assert rv.status_code == 500
    assert b"Failed to load torrent trackers." in rv.data
    assert b"secret tracker detail" not in rv.data


def test_torrents_files_returns_client_data(auth_client):
    mock_client = MagicMock()
    mock_client.get_files.return_value = [
        {'index': 0, 'name': 'example.txt', 'size': 1024, 'progress': 1.0, 'priority': 1}
    ]
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/files?hash=abc123')

    assert rv.status_code == 200
    assert rv.get_json() == mock_client.get_files.return_value
    mock_client.get_files.assert_called_once_with('abc123')


def test_torrents_files_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.get('/api/v2/torrents/files?hash=abc123')

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_files_requires_hash(auth_client):
    web_server.WEB_CONFIG['client'] = MagicMock()

    rv = auth_client.get('/api/v2/torrents/files')

    assert rv.status_code == 400
    assert b"Torrent hash is required." in rv.data


def test_torrents_files_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.get_files.side_effect = RuntimeError("secret file detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/files?hash=abc123')

    assert rv.status_code == 500
    assert b"Failed to load torrent files." in rv.data
    assert b"secret file detail" not in rv.data

def test_app_prefs_save_persists_before_success(auth_client, monkeypatch):
    mock_app = MagicMock()
    web_server.WEB_CONFIG['app'] = mock_app
    call_after = MagicMock()
    monkeypatch.setattr("wx.CallAfter", call_after)

    rv = auth_client.post(
        '/api/v2/app/prefs',
        json={'download_path': 'C:/Downloads'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    mock_app.config_manager.set_preferences.assert_called_once_with(
        {'download_path': 'C:/Downloads'}
    )
    assert call_after.call_count == 2
    call_after.assert_any_call(mock_app._update_client_default_save_path)
    call_after.assert_any_call(mock_app._update_web_ui)


def test_app_prefs_save_reports_persistence_failure(auth_client, monkeypatch):
    mock_app = MagicMock()
    mock_app.config_manager.set_preferences.side_effect = OSError("disk full")
    web_server.WEB_CONFIG['app'] = mock_app
    call_after = MagicMock()
    monkeypatch.setattr("wx.CallAfter", call_after)

    rv = auth_client.post(
        '/api/v2/app/prefs',
        json={'download_path': 'C:/Downloads'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to save settings." in rv.data
    assert b"disk full" not in rv.data
    call_after.assert_not_called()


def test_app_prefs_save_rejects_non_object_json(auth_client):
    mock_app = MagicMock()
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/app/prefs',
        json=['not', 'an', 'object'],
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Preferences object is required." in rv.data
    mock_app.config_manager.set_preferences.assert_not_called()


def test_app_prefs_save_requires_application_context(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['app'] = None

        rv = auth_client.post(
            '/api/v2/app/prefs',
            json={'download_path': 'C:/Downloads'},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"Application context is unavailable." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_profile_switch_reports_async_start(auth_client, monkeypatch):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {
        'remote': {'name': 'Remote', 'type': 'qbittorrent'}
    }
    web_server.WEB_CONFIG['app'] = mock_app
    call_after = MagicMock()
    monkeypatch.setattr("wx.CallAfter", call_after)

    rv = auth_client.post(
        '/api/v2/profiles/switch',
        data={'id': 'remote'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 202
    assert b"Profile switch started." in rv.data
    call_after.assert_called_once_with(mock_app.connect_profile, 'remote')

def test_rss_add_feed_reports_persistence_failure(auth_client):
    manager = MagicMock()
    manager.feeds = {}
    manager.add_feed.return_value = False
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/add_feed',
        data={'url': 'https://example.com/feed.xml', 'alias': 'Example'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to save RSS feed." in rv.data
    manager.add_feed.assert_called_once_with('https://example.com/feed.xml', 'Example')


def test_rss_add_feed_rejects_duplicate(auth_client):
    url = 'https://example.com/feed.xml'
    manager = MagicMock()
    manager.feeds = {url: {'alias': 'Example'}}
    manager.add_feed.return_value = False
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/add_feed',
        data={'url': url},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 409
    assert b"RSS feed already exists." in rv.data


def test_rss_remove_feed_reports_persistence_failure(auth_client):
    url = 'https://example.com/feed.xml'
    manager = MagicMock()
    manager.feeds = {url: {'alias': 'Example'}}
    manager.remove_feed.return_value = False
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/remove_feed',
        data={'url': url},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to remove RSS feed." in rv.data


def test_rss_remove_feed_reports_missing_feed(auth_client):
    manager = MagicMock()
    manager.feeds = {}
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/remove_feed',
        data={'url': 'https://example.com/missing.xml'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"RSS feed not found." in rv.data
    manager.remove_feed.assert_not_called()


def test_torrents_all_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.get('/api/v2/torrents/all')

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_all_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.get_torrents_full.side_effect = RuntimeError("secret backend detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/torrents/all')

    assert rv.status_code == 500
    assert b"Failed to fetch torrents." in rv.data
    assert b"secret backend detail" not in rv.data

def test_rss_set_rule_creates_disabled_rule(auth_client):
    manager = MagicMock()
    manager.rules = []
    manager.add_rule.return_value = True
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/set_rule',
        data={'pattern': 'ubuntu', 'type': 'accept', 'enabled': 'false'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    manager.add_rule.assert_called_once_with('ubuntu', 'accept', enabled=False)


def test_rss_set_rule_reports_persistence_failure(auth_client):
    manager = MagicMock()
    manager.rules = []
    manager.add_rule.return_value = False
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/set_rule',
        data={'pattern': 'ubuntu', 'type': 'accept', 'enabled': 'true'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to save RSS rule." in rv.data


def test_rss_set_rule_rejects_unknown_type(auth_client):
    manager = MagicMock()
    manager.rules = []
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/set_rule',
        data={'pattern': 'ubuntu', 'type': 'maybe', 'enabled': 'true'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Unsupported rule type." in rv.data
    manager.add_rule.assert_not_called()


def test_rss_set_rule_reports_missing_index(auth_client):
    manager = MagicMock()
    manager.rules = []
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/set_rule',
        data={'index': '4', 'pattern': 'ubuntu', 'type': 'accept', 'enabled': 'true'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"RSS rule not found." in rv.data
    manager.update_rule.assert_not_called()


def test_rss_remove_rule_reports_persistence_failure(auth_client):
    manager = MagicMock()
    manager.rules = [{'pattern': 'ubuntu'}]
    manager.remove_rule.return_value = False
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/remove_rule',
        data={'index': '0'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to remove RSS rule." in rv.data


def test_rss_remove_rule_reports_missing_rule(auth_client):
    manager = MagicMock()
    manager.rules = []
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/remove_rule',
        data={'index': '0'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"RSS rule not found." in rv.data
    manager.remove_rule.assert_not_called()


def test_app_prefs_get_requires_application_context(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['app'] = None

        rv = auth_client.get('/api/v2/app/prefs')

        assert rv.status_code == 503
        assert b"Application context is unavailable." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_app_prefs_get_hides_backend_errors(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_preferences.side_effect = RuntimeError("secret config detail")
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.get('/api/v2/app/prefs')

    assert rv.status_code == 500
    assert b"Failed to load settings." in rv.data
    assert b"secret config detail" not in rv.data


def test_remote_prefs_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.get('/api/v2/app/remote_prefs')

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_remote_prefs_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.get_app_preferences.side_effect = RuntimeError("secret backend detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.get('/api/v2/app/remote_prefs')

    assert rv.status_code == 500
    assert b"Failed to load remote preferences." in rv.data
    assert b"secret backend detail" not in rv.data


def test_rss_import_flexget_returns_completed_counts(auth_client):
    manager = MagicMock()
    manager.import_flexget_config.return_value = (2, 3)
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/import_flexget',
        data={'config': (io.BytesIO(b'tasks: {}\n'), 'flexget.yml')},
        headers=csrf_headers(auth_client),
        content_type='multipart/form-data',
    )

    assert rv.status_code == 200
    assert rv.get_json() == {
        'status': 'Import complete',
        'feeds': 2,
        'rules': 3,
    }
    manager.import_flexget_config.assert_called_once()


def test_rss_import_flexget_rejects_invalid_config(auth_client):
    manager = MagicMock()
    manager.import_flexget_config.side_effect = ValueError("parse detail")
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/import_flexget',
        data={'config': (io.BytesIO(b'not: valid'), 'flexget.yml')},
        headers=csrf_headers(auth_client),
        content_type='multipart/form-data',
    )

    assert rv.status_code == 400
    assert b"Invalid FlexGet configuration." in rv.data
    assert b"parse detail" not in rv.data


def test_rss_import_flexget_reports_import_failure(auth_client):
    manager = MagicMock()
    manager.import_flexget_config.side_effect = OSError("disk full")
    mock_app = MagicMock()
    mock_app.rss_panel.manager = manager
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/import_flexget',
        data={'config': (io.BytesIO(b'tasks: {}\n'), 'flexget.yml')},
        headers=csrf_headers(auth_client),
        content_type='multipart/form-data',
    )

    assert rv.status_code == 500
    assert b"Failed to import FlexGet configuration." in rv.data
    assert b"disk full" not in rv.data


def test_rss_import_flexget_requires_rss_context(auth_client):
    mock_app = MagicMock(spec=[])
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/rss/import_flexget',
        data={'config': (io.BytesIO(b'tasks: {}\n'), 'flexget.yml')},
        headers=csrf_headers(auth_client),
        content_type='multipart/form-data',
    )

    assert rv.status_code == 503
    assert b"Application context is unavailable." in rv.data


def test_remote_prefs_write_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.post(
            '/api/v2/app/remote_prefs',
            json={'max_downloads': 3},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_remote_prefs_write_requires_object_json(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/app/remote_prefs',
        json=['invalid'],
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Remote preferences object is required." in rv.data
    mock_client.set_app_preferences.assert_not_called()


def test_remote_prefs_write_hides_backend_errors(auth_client):
    mock_client = MagicMock()
    mock_client.set_app_preferences.side_effect = RuntimeError("secret backend detail")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/app/remote_prefs',
        json={'max_downloads': 3},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to update remote preferences." in rv.data
    assert b"secret backend detail" not in rv.data


def test_remote_prefs_write_persists_valid_object(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/app/remote_prefs',
        json={'max_downloads': 3},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    mock_client.set_app_preferences.assert_called_once_with({'max_downloads': 3})

def test_rss_feeds_requires_application_context(auth_client):
    mock_app = MagicMock(spec=[])
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.get('/api/v2/rss/feeds')

    assert rv.status_code == 503
    assert b"Application context is unavailable." in rv.data


def test_rss_rules_requires_application_context(auth_client):
    mock_app = MagicMock(spec=[])
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.get('/api/v2/rss/rules')

    assert rv.status_code == 503
    assert b"Application context is unavailable." in rv.data
