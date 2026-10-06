# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized application entry point.

This keeps the legacy MainFrame logic intact while wiring the extracted,
tested localization/accessibility modules into the running application.
"""

from __future__ import annotations

import sys

import wx
import wx.adv

from external_catalog_runtime import install_external_catalogs

# External PO catalogs must be registered before localized modules import
# normalize_language/translation helpers into their own module namespaces.
install_external_catalogs()

import main as legacy
import watch_folder
from completion_notifications import CompletionTracker
from add_torrent_dialog import AddTorrentDialog as LocalizedAddTorrentDialog
from connection_dialog import ConnectDialog
from main_ui_i18n import sidebar_label, tr_main
from preferences_dialog import PreferencesDialog
from runtime_actions_i18n import register_associations
from torrent_list import TorrentListCtrl as LocalizedTorrentListCtrl

# The legacy handlers resolve AddTorrentDialog from main.py at call time. Point
# that name at the localized implementation without editing the maintainer's
# reviewed main.py.
legacy.AddTorrentDialog = LocalizedAddTorrentDialog


class LocalizedMainFrame(legacy.MainFrame):
    """Main frame with localized menus, sidebar and extracted dialogs."""

    def _language(self):
        return self.config_manager.get_preferences().get("language", "system")

    def _(self, text):
        return tr_main(text, self._language())

    def __init__(self):
        self._completion_tracker = CompletionTracker()
        self._name_filter_query = ""
        super().__init__()
        self._install_localized_torrent_list()
        self._apply_localized_static_labels()
        self._watch_scan_busy = False
        self.watch_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_watch_timer, self.watch_timer)
        self.watch_timer.Start(watch_folder.SCAN_INTERVAL_SECONDS * 1000)

    def on_watch_timer(self, event):
        folder = watch_folder.clean_folder_path(self.config_manager.get_preferences().get("watch_folder"))
        if not folder or not self.client or self._watch_scan_busy or self._closing:
            return
        self._watch_scan_busy = True
        try:
            self.thread_pool.submit(
                self._watch_scan_background, self.client, self.client_generation, folder)
        except RuntimeError:
            # A busy flag left set here would stop every later scan.
            self._watch_scan_busy = False

    def _watch_scan_background(self, client, generation, folder):
        hashes = []

        def add(data):
            if generation != self.client_generation:
                raise watch_folder.RetryImportLater(self._("The active profile changed."))
            client.add_torrent_file(data, None, None)
            hash_hint = self._maybe_hash_from_torrent_bytes(data)
            if hash_hint:
                hashes.append(hash_hint)

        added, failed = [], []
        try:
            added, failed = watch_folder.import_folder(folder, add)
            if hashes and self.config_manager.get_preferences().get("auto_start", True):
                self._auto_start_hashes(generation, hashes)
        finally:
            wx.CallAfter(self._on_watch_scan_done, added, failed)

    def _on_watch_scan_done(self, added, failed):
        self._watch_scan_busy = False
        if self._closing or not (added or failed):
            return
        # Errors go to the status bar, not a dialog: this runs every minute
        # unattended, and a broken file is renamed to .failed so it stops.
        if failed:
            message = self._("Watch folder: added {added}, failed {failed} ({name}: {error})").format(
                added=len(added), failed=len(failed), name=failed[0][0], error=failed[0][1])
        else:
            message = self._("Watch folder: added {count} torrent(s)").format(count=len(added))
        self.statusbar.SetStatusText(message, 0)
        self.refresh_data()

    def _install_localized_torrent_list(self):
        """Replace the empty legacy list before deferred auto-connect can populate it."""
        old_list = self.torrent_list
        new_list = LocalizedTorrentListCtrl(
            self.right_splitter,
            language=self._language(),
        )
        new_list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)
        new_list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        new_list.Bind(wx.EVT_RIGHT_DOWN, self.on_context_menu)
        new_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_torrent_selected)
        new_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_torrent_selected)
        new_list.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_torrent_selected)

        # A new child goes last in Tab order; keep the list before the details panel.
        new_list.MoveBeforeInTabOrder(old_list)
        self.right_splitter.ReplaceWindow(old_list, new_list)
        old_list.Hide()
        self.torrent_list = new_list
        new_list.Show()
        old_list.Destroy()
        self.right_splitter.Layout()

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
                item = connect_menu.Append(wx.ID_ANY, label, _("Connect to this profile"))
                self._connect_menu_id_to_profile[item.GetId()] = pid
                self.Bind(wx.EVT_MENU, self.on_connect_profile_menu, item)

            connect_menu.AppendSeparator()
            manage_item = connect_menu.Append(
                wx.ID_ANY,
                _("Connection Manager...\tCtrl+Shift+C"),
                _("Add/edit/delete profiles and connect"),
            )
            self.Bind(wx.EVT_MENU, self.on_connect, manage_item)
            file_menu.AppendSubMenu(connect_menu, _("&Connect"), _("Connect or switch profile"))
        else:
            connect_item = file_menu.Append(
                wx.ID_ANY,
                _("&Connect...\tCtrl+Shift+C"),
                _("Manage Profiles & Connect"),
            )
            self.Bind(wx.EVT_MENU, self.on_connect, connect_item)

        add_file_item = file_menu.Append(
            wx.ID_ANY,
            _("&Add Torrent File...\tCtrl+O"),
            _("Add a torrent from a local file"),
        )
        add_url_item = file_menu.Append(
            wx.ID_ANY,
            _("Add &URL/Magnet...\tCtrl+U"),
            _("Add a torrent from a URL or Magnet link"),
        )
        create_torrent_item = file_menu.Append(
            wx.ID_ANY,
            _("Create &Torrent...\tCtrl+N"),
            _("Create a .torrent file from a file or folder"),
        )
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, _("E&xit"), _("Exit application"))
        menubar.Append(file_menu, _("&File"))

        actions_menu = wx.Menu()
        start_item = actions_menu.Append(
            wx.ID_ANY, _("&Start\tCtrl+S"), _("Start selected torrents")
        )
        pause_item = actions_menu.Append(
            wx.ID_ANY, _("&Pause\tCtrl+P"), _("Pause selected torrents")
        )
        resume_item = actions_menu.Append(
            wx.ID_ANY, _("&Resume\tCtrl+R"), _("Resume selected torrents")
        )
        start_all_item = actions_menu.Append(wx.ID_ANY, _("Start All"))
        stop_all_item = actions_menu.Append(wx.ID_ANY, _("Stop All"))
        actions_menu.AppendSeparator()
        recheck_item = actions_menu.Append(
            wx.ID_ANY,
            _("Force Re&check"),
            _("Force a recheck/verification (if supported)"),
        )
        reannounce_item = actions_menu.Append(
            wx.ID_ANY,
            _("Force Reannoun&ce"),
            _("Force an immediate tracker announce (if supported)"),
        )
        queue_menu = wx.Menu()
        queue_top_item = queue_menu.Append(
            wx.ID_ANY,
            _("Move to &top\tCtrl+Alt+Home"),
            _("Move selected torrents to the top of the queue"),
        )
        queue_up_item = queue_menu.Append(
            wx.ID_ANY,
            _("Move &up\tCtrl+Alt+Up"),
            _("Move selected torrents up in the queue"),
        )
        queue_down_item = queue_menu.Append(
            wx.ID_ANY,
            _("Move &down\tCtrl+Alt+Down"),
            _("Move selected torrents down in the queue"),
        )
        queue_bottom_item = queue_menu.Append(
            wx.ID_ANY,
            _("Move to &bottom\tCtrl+Alt+End"),
            _("Move selected torrents to the bottom of the queue"),
        )
        actions_menu.AppendSubMenu(
            queue_menu,
            _("Queue"),
            _("Change selected torrent queue position"),
        )
        actions_menu.AppendSeparator()
        copy_hash_item = actions_menu.Append(
            wx.ID_ANY,
            _("Copy &Info Hash\tCtrl+I"),
            _("Copy the info hash for selected torrents"),
        )
        copy_magnet_item = actions_menu.Append(
            wx.ID_ANY,
            _("Copy &Magnet Link\tCtrl+M"),
            _("Copy a magnet link for selected torrents"),
        )
        open_folder_item = actions_menu.Append(
            wx.ID_ANY,
            _("Open Download &Folder"),
            _("Open the download folder (if available)"),
        )
        actions_menu.AppendSeparator()
        remove_item = actions_menu.Append(
            wx.ID_ANY, _("&Remove\tDel"), _("Remove selected torrents")
        )
        remove_data_item = actions_menu.Append(
            wx.ID_ANY,
            _("Remove with &Data\tShift+Del"),
            _("Remove selected torrents and data"),
        )
        select_all_item = actions_menu.Append(
            wx.ID_SELECTALL,
            _("Select &All\tCtrl+A"),
            _("Select all torrents"),
        )
        select_none_item = actions_menu.Append(
            wx.ID_ANY,
            _("Select &none"),
        )
        menubar.Append(actions_menu, _("&Actions"))

        tools_menu = wx.Menu()
        search_item = tools_menu.Append(
            wx.ID_ANY,
            _("&Search for Torrents...\tCtrl+F"),
            _("Search torrent indexers and add what you find"),
        )
        filter_name_item = tools_menu.Append(
            wx.ID_ANY,
            _("Filter torrent list by &name...\tCtrl+L"),
            _("Filter the current torrent list by name"),
        )
        clear_name_filter_item = tools_menu.Append(
            wx.ID_ANY,
            _("Clear torrent name filter\tCtrl+Shift+L"),
            _("Show all torrents allowed by the current sidebar filter"),
        )
        tools_menu.AppendSeparator()
        assoc_item = tools_menu.Append(
            wx.ID_ANY,
            _("Register &Associations"),
            _("Associate .torrent and magnet links with this app"),
        )
        update_item = tools_menu.Append(
            wx.ID_ANY,
            _("Check for &Updates...\tF5"),
            _("Check for updates"),
        )
        tools_menu.AppendSeparator()

        self.qbit_remote_prefs_item = tools_menu.Append(
            wx.ID_ANY,
            _("qBittorrent Remote &Settings..."),
            _("Edit connected qBittorrent settings"),
        )
        self.trans_remote_prefs_item = tools_menu.Append(
            wx.ID_ANY,
            _("Transmission Remote &Settings..."),
            _("Edit connected Transmission settings"),
        )
        self.rtorrent_remote_prefs_item = tools_menu.Append(
            wx.ID_ANY,
            _("rTorrent Remote &Settings..."),
            _("Edit connected rTorrent settings"),
        )
        tools_menu.AppendSeparator()
        local_settings_item = tools_menu.Append(
            wx.ID_PREFERENCES,
            _("Local Session &Settings...\tCtrl+,"),
            _("Configure local session and application settings"),
        )

        self.qbit_remote_prefs_item.Enable(False)
        self.trans_remote_prefs_item.Enable(False)
        self.rtorrent_remote_prefs_item.Enable(False)
        menubar.Append(tools_menu, _("&Tools"))

        help_menu = wx.Menu()
        about_item = help_menu.Append(
            wx.ID_ABOUT, _("&About SerrebiTorrent"), _("About this application")
        )
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
        self.Bind(wx.EVT_MENU, lambda event: self.start_all_torrents(), start_all_item)
        self.Bind(wx.EVT_MENU, lambda event: self.stop_all_torrents(), stop_all_item)
        self.Bind(wx.EVT_MENU, self.on_recheck, recheck_item)
        self.Bind(wx.EVT_MENU, self.on_reannounce, reannounce_item)
        self.Bind(wx.EVT_MENU, self.on_queue_top, queue_top_item)
        self.Bind(wx.EVT_MENU, self.on_queue_up, queue_up_item)
        self.Bind(wx.EVT_MENU, self.on_queue_down, queue_down_item)
        self.Bind(wx.EVT_MENU, self.on_queue_bottom, queue_bottom_item)
        self.Bind(wx.EVT_MENU, self.on_copy_info_hash, copy_hash_item)
        self.Bind(wx.EVT_MENU, self.on_copy_magnet, copy_magnet_item)
        self.Bind(wx.EVT_MENU, self.on_open_download_folder, open_folder_item)
        self.Bind(wx.EVT_MENU, self.on_remove, remove_item)
        self.Bind(wx.EVT_MENU, self.on_remove_data, remove_data_item)
        self.Bind(wx.EVT_MENU, self.on_select_all, select_all_item)
        self.Bind(wx.EVT_MENU, self.on_select_none, select_none_item)

        self.Bind(wx.EVT_MENU, self.on_search_torrents, search_item)
        self.Bind(wx.EVT_MENU, self.on_filter_torrents_by_name, filter_name_item)
        self.Bind(wx.EVT_MENU, self.on_clear_torrent_name_filter, clear_name_filter_item)
        self.Bind(
            wx.EVT_MENU,
            lambda event: register_associations(self._language()),
            assoc_item,
        )
        self.Bind(wx.EVT_MENU, self.on_check_updates, update_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.qbit_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.trans_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_remote_preferences, self.rtorrent_remote_prefs_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

        self._update_remote_prefs_menu_state()
        accel_entries = [
            (wx.ACCEL_CTRL, ord("A"), select_all_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("A"), select_none_item.GetId()),
            (wx.ACCEL_CTRL, ord("S"), start_item.GetId()),
            (wx.ACCEL_CTRL, ord("P"), pause_item.GetId()),
            (wx.ACCEL_CTRL, ord("R"), resume_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, ord("S"), start_all_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, ord("P"), stop_all_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_HOME, queue_top_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_UP, queue_up_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_DOWN, queue_down_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_END, queue_bottom_item.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, remove_item.GetId()),
            (wx.ACCEL_SHIFT, wx.WXK_DELETE, remove_data_item.GetId()),
            (wx.ACCEL_CTRL, ord("O"), add_file_item.GetId()),
            (wx.ACCEL_CTRL, ord("U"), add_url_item.GetId()),
            (wx.ACCEL_CTRL, ord("N"), create_torrent_item.GetId()),
            (wx.ACCEL_CTRL, ord("I"), copy_hash_item.GetId()),
            (wx.ACCEL_CTRL, ord("M"), copy_magnet_item.GetId()),
            (wx.ACCEL_CTRL, ord(","), local_settings_item.GetId()),
            (wx.ACCEL_CTRL, ord("F"), search_item.GetId()),
            (wx.ACCEL_CTRL, ord("L"), filter_name_item.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("L"), clear_name_filter_item.GetId()),
        ]
        self.SetAcceleratorTable(wx.AcceleratorTable(accel_entries))

    def on_select_none(self, event):
        count = self.torrent_list.GetItemCount()
        for index in range(count):
            self.torrent_list.Select(index, False)

    def on_filter_torrents_by_name(self, event):
        dialog = wx.TextEntryDialog(
            self,
            self._("Filter torrent list by name:"),
            self._("Filter Torrents"),
            self._name_filter_query,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self._name_filter_query = dialog.GetValue().strip()
        finally:
            dialog.Destroy()

        self.refresh_data()
        if hasattr(self, "statusbar"):
            if self._name_filter_query:
                self.statusbar.SetStatusText(
                    self._("Torrent name filter: {query}").format(
                        query=self._name_filter_query
                    ),
                    0,
                )
            else:
                self.statusbar.SetStatusText(self._("Torrent name filter cleared."), 0)

    def on_clear_torrent_name_filter(self, event):
        if not self._name_filter_query:
            return
        self._name_filter_query = ""
        self.refresh_data()
        if hasattr(self, "statusbar"):
            self.statusbar.SetStatusText(self._("Torrent name filter cleared."), 0)

    def _run_queue_action(self, method_name, progress_message, success_message):
        if not self.client:
            self.statusbar.SetStatusText(self._("Not connected to any client."), 0)
            return
        if not getattr(self.client, "supports_queue_reordering", False):
            self.statusbar.SetStatusText(
                self._("Queue reordering is not supported by this client."),
                0,
            )
            return

        hashes = self.torrent_list.get_selected_hashes()
        if not hashes:
            self.statusbar.SetStatusText(self._("No torrents selected."), 0)
            return

        action = getattr(self.client, method_name)
        generation = self.client_generation
        self.statusbar.SetStatusText(self._(progress_message), 0)
        self.thread_pool.submit(
            self._queue_action_background,
            action,
            hashes,
            generation,
            self._(success_message),
            self._("Queue action completed with {failed} failure(s). Last error: {error}"),
            self._("Queue action failed: {error}"),
        )

    def _queue_action_background(
        self,
        action,
        hashes,
        generation,
        success_message,
        partial_template,
        failure_template,
    ):
        failed = 0
        last_error = None
        for torrent_hash in hashes:
            if generation != self.client_generation or self._closing:
                return
            try:
                action(torrent_hash)
            except Exception as exc:  # noqa: BLE001 - remote client boundary
                failed += 1
                last_error = exc

        if generation != self.client_generation or self._closing:
            return
        if failed == 0:
            wx.CallAfter(self._on_action_complete, success_message)
        elif failed < len(hashes):
            wx.CallAfter(
                self.statusbar.SetStatusText,
                partial_template.format(failed=failed, error=last_error),
                0,
            )
            wx.CallAfter(self.refresh_data)
        else:
            wx.CallAfter(
                self._on_action_error,
                failure_template.format(error=last_error),
            )

    def on_queue_top(self, event):
        self._run_queue_action(
            "queue_top",
            "Moving selected torrents to the top of the queue...",
            "Selected torrents moved to the top of the queue.",
        )

    def on_queue_up(self, event):
        self._run_queue_action(
            "queue_up",
            "Moving selected torrents up in the queue...",
            "Selected torrents moved up in the queue.",
        )

    def on_queue_down(self, event):
        self._run_queue_action(
            "queue_down",
            "Moving selected torrents down in the queue...",
            "Selected torrents moved down in the queue.",
        )

    def on_queue_bottom(self, event):
        self._run_queue_action(
            "queue_bottom",
            "Moving selected torrents to the bottom of the queue...",
            "Selected torrents moved to the bottom of the queue.",
        )

    def on_prefs(self, event):
        dlg = PreferencesDialog(self, self.config_manager)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            previous_prefs = self.config_manager.get_preferences()
            prefs = dlg.get_preferences()
            try:
                self.config_manager.set_preferences(prefs)
            except Exception as exc:  # noqa: BLE001 - UI boundary
                wx.MessageBox(
                    self._("Failed to apply settings: {error}").format(error=exc),
                    "SerrebiTorrent",
                    wx.OK | wx.ICON_ERROR,
                    self,
                )
                return
            session = legacy.SessionManager.get_instance()
            try:
                session.apply_preferences(prefs)
            except Exception as exc:  # noqa: BLE001 - UI boundary
                try:
                    self.config_manager.set_preferences(previous_prefs)
                except Exception:
                    pass
                try:
                    session.apply_preferences(previous_prefs)
                except Exception:
                    pass
                wx.MessageBox(
                    self._("Failed to apply settings: {error}").format(error=exc),
                    "SerrebiTorrent",
                    wx.OK | wx.ICON_ERROR,
                    self,
                )
                return
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

    def connect_profile(self, pid):
        profile = self.config_manager.get_profile(pid)
        if not profile:
            return
        self._completion_tracker.reset()
        super().connect_profile(pid)
        if hasattr(self, "statusbar") and not self.connected:
            self.statusbar.SetStatusText(self._("Connecting..."), 0)

    def _on_connect_complete(self, generation, profile, client, error):
        super()._on_connect_complete(generation, profile, client, error)
        if generation != self.client_generation or not hasattr(self, "statusbar"):
            return
        if error or not client:
            self.statusbar.SetStatusText(self._("Connection Failed"), 0)
            return
        message = self._("Connected to {name}").format(
            name=profile.get("name", self._("Profile"))
        )
        if profile.get("type") != "local":
            message += f" ({self._('Local session active')})"
        self.statusbar.SetStatusText(message, 0)

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

    def on_context_menu(self, event):
        self._prepare_torrent_context_menu_target(event)
        menu = wx.Menu()

        start = menu.Append(wx.ID_ANY, self._("Start"))
        pause = menu.Append(wx.ID_ANY, self._("Pause"))
        resume = menu.Append(wx.ID_ANY, self._("Resume"))
        menu.AppendSeparator()
        recheck = menu.Append(wx.ID_ANY, self._("Force Recheck"))
        reannounce = menu.Append(wx.ID_ANY, self._("Force Reannounce"))
        queue_menu = wx.Menu()
        queue_top = queue_menu.Append(wx.ID_ANY, self._("Move to top"))
        queue_up = queue_menu.Append(wx.ID_ANY, self._("Move up"))
        queue_down = queue_menu.Append(wx.ID_ANY, self._("Move down"))
        queue_bottom = queue_menu.Append(wx.ID_ANY, self._("Move to bottom"))
        menu.AppendSubMenu(queue_menu, self._("Queue"))
        menu.AppendSeparator()
        copy_hash = menu.Append(wx.ID_ANY, self._("Copy Info Hash"))
        copy_magnet = menu.Append(wx.ID_ANY, self._("Copy Magnet Link"))
        open_folder = menu.Append(wx.ID_ANY, self._("Open Download Folder"))
        menu.AppendSeparator()
        remove = menu.Append(wx.ID_ANY, self._("Remove"))
        remove_data = menu.Append(wx.ID_ANY, self._("Remove with Data"))

        self.Bind(wx.EVT_MENU, self.on_start, start)
        self.Bind(wx.EVT_MENU, self.on_pause, pause)
        self.Bind(wx.EVT_MENU, self.on_resume, resume)
        self.Bind(wx.EVT_MENU, self.on_recheck, recheck)
        self.Bind(wx.EVT_MENU, self.on_reannounce, reannounce)
        self.Bind(wx.EVT_MENU, self.on_queue_top, queue_top)
        self.Bind(wx.EVT_MENU, self.on_queue_up, queue_up)
        self.Bind(wx.EVT_MENU, self.on_queue_down, queue_down)
        self.Bind(wx.EVT_MENU, self.on_queue_bottom, queue_bottom)
        self.Bind(wx.EVT_MENU, self.on_copy_info_hash, copy_hash)
        self.Bind(wx.EVT_MENU, self.on_copy_magnet, copy_magnet)
        self.Bind(wx.EVT_MENU, self.on_open_download_folder, open_folder)
        self.Bind(wx.EVT_MENU, self.on_remove, remove)
        self.Bind(wx.EVT_MENU, self.on_remove_data, remove_data)

        try:
            self.PopupMenu(menu)
        finally:
            menu.Destroy()

    def on_about(self, event):
        from app_version import APP_VERSION

        info = wx.adv.AboutDialogInfo()
        info.SetName("SerrebiTorrent")
        info.SetVersion(APP_VERSION)
        info.SetDescription(
            self._(
                "A Windows desktop torrent manager designed for keyboard-first use and screen readers."
            )
        )
        info.SetCopyright("Copyright © 2025-2026 serrebidev and contributors")
        info.SetWebSite("https://github.com/serrebidev/SerrebiTorrent")
        info.AddDeveloper("serrebidev")
        wx.adv.AboutBox(info)

    def _restore_statusbar_accessible_name(self, announced_name, original_name):
        if self._closing or not hasattr(self, "statusbar"):
            return
        if self.statusbar.GetName() == announced_name:
            self.statusbar.SetName(original_name)

    def _announce_download_completion(self, completed):
        if not hasattr(self, "statusbar"):
            return
        if len(completed) == 1:
            message = self._("Download complete: {name}").format(name=completed[0])
        else:
            message = self._("{count} downloads completed.").format(count=len(completed))

        self.statusbar.SetStatusText(message, 0)
        original_name = self.statusbar.GetName()
        self.statusbar.SetName(message)
        legacy.notify_win_event(
            0x800C,  # EVENT_OBJECT_NAMECHANGE
            self.statusbar.GetHandle(),
            legacy.OBJID_CLIENT,
            0,
        )
        wx.CallLater(
            1500,
            self._restore_statusbar_accessible_name,
            message,
            original_name,
        )

    def _pause_completed_background(self, client, generation, completed_events):
        if generation != self.client_generation or self._closing:
            return

        failures = []
        for event in completed_events:
            if generation != self.client_generation or self._closing:
                return
            try:
                client.stop_torrent(event["hash"])
            except Exception as exc:  # noqa: BLE001 - client boundary
                failures.append((event["name"], exc))

        if generation != self.client_generation or self._closing:
            return

        if failures:
            name, error = failures[0]
            wx.CallAfter(
                self.statusbar.SetStatusText,
                self._("Failed to pause completed torrent {name}: {error}").format(
                    name=name,
                    error=error,
                ),
                0,
            )
        wx.CallAfter(self.refresh_data)

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
        filtered_display_data = display_data
        query = self._name_filter_query.strip().casefold()
        if query:
            filtered_display_data = [
                torrent
                for torrent in display_data
                if query in str(torrent.get("name") or "").casefold()
            ]

        super()._on_refresh_complete(
            generation,
            torrents,
            filtered_display_data,
            stats,
            tracker_counts,
            g_down,
            g_up,
        )
        if (
            self._closing
            or generation != self.client_generation
            or not self.connected
        ):
            return

        completion_events = self._completion_tracker.update_events(torrents)
        completed = [event["name"] for event in completion_events]
        preferences = self.config_manager.get_preferences()
        if completed and preferences.get("announce_download_complete", True):
            self._announce_download_completion(completed)

        if completion_events and preferences.get("pause_on_download_complete", False):
            try:
                self.thread_pool.submit(
                    self._pause_completed_background,
                    self.client,
                    generation,
                    completion_events,
                )
            except RuntimeError:
                pass

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
                tr_main("Another instance of SerrebiTorrent is already running.", "system"),
                tr_main("Error", "system"),
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
