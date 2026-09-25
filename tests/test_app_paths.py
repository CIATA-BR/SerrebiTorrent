import os

import app_paths


def test_macos_user_data_base_dir_uses_application_support(monkeypatch):
    monkeypatch.setattr(app_paths.sys, "platform", "darwin")
    monkeypatch.setattr(app_paths.os.path, "expanduser", lambda value: "/Users/test")

    assert app_paths.get_user_data_base_dir() == os.path.join(
        "/Users/test", "Library", "Application Support"
    )


def test_linux_user_data_base_dir_still_honors_xdg(monkeypatch):
    monkeypatch.setattr(app_paths.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg-data")

    assert app_paths.get_user_data_base_dir() == "/tmp/xdg-data"


def test_macos_keeps_existing_legacy_data_dir(monkeypatch, tmp_path):
    (tmp_path / ".local" / "share" / app_paths.APP_DIR_NAME).mkdir(parents=True)
    monkeypatch.setattr(app_paths.sys, "platform", "darwin")
    monkeypatch.setattr(app_paths.os.path, "expanduser", lambda value: str(tmp_path))

    assert app_paths.get_user_data_base_dir() == os.path.join(str(tmp_path), ".local", "share")
