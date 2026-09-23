from pathlib import Path

import runtime_messages_i18n


def test_daily_torrent_messages_translate_to_pt_br():
    source_strings = (
        "Enter Magnet Link or URL:",
        "Add Torrent",
        "Magnet Link",
        "Adding magnet link...",
        "Downloading torrent file...",
        "Adding torrent...",
        "Torrent added",
        "Connect to a client before adding torrents.",
        "Not connected to any client.",
        "No torrents to start.",
        "No torrents to stop.",
        "Starting all torrents...",
        "Stopping all torrents...",
        "Recheck not supported by this client.",
        "Reannounce not supported by this client.",
        "No torrents selected.",
        "No torrent selected.",
        "Info hash copied to clipboard.",
        "Magnet link(s) copied to clipboard.",
        "Opened download folder.",
        "Download folder not available.",
    )
    for source in source_strings:
        assert runtime_messages_i18n.tr_runtime_message(source, "pt-BR") != source


def test_dynamic_messages_preserve_runtime_values():
    assert (
        runtime_messages_i18n.tr_runtime_message(
            "Failed to download torrent from URL: {error}", "pt-BR"
        ).format(error="boom")
        == "Falha ao baixar o torrent da URL: boom"
    )
    assert (
        runtime_messages_i18n.tr_runtime_message(
            "Adding {count} torrents...", "pt-BR"
        ).format(count=3)
        == "Adicionando 3 torrents..."
    )
    assert (
        runtime_messages_i18n.tr_runtime_message(
            "No torrents selected to {action}.", "pt-BR"
        ).format(action="pausar")
        == "Nenhum torrent selecionado para pausar."
    )


def test_canonical_action_keys_are_not_localized_before_dispatch():
    assert runtime_messages_i18n._action_verb("Start", "pt-BR") == "iniciar"
    assert runtime_messages_i18n._action_verb("Pause", "pt-BR") == "pausar"
    assert runtime_messages_i18n._action_verb("Resume", "pt-BR") == "retomar"
    assert runtime_messages_i18n._action_verb("Recheck", "pt-BR") == "reverificar"
    assert runtime_messages_i18n._action_progress("Start", "pt-BR") == "Iniciando torrents..."
    assert runtime_messages_i18n._action_progress("Pause", "pt-BR") == "Pausando torrents..."


def test_runtime_installer_wires_message_localization_late():
    installer = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    assert "from runtime_messages_i18n import install_runtime_message_localization" in installer
    assert "install_runtime_message_localization()" in installer

    source = Path("runtime_messages_i18n.py").read_text(encoding="utf-8")
    for assignment in (
        "legacy.MainFrame.on_search_torrents = localized_on_search_torrents",
        "legacy.MainFrame.on_add_url = localized_on_add_url",
        "legacy.MainFrame._apply_to_selected = localized_apply_to_selected",
        "legacy.MainFrame.on_recheck = localized_on_recheck",
        "legacy.MainFrame.on_reannounce = localized_on_reannounce",
        "legacy.MainFrame.on_copy_info_hash = localized_on_copy_info_hash",
        "legacy.MainFrame.on_copy_magnet = localized_on_copy_magnet",
        "legacy.MainFrame.on_open_download_folder = localized_on_open_download_folder",
    ):
        assert assignment in source
