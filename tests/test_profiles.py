from __future__ import annotations

import pytest
from config_manager import ConfigManager
import config_manager


def _configure_paths(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    legacy_path = tmp_path / "legacy_config.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", str(config_path))
    monkeypatch.setattr(config_manager, "LEGACY_CONFIG_FILE", str(legacy_path))
    return config_path, legacy_path


def test_profiles_creates_default_profile(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)

    cm = ConfigManager()
    profiles = cm.get_profiles()
    assert isinstance(profiles, dict)
    assert profiles, "Default profile should be created automatically"

    default_id = cm.get_default_profile_id()
    assert default_id in profiles

    profile = profiles[default_id]
    assert profile.get("name") == "Local"
    assert profile.get("type") == "local"
    assert "url" in profile



def _credentialed_profile_url():
    return "https://" + "demo" + ":" + "pw" + "@example.test:8080"


def test_remote_profile_rejects_embedded_url_credentials(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    with pytest.raises(ValueError, match="must not contain embedded credentials"):
        cm.add_profile("Remote", "qbittorrent", _credentialed_profile_url(), "", "")


def test_local_profile_path_is_not_treated_as_url_credentials(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    pid = cm.add_profile("Local 2", "local", r"C:\\Downloads", "", "")

    assert cm.get_profile(pid)["url"] == r"C:\\Downloads"


def test_remote_profile_update_rejects_embedded_url_credentials(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()
    pid = cm.add_profile("Remote", "transmission", "http://example.test:9091", "demo", "pw")
    before = cm.get_profile(pid)

    with pytest.raises(ValueError, match="must not contain embedded credentials"):
        cm.update_profile(pid, "Remote", "transmission", _credentialed_profile_url(), "", "")

    assert cm.get_profile(pid) == before



@pytest.mark.parametrize(
    ("client_type", "url"),
    [
        ("qbittorrent", "ftp://example.test"),
        ("transmission", "scgi://example.test:5000"),
        ("rtorrent", "ftp://example.test"),
        ("qbittorrent", "https:///missing-host"),
    ],
)
def test_remote_profile_rejects_invalid_endpoint_scheme_or_host(tmp_path, monkeypatch, client_type, url):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    with pytest.raises(ValueError, match="Profile URL must use"):
        cm.add_profile("Remote", client_type, url, "", "")


@pytest.mark.parametrize(
    ("client_type", "url"),
    [
        ("qbittorrent", "https://example.test:8080"),
        ("transmission", "http://example.test:9091/transmission/rpc"),
        ("rtorrent", "scgi://example.test:5000"),
    ],
)
def test_remote_profile_accepts_supported_endpoint_schemes(tmp_path, monkeypatch, client_type, url):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    pid = cm.add_profile("Remote", client_type, url, "", "")

    assert cm.get_profile(pid)["url"] == url



def test_rtorrent_scgi_profile_requires_port(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    with pytest.raises(ValueError, match="SCGI profile URL must include a port"):
        cm.add_profile("rTorrent", "rtorrent", "scgi://example.test", "", "")


def test_rtorrent_scgi_profile_accepts_explicit_port(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)
    cm = ConfigManager()

    pid = cm.add_profile("rTorrent", "rtorrent", "scgi://example.test:5000", "", "")

    assert cm.get_profile(pid)["url"] == "scgi://example.test:5000"
