# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Accessible in-app Translation Center for community contributors."""

from __future__ import annotations

from pathlib import Path
import json
import os
import webbrowser

import wx

import i18n
from translation_catalog import render_po, validate_catalog_code, validate_translation


DRAFT_DIR_NAME = "translations"
DEFAULT_ONLINE_TRANSLATION_URL = "https://torrent.ciata.org.br/"
ONLINE_TRANSLATION_URL = os.environ.get(
    "SERREBITORRENT_TRANSLATION_URL",
    DEFAULT_ONLINE_TRANSLATION_URL,
).strip()


def source_messages() -> list[str]:
    """Return the canonical English source strings currently known to the app."""
    messages: set[str] = set()
    for catalog in i18n.CATALOGS.values():
        messages.update(catalog.keys())
    messages.update(
        {
            "Translation Center",
            "Language code:",
            "Language name:",
            "Filter:",
            "All",
            "Untranslated",
            "Needs review",
            "Translated",
            "Source text",
            "Translation",
            "Context / validation",
            "Previous",
            "Save entry",
            "Next",
            "Export PO...",
            "Open online translation",
            "Close",
        }
    )
    return sorted(messages, key=str.casefold)


def _data_dir() -> Path:
    try:
        from app_paths import get_data_dir

        root = Path(get_data_dir())
    except Exception:
        root = Path.cwd() / "SerrebiTorrent_Data"
    path = root / DRAFT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_code(code: str) -> str:
    cleaned = "".join(ch for ch in code.strip() if ch.isalnum() or ch in "-_")
    return cleaned or "new-language"


def draft_path(code: str) -> Path:
    return _data_dir() / f"{_safe_code(code)}.json"


def load_draft(code: str) -> dict[str, str]:
    path = draft_path(code)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.get("translations", {}).items()}
    except (OSError, ValueError, TypeError):
        return {}


def save_draft(code: str, name: str, translations: dict[str, str]) -> Path:
    path = draft_path(code)
    payload = {
        "language": code.strip(),
        "language_name": name.strip(),
        "translations": dict(sorted(translations.items(), key=lambda item: item[0].casefold())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def progress(messages: list[str], translations: dict[str, str]) -> tuple[int, int, int]:
    translated = sum(1 for source in messages if translations.get(source, "").strip())
    review = sum(
        1
        for source in messages
        if translations.get(source, "").strip()
        and validate_translation(source, translations[source])
    )
    return translated, len(messages), review


class TranslationCenterDialog(wx.Dialog):
    """Keyboard-first editor for contributor translation drafts."""

    FILTERS = ("All", "Untranslated", "Needs review", "Translated")

    def __init__(self, parent, default_language="pt-BR"):
        super().__init__(parent, title="Translation Center", size=(900, 680))
        self.messages = source_messages()
        self.translations: dict[str, str] = {}
        self.visible_messages: list[str] = []
        self.current_source: str | None = None

        root = wx.BoxSizer(wx.VERTICAL)
        language_row = wx.BoxSizer(wx.HORIZONTAL)
        language_row.Add(wx.StaticText(self, label="Language code:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.language_code = wx.TextCtrl(self, value=default_language)
        self.language_code.SetName("Language code")
        language_row.Add(self.language_code, 1, wx.RIGHT, 12)
        language_row.Add(wx.StaticText(self, label="Language name:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.language_name = wx.TextCtrl(self, value="Português (Brasil)" if default_language == "pt-BR" else "")
        self.language_name.SetName("Language name")
        language_row.Add(self.language_name, 1)
        root.Add(language_row, 0, wx.EXPAND | wx.ALL, 8)

        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(wx.StaticText(self, label="Filter:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.filter_choice = wx.Choice(self, choices=list(self.FILTERS))
        self.filter_choice.SetSelection(0)
        self.filter_choice.SetName("Translation filter")
        filter_row.Add(self.filter_choice, 0, wx.RIGHT, 12)
        self.progress_label = wx.StaticText(self, label="")
        self.progress_label.SetName("Translation progress")
        filter_row.Add(self.progress_label, 1, wx.ALIGN_CENTER_VERTICAL)
        root.Add(filter_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.entries = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.entries.SetName("Translation entries")
        self.entries.InsertColumn(0, "Status", width=120)
        self.entries.InsertColumn(1, "Source text", width=560)
        root.Add(self.entries, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        edit = wx.FlexGridSizer(cols=2, hgap=8, vgap=6)
        edit.AddGrowableCol(1, 1)
        edit.Add(wx.StaticText(self, label="Source text:"), 0, wx.ALIGN_TOP)
        self.source_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 76))
        self.source_text.SetName("Source text")
        edit.Add(self.source_text, 1, wx.EXPAND)
        edit.Add(wx.StaticText(self, label="Translation:"), 0, wx.ALIGN_TOP)
        self.translation_text = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 90))
        self.translation_text.SetName("Translation")
        edit.Add(self.translation_text, 1, wx.EXPAND)
        edit.Add(wx.StaticText(self, label="Context / validation:"), 0, wx.ALIGN_TOP)
        self.validation_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 66))
        self.validation_text.SetName("Context and validation")
        edit.Add(self.validation_text, 1, wx.EXPAND)
        root.Add(edit, 0, wx.EXPAND | wx.ALL, 8)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        self.prev_button = wx.Button(self, label="&Previous")
        self.save_button = wx.Button(self, label="&Save entry")
        self.next_button = wx.Button(self, label="&Next")
        self.export_button = wx.Button(self, label="&Export PO...")
        self.online_button = wx.Button(self, label="Open &online translation")
        self.online_button.Enable(bool(ONLINE_TRANSLATION_URL))
        close_button = wx.Button(self, wx.ID_CLOSE, label="&Close")
        for button in (self.prev_button, self.save_button, self.next_button, self.export_button, self.online_button):
            nav.Add(button, 0, wx.RIGHT, 6)
        nav.AddStretchSpacer()
        nav.Add(close_button, 0)
        root.Add(nav, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(root)

        self.entries.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.filter_choice.Bind(wx.EVT_CHOICE, lambda _event: self._refresh_list())
        self.language_code.Bind(wx.EVT_KILL_FOCUS, self._on_language_change)
        self.save_button.Bind(wx.EVT_BUTTON, self._on_save_entry)
        self.prev_button.Bind(wx.EVT_BUTTON, lambda _event: self._move(-1))
        self.next_button.Bind(wx.EVT_BUTTON, lambda _event: self._move(1))
        self.export_button.Bind(wx.EVT_BUTTON, self._on_export)
        self.online_button.Bind(wx.EVT_BUTTON, self._on_online)
        close_button.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_CLOSE))
        self._load_language(default_language)

    def _load_language(self, code: str) -> None:
        code = code.strip() or "new-language"
        if code == "pt-BR":
            self.translations = dict(i18n.CATALOGS.get("pt-BR", {}))
        else:
            self.translations = load_draft(code)
        self._refresh_list()

    def _on_language_change(self, event) -> None:
        self._save_current_to_memory()
        self._load_language(self.language_code.GetValue())
        event.Skip()

    def _status(self, source: str) -> str:
        value = self.translations.get(source, "")
        if not value.strip():
            return "Untranslated"
        if validate_translation(source, value):
            return "Needs review"
        return "Translated"

    def _refresh_list(self) -> None:
        self._save_current_to_memory()
        wanted = self.FILTERS[self.filter_choice.GetSelection()]
        self.visible_messages = [source for source in self.messages if wanted == "All" or self._status(source) == wanted]
        self.entries.DeleteAllItems()
        for source in self.visible_messages:
            index = self.entries.InsertItem(self.entries.GetItemCount(), self._status(source))
            self.entries.SetItem(index, 1, source)
        translated, total, review = progress(self.messages, self.translations)
        pct = (translated / total * 100.0) if total else 100.0
        self.progress_label.SetLabel(f"{translated} of {total} translated — {pct:.1f}% — {review} need review")
        if self.visible_messages:
            self.entries.Select(0)
            self.entries.Focus(0)
        else:
            self._show_source(None)

    def _on_select(self, event) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self.visible_messages):
            self._show_source(self.visible_messages[index])

    def _show_source(self, source: str | None) -> None:
        self.current_source = source
        if not source:
            self.source_text.SetValue("")
            self.translation_text.SetValue("")
            self.validation_text.SetValue("")
            return
        self.source_text.SetValue(source)
        self.translation_text.SetValue(self.translations.get(source, ""))
        self._update_validation()

    def _save_current_to_memory(self) -> None:
        if self.current_source:
            value = self.translation_text.GetValue()
            if value:
                self.translations[self.current_source] = value
            else:
                self.translations.pop(self.current_source, None)

    def _update_validation(self) -> None:
        if not self.current_source:
            self.validation_text.SetValue("")
            return
        value = self.translation_text.GetValue()
        problems = validate_translation(self.current_source, value) if value else []
        self.validation_text.SetValue("\n".join(problems) if problems else "No validation problems. Preserve technical names and test the result in context.")

    def _on_save_entry(self, _event) -> None:
        self._save_current_to_memory()
        source = self.current_source
        if source:
            problems = validate_translation(source, self.translations.get(source, ""))
            self.validation_text.SetValue("\n".join(problems) if problems else "Saved. No validation problems.")
        save_draft(self.language_code.GetValue(), self.language_name.GetValue(), self.translations)
        self._refresh_list()

    def _move(self, delta: int) -> None:
        selected = self.entries.GetFirstSelected()
        if selected < 0:
            selected = 0
        target = max(0, min(self.entries.GetItemCount() - 1, selected + delta))
        if target >= 0:
            self.entries.Select(target)
            self.entries.Focus(target)
            self.entries.EnsureVisible(target)

    def _on_export(self, _event) -> None:
        self._save_current_to_memory()
        code = self.language_code.GetValue().strip()
        name = self.language_name.GetValue().strip()
        if not code or not name:
            wx.MessageBox("Language code and language name are required.", "Translation Center", wx.OK | wx.ICON_ERROR)
            return
        try:
            code = validate_catalog_code(code)
        except ValueError:
            wx.MessageBox(
                "Language code must use hyphenated BCP47-style subtags, for example pt-BR or es-ES.",
                "Translation Center",
                wx.OK | wx.ICON_ERROR,
            )
            self.language_code.SetFocus()
            return
        problems = {source: validate_translation(source, value) for source, value in self.translations.items() if value and validate_translation(source, value)}
        if problems:
            answer = wx.MessageBox(
                f"{len(problems)} translated entries still need review. Export anyway?",
                "Translation validation",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if answer != wx.YES:
                return
        with wx.FileDialog(
            self,
            "Export translation catalog",
            wildcard="GNU gettext PO (*.po)|*.po",
            defaultFile=f"{_safe_code(code)}.po",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            Path(dialog.GetPath()).write_text(render_po(code, name, self.translations), encoding="utf-8")
        save_draft(code, name, self.translations)
        wx.MessageBox("Translation catalog exported successfully.", "Translation Center")

    def _on_online(self, _event) -> None:
        if ONLINE_TRANSLATION_URL:
            webbrowser.open(ONLINE_TRANSLATION_URL)


def attach_translation_center(frame) -> None:
    """Append the contributor UI to Help without rebuilding the existing menu."""
    menubar = frame.GetMenuBar()
    if not menubar or menubar.GetMenuCount() == 0:
        return
    help_menu = menubar.GetMenu(menubar.GetMenuCount() - 1)
    if help_menu is None:
        return
    for existing in help_menu.GetMenuItems():
        if existing.GetItemLabelText() == "Contribute Translation...":
            return
    help_menu.AppendSeparator()
    item = help_menu.Append(wx.ID_ANY, "Contribute &Translation...", "Open the accessible Translation Center")

    def open_center(_event) -> None:
        default_language = "pt-BR"
        try:
            configured = frame._language()
            if configured not in ("", "system", "en"):
                default_language = configured
        except Exception:
            pass
        dialog = TranslationCenterDialog(frame, default_language=default_language)
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()

    frame.Bind(wx.EVT_MENU, open_center, item)
