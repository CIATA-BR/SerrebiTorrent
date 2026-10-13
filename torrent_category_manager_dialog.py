# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Accessible profile-scoped torrent category manager."""

from __future__ import annotations

import wx


class TorrentCategoryManagerDialog(wx.Dialog):
    def __init__(self, parent, store, profile_id, translate):
        super().__init__(
            parent, title=translate("Manage Torrent Categories"), size=(650, 420)
        )
        self.store = store
        self.profile_id = profile_id
        self._ = translate
        self.operations = []

        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        label = self._("Categories in this profile:")
        layout.Add(wx.StaticText(panel, label=label), 0, wx.ALL, 8)
        self.category_list = wx.ListBox(panel)
        self.category_list.SetName(label)
        layout.Add(self.category_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        rename = wx.Button(panel, label=self._("Rename Category..."))
        rename.Bind(wx.EVT_BUTTON, self.on_rename)
        buttons.Add(rename, 0, wx.RIGHT, 8)

        remove = wx.Button(panel, label=self._("Remove Category..."))
        remove.Bind(wx.EVT_BUTTON, self.on_remove)
        buttons.Add(remove, 0, wx.RIGHT, 8)

        close = wx.Button(panel, wx.ID_CLOSE, label=self._("Close"))
        close.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CLOSE))
        close.SetDefault()
        buttons.Add(close, 0)

        layout.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        panel.SetSizer(layout)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(outer)

        self._reload()
        self.category_list.SetFocus()

    def _reload(self, select_name=None):
        self.category_list.Clear()
        categories = self.store.categories(self.profile_id)
        for name in categories:
            self.category_list.Append(name)
        if categories:
            index = categories.index(select_name) if select_name in categories else 0
            self.category_list.SetSelection(index)

    def _selected_category(self):
        index = self.category_list.GetSelection()
        if index == wx.NOT_FOUND:
            wx.MessageBox(
                self._("Select a category first."),
                self._("Manage Torrent Categories"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return None
        return self.category_list.GetString(index)

    def on_rename(self, event):
        old = self._selected_category()
        if old is None:
            return
        dialog = wx.TextEntryDialog(
            self,
            self._("New category name:"),
            self._("Rename Category"),
            old,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            new = self.store.clean_category(dialog.GetValue())
        finally:
            dialog.Destroy()

        if not new:
            wx.MessageBox(
                self._("Category name is required."),
                self._("Manage Torrent Categories"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        if old == new:
            return
        try:
            changed = self.store.rename_category(self.profile_id, old, new)
        except ValueError:
            wx.MessageBox(
                self._("A category with that name already exists."),
                self._("Manage Torrent Categories"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        if changed:
            self.operations.append(("rename", old, new, changed))
            self._reload(new)
            self.category_list.SetFocus()

    def on_remove(self, event):
        name = self._selected_category()
        if name is None:
            return
        question = self._(
            'Remove category "{name}" from all torrents in this profile? '
            "No torrent files or data will be deleted."
        ).format(name=name)
        if wx.MessageBox(
            question,
            self._("Manage Torrent Categories"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        ) != wx.YES:
            return

        changed = self.store.delete_category(self.profile_id, name)
        if changed:
            self.operations.append(("delete", name, "", changed))
            self._reload()
            self.category_list.SetFocus()
