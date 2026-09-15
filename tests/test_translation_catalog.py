from pathlib import Path

from translation_catalog import (
    CatalogEntry,
    catalog_stats,
    load_po,
    merge_template,
    placeholders,
    save_po,
    validate_entry,
)


def test_po_round_trip_preserves_utf8_flags_and_context(tmp_path):
    path = tmp_path / "es-ES.po"
    entries = {
        "Hello {name}": CatalogEntry(
            "Hello {name}",
            "Hola {name}",
            context="Greeting",
            comments=["Shown in a welcome dialog"],
            flags={"fuzzy"},
        )
    }
    save_po(path, entries, "es-ES")
    loaded = load_po(path)
    assert loaded["Hello {name}"].msgstr == "Hola {name}"
    assert loaded["Hello {name}"].context == "Greeting"
    assert "fuzzy" in loaded["Hello {name}"].flags


def test_placeholder_validation_rejects_missing_fields():
    entry = CatalogEntry("Connected to {name}", "Conectado")
    errors = validate_entry(entry)
    assert any("Placeholder mismatch" in error for error in errors)


def test_mnemonic_validation_requires_ampersand():
    entry = CatalogEntry("&Open", "Abrir")
    assert "Keyboard mnemonic '&' is missing from the translation" in validate_entry(entry)


def test_template_merge_keeps_existing_translation_and_adds_new_source():
    current = {"One": CatalogEntry("One", "Um")}
    merged = merge_template(["One", "Two"], current)
    assert merged["One"].msgstr == "Um"
    assert merged["Two"].msgstr == ""


def test_catalog_stats_separate_review_from_completed():
    entries = {
        "A": CatalogEntry("A", "AA"),
        "B": CatalogEntry("B", "BB", flags={"fuzzy"}),
        "C": CatalogEntry("C", ""),
    }
    assert catalog_stats(entries) == (3, 1, 1)


def test_placeholders_support_named_format_fields():
    assert placeholders("{count} results from {source}") == {"count", "source"}


def test_seed_pt_br_catalog_is_valid():
    path = Path("locales/pt-BR.po")
    entries = load_po(path)
    assert entries["Contribute &Translations..."].msgstr == "Contribuir com &traduções..."
    for entry in entries.values():
        assert validate_entry(entry) == []
