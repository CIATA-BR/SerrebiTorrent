# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized runtime subclasses for legacy components kept in main.py."""

from __future__ import annotations

import wx

import main as legacy
from main_ui_i18n import tr_main


_TRAY_PT_BR = {
    "Start All": "Iniciar todos",
    "Stop All": "Parar todos",
    "Current": "Atual",
    "Connection Manager...": "Gerenciador de conexões...",
    "Switch Profile": "Trocar perfil",
    "Local Session Settings...": "Configurações da sessão local...",
    "qBittorrent Remote Settings...": "Configurações remotas do qBittorrent...",
    "Transmission Remote Settings...": "Configurações remotas do Transmission...",
    "rTorrent Remote Settings...": "Configurações remotas do rTorrent...",
    "Settings": "Configurações",
    "Open {name}": "Abrir {name}",
    "Exit": "Sair",
}


def _language(frame):
    try:
        return frame._language()
    except Exception:
        try:
            return frame.config_manager.get_preferences().get("language", "system")
        except Exception:
            return "system"


def tr_runtime(text, language=None):
    translated = tr_main(text, language)
    if translated != text:
        return translated
    try:
        from main_ui_i18n import resolved_language

        if resolved_language(language) == "pt-BR":
            return _TRAY_PT_BR.get(text, text)
    except Exception:
        pass
    return text


def _set_column_text(control, index, label):
    try:
        column = control.GetColumn(index)
        column.SetText(label)
        control.SetColumn(index, column)
    except Exception:
        pass


class LocalizedFilesListCtrl(legacy.FilesListCtrl):
    def __init__(self, parent):
        super().__init__(parent)
        language = _language(parent.GetParent().GetParent()) if parent else "system"
        self._runtime_language = language
        self.SetName(tr_runtime("Files", language))
        for index, source in enumerate(("Name", "Size", "Progress", "Priority")):
            _set_column_text(self, index, tr_runtime(source, language))

    def OnGetItemText(self, item, col):
        text = super().OnGetItemText(item, col)
        if col == 3 and text in {"Skip", "Normal", "High"}:
            return tr_runtime(text, self._runtime_language)
        return text


class LocalizedPeersListCtrl(legacy.PeersListCtrl):
    def __init__(self, parent):
        super().__init__(parent)
        language = _language(parent.GetParent().GetParent()) if parent else "system"
        self.SetName(tr_runtime("Peers", language))
        for index, source in enumerate(("IP", "Client", "Progress", "Down Speed", "Up Speed")):
            _set_column_text(self, index, tr_runtime(source, language))


class LocalizedTrackersListCtrl(legacy.TrackersListCtrl):
    def __init__(self, parent):
        super().__init__(parent)
        language = _language(parent.GetParent().GetParent()) if parent else "system"
        self.SetName(tr_runtime("Trackers", language))
        for index, source in enumerate(("URL", "Status", "Peers", "Message")):
            _set_column_text(self, index, tr_runtime(source, language))


class LocalizedTorrentDetailsPanel(legacy.TorrentDetailsPanel):
    def __init__(self, parent, frame):
        super().__init__(parent, frame)
        language = _language(frame)
        self.notebook.SetPageText(0, tr_runtime("Files", language))
        self.notebook.SetPageText(1, tr_runtime("Peers", language))
        self.notebook.SetPageText(2, tr_runtime("Trackers", language))

    def on_files_context_menu(self, event):
        if not self.files_list.GetSelectedItemCount():
            return

        language = _language(self.frame)
        menu = wx.Menu()
        prio_menu = wx.Menu()
        high = prio_menu.Append(wx.ID_ANY, tr_runtime("High", language))
        normal = prio_menu.Append(wx.ID_ANY, tr_runtime("Normal", language))
        skip = prio_menu.Append(wx.ID_ANY, tr_runtime("Skip", language))
        menu.AppendSubMenu(prio_menu, tr_runtime("Priority", language))

        self.Bind(wx.EVT_MENU, lambda event: self.set_priority(2), high)
        self.Bind(wx.EVT_MENU, lambda event: self.set_priority(1), normal)
        self.Bind(wx.EVT_MENU, lambda event: self.set_priority(0), skip)
        try:
            self.PopupMenu(menu)
        finally:
            menu.Destroy()


class LocalizedTaskBarIcon(legacy.TaskBarIcon):
    def CreatePopupMenu(self):
        language = _language(self.frame)
        _ = lambda text: tr_runtime(text, language)
        menu = wx.Menu()

        start_all_item = menu.Append(wx.ID_ANY, _("Start All"))
        stop_all_item = menu.Append(wx.ID_ANY, _("Stop All"))
        self.Bind(wx.EVT_MENU, self.on_start_all, start_all_item)
        self.Bind(wx.EVT_MENU, self.on_stop_all, stop_all_item)

        switch_menu = wx.Menu()
        try:
            profiles = self.frame.config_manager.get_profiles() or {}
        except Exception:
            profiles = {}
        try:
            default_id = self.frame.config_manager.get_default_profile_id()
        except Exception:
            default_id = None
        current_id = getattr(self.frame, "current_profile_id", None)

        if profiles:
            def _sort_key(kv):
                pid, profile = kv
                return str(profile.get("name", pid)).lower()

            for pid, profile in sorted(profiles.items(), key=_sort_key):
                label = str(profile.get("name") or pid)
                if default_id and pid == default_id:
                    label += f" ({_('Default')})"
                if current_id and pid == current_id:
                    label += f" ({_('Current')})"
                item = switch_menu.Append(wx.ID_ANY, label, _("Connect to this profile"))
                self.Bind(
                    wx.EVT_MENU,
                    lambda event, pid=pid: self._on_switch_profile_pid(pid),
                    item,
                )
            switch_menu.AppendSeparator()

        manage_item = switch_menu.Append(
            wx.ID_ANY,
            _("Connection Manager..."),
            _("Add/edit/delete profiles and connect"),
        )
        self.Bind(wx.EVT_MENU, self.on_connection_manager, manage_item)
        menu.AppendSubMenu(switch_menu, _("Switch Profile"))

        menu.AppendSeparator()
        settings_menu = wx.Menu()
        try:
            local_settings_item = settings_menu.Append(
                wx.ID_PREFERENCES, _("Local Session Settings...")
            )
        except Exception:
            local_settings_item = settings_menu.Append(
                wx.ID_ANY, _("Local Session Settings...")
            )
        self.Bind(wx.EVT_MENU, self.on_local_settings, local_settings_item)
        settings_menu.AppendSeparator()

        qbit_settings_item = settings_menu.Append(
            wx.ID_ANY, _("qBittorrent Remote Settings...")
        )
        trans_settings_item = settings_menu.Append(
            wx.ID_ANY, _("Transmission Remote Settings...")
        )
        rtorrent_settings_item = settings_menu.Append(
            wx.ID_ANY, _("rTorrent Remote Settings...")
        )

        qbit_settings_item.Enable(
            isinstance(self.frame.client, legacy.QBittorrentClient) and self.frame.connected
        )
        trans_settings_item.Enable(
            isinstance(self.frame.client, legacy.TransmissionClient) and self.frame.connected
        )
        rtorrent_settings_item.Enable(
            isinstance(self.frame.client, legacy.RTorrentClient) and self.frame.connected
        )

        self.Bind(wx.EVT_MENU, self.on_remote_settings, qbit_settings_item)
        self.Bind(wx.EVT_MENU, self.on_remote_settings, trans_settings_item)
        self.Bind(wx.EVT_MENU, self.on_remote_settings, rtorrent_settings_item)
        menu.AppendSubMenu(settings_menu, _("Settings"))

        open_item = menu.Append(wx.ID_ANY, _("Open {name}").format(name=legacy.APP_NAME))
        self.Bind(wx.EVT_MENU, self.on_restore, open_item)
        menu.AppendSeparator()
        exit_item = menu.Append(wx.ID_EXIT, _("Exit"))
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        return menu
