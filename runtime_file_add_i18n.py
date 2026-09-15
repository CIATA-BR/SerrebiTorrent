# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized local .torrent-file add flow."""

from __future__ import annotations

import wx

import main as legacy
from runtime_messages_i18n import tr_runtime_message


_PT_BR = {
    "Open Torrent File": "Abrir arquivo torrent",
    "Torrent files (*.torrent)|*.torrent": "Arquivos torrent (*.torrent)|*.torrent",
    "Error adding file: {error}": "Erro ao adicionar arquivo: {error}",
}


def _language(frame):
    try:
        return frame._language()
    except Exception:
        try:
            return frame.config_manager.get_preferences().get("language", "system")
        except Exception:
            return "system"


def tr_file_add(text, language=None):
    translated = tr_runtime_message(text, language)
    if translated != text:
        return translated
    from main_ui_i18n import resolved_language

    if resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


def localized_on_add_file(self, event):
    language = _language(self)
    with wx.FileDialog(
        self,
        tr_file_add("Open Torrent File", language),
        wildcard=tr_file_add("Torrent files (*.torrent)|*.torrent", language),
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return
        path = file_dialog.GetPath()
        try:
            with open(path, "rb") as torrent_file:
                data = torrent_file.read()

            file_list = []
            name = tr_runtime_message("Unknown", language)
            if legacy.lt:
                try:
                    info = legacy.lt.torrent_info(data)
                    name = info.name()
                    num = info.num_files()
                    fs = legacy.torrent_file_storage(info)
                    file_list = [(fs.file_path(i), fs.file_size(i)) for i in range(num)]
                except Exception:
                    pass

            default_path = self._get_default_save_path()
            dlg = legacy.AddTorrentDialog(self, name, file_list, default_path)
            try:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                save_path = dlg.get_selected_path() or None
                priorities = dlg.get_file_priorities()
                hash_hint = self._maybe_hash_from_torrent_bytes(data)
                if not self.client:
                    self.statusbar.SetStatusText(
                        tr_runtime_message("Not connected to any client.", language), 0
                    )
                    return
                self._prepare_auto_start()
                if hash_hint:
                    self.pending_hash_starts.add(hash_hint)
                generation = self.client_generation
                client = self.client
                self.statusbar.SetStatusText(
                    tr_runtime_message("Adding torrent...", language), 0
                )
                self.thread_pool.submit(
                    self._add_torrent_file_background,
                    client,
                    generation,
                    data,
                    save_path,
                    priorities,
                    tr_runtime_message("Torrent added", language),
                )
            finally:
                dlg.Destroy()
        except Exception as exc:  # noqa: BLE001 - file/UI boundary
            wx.LogError(
                tr_file_add("Error adding file: {error}", language).format(error=exc)
            )


def install_file_add_localization():
    legacy.MainFrame.on_add_file = localized_on_add_file
