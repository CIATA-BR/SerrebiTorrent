# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Application entry point with external catalogs and contributor Translation Center."""

from __future__ import annotations

from translation_runtime import install_runtime_catalogs

# Install before app_entry imports UI modules that bind i18n callables.
install_runtime_catalogs()

import wx
import app_entry
from translation_center import TranslationCenterDialog


class TranslationMainFrame(app_entry.LocalizedMainFrame):
    def _build_menu_bar(self):
        super()._build_menu_bar()
        menubar = self.GetMenuBar()
        help_index = menubar.FindMenu(self._("&Help"))
        if help_index == wx.NOT_FOUND:
            return
        help_menu = menubar.GetMenu(help_index)
        help_menu.InsertSeparator(0)
        item = help_menu.Insert(
            0,
            wx.ID_ANY,
            self._("Contribute &Translations..."),
            self._("Translate SerrebiTorrent or review an existing language"),
        )
        self.Bind(wx.EVT_MENU, self.on_translation_center, item)

    def on_translation_center(self, _event):
        dlg = TranslationCenterDialog(self)
        try:
            dlg.ShowModal()
        finally:
            dlg.Destroy()


def main():
    app_entry.LocalizedMainFrame = TranslationMainFrame
    return app_entry.main()


if __name__ == "__main__":
    raise SystemExit(main())
