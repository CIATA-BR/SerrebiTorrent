# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized runtime actions that remain global in the legacy main module."""

from __future__ import annotations

import os
import sys

import wx

from i18n import normalize_language, system_language, translate


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
