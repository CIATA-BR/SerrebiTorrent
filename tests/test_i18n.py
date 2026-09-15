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
    for source in source_strings:
        translated = i18n.translate(source, "pt-BR")
        assert "&" in translated
        assert translated != source


def test_pt_br_dynamic_search_messages_format_cleanly():
    tr = i18n.translator("pt-BR")
    assert tr("Searching {count} indexers...").format(count=3) == "Pesquisando em 3 indexadores..."
    assert tr("Search failed: {error}").format(error="timeout") == "Falha na pesquisa: timeout"
    assert tr("Results, {count} results").format(count=2) == "Resultados, 2 resultados"
    assert tr("Removed {name}.").format(name="Teste") == "Teste removido."
