"""Connection/profile dialogs split out of main.py with localization support."""

from __future__ import annotations

import os

import wx

from i18n import translator


def _translator_for(config_manager):
    prefs = config_manager.get_preferences()
    return translator(prefs.get("language", "system"))


def profile_display_label(profile, *, is_default=False, translate=lambda text: text):
    label = str(profile.get("name") or "")
    if is_default:
        label += f" ({translate('Default')})"
    return label


class ProfileDialog(wx.Dialog):
    def __init__(self, parent, translate, profile=None):
        self._ = translate
        title = self._("Edit Profile") if profile else self._("Add Profile")
        super().__init__(parent, title=title)
        self.profile = profile

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label=self._("Profile Name:")), 0, wx.ALL, 5)
        self.name_input = wx.TextCtrl(self, value=profile["name"] if profile else "")
        self.name_input.SetName(self._("Profile Name"))
        sizer.Add(self.name_input, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(self, label=self._("Client Type:")), 0, wx.ALL, 5)
        self.type_input = wx.Choice(
            self, choices=["local", "rtorrent", "qbittorrent", "transmission"]
        )
        self.type_input.SetName(self._("Client Type"))
        self.type_input.Bind(wx.EVT_CHOICE, self.on_type_change)
        if profile:
            self.type_input.SetStringSelection(profile.get("type", "local"))
        else:
            self.type_input.SetSelection(0)
        sizer.Add(self.type_input, 0, wx.EXPAND | wx.ALL, 5)

        self.url_label = wx.StaticText(
            self, label=self._("URL (e.g. scgi://... or http://...):")
        )
        sizer.Add(self.url_label, 0, wx.ALL, 5)
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.url_input = wx.TextCtrl(self, value=profile["url"] if profile else "")
        self.url_input.SetName(self._("URL or download path"))
        url_sizer.Add(self.url_input, 1, wx.EXPAND | wx.RIGHT, 5)
        self.url_browse_btn = wx.Button(self, label=self._("Browse..."))
        self.url_browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_url_path)
        url_sizer.Add(self.url_browse_btn, 0)
        sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.user_label = wx.StaticText(self, label=self._("Username:"))
        sizer.Add(self.user_label, 0, wx.ALL, 5)
        self.user_input = wx.TextCtrl(self, value=profile["user"] if profile else "")
        self.user_input.SetName(self._("Username"))
        sizer.Add(self.user_input, 0, wx.EXPAND | wx.ALL, 5)

        self.pass_label = wx.StaticText(self, label=self._("Password:"))
        sizer.Add(self.pass_label, 0, wx.ALL, 5)
        self.pass_input = wx.TextCtrl(
            self,
            value=profile["password"] if profile else "",
            style=wx.TE_PASSWORD,
        )
        self.pass_input.SetName(self._("Password"))
        sizer.Add(self.pass_input, 0, wx.EXPAND | wx.ALL, 5)

        btns = wx.StdDialogButtonSizer()
        btns.AddButton(wx.Button(self, wx.ID_OK))
        btns.AddButton(wx.Button(self, wx.ID_CANCEL))
        btns.Realize()
        sizer.Add(btns, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(sizer)
        self.Fit()
        self.Center()
        self.on_type_change(None)

    def on_type_change(self, event):
        local = self.type_input.GetStringSelection() == "local"
        self.url_label.SetLabel(
            self._("Download Path:") if local else self._("URL (e.g. scgi://... or http://...):")
        )
        self.url_browse_btn.Show(local)
        self.user_input.Enable(not local)
        self.pass_input.Enable(not local)
        self.Layout()
        if event is not None:
            event.Skip()

    def on_browse_url_path(self, event):
        start = self.url_input.GetValue().strip()
        if not start or not os.path.isdir(start):
            start = os.path.expanduser("~")
        with wx.DirDialog(
            self,
            self._("Choose Download Folder"),
            start,
            style=wx.DD_DEFAULT_STYLE,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.url_input.SetValue(dlg.GetPath())

    def GetProfileData(self):
        return {
            "name": self.name_input.GetValue(),
            "type": self.type_input.GetStringSelection(),
            "url": self.url_input.GetValue(),
            "user": self.user_input.GetValue(),
            "password": self.pass_input.GetValue(),
        }


class ConnectDialog(wx.Dialog):
    def __init__(self, parent, config_manager):
        self.cm = config_manager
        self._ = _translator_for(config_manager)
        super().__init__(parent, title=self._("Connection Manager"), size=(560, 320))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_box = wx.ListBox(self, style=wx.LB_SINGLE)
        self.list_box.SetName(self._("Connection profiles"))
        self.list_box.SetHelpText(self._("Choose a profile, then connect or manage it with the buttons below."))
        sizer.Add(self.list_box, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self, label=self._("Add"))
        edit_btn = wx.Button(self, label=self._("Edit"))
        del_btn = wx.Button(self, label=self._("Delete"))
        set_def_btn = wx.Button(self, label=self._("Set Default"))
        connect_btn = wx.Button(self, label=self._("Connect"))
        close_btn = wx.Button(self, wx.ID_CANCEL, label=self._("Close"))

        add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        edit_btn.Bind(wx.EVT_BUTTON, self.on_edit)
        del_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        set_def_btn.Bind(wx.EVT_BUTTON, self.on_set_default)
        connect_btn.Bind(wx.EVT_BUTTON, self.on_connect)
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_CANCEL))

        for index, button in enumerate((add_btn, edit_btn, del_btn, set_def_btn, connect_btn, close_btn)):
            btn_sizer.Add(button, 0, wx.LEFT if index else 0, 8 if index else 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(sizer)
        self.Center()
        self.SetEscapeId(wx.ID_CANCEL)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        self.selected_profile_id = None
        self.refresh_list()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def refresh_list(self, select_pid=None):
        self.list_box.Clear()
        self.profiles_map = []
        profiles = self.cm.get_profiles()
        default_id = self.cm.get_default_profile_id()
        selection_idx = 0
        for pid, profile in profiles.items():
            idx = self.list_box.Append(
                profile_display_label(
                    profile,
                    is_default=(pid == default_id),
                    translate=self._,
                )
            )
            self.profiles_map.append(pid)
            if select_pid and pid == select_pid:
                selection_idx = idx
        if self.profiles_map:
            self.list_box.SetSelection(min(selection_idx, self.list_box.GetCount() - 1))

    def get_selected_id(self):
        sel = self.list_box.GetSelection()
        if sel != wx.NOT_FOUND and sel < len(self.profiles_map):
            return self.profiles_map[sel]
        return None

    def _show_profile_dialog(self, profile=None):
        dlg = ProfileDialog(self, self._, profile)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetProfileData()
            return None
        finally:
            dlg.Destroy()

    def _run_config_change(self, callback):
        try:
            result = callback()
            return True if result is None else result
        except Exception as exc:
            wx.MessageBox(
                str(exc),
                "SerrebiTorrent",
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return None

    def on_add(self, event):
        data = self._show_profile_dialog()
        if data:
            pid = self._run_config_change(
                lambda: self.cm.add_profile(
                    data["name"], data["type"], data["url"], data["user"], data["password"]
                )
            )
            if pid:
                self.refresh_list(select_pid=pid)

    def on_edit(self, event):
        pid = self.get_selected_id()
        if not pid:
            return
        data = self._show_profile_dialog(self.cm.get_profile(pid))
        if data:
            changed = self._run_config_change(
                lambda: self.cm.update_profile(
                    pid,
                    data["name"],
                    data["type"],
                    data["url"],
                    data["user"],
                    data["password"],
                )
            )
            if changed is not None:
                self.refresh_list(select_pid=pid)

    def on_delete(self, event):
        pid = self.get_selected_id()
        if pid and wx.MessageBox(
            self._("Delete this profile?"),
            self._("Confirm"),
            wx.YES_NO | wx.ICON_WARNING,
            self,
        ) == wx.YES:
            if self._run_config_change(lambda: self.cm.delete_profile(pid)) is not None:
                self.refresh_list()

    def on_set_default(self, event):
        pid = self.get_selected_id()
        if pid:
            if self._run_config_change(lambda: self.cm.set_default_profile_id(pid)) is not None:
                self.refresh_list(select_pid=pid)

    def on_connect(self, event):
        self.selected_profile_id = self.get_selected_id()
        if self.selected_profile_id:
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox(
                self._("Please select a profile to connect."),
                self._("Warning"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
