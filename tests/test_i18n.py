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
