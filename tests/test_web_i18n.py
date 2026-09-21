from pathlib import Path


INDEX = Path("web_static/index.html").read_text(encoding="utf-8")
I18N = Path("web_static/i18n.js").read_text(encoding="utf-8")
LOGIN = Path("web_static/login.html").read_text(encoding="utf-8")


def test_web_i18n_loads_before_app_runtime():
    assert 'src="i18n.js?v=1"' in INDEX
    assert 'src="app.js?v=7"' in INDEX
    assert INDEX.index('src="i18n.js?v=1"') < INDEX.index('src="app.js?v=7"')


def test_canonical_filter_values_are_not_translated_in_markup():
    for value in ("All", "Downloading", "Seeding", "Finished", "Stopped", "Failed", "RSS"):
        assert f'data-filter="{value}"' in INDEX


def test_pt_br_layer_covers_accessibility_critical_strings():
    expected = (
        "Pular para a lista de torrents",
        "Barra lateral de navegação",
        "Ações do torrent",
        "Menu de ações aberto. Use as setas para navegar.",
        "Selecione pelo menos um torrent primeiro.",
        "Seleção limpa",
    )
    for text in expected:
        assert text in I18N


def test_web_language_uses_saved_app_preference_with_system_fallback():
    assert "'/api/v2/app/prefs'" in I18N
    assert "prefs.language" in I18N
    assert "systemLanguage()" in I18N
    assert "document.documentElement.lang = 'pt-BR'" in I18N


def test_language_selector_uses_canonical_preference_values():
    assert 'id="appLanguage"' in I18N
    assert 'name="language"' in I18N
    assert '<option value="system">System default</option>' in I18N
    assert '<option value="en">English</option>' in I18N
    assert '<option value="pt-BR">Portuguese (Brazil)</option>' in I18N
    assert "pendingLanguage" in I18N
    assert "window.location.reload()" in I18N


def test_community_languages_load_from_generated_web_catalogs():
    assert "'/locales/index.json'" in I18N
    assert "availableLanguages" in I18N
    assert "populateExternalLanguageOptions" in I18N
    assert "loadExternalCatalog" in I18N
    assert "`/locales/${encodeURIComponent(language)}.json`" in I18N
    assert "externalTranslations" in I18N
    assert "Object.prototype.hasOwnProperty.call(externalTranslations, text)" in I18N


def test_dynamic_content_and_accessible_attributes_are_localized():
    assert "MutationObserver" in I18N
    assert "'aria-label'" in I18N
    assert "window.announceToSR" in I18N
    assert "window.alert" in I18N
    assert "window.confirm" in I18N


def test_user_supplied_torrent_names_are_not_translated():
    assert "isUserContentTextNode" in I18N
    assert ".col-name, #details-general h3" in I18N
    assert "element.matches('tr[data-hash]')" in I18N
    assert "element.classList.contains('col-name')" in I18N
    assert "element.classList.contains('row-check')" in I18N
    assert "`Selecionar ${source.slice(7)}`" in I18N


def test_remote_labels_are_translated_without_changing_api_keys():
    assert "REMOTE_WORDS" in I18N
    assert "#remoteSettingsFields label" in I18N
    assert "translateRemoteLabel" in I18N


def test_login_uses_generated_catalogs_with_english_source_fallback():
    assert '<html lang="en">' in LOGIN
    assert "navigator.language" in LOGIN
    assert "'serrebitorrent-language'" in LOGIN
    assert "'/locales/index.json'" in LOGIN
    assert "`/locales/${encodeURIComponent(language)}.json`" in LOGIN
    assert "document.documentElement.lang = language" in LOGIN
    assert "loginT('Login - SerrebiTorrent')" in LOGIN
    assert 'data-i18n="Username"' in LOGIN
    assert 'data-i18n="Invalid credentials."' in LOGIN
    assert 'role="alert"' in LOGIN
    assert 'aria-live="assertive"' in LOGIN
def test_removed_configured_language_keeps_selector_on_effective_fallback():
    assert "configuredLanguage = currentLanguage;" in I18N
    assert "If a configured catalog was removed or renamed" in I18N


def test_login_distinguishes_rate_limit_from_invalid_credentials():
    assert "res.status === 429" in LOGIN
    assert "'Too many failed attempts. Try again later.'" in LOGIN
    assert "error.textContent = loginT(source)" in LOGIN
    assert "aria-live=\"assertive\"" in LOGIN
