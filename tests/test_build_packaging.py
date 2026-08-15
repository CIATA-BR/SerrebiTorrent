from pathlib import Path

import pytest

from tools import audit_bundle, select_libtorrent_wheel


ROOT = Path(__file__).resolve().parents[1]


def test_spec_packages_native_libtorrent_without_broad_dependency_collection():
    spec = (ROOT / "SerrebiTorrent.spec").read_text(encoding="utf-8")

    assert "binaries = [(os.path.abspath(libtorrent_spec.origin), '.')]" in spec
    assert "hiddenimports=['libtorrent']" in spec
    assert "collect_submodules" not in spec
    assert "libcrypto-1_1" not in spec
    assert "libssl-3-x64.dll" not in spec


def test_build_tools_are_not_runtime_requirements():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    build = (ROOT / "requirements-build.txt").read_text(encoding="utf-8").lower()

    assert "pyinstaller" not in runtime
    assert "pywin32" not in runtime
    assert "pyinstaller" in build


def test_native_build_policy_uses_local_windows_ssh_linux_and_actions_macos():
    batch = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
    remote = (ROOT / "tools/build_linux_remote.ps1").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "%LOCALAPPDATA%\\Programs\\Python\\Launcher\\py.exe" in batch
    assert "root@serrebiradio.com" in remote
    assert "runs-on: macos-15" in workflow
    assert "windows-latest" not in workflow
    assert "ubuntu-latest" not in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_linux_bundle_strips_native_debug_symbols():
    spec = (ROOT / "SerrebiTorrent.spec").read_text(encoding="utf-8")

    assert "strip=sys.platform.startswith('linux')" in spec


def test_select_libtorrent_wheel_prefers_stable_version_then_stamp(tmp_path):
    names = [
        "libtorrent-2.0.14+20260815-cp314-cp314-win_amd64.whl",
        "libtorrent-2.1.1+20260814-cp314-cp314-win_amd64.whl",
        "libtorrent-2.1.1+20260816-cp314-cp314-win_amd64.whl",
        "libtorrent-2.2.0+20260816-cp313-cp313-win_amd64.whl",
    ]
    for name in names:
        (tmp_path / name).touch()

    path, version = select_libtorrent_wheel.select_wheel(
        tmp_path, "cp314", "win_amd64"
    )

    assert path.name == names[2]
    assert version == "2.1.1"


def test_bundle_audit_rejects_legacy_openssl_on_windows(tmp_path, monkeypatch):
    (tmp_path / "libtorrent.cp314-win_amd64.pyd").touch()
    (tmp_path / "libcrypto-1_1.dll").touch()
    monkeypatch.setattr(audit_bundle.sys, "platform", "win32")
    monkeypatch.setattr(
        audit_bundle.sys, "argv", ["audit_bundle.py", str(tmp_path)]
    )

    with pytest.raises(SystemExit, match="Legacy OpenSSL"):
        audit_bundle.main()


def test_bundle_audit_allows_dist_info_wheel_metadata(tmp_path, monkeypatch):
    (tmp_path / "libtorrent.cp314-win_amd64.pyd").touch()
    metadata = tmp_path / "flask-3.1.3.dist-info"
    metadata.mkdir()
    (metadata / "WHEEL").touch()
    monkeypatch.setattr(audit_bundle.sys, "platform", "win32")
    monkeypatch.setattr(
        audit_bundle.sys, "argv", ["audit_bundle.py", str(tmp_path)]
    )

    assert audit_bundle.main() == 0
