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


def test_dynamic_content_and_accessible_attributes_are_localized():
    assert "MutationObserver" in I18N
    assert "'aria-label'" in I18N
    assert "window.announceToSR" in I18N
    assert "window.alert" in I18N
    assert "window.confirm" in I18N


def test_login_keeps_english_source_and_pt_br_browser_fallback():
    assert '<html lang="en">' in LOGIN
    assert "navigator.language" in LOGIN
    assert "document.documentElement.lang = 'pt-BR'" in LOGIN
    assert 'role="alert"' in LOGIN
    assert 'aria-live="assertive"' in LOGIN
    assert "Nome de usuário" in LOGIN
    assert "Credenciais inválidas." in LOGIN
