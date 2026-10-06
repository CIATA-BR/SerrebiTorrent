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
        "wx.ACCEL_CTRL | wx.ACCEL_SHIFT",
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



def test_download_completion_announcements_use_accessibility_event_without_stealing_focus():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "CompletionTracker" in source
    assert '"announce_download_complete", True' in source
    assert '"Download complete: {name}"' in source
    assert '"{count} downloads completed."' in source
    assert "legacy.notify_win_event(" in source
    assert "0x800C" in source
    assert "self.statusbar.SetName(message)" in source
    assert "self._completion_tracker.reset()" in source


def test_pause_on_completion_runs_client_action_in_background():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "def _pause_completed_background(" in source
    assert 'client.stop_torrent(event["hash"])' in source
    assert '"pause_on_download_complete", False' in source
    assert "self.thread_pool.submit(" in source
    assert "completion_events = self._completion_tracker.update_events(torrents)" in source


def test_watch_profile_switch_is_retryable_not_permanent_failure():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "watch_folder.RetryImportLater" in source


def test_localized_entry_point_can_clear_torrent_selection_without_moving_focus():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "def on_select_none(self, event):" in source
    assert "self.torrent_list.Select(index, False)" in source
    assert "_(\"Select &none\")" in source


def test_main_actions_expose_start_and_stop_all():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert '_("Start All")' in source
    assert '_("Stop All")' in source
    assert "self.start_all_torrents()" in source
    assert "self.stop_all_torrents()" in source
    assert "wx.ACCEL_CTRL | wx.ACCEL_ALT" in source
def test_desktop_torrent_name_filter_combines_with_existing_sidebar_filter():
    source = Path("app_entry.py").read_text(encoding="utf-8")

    assert 'self._name_filter_query = ""' in source
    assert "def on_filter_torrents_by_name(self, event):" in source
    assert "def on_clear_torrent_name_filter(self, event):" in source
    assert "filtered_display_data = display_data" in source
    assert 'torrent.get("name")' in source
    assert "casefold()" in source
    assert "filtered_display_data," in source
    assert 'ord("L")' in source
    assert "wx.ACCEL_CTRL | wx.ACCEL_SHIFT" in source
