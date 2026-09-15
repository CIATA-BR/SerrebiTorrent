import string

import i18n


def test_normalize_brazilian_portuguese_variants():
    assert i18n.normalize_language("pt_BR") == "pt-BR"
    assert i18n.normalize_language("pt-BR") == "pt-BR"
    assert i18n.normalize_language("pt_BR.UTF-8") == "pt-BR"


def test_unknown_language_falls_back_to_english():
    assert i18n.normalize_language("es-ES") == "en"
    assert i18n.translate("Settings", "es-ES") == "Settings"


def test_pt_br_translates_known_ui_string():
    assert i18n.translate("Settings", "pt-BR") == "Configurações"
    assert i18n.translate("Torrent List", "pt-BR") == "Lista de torrents"


def test_unknown_source_string_is_preserved():
    assert i18n.translate("Future untranslated label", "pt-BR") == "Future untranslated label"


def test_translator_returns_bound_callable():
    tr = i18n.translator("pt-BR")
    assert tr("Search") == "Pesquisar"


def test_search_ui_labels_have_pt_br_translations():
    source_strings = (
        "Search for Torrents",
        "&Search for:",
        "Sea&rch",
        "Sort &by:",
        "Search si&tes...",
        "My &indexers...",
        "Results",
        "&Add selected",
        "&Close",
        "Search sites",
        "&Indexers to search:",
        "Indexers to search",
        "Select &all",
        "Select &none",
        "Edit indexer",
        "Add indexer",
        "Indexer name",
        "Indexer URL",
        "API key",
        "My torrent indexers",
        "&Indexers:",
        "&Add...",
        "&Edit...",
        "&Remove",
    )
    for source in source_strings:
        assert i18n.translate(source, "pt-BR") != source


def test_torrent_creator_labels_have_pt_br_translations():
    source_strings = (
        "Create Torrent",
        "Source (file or folder):",
        "File...",
        "Folder...",
        "Output .torrent file:",
        "Save As...",
        "Torrent Options",
        "Private torrent (disables DHT/PEX/LSD in most clients)",
        "Piece size:",
        "Public tracker list (press Enter to add to Included trackers).",
        "Included trackers (one per line):",
        "Add Tracker",
        "Remove Selected",
        "Web Seeds (optional)",
        "One URL per line (HTTP/HTTPS).",
        "Metadata (optional)",
        "Comment:",
        "Source (written into info dict as 'source'):",
        "Created by:",
        "After Creation",
        "Add created torrent to the currently connected client",
        "Copy magnet link to clipboard",
        "Select File",
        "Select Folder",
        "Save Torrent As",
    )
    for source in source_strings:
        assert i18n.translate(source, "pt-BR") != source


def test_pt_br_mnemonics_are_preserved_for_keyboard_navigation():
    source_strings = (
        "&Search for:",
        "Sea&rch",
        "Sort &by:",
        "Search si&tes...",
        "My &indexers...",
        "&Add selected",
        "&Close",
        "&Indexers to search:",
        "Select &all",
        "Select &none",
        "&Name:",
        "&URL:",
        "API &key:",
        "&Indexers:",
        "&Add...",
        "&Edit...",
        "&Remove",
    )
    language_neutral = {"&URL:"}
    for source in source_strings:
        translated = i18n.translate(source, "pt-BR")
        assert "&" in translated
        if source not in language_neutral:
            assert translated != source


def test_pt_br_dynamic_search_messages_format_cleanly():
    tr = i18n.translator("pt-BR")
    assert tr("Searching {count} indexers...").format(count=3) == "Pesquisando em 3 indexadores..."
    assert tr("Search failed: {error}").format(error="timeout") == "Falha na pesquisa: timeout"
    assert tr("Results, {count} results").format(count=2) == "Resultados, 2 resultados"
    assert tr("Removed {name}.").format(name="Teste") == "Teste removido."


def test_catalogs_preserve_format_placeholders():
    formatter = string.Formatter()
    for language, catalog in i18n.CATALOGS.items():
        for source, translated in catalog.items():
            source_fields = {
                field_name
                for _literal, field_name, _format_spec, _conversion in formatter.parse(source)
                if field_name is not None
            }
            translated_fields = {
                field_name
                for _literal, field_name, _format_spec, _conversion in formatter.parse(translated)
                if field_name is not None
            }
            assert translated_fields == source_fields, (language, source, translated)


def _mnemonic(label):
    index = label.find("&")
    return label[index + 1].casefold() if 0 <= index < len(label) - 1 else None


def test_mnemonics_do_not_collide_within_a_dialog():
    dialogs = (
        ("&Search for:", "Sea&rch", "Sort &by:", "Search si&tes...",
         "My &indexers...", "&Add selected", "&Close"),
        ("&Indexers to search:", "Select &all", "Select &none"),
        ("&Name:", "&URL:", "API &key:"),
        ("&Indexers:", "&Add...", "&Edit...", "&Remove"),
    )
    for language in ("en", *i18n.CATALOGS):
        for labels in dialogs:
            keys = [_mnemonic(i18n.translate(label, language)) for label in labels]
            assert len(keys) == len(set(keys)), (language, labels, keys)
