# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized application entry point.

This keeps the legacy MainFrame logic intact while wiring the extracted,
tested localization/accessibility modules into the running application.
"""

from __future__ import annotations

import sys

import wx

import main as legacy
from connection_dialog import ConnectDialog
from main_ui_i18n import sidebar_label, tr_main
from preferences_dialog import PreferencesDialog


class LocalizedMainFrame(legacy.MainFrame):
    """Main frame with localized menus, sidebar and extracted dialogs."""

    def _language(self):
        return self.config_manager.get_preferences().get("language", "system")

    def _(self, text):
        return tr_main(text, self._language())

    def __init__(self):
        super().__init__()
        self._apply_localized_static_labels()

    def _apply_localized_static_labels(self):
        language = self._language()
        if hasattr(self, "sidebar"):
            self.sidebar.SetName(tr_main("Categories", language))
            for key, item_id in getattr(self, "cat_ids", {}).items():
                self.sidebar.SetItemText(item_id, sidebar_label(key, language=language))
            if hasattr(self, "trackers_root"):
                self.sidebar.SetItemText(self.trackers_root, tr_main("Trackers", language))
        if hasattr(self, "torrent_list"):
            self.torrent_list.SetName(tr_main("Torrent List", language))
        if hasattr(self, "statusbar") and not self.connected:
            self.statusbar.SetStatusText(tr_main("Disconnected", language), 0)

    def _build_menu_bar(self):
        """Build the existing menu structure with localized visible labels."""
        _ = self._
        menubar = wx.MenuBar()

        file_menu = wx.Menu()
        profiles = self.config_manager.get_profiles()
        self._connect_menu_id_to_profile = {}

        if profiles:
            connect_menu = wx.Menu()
            default_id = self.config_manager.get_default_profile_id()

            def _sort_key(kv):
                pid, profile = kv
                return str(profile.get("name", pid)).lower()

            for pid, profile in sorted(profiles.items(), key=_sort_key):
                label = str(profile.get("name") or pid)
                if default_id and pid == default_id:
                    label += f" ({_('Default')})"
                item = connect_menu.Append(wx.ID_ANY, label, "Connect to this profile")
                self._connect_menu_id_to_profile[item.GetId()] = pid
                self.Bind(wx.EVT_MENU, self.on_connect_profile_menu, item)

            connect_menu.AppendSeparator()
            manage_item = connect_menu.Append(
                wx.ID_ANY,
                _("Connection Manager...\tCtrl+Shift+C"),
                "Add/edit/delete profiles and connect",
            )
            self.Bind(wx.EVT_MENU, self.on_connect, manage_item)
            file_menu.AppendSubMenu(connect_menu, _("&Connect"), "Connect or switch profile")
        else:
            connect_item = file_menu.Append(
                wx.ID_ANY,
                _("&Connect...\tCtrl+Shift+C"),
                "Manage Profiles & Connect",
            )
            self.Bind(wx.EVT_MENU, self.on_connect, connect_item)

        add_file_item = file_menu.Append(
            wx.ID_ANY, _("&Add Torrent File...\tCtrl+O"), "Add a torrent from a local file")
        add_url_item = file_menu.Append(
            wx.ID_ANY, _("Add &URL/Magnet...\tCtrl+U"), "Add a torrent from a URL or Magnet link")
        create_torrent_item = file_menu.Append(
            wx.ID_ANY, _("Create &Torrent...\tCtrl+N"), "Create a .torrent file from a file or folder")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, _("E&xit"), "Exit application")
        menubar.Append(file_menu, _("&File"))

        actions_menu = wx.Menu()
        start_item = actions_menu.Append(wx.ID_ANY, _("&Start\tCtrl+S"), "Start selected torrents")
        pause_item = actions_menu.Append(wx.ID_ANY, _("&Pause\tCtrl+P"), "Pause selected torrents")
        resume_item = actions_menu.Append(wx.ID_ANY, _("&Resume\tCtrl+R"), "Resume selected torrents")
        actions_menu.AppendSeparator()
        recheck_item = actions_menu.Append(wx.ID_ANY, _("Force Re&check"), "Force a recheck/verification (if supported)")
        reannounce_item = actions_menu.Append(wx.ID_ANY, _("Force Reannoun&ce"), "Force an immediate tracker announce (if supported)")
        actions_menu.AppendSeparator()
        copy_hash_item = actions_menu.Append(wx.ID_ANY, _("Copy &Info Hash\tCtrl+I"), "Copy the info hash for selected torrents")
        copy_magnet_item = actions_menu.Append(wx.ID_ANY, _("Copy &Magnet Link\tCtrl+M"), "Copy a magnet link for selected torrents")
        open_folder_item = actions_menu.Append(wx.ID_ANY, _("Open Download &Folder"), "Open the download folder (if available)")
        actions_menu.AppendSeparator()
        remove_item = actions_menu.Append(wx.ID_ANY, _("&Remove\tDel"), "Remove selected torrents")
        remove_data_item = actions_menu.Append(wx.ID_ANY, _("Remove with &Data\tShift+Del"), "Remove selected torrents and data")
        select_all_item = actions_menu.Append(wx.ID_SELECTALL, _("Select &All\tCtrl+A"), "Select all torrents")
        menubar.Append(actions_menu, _("&Actions"))

        tools_menu = wx.Menu()
        search_item = tools_menu.Append(wx.ID_ANY, _("&Search for Torrents...\tCtrl+F"), "Search torrent indexers and add what you find")
        tools_menu.AppendSeparator()
        assoc_item = tools_menu.Append(wx.ID_ANY, _("Register &Associations"), "Associate .torrent and magnet links with this app")
        update_item = tools_menu.Append(wx.ID_ANY, _("Check for &Updates...\tF5"), "Check for updates")
        tools_menu.AppendSeparator()

        self.qbit_remote_prefs_item = tools_menu.Append(wx.ID_ANY, _("qBittorrent Remote &Settings..."), "Edit connected qBittorrent settings")
        self.trans_remote_prefs_item = tools_menu.Append(wx.ID_ANY, _("Transmission Remote &Settings..."), "Edit connected Transmission settings")
        self.rtorrent_remote_prefs_item = tools_menu.Append(wx.ID_ANY, _("rTorrent Remote &Settings..."), "Edit connected rTorrent settings")
        tools_menu.AppendSeparator()
        local_settings_item = tools_menu.Append(
            wx.ID_PREFERENCES,
            _("Local Session &Settings...\tCtrl+,"),
            "Configure local session and application settings",
        )

        self.qbit_remote_prefs_item.Enable(False)
        self.trans_remote_prefs_item.Enable(False)
        self.rtorrent_remote_prefs_item.Enable(False)
        menubar.Append(tools_menu, _("&Tools"))

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, _("&About SerrebiTorrent"), "About this application")
        menubar.Append(help_menu, _("&Help"))
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_add_file, add_file_item)
        self.Bind(wx.EVT_MENU, self.on_add_url, add_url_item)
        self.Bind(wx.EVT_MENU, self.on_create_torrent, create_torrent_item)
        self.Bind(wx.EVT_MENU, self.on_prefs, local_settings_item)
        self.Bind(wx.EVT_MENU, lambda event: self.Close(force=True), exit_item)

        self.Bind(wx.EVT_MENU, self.on_start, start_item)
        self.Bind(wx.EVT_MENU, self.on_pause, pause_item)
        self.Bind(wx.EVT_MENU, self.on_resume, resume_item)
        self.Bind(wx.EVT_MENU, self.on_recheck, recheck_item)
        self.Bind(wx.EVT_MENU, self.on_reannounce, reannounce_item)
        self.Bind(wx.EVT_MENU, self.on_copy_info_hash, copy_hash_item)
        self.Bind(wx.EVT_MENU, self.on_copy_magnet, copy_magnet_item)
        self.Bind(wx.EVT_MENU, self.on_open_download_folder, open_folder_item)
        self.Bind(wx.EVT_MENU, self.on_remove, remove_item)
        self.Bind(wx.EVT_MENU, self.on_remove_data, remove_data_item)
        self.Bind(wx.EVT_MENU, self.on_select_all, select_all_item)

        self.Bind(wx.EVT_MENU, self.on_search_torrents, search_item)
        self.Bind(wx.EVT_MENU, lambda event: legacy.register_associations(), assoc_item)
        self.Bind(wx.EVT_MENU, self.on_check_updates, update_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.qbit_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.trans_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.rtorrent_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

        self._update_remote_prefs_menu_state()
        accel_entries = [
            (wx.ACCEL_CTRL, ord("A"), select_all_item.GetId()),
            (wx.ACCEL_CTRL, ord("S"), start_item.GetId()),
            (wx.ACCEL_CTRL, ord("P"), pause_item.GetId()),
            (wx.ACCEL_CTRL, ord("R"), resume_item.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, remove_item.GetId()),
            (wx.ACCEL_SHIFT, wx.WXK_DELETE, remove_data_item.GetId()),
            (wx.ACCEL_CTRL, ord("O"), add_file_item.GetId()),
            (wx.ACCEL_CTRL, ord("U"), add_url_item.GetId()),
            (wx.ACCEL_CTRL, ord("N"), create_torrent_item.GetId()),
            (wx.ACCEL_CTRL, ord("I"), copy_hash_item.GetId()),
            (wx.ACCEL_CTRL, ord("M"), copy_magnet_item.GetId()),
            (wx.ACCEL_CTRL, ord(","), local_settings_item.GetId()),
            (wx.ACCEL_CTRL, ord("F"), search_item.GetId()),
        ]
        self.SetAcceleratorTable(wx.AcceleratorTable(accel_entries))

    def on_prefs(self, event):
        dlg = PreferencesDialog(self, self.config_manager)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            prefs = dlg.get_preferences()
            self.config_manager.set_preferences(prefs)
            try:
                legacy.SessionManager.get_instance().apply_preferences(prefs)
            except Exception as exc:  # noqa: BLE001 - UI boundary
                wx.LogError(f"Failed to apply settings: {exc}")
            self._update_client_default_save_path()
            self._update_web_ui()
            self._schedule_auto_update_check()

            interval = legacy.clamp_rss_interval(prefs.get("rss_update_interval", 300))
            self.rss_timer.Start(interval * 1000)

            if hasattr(self, "rss_panel"):
                self.rss_panel.manager.load()
                self.rss_panel.refresh_feeds_list()
                self.rss_panel.article_list.SetItemCount(0)
                self.rss_panel.current_articles = []

            self._build_menu_bar()
            self._apply_localized_static_labels()
        finally:
            dlg.Destroy()

    def on_connect(self, event):
        dlg = ConnectDialog(self, self.config_manager)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.connect_profile(dlg.selected_profile_id)
        finally:
            dlg.Destroy()
        self._build_menu_bar()

    def on_filter_change(self, event):
        """Keep canonical filter keys independent from translated sidebar labels."""
        item = event.GetItem()
        if not item.IsOk():
            return

        target_window = self.right_splitter
        if item == self.rss_id:
            target_window = self.rss_panel

        current_window = self.splitter.GetWindow2()
        if current_window != target_window:
            if current_window:
                self.splitter.ReplaceWindow(current_window, target_window)
                current_window.Hide()
            else:
                self.splitter.SplitVertically(self.sidebar, target_window, 220)
            target_window.Show()

        if item == self.rss_id:
            return

        for key, item_id in self.cat_ids.items():
            if item == item_id:
                self.current_filter = key
                self.refresh_data()
                return

        text = self.sidebar.GetItemText(item)
        if "(" in text:
            text = text.rsplit(" (", 1)[0]
        self.current_filter = text
        self.refresh_data()

    def _on_refresh_complete(
        self,
        generation,
        torrents,
        display_data,
        stats,
        tracker_counts,
        g_down,
        g_up,
    ):
        super()._on_refresh_complete(
            generation,
            torrents,
            display_data,
            stats,
            tracker_counts,
            g_down,
            g_up,
        )
        language = self._language()
        for key, item_id in self.cat_ids.items():
            self.sidebar.SetItemText(item_id, sidebar_label(key, stats.get(key, 0), language))
        self.sidebar.SetItemText(self.trackers_root, tr_main("Trackers", language))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        raise SystemExit(legacy.frozen_self_test(sys.argv[2]))

    try:
        print("Starting application...")
        app = wx.App(False)
        print("wx.App initialized.")

        name = f"SerrebiTorrent-{wx.GetUserId()}"
        checker = wx.SingleInstanceChecker(name)
        if checker.IsAnotherRunning():
            wx.MessageBox(
                "Another instance of SerrebiTorrent is already running.",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return 0

        legacy.updater.cleanup_update_artifacts()
        frame = LocalizedMainFrame()
        print("MainFrame initialized.")
        frame.Show()
        print("MainFrame shown. Entering MainLoop.")
        app.MainLoop()
        print("MainLoop exited.")
        return 0
    except Exception as exc:  # noqa: BLE001 - application boundary
        print(f"CRITICAL ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
