from pathlib import Path

from translation_catalog import (
    parse_po_text,
    render_po,
    render_pot,
    validate_catalog,
    validate_translation,
)


def test_parse_po_reads_metadata_and_translations():
    metadata, translations = parse_po_text(
        'msgid ""\n'
        'msgstr ""\n'
        '"Language: es-ES\\n"\n'
        '"X-Language-Name: Español (España)\\n"\n'
        '\n'
        'msgid "Settings"\n'
        'msgstr "Configuración"\n'
    )
    assert metadata["Language"] == "es-ES"
    assert metadata["X-Language-Name"] == "Español (España)"
    assert translations["Settings"] == "Configuración"


def test_fuzzy_po_entry_is_not_loaded():
    _metadata, translations = parse_po_text(
        '#, fuzzy\nmsgid "Settings"\nmsgstr "Configuración"\n'
    )
    assert "Settings" not in translations


def test_placeholder_validation_requires_same_named_fields():
    assert validate_translation("Connected to {name}", "Conectado a {name}") == []
    problems = validate_translation("Connected to {name}", "Conectado")
    assert any("Placeholders differ" in problem for problem in problems)


def test_mnemonic_validation_requires_ampersand_when_source_has_one():
    assert validate_translation("&Search", "&Pesquisar") == []
    assert "Keyboard mnemonic marker '&' is missing." in validate_translation("&Search", "Pesquisar")


def test_catalog_validation_returns_only_problem_entries():
    result = validate_catalog({"Connected to {name}": "Conectado", "Settings": "Configurações"})
    assert "Connected to {name}" in result
    assert "Settings" not in result


def test_render_po_round_trips_unicode_translation():
    text = render_po("pt-BR", "Português (Brasil)", {"Settings": "Configurações"})
    metadata, translations = parse_po_text(text)
    assert metadata["Language"] == "pt-BR"
    assert translations["Settings"] == "Configurações"


def test_render_pot_contains_unique_source_messages():
    text = render_pot(["Settings", "Settings", "Search"])
    assert text.count('msgid "Settings"') == 1
    assert text.count('msgid "Search"') == 1


def test_printf_placeholders_must_match_exactly():
    assert validate_translation("Downloaded: %0.1f%%", "Baixado: %0.1f%%") == []
    problems = validate_translation("Downloaded: %0.1f%%", "Baixado: %s")
    assert any("Printf placeholders differ" in problem for problem in problems)


def test_keyboard_shortcut_suffix_must_be_preserved():
    assert validate_translation("&Open\tCtrl+O", "&Abrir\tCtrl+O") == []
    problems = validate_translation("&Open\tCtrl+O", "&Abrir\tCtrl+A")
    assert any("Keyboard shortcuts differ" in problem for problem in problems)


def test_newline_count_must_be_preserved():
    assert validate_translation("Line one\nLine two", "Linha um\nLinha dois") == []
    problems = validate_translation("Line one\nLine two", "Linha um Linha dois")
    assert any("Newline count differs" in problem for problem in problems)


def test_mnemonic_count_must_match_and_escaped_ampersands_are_ignored():
    assert validate_translation("Save && E&xit", "Salvar && Sai&r") == []
    missing = validate_translation("&Search", "Pesquisar")
    extra = validate_translation("Search", "&Pesquisar")
    assert any("Keyboard mnemonic count differs" in problem for problem in missing)
    assert any("Keyboard mnemonic count differs" in problem for problem in extra)
