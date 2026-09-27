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



def test_writable_dir_rejects_paths_when_probe_cannot_be_removed(tmp_path, monkeypatch):
    original_remove = app_paths.os.remove

    def fail_probe_remove(path):
        if os.path.basename(path).startswith(".serrebitorrent-write-"):
            raise OSError("cannot remove")
        return original_remove(path)

    monkeypatch.setattr(app_paths.os, "remove", fail_probe_remove)

    assert app_paths._is_writable_dir(str(tmp_path)) is False


def test_writable_dir_does_not_clobber_fixed_probe_name(tmp_path):
    existing = tmp_path / ".write_test"
    existing.write_text("keep-me", encoding="utf-8")

    assert app_paths._is_writable_dir(str(tmp_path)) is True
    assert existing.read_text(encoding="utf-8") == "keep-me"



def test_restrict_dir_permissions_uses_owner_only_mode_on_posix(monkeypatch):
    chmod = []
    monkeypatch.setattr(app_paths.os, "name", "posix", raising=False)
    monkeypatch.setattr(app_paths.os, "chmod", lambda path, mode: chmod.append((path, mode)))

    app_paths._restrict_dir_permissions("/tmp/private")

    assert chmod == [("/tmp/private", 0o700)]


def test_ensure_dir_applies_private_permissions(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(app_paths, "_restrict_dir_permissions", lambda path: calls.append(path))
    target = tmp_path / "state"

    result = app_paths.ensure_dir(str(target))

    assert result == str(target)
    assert target.is_dir()
    assert calls == [str(target)]
