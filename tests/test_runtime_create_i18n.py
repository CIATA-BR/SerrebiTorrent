from pathlib import Path

import runtime_create_i18n


def test_create_torrent_messages_translate_to_pt_br():
    messages = (
        "Create Torrent",
        "Hashing pieces and generating torrent metadata...",
        "Adding created torrent...",
        "Created torrent added",
        "Source path is required.",
        "Output .torrent path is required.",
    )
    for source in messages:
        assert runtime_create_i18n.tr_create(source, "pt-BR") != source


def test_create_torrent_dynamic_messages_preserve_values():
    assert runtime_create_i18n.tr_create(
        "Created torrent, but failed to add to client: {error}", "pt-BR"
    ).format(error="boom") == (
        "Torrent criado, mas houve falha ao adicioná-lo ao cliente: boom"
    )


def test_runtime_installs_creator_localization_lazily():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    assert "install_create_torrent_localization" in source
    assert "install_localized_runtime_components" in source
