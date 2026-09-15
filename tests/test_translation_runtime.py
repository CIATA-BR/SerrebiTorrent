import i18n
import translation_runtime


def test_runtime_catalog_supports_language_not_compiled_into_i18n():
    translation_runtime.install_runtime_catalogs()
    translation_runtime.install_session_catalog("es-ES", {"Settings": "Configuración"})
    translation_runtime.set_session_language("es-ES")
    try:
        assert i18n.translate("Settings", "system") == "Configuración"
        assert i18n.translate("Unknown source", "system") == "Unknown source"
        assert i18n.normalize_language("es_ES") == "es-ES"
    finally:
        translation_runtime.clear_session_language()


def test_language_options_include_external_catalog_languages():
    translation_runtime.install_runtime_catalogs()
    translation_runtime.install_session_catalog("fr-FR", {"Settings": "Paramètres"})
    values = dict(i18n.language_options("en"))
    assert "fr-FR" in values
    assert values["fr-FR"] == "fr-FR"


def test_pt_br_packaged_overlay_keeps_legacy_catalog_fallback():
    translation_runtime.install_runtime_catalogs()
    assert i18n.translate("Contribute &Translations...", "pt-BR") == "Contribuir com &traduções..."
    # Existing strings not duplicated in the small external overlay still fall back.
    assert i18n.translate("Settings", "pt-BR") == "Configurações"
