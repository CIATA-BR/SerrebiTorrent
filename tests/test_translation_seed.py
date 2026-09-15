from pathlib import Path

from translation_seed import seed_entries


def test_pt_br_seed_includes_existing_desktop_catalog():
    entries = seed_entries(Path("."), "pt-BR")
    assert entries["Settings"].msgstr == "Configurações"
    assert entries["Search"].msgstr == "Pesquisar"


def test_pt_br_seed_includes_existing_web_catalog():
    entries = seed_entries(Path("."), "pt-BR")
    assert entries["Skip to torrent list"].msgstr == "Pular para a lista de torrents"


def test_packaged_po_overrides_legacy_seed_for_same_key():
    entries = seed_entries(Path("."), "pt-BR")
    assert entries["Translation Center"].msgstr == "Central de traduções"
