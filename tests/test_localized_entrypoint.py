import importlib
import inspect
from pathlib import Path


def test_pyinstaller_packages_localized_entry_point():
    spec = Path("SerrebiTorrent.spec").read_text(encoding="utf-8")
    assert "['app_entry.py']" in spec
    assert "['main.py']" not in spec


def test_localized_entry_point_imports_without_starting_gui():
    module = importlib.import_module("app_entry")
    assert module.LocalizedMainFrame.__name__ == "LocalizedMainFrame"
    assert callable(module.main)


def test_import_keeps_legacy_mainframe_constructor_inspectable():
    import main

    source = inspect.getsource(main.MainFrame.__init__)
    assert "wx.EVT_LIST_ITEM_FOCUSED" in source
    assert "self._closing = False" in source


def test_localized_entry_point_uses_extracted_dialogs_and_subclass():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "class LocalizedMainFrame(legacy.MainFrame):" in source
    assert "from preferences_dialog import PreferencesDialog" in source
    assert "from connection_dialog import ConnectDialog" in source
    assert "frame = LocalizedMainFrame()" in source


def test_localized_entry_point_activates_extracted_torrent_list():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "from torrent_list import TorrentListCtrl as LocalizedTorrentListCtrl" in source
    assert "self._install_localized_torrent_list()" in source
    assert "new_list = LocalizedTorrentListCtrl(" in source
    assert "self.right_splitter.ReplaceWindow(old_list, new_list)" in source
    assert "self.torrent_list = new_list" in source


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


def test_translated_sidebar_does_not_become_filter_key():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "for key, item_id in self.cat_ids.items():" in source
    assert "self.current_filter = key" in source


def test_localized_entry_point_installs_external_catalogs_before_i18n_helpers():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    install = source.index("install_external_catalogs()")
    helpers = source.index("from main_ui_i18n import sidebar_label, tr_main")
    preferences = source.index("from preferences_dialog import PreferencesDialog")

    assert install < helpers
    assert install < preferences
