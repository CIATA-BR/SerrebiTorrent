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



def test_main_preferences_save_has_ui_error_boundary():
    from pathlib import Path

    source = Path("app_entry.py").read_text(encoding="utf-8")
    start = source.index("    def on_prefs(self, event):")
    end = source.index("    def on_connect(self, event):", start)
    block = source[start:end]

    save = block.index("self.config_manager.set_preferences(prefs)")
    error_box = block.index("wx.MessageBox(", save)
    runtime_apply = block.index("legacy.SessionManager.get_instance().apply_preferences(prefs)")

    assert "except Exception as exc" in block[save:error_box]
    assert error_box < runtime_apply
    assert 'self._("Failed to apply settings: {error}")' in block
