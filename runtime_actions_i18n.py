# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized runtime actions and component installation for the legacy main module."""

from __future__ import annotations

import os
import sys

import wx

import main as legacy
from i18n import normalize_language, system_language, translate
from rss_i18n import (
    LocalizedArticleListCtrl,
    LocalizedRSSPanel,
    LocalizedRuleEditDialog,
    LocalizedRulesManagerDialog,
)
from runtime_components_i18n import (
    LocalizedFilesListCtrl,
    LocalizedPeersListCtrl,
    LocalizedTaskBarIcon,
    LocalizedTorrentDetailsPanel,
    LocalizedTrackersListCtrl,
)


def install_localized_runtime_components():
    """Install localized legacy bindings immediately before localized frame creation."""
    legacy.FilesListCtrl = LocalizedFilesListCtrl
    legacy.PeersListCtrl = LocalizedPeersListCtrl
    legacy.TrackersListCtrl = LocalizedTrackersListCtrl
    legacy.TorrentDetailsPanel = LocalizedTorrentDetailsPanel
    legacy.TaskBarIcon = LocalizedTaskBarIcon
    legacy.ArticleListCtrl = LocalizedArticleListCtrl
    legacy.RuleEditDialog = LocalizedRuleEditDialog
    legacy.RulesManagerDialog = LocalizedRulesManagerDialog
    legacy.RSSPanel = LocalizedRSSPanel


# ``app_entry`` imports this module before defining LocalizedMainFrame. Wrapping
# the legacy constructor lets us defer the class rebinding until an actual
# localized frame is instantiated. Importing app_entry therefore leaves the
# original detail/RSS classes intact for upstream source-inspection tests.
_LEGACY_MAINFRAME_INIT = legacy.MainFrame.__init__


def _localized_runtime_mainframe_init(self, *args, **kwargs):
    if self.__class__.__name__ == "LocalizedMainFrame":
        install_localized_runtime_components()
    return _LEGACY_MAINFRAME_INIT(self, *args, **kwargs)


legacy.MainFrame.__init__ = _localized_runtime_mainframe_init


_PT_BR = {
    "Association is only supported on Windows for now.": "No momento, o registro de associações é compatível apenas com Windows.",
    "Info": "Informação",
    "Torrent File": "Arquivo torrent",
    "URL:Magnet Link": "URL:Link magnet",
    "Associations registered successfully!": "Associações registradas com sucesso!",
    "Success": "Sucesso",
    "Failed to register associations: {error}": "Falha ao registrar associações: {error}",
}


def _resolved_language(language):
    if language in (None, "", "system"):
        return system_language()
    return normalize_language(language)


def tr_action(text, language=None):
    translated = translate(text, language)
    if translated != text:
        return translated
    if _resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


def register_associations(language="system"):
    """Register .torrent and magnet handlers while localizing user feedback."""
    _ = lambda text: tr_action(text, language)

    if sys.platform != "win32":
        wx.MessageBox(
            _("Association is only supported on Windows for now."),
            _("Info"),
        )
        return

    try:
        import winreg

        exe_path = sys.executable
        if not getattr(sys, "frozen", False):
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            cmd = f'"{python_exe}" "{os.path.abspath(sys.argv[0])}" "%1"'
        else:
            cmd = f'"{exe_path}" "%1"'

        key_path = r"Software\Classes\.torrent"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "SerrebiTorrent.Torrent")

        key_path = r"Software\Classes\SerrebiTorrent.Torrent"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, _("Torrent File"))
            with winreg.CreateKey(key, r"shell\open\command") as cmd_key:
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, cmd)

        key_path = r"Software\Classes\magnet"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, _("URL:Magnet Link"))
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(key, r"shell\open\command") as cmd_key:
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, cmd)

        wx.MessageBox(_("Associations registered successfully!"), _("Success"))
    except Exception as exc:  # noqa: BLE001 - user-facing OS integration boundary
        wx.LogError(_("Failed to register associations: {error}").format(error=exc))
