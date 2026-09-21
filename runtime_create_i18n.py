# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized Create Torrent runtime feedback layered over main.py."""

from __future__ import annotations

import os
import threading

import wx

import main as legacy
from main_ui_i18n import resolved_language, tr_main


_PT_BR = {
    "Create Torrent": "Criar torrent",
    "Hashing pieces and generating torrent metadata...": "Calculando hashes das peças e gerando metadados do torrent...",
    "libtorrent is not available. Torrent creation requires python-libtorrent.": "O libtorrent não está disponível. A criação de torrents requer python-libtorrent.",
    "Adding created torrent...": "Adicionando torrent criado...",
    "Created torrent added": "Torrent criado adicionado",
    "Torrent created:\n{path}": "Torrent criado:\n{path}",
    "Info Hash: {hash}": "Info hash: {hash}",
    "Magnet copied to clipboard.": "Link magnet copiado para a área de transferência.",
    "Magnet: {magnet}": "Magnet: {magnet}",
    "Created torrent, but failed to add to client: {error}": "Torrent criado, mas houve falha ao adicioná-lo ao cliente: {error}",
    "Source path is required.": "O caminho de origem é obrigatório.",
    "Output .torrent path is required.": "O caminho do arquivo .torrent de saída é obrigatório.",
    "Source path must not be a symlink or Windows reparse point.": "O caminho de origem não pode ser um link simbólico nem um ponto de nova análise do Windows.",
    "No regular files found to include in torrent.": "Nenhum arquivo regular foi encontrado para incluir no torrent.",
}


def _language(frame):
    try:
        return frame._language()
    except Exception:
        try:
            return frame.config_manager.get_preferences().get("language", "system")
        except Exception:
            return "system"


def tr_create(text, language=None):
    translated = tr_main(text, language)
    if translated != text:
        return translated
    if resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


def _translate_exception(exc, language):
    text = str(exc)
    return tr_create(text, language)


def localized_on_create_torrent(self, event):
    language = _language(self)
    dlg = legacy.CreateTorrentDialog(self, language)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return
        try:
            opts = dlg.get_options()
        except Exception as exc:  # noqa: BLE001 - dialog validation boundary
            wx.MessageBox(
                _translate_exception(exc, language),
                tr_create("Create Torrent", language),
                wx.OK | wx.ICON_ERROR,
            )
            return
    finally:
        dlg.Destroy()

    if not legacy.lt:
        wx.MessageBox(
            tr_create(
                "libtorrent is not available. Torrent creation requires python-libtorrent.",
                language,
            ),
            tr_create("Create Torrent", language),
            wx.OK | wx.ICON_ERROR,
        )
        return

    source_path = opts["source_path"]
    output_path = opts["output_path"]
    progress = wx.ProgressDialog(
        tr_create("Create Torrent", language),
        tr_create("Hashing pieces and generating torrent metadata...", language),
        maximum=100,
        parent=self,
        style=wx.PD_APP_MODAL | wx.PD_PULSE | wx.PD_ELAPSED_TIME,
    )
    result = {"torrent_bytes": None, "magnet": "", "info_hash": "", "error": None}

    def worker():
        try:
            torrent_bytes, magnet, info_hash = legacy.create_torrent_bytes(
                source_path=source_path,
                trackers=opts.get("trackers", []),
                web_seeds=opts.get("web_seeds", []),
                piece_size=opts.get("piece_size", 0),
                private=opts.get("private", False),
                comment=opts.get("comment", ""),
                creator=opts.get("creator", ""),
                source=opts.get("source", ""),
            )
            out_dir = os.path.dirname(os.path.abspath(output_path))
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "wb") as handle:
                handle.write(torrent_bytes)
            result["torrent_bytes"] = torrent_bytes
            result["magnet"] = magnet
            result["info_hash"] = info_hash
        except Exception as exc:  # noqa: BLE001 - worker boundary
            result["error"] = _translate_exception(exc, language)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def poll():
        if thread.is_alive():
            try:
                progress.Pulse()
            except Exception:
                pass
            wx.CallLater(200, poll)
            return
        try:
            progress.Destroy()
        except Exception:
            pass

        if result["error"]:
            wx.MessageBox(
                result["error"],
                tr_create("Create Torrent", language),
                wx.OK | wx.ICON_ERROR,
            )
            return

        if opts.get("copy_magnet") and result.get("magnet"):
            self._set_clipboard_text(result["magnet"])

        if opts.get("add_to_client") and self.client:
            try:
                seed_save_path = legacy.seed_save_path_for_source(source_path)
                with open(output_path, "rb") as handle:
                    content = handle.read()
                self._prepare_auto_start()
                generation = self.client_generation
                client = self.client
                self.statusbar.SetStatusText(tr_create("Adding created torrent...", language), 0)
                self.thread_pool.submit(
                    self._add_torrent_file_background,
                    client,
                    generation,
                    content,
                    seed_save_path,
                    None,
                    tr_create("Created torrent added", language),
                )
            except Exception as exc:  # noqa: BLE001 - client boundary
                wx.MessageBox(
                    tr_create(
                        "Created torrent, but failed to add to client: {error}", language
                    ).format(error=exc),
                    tr_create("Create Torrent", language),
                    wx.OK | wx.ICON_WARNING,
                )

        message = tr_create("Torrent created:\n{path}", language).format(path=output_path)
        if result.get("info_hash"):
            message += "\n" + tr_create("Info Hash: {hash}", language).format(
                hash=result["info_hash"]
            )
        if result.get("magnet"):
            if opts.get("copy_magnet"):
                message += "\n" + tr_create("Magnet copied to clipboard.", language)
            else:
                message += "\n" + tr_create("Magnet: {magnet}", language).format(
                    magnet=result["magnet"]
                )
        wx.MessageBox(
            message,
            tr_create("Create Torrent", language),
            wx.OK | wx.ICON_INFORMATION,
        )

    poll()


def install_create_torrent_localization():
    legacy.MainFrame.on_create_torrent = localized_on_create_torrent
