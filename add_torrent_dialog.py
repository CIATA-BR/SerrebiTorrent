# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized, screen-reader-friendly dialog used before adding a torrent."""

from __future__ import annotations

import wx

from i18n import normalize_language, system_language, translate
from ui_formatting import fmt_size


_PT_BR = {
    "Add Torrent: {name}": "Adicionar torrent: {name}",
    "Save Path:": "Pasta de destino:",
    "Save Path": "Pasta de destino",
    "Browse...": "Procurar...",
    "Files:": "Arquivos:",
    "Files": "Arquivos",
    "Select All": "Selecionar tudo",
    "Deselect All": "Desmarcar tudo",
    "File list not available (Magnet link).": "Lista de arquivos indisponível (link magnet).",
    "Choose Download Directory": "Escolher pasta de download",
    "Check": "Marcar",
    "Uncheck": "Desmarcar",
    "Check All": "Marcar tudo",
    "Uncheck All": "Desmarcar tudo",
}


def _resolved_language(language):
    if language in (None, "", "system"):
        return system_language()
    return normalize_language(language)


def tr_add(text, language=None):
    translated = translate(text, language)
    if translated != text:
        return translated
    if _resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


class AddTorrentDialog(wx.Dialog):
    def __init__(self, parent, name, file_list=None, default_path="", language=None):
        self.language = language or self._parent_language(parent)
        self._ = lambda text: tr_add(text, self.language)
        super().__init__(
            parent,
            title=self._("Add Torrent: {name}").format(name=name),
            size=(600, 500),
        )

        self.file_list = file_list or []
        self.item_map = {}

        sizer = wx.BoxSizer(wx.VERTICAL)

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(
            wx.StaticText(self, label=self._("Save Path:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            5,
        )
        self.path_input = wx.TextCtrl(self, value=default_path)
        self.path_input.SetName(self._("Save Path"))
        path_sizer.Add(self.path_input, 1, wx.EXPAND | wx.RIGHT, 5)
        browse_btn = wx.Button(self, label=self._("Browse..."))
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        path_sizer.Add(browse_btn, 0)
        sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 10)

        if self.file_list:
            sizer.Add(wx.StaticText(self, label=self._("Files:")), 0, wx.LEFT | wx.RIGHT, 10)

            self.tree = wx.TreeCtrl(
                self,
                style=(
                    wx.TR_DEFAULT_STYLE
                    | wx.TR_HIDE_ROOT
                    | wx.TR_HAS_BUTTONS
                    | wx.TR_LINES_AT_ROOT
                ),
            )
            self.tree.SetName(self._("Files"))
            self.root = self.tree.AddRoot(name)
            self.item_map[self.root] = {"name": name, "size": 0, "idx": None}

            self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_toggle)
            self.tree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
            self.tree.Bind(wx.EVT_LEFT_DOWN, self.on_click)
            self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_tree_context_menu)

            def get_or_create_child(parent_item, text):
                child, cookie = self.tree.GetFirstChild(parent_item)
                while child.IsOk():
                    if self.item_map[child]["name"] == text:
                        return child
                    child, cookie = self.tree.GetNextChild(parent_item, cookie)

                item = self.tree.AppendItem(parent_item, "")
                self.item_map[item] = {"name": text, "size": 0, "idx": None}
                self.update_item_label(item, True)
                return item

            for idx, (fpath, fsize) in enumerate(self.file_list):
                parts = fpath.replace("\\", "/").split("/")
                current_item = self.root
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        item = self.tree.AppendItem(current_item, "")
                        self.item_map[item] = {"name": part, "size": fsize, "idx": idx}
                        self.update_item_label(item, True)
                    else:
                        current_item = get_or_create_child(current_item, part)

            self.tree.ExpandAll()
            sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 10)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            sel_all = wx.Button(self, label=self._("Select All"))
            sel_all.Bind(wx.EVT_BUTTON, lambda event: self.set_root_state(True))
            btn_sizer.Add(sel_all, 0, wx.RIGHT, 5)

            desel_all = wx.Button(self, label=self._("Deselect All"))
            desel_all.Bind(wx.EVT_BUTTON, lambda event: self.set_root_state(False))
            btn_sizer.Add(desel_all, 0)
            sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM, 10)
        else:
            sizer.Add(
                wx.StaticText(self, label=self._("File list not available (Magnet link).")),
                0,
                wx.ALL,
                20,
            )

        btns = wx.StdDialogButtonSizer()
        btns.AddButton(wx.Button(self, wx.ID_OK))
        btns.AddButton(wx.Button(self, wx.ID_CANCEL))
        btns.Realize()
        sizer.Add(btns, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(sizer)
        self.Center()

    @staticmethod
    def _parent_language(parent):
        try:
            return parent.config_manager.get_preferences().get("language", "system")
        except Exception:
            return "system"

    def on_browse(self, event):
        dlg = wx.DirDialog(
            self,
            self._("Choose Download Directory"),
            self.path_input.GetValue(),
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.path_input.SetValue(dlg.GetPath())
        finally:
            dlg.Destroy()

    def update_item_label(self, item, checked):
        data = self.item_map.get(item)
        if not data:
            return
        prefix = "[x]" if checked else "[ ]"
        size_str = f" ({fmt_size(data['size'])})" if data["size"] > 0 else ""
        self.tree.SetItemText(item, f"{prefix} {data['name']}{size_str}")

    def is_checked(self, item):
        return self.tree.GetItemText(item).startswith("[x]")

    def on_toggle(self, event):
        item = event.GetItem()
        if item.IsOk():
            self.toggle_item(item)

    def on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_SPACE:
            item = self.tree.GetSelection()
            if item.IsOk():
                self.toggle_item(item)
        else:
            event.Skip()

    def on_click(self, event):
        event.Skip()

    def on_tree_context_menu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            item = self.tree.GetSelection()
        if not item.IsOk():
            return

        menu = wx.Menu()
        check_item = menu.Append(wx.ID_ANY, self._("Check"))
        uncheck_item = menu.Append(wx.ID_ANY, self._("Uncheck"))
        menu.AppendSeparator()
        check_all = menu.Append(wx.ID_ANY, self._("Check All"))
        uncheck_all = menu.Append(wx.ID_ANY, self._("Uncheck All"))

        self.Bind(
            wx.EVT_MENU,
            lambda event: self.set_item_state_recursive(item, True),
            check_item,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda event: self.set_item_state_recursive(item, False),
            uncheck_item,
        )
        self.Bind(wx.EVT_MENU, lambda event: self.set_root_state(True), check_all)
        self.Bind(wx.EVT_MENU, lambda event: self.set_root_state(False), uncheck_all)

        try:
            self.PopupMenu(menu)
        finally:
            menu.Destroy()

    def toggle_item(self, item):
        self.set_item_state_recursive(item, not self.is_checked(item))

    def set_item_state_recursive(self, item, state):
        self.update_item_label(item, state)
        self.update_children(item, state)

        parent = self.tree.GetItemParent(item)
        while parent.IsOk() and parent != self.root:
            self.update_parent(parent)
            parent = self.tree.GetItemParent(parent)

    def update_children(self, parent, state):
        child, cookie = self.tree.GetFirstChild(parent)
        while child.IsOk():
            self.update_item_label(child, state)
            self.update_children(child, state)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def update_parent(self, parent):
        has_checked = False
        child, cookie = self.tree.GetFirstChild(parent)
        while child.IsOk():
            if self.is_checked(child):
                has_checked = True
                break
            child, cookie = self.tree.GetNextChild(parent, cookie)
        self.update_item_label(parent, has_checked)

    def set_root_state(self, state):
        child, cookie = self.tree.GetFirstChild(self.root)
        while child.IsOk():
            self.set_item_state_recursive(child, state)
            child, cookie = self.tree.GetNextChild(self.root, cookie)

    def get_selected_path(self):
        return self.path_input.GetValue()

    def get_file_priorities(self):
        if not self.file_list:
            return None
        priorities = [0] * len(self.file_list)

        def traverse(item):
            if not item.IsOk():
                return
            data = self.item_map.get(item)
            if data and data["idx"] is not None:
                priorities[data["idx"]] = 1 if self.is_checked(item) else 0
            child, cookie = self.tree.GetFirstChild(item)
            while child.IsOk():
                traverse(child)
                child, cookie = self.tree.GetNextChild(item, cookie)

        traverse(self.root)
        return priorities
