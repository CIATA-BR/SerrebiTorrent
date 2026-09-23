from preferences_dialog import _language_index, _language_value


def test_language_index_finds_saved_preference():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_index(options, "pt-BR") == 2
    assert _language_index(options, "en") == 1


def test_language_index_falls_back_to_english_for_unknown_value():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_index(options, "es") == 1


def test_language_value_uses_stable_preference_value_not_display_label():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_value(options, 0) == "system"
    assert _language_value(options, 2) == "pt-BR"


def test_language_value_falls_back_to_system_for_invalid_selection():
    options = [("system", "Sistema"), ("en", "English")]
    assert _language_value(options, -1) == "system"
    assert _language_value(options, 99) == "system"
