import i18n
import external_catalog_runtime as runtime_catalogs
from translation_catalog import render_po


def _restore_i18n(catalogs, supported, options, normalize, installed):
    i18n.CATALOGS.clear()
    i18n.CATALOGS.update(catalogs)
    i18n.SUPPORTED_LANGUAGES = supported
    i18n.LANGUAGE_OPTIONS = options
    i18n.normalize_language = normalize
    runtime_catalogs._INSTALLED_CODES = installed


def test_po_catalog_adds_language_without_python_catalog_change(tmp_path, monkeypatch):
    catalog_path = tmp_path / "es-ES.po"
    catalog_path.write_text(
        render_po(
            "es-ES",
            "Español (España)",
            {
                "Settings": "Configuración",
                "Search": "Buscar",
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SERREBITORRENT_LOCALES_DIR", str(tmp_path))

    before_catalogs = {code: dict(values) for code, values in i18n.CATALOGS.items()}
    before_supported = i18n.SUPPORTED_LANGUAGES
    before_options = i18n.LANGUAGE_OPTIONS
    before_normalize = i18n.normalize_language
    before_installed = runtime_catalogs._INSTALLED_CODES
    try:
        installed = runtime_catalogs.install_external_catalogs()
        assert installed == ("es-ES",)
        assert i18n.normalize_language("es_ES") == "es-ES"
        assert i18n.normalize_language("es") == "es-ES"
        assert i18n.translate("Settings", "es-ES") == "Configuración"
        assert i18n.translate("Unknown source", "es-ES") == "Unknown source"
        assert ("es-ES", "Español (España)") in i18n.language_options("en")
        assert "es-ES" in i18n.SUPPORTED_LANGUAGES
    finally:
        _restore_i18n(
            before_catalogs,
            before_supported,
            before_options,
            before_normalize,
            before_installed,
        )


def test_external_catalog_extends_existing_language_instead_of_erasing_fallback(tmp_path, monkeypatch):
    catalog_path = tmp_path / "pt-BR.po"
    catalog_path.write_text(
        render_po("pt-BR", "Português (Brasil)", {"Settings": "Preferências PO"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SERREBITORRENT_LOCALES_DIR", str(tmp_path))

    before_catalogs = {code: dict(values) for code, values in i18n.CATALOGS.items()}
    before_supported = i18n.SUPPORTED_LANGUAGES
    before_options = i18n.LANGUAGE_OPTIONS
    before_normalize = i18n.normalize_language
    before_installed = runtime_catalogs._INSTALLED_CODES
    try:
        runtime_catalogs.install_external_catalogs()
        assert i18n.translate("Settings", "pt-BR") == "Preferências PO"
        # A key absent from the PO still comes from the established runtime catalog.
        assert i18n.translate("Search", "pt-BR") == "Pesquisar"
    finally:
        _restore_i18n(
            before_catalogs,
            before_supported,
            before_options,
            before_normalize,
            before_installed,
        )
