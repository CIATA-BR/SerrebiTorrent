from pathlib import Path


def test_pyinstaller_packages_localized_entry_point():
    spec = Path("SerrebiTorrent.spec").read_text(encoding="utf-8")
    assert "['app_entry.py']" in spec
    assert "['main.py']" not in spec


def test_localized_entry_point_uses_extracted_dialogs_and_subclass():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "class LocalizedMainFrame(legacy.MainFrame):" in source
    assert "from preferences_dialog import PreferencesDialog" in source
    assert "from connection_dialog import ConnectDialog" in source
    assert "frame = LocalizedMainFrame()" in source


def test_localized_entry_point_preserves_keyboard_accelerators():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    for accelerator in (
        "ord(\"A\")",
        "ord(\"S\")",
        "ord(\"P\")",
        "ord(\"R\")",
        "wx.WXK_DELETE",
        "ord(\"O\")",
        "ord(\"U\")",
        "ord(\"N\")",
        "ord(\"I\")",
        "ord(\"M\")",
        "ord(\",\")",
        "ord(\"F\")",
    ):
        assert accelerator in source
