import inspect

import i18n
import runtime_actions_i18n
import translation_center


def test_source_messages_include_existing_catalog_and_contributor_strings():
    messages = translation_center.source_messages()
    assert "Settings" in messages
    assert "Translation Center" in messages
    assert messages == sorted(set(messages), key=str.casefold)


def test_progress_counts_translated_and_needs_review_entries():
    messages = ["Settings", "Connected to {name}", "Search"]
    translations = {
        "Settings": "Configurações",
        "Connected to {name}": "Conectado",
    }
    translated, total, review = translation_center.progress(messages, translations)
    assert (translated, total, review) == (2, 3, 1)


def test_pt_br_center_starts_from_existing_runtime_catalog():
    assert i18n.CATALOGS["pt-BR"]["Settings"] == "Configurações"
    assert "pt-BR" in inspect.getsource(translation_center.TranslationCenterDialog._load_language)
    assert "i18n.CATALOGS" in inspect.getsource(translation_center.TranslationCenterDialog._load_language)


def test_runtime_attaches_translation_center_only_after_localized_frame_init():
    source = inspect.getsource(runtime_actions_i18n._localized_init_subclass)
    assert "result = original_init" in source
    assert "attach_translation_center(self)" in source
    assert source.index("result = original_init") < source.index("attach_translation_center(self)")


def test_online_translation_does_not_embed_credentials():
    source = inspect.getsource(translation_center)
    assert "SERREBITORRENT_TRANSLATION_URL" in source
    assert "GITHUB_TOKEN" not in source
    assert "ghp_" not in source


def test_ciata_translation_portal_is_the_default_online_endpoint():
    assert translation_center.DEFAULT_ONLINE_TRANSLATION_URL == "https://torrent.ciata.org.br/"
    assert translation_center.ONLINE_TRANSLATION_URL
