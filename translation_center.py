# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Accessible in-app translation contribution editor."""

from __future__ import annotations

from pathlib import Path

import wx

from translation_catalog import (
    CatalogEntry,
    catalog_stats,
    extract_python_catalog_strings,
    extract_web_catalog_strings,
    load_po,
    merge_template,
    save_po,
    validate_entry,
)
from translation_runtime import (
    install_session_catalog,
    reload_catalogs,
    set_session_language,
    user_catalog_path,
)


FILTERS = (
    ("untranslated", "Untranslated"),
    ("review", "Needs review"),
    ("translated", "Translated"),
    ("all", "All"),
)


def collect_source_strings(root: Path | None = None) -> list[str]:
    root = root or Path(__file__).resolve().parent
    strings = set(extract_python_catalog_strings(root))
    web = root / "web_static" / "i18n.js"
    if web.exists():
        strings.update(extract_web_catalog_strings(web))
    return sorted(strings, key=str.casefold)


class TranslationCenterDialog(wx.Dialog):
    """Keyboard-first editor for gettext-compatible contribution catalogs."""

    def __init__(self, parent):
        super().__init__(parent, title="Translation Center", size=(920, 720))
        self.root = Path(__file__).resolve().parent
        self.source_strings = collect_source_strings(self.root)
        self.language = "pt-BR"
        self.entries: dict[str, CatalogEntry] = {}
        self.visible_keys: list[str] = []
        self.current_key: str | None = None
        self._build_ui()
        self._load_language(self.language)

    def _build_ui(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(self, label="&Language:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.language_ctrl = wx.ComboBox(self, value="pt-BR", style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        self.language_ctrl.SetName("Translation language")
        top.Add(self.language_ctrl, 1, wx.RIGHT, 12)
        top.Add(wx.StaticText(self, label="&Filter:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.filter_ctrl = wx.Choice(self, choices=[label for _, label in FILTERS])
        self.filter_ctrl.SetSelection(0)
        self.filter_ctrl.SetName("Translation filter")
        top.Add(self.filter_ctrl, 0)
        outer.Add(top, 0, wx.EXPAND | wx.ALL, 10)

        self.progress = wx.StaticText(self, label="")
        self.progress.SetName("Translation progress")
        outer.Add(self.progress, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.InsertColumn(0, "Source", width=430)
        self.list.InsertColumn(1, "Status", width=130)
        self.list.InsertColumn(2, "Translation", width=300)
        self.list.SetName("Translation entries")
        outer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        grid = wx.FlexGridSizer(cols=2, hgap=8, vgap=8)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, label="Source:"), 0, wx.ALIGN_TOP)
        self.source = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.source.SetName("English source text")
        grid.Add(self.source, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label="Context:"), 0, wx.ALIGN_TOP)
        self.context = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.context.SetName("Translation context")
        grid.Add(self.context, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label="&Translation:"), 0, wx.ALIGN_TOP)
        self.translation = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.translation.SetName("Translated text")
        grid.Add(self.translation, 1, wx.EXPAND)
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self.review = wx.CheckBox(self, label="&Needs review")
        outer.Add(self.review, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.validation = wx.StaticText(self, label="")
        self.validation.SetName("Translation validation status")
        outer.Add(self.validation, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            ("&Previous", self.on_previous),
            ("&Save entry", self.on_save_entry),
            ("&Next", self.on_next),
            ("&Import...", self.on_import),
            ("E&xport...", self.on_export),
            ("&Test in this session", self.on_test),
        ):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        close = wx.Button(self, wx.ID_CLOSE, "&Close")
        close.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_CLOSE))
        buttons.AddStretchSpacer()
        buttons.Add(close, 0)
        outer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)
        self.filter_ctrl.Bind(wx.EVT_CHOICE, lambda _event: self._refresh_list())
        self.language_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_language_change)
        self.language_ctrl.Bind(wx.EVT_KILL_FOCUS, self.on_language_change)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selected)
        self.translation.Bind(wx.EVT_TEXT, self.on_translation_changed)

    def _load_language(self, language: str):
        language = language.strip().replace("_", "-") or "en"
        self.language = language
        self.language_ctrl.SetValue(language)
        path = user_catalog_path(language)
        current = load_po(path)
        self.entries = merge_template(self.source_strings, current)
        self._refresh_list()

    def _status(self, entry: CatalogEntry) -> str:
        if "fuzzy" in entry.flags:
            return "Needs review"
        if entry.msgstr.strip():
            return "Translated"
        return "Untranslated"

    def _matches_filter(self, entry: CatalogEntry) -> bool:
        key = FILTERS[self.filter_ctrl.GetSelection()][0]
        if key == "all":
            return True
        if key == "review":
            return "fuzzy" in entry.flags
        if key == "translated":
            return entry.translated
        return not entry.msgstr.strip()

    def _refresh_list(self):
        self.list.DeleteAllItems()
        self.visible_keys = [k for k, e in self.entries.items() if self._matches_filter(e)]
        for key in self.visible_keys:
            entry = self.entries[key]
            row = self.list.InsertItem(self.list.GetItemCount(), entry.msgid)
            self.list.SetItem(row, 1, self._status(entry))
            self.list.SetItem(row, 2, entry.msgstr)
        total, translated, review = catalog_stats(self.entries)
        pct = 100.0 if total == 0 else translated * 100.0 / total
        self.progress.SetLabel(
            f"{translated} of {total} translated ({pct:.1f}%). {review} need review."
        )
        if self.visible_keys:
            self.list.Select(0)
            self.list.Focus(0)

    def on_selected(self, event):
        index = event.GetIndex()
        if index < 0 or index >= len(self.visible_keys):
            return
        self.current_key = self.visible_keys[index]
        entry = self.entries[self.current_key]
        self.source.ChangeValue(entry.msgid)
        self.context.ChangeValue(entry.context or "No additional context.")
        self.translation.ChangeValue(entry.msgstr)
        self.review.SetValue("fuzzy" in entry.flags)
        self._validate_current()

    def _validate_current(self):
        if not self.current_key:
            self.validation.SetLabel("")
            return []
        entry = CatalogEntry(
            self.current_key,
            self.translation.GetValue(),
            self.entries[self.current_key].context,
            flags={"fuzzy"} if self.review.GetValue() else set(),
        )
        errors = validate_entry(entry)
        self.validation.SetLabel("Ready." if not errors else "Validation: " + "; ".join(errors))
        return errors

    def on_translation_changed(self, _event):
        self._validate_current()

    def on_save_entry(self, _event):
        if not self.current_key:
            return
        errors = self._validate_current()
        if errors:
            wx.MessageBox("\n".join(errors), "Translation validation", wx.OK | wx.ICON_WARNING)
            return
        entry = self.entries[self.current_key]
        entry.msgstr = self.translation.GetValue()
        if self.review.GetValue():
            entry.flags.add("fuzzy")
        else:
            entry.flags.discard("fuzzy")
        save_po(user_catalog_path(self.language), self.entries, self.language)
        reload_catalogs()
        self._refresh_list()

    def _move(self, delta: int):
        selected = self.list.GetFirstSelected()
        if selected < 0:
            return
        target = max(0, min(self.list.GetItemCount() - 1, selected + delta))
        self.list.Select(target)
        self.list.Focus(target)
        self.list.EnsureVisible(target)

    def on_previous(self, _event):
        self._move(-1)

    def on_next(self, _event):
        self._move(1)

    def on_import(self, _event):
        dlg = wx.FileDialog(self, "Import translation", wildcard="PO files (*.po)|*.po", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            incoming = load_po(dlg.GetPath())
            for key, entry in incoming.items():
                if key in self.entries:
                    self.entries[key] = entry
            save_po(user_catalog_path(self.language), self.entries, self.language)
            reload_catalogs()
            self._refresh_list()
        finally:
            dlg.Destroy()

    def on_export(self, _event):
        default = f"SerrebiTorrent-{self.language}.po"
        dlg = wx.FileDialog(self, "Export translation", defaultFile=default, wildcard="PO files (*.po)|*.po", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            save_po(dlg.GetPath(), self.entries, self.language)
        finally:
            dlg.Destroy()

    def on_test(self, _event):
        mapping = {key: entry.msgstr for key, entry in self.entries.items() if entry.translated}
        install_session_catalog(self.language, mapping)
        set_session_language(self.language)
        parent = self.GetParent()
        if hasattr(parent, "_build_menu_bar"):
            parent._build_menu_bar()
        if hasattr(parent, "_apply_localized_static_labels"):
            parent._apply_localized_static_labels()
        wx.MessageBox(
            "The translation is active for this session. Reopen dialogs to preview them. Restart to return to the saved language.",
            "Translation preview",
            wx.OK | wx.ICON_INFORMATION,
        )

    def on_language_change(self, event):
        value = self.language_ctrl.GetValue().strip()
        if value and value != self.language:
            self._load_language(value)
        event.Skip()
