# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized presentation wrapper for the contributor Translation Center."""

from __future__ import annotations

import wx

import i18n
from translation_catalog import load_po, merge_template
from translation_center import FILTERS, TranslationCenterDialog
from translation_runtime import user_catalog_path
from translation_seed import seed_entries


TRANSLATABLE_STRINGS = (
    "Translation Center",
    "&Language:",
    "Translation language",
    "&Filter:",
    "Translation filter",
    "Translation progress",
    "Translation entries",
    "Source",
    "Status",
    "Translation",
    "Source:",
    "English source text",
    "Context:",
    "Translation context",
    "&Translation:",
    "Translated text",
    "&Needs review",
    "Translation validation status",
    "&Previous",
    "&Save entry",
    "&Next",
    "&Import...",
    "E&xport...",
    "&Test in this session",
    "&Close",
    "Untranslated",
    "Needs review",
    "Translated",
    "All",
)


class LocalizedTranslationCenterDialog(TranslationCenterDialog):
    def __init__(self, parent):
        self._ui_language = self._language_from_parent(parent)
        super().__init__(parent)
        self._localize_controls()

    @staticmethod
    def _language_from_parent(parent):
        try:
            return parent._language()
        except Exception:
            return "system"

    def _(self, text):
        return i18n.translate(text, self._ui_language)

    def _load_language(self, language: str):
        language = language.strip().replace("_", "-") or "en"
        self.language = language
        self.language_ctrl.SetValue(language)

        # Start from translations already shipped by the application so the
        # contributor sees real completion rather than an empty migration.
        current = seed_entries(self.root, language)

        # User edits are the highest-precedence layer.
        user_entries = load_po(user_catalog_path(language))
        current.update(user_entries)

        self.entries = merge_template(self.source_strings, current)
        self._refresh_list()

    def _localize_controls(self):
        self.SetTitle(self._("Translation Center"))

        def visit(window):
            try:
                label = window.GetLabel()
            except Exception:
                label = ""
            if label:
                translated = self._(label)
                if translated != label:
                    try:
                        window.SetLabel(translated)
                    except Exception:
                        pass
            try:
                name = window.GetName()
            except Exception:
                name = ""
            if name:
                translated_name = self._(name)
                if translated_name != name:
                    try:
                        window.SetName(translated_name)
                    except Exception:
                        pass
            try:
                children = window.GetChildren()
            except Exception:
                children = ()
            for child in children:
                visit(child)

        visit(self)

        for column, source in enumerate(("Source", "Status", "Translation")):
            item = self.list.GetColumn(column)
            item.SetText(self._(source))
            self.list.SetColumn(column, item)

        selection = self.filter_ctrl.GetSelection()
        self.filter_ctrl.Clear()
        for _key, label in FILTERS:
            self.filter_ctrl.Append(self._(label))
        self.filter_ctrl.SetSelection(max(0, selection))
