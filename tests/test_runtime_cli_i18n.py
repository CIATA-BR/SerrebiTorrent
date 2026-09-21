from pathlib import Path

import runtime_cli_i18n


def test_cli_messages_translate_to_pt_br():
    messages = (
        "Adding magnet link from CLI...",
        "Magnet link added from CLI",
        "Adding torrent file from CLI...",
        "Torrent file added from CLI",
        "Auto-started new torrent(s)",
        "No client connected.",
    )
    for source in messages:
        assert runtime_cli_i18n.tr_cli(source, "pt-BR") != source


def test_cli_dynamic_messages_preserve_values():
    assert runtime_cli_i18n.tr_cli(
        "Invalid argument: {arg}", "pt-BR"
    ).format(arg="bad") == "Argumento inválido: bad"
    assert runtime_cli_i18n.tr_cli(
        "Failed to add torrent: {error}", "pt-BR"
    ).format(error="boom") == "Falha ao adicionar torrent: boom"


def test_runtime_installs_cli_localization_lazily():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    assert "install_cli_localization" in source
    assert "install_localized_runtime_components" in source
