# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized runtime actions and component installation for the legacy main module."""

from __future__ import annotations

import os
import sys

import wx

import main as legacy
import translation_center as translation_center_module
from external_catalog_runtime import install_external_catalogs
from i18n import normalize_language, system_language, translate
from remote_preferences_i18n import install_remote_preferences_localization
from rss_i18n import (
    LocalizedArticleListCtrl,
    LocalizedRSSPanel,
    LocalizedRuleEditDialog,
    LocalizedRulesManagerDialog,
)
from runtime_cli_i18n import install_cli_localization
from runtime_components_i18n import (
    LocalizedFilesListCtrl,
    LocalizedPeersListCtrl,
    LocalizedTaskBarIcon,
    LocalizedTorrentDetailsPanel,
    LocalizedTrackersListCtrl,
)
from runtime_create_i18n import install_create_torrent_localization
from runtime_file_add_i18n import install_file_add_localization
from runtime_messages_i18n import install_runtime_message_localization
from runtime_update_i18n import install_update_localization
from translation_center import attach_translation_center
from translation_inventory import collect_source_messages

# Extend the existing i18n registries before any localized frame/dialog is
# created. Existing translator function objects remain valid because they read
# CATALOGS and normalize_language from the i18n module at call time.
install_external_catalogs()
# The contributor UI and POT generator share the same static inventory. Keeping
# this assignment outside translation_center avoids making that wx module a
# dependency of the command-line catalog tooling.
translation_center_module.source_messages = collect_source_messages


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
    install_remote_preferences_localization()
    install_runtime_message_localization()
    install_file_add_localization()
    install_create_torrent_localization()
    install_update_localization()
    install_cli_localization()


# app_entry imports this module before defining LocalizedMainFrame. Hook only
# subclass creation so main.MainFrame.__init__ remains byte-for-byte inspectable
# by the upstream regression tests. Once LocalizedMainFrame exists, only its own
# constructor is wrapped to install presentation bindings before the legacy
# constructor builds child controls.
def _localized_init_subclass(cls, **kwargs):
    super(legacy.MainFrame, cls).__init_subclass__(**kwargs)
    if cls.__name__ != "LocalizedMainFrame":
        return
    original_init = cls.__init__

    def localized_init(self, *args, **init_kwargs):
        install_localized_runtime_components()
        result = original_init(self, *args, **init_kwargs)
        attach_translation_center(self)
        return result

    cls.__init__ = localized_init


legacy.MainFrame.__init_subclass__ = classmethod(_localized_init_subclass)


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
