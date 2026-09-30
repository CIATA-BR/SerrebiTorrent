import inspect
import json
import pytest
from pathlib import Path

import i18n
import runtime_actions_i18n
import translation_center
from translation_catalog import load_po


def test_source_messages_include_existing_catalog_and_contributor_strings():
    messages = translation_center.source_messages()
    assert "Settings" in messages
    assert "Translation Center" in messages
    assert "Import PO..." in messages
    assert messages == sorted(set(messages), key=lambda s: (s.casefold(), s))


def test_load_shipped_catalog_returns_the_reviewed_entries():
    shipped = translation_center.load_shipped_catalog("de-DE")

    assert shipped == load_po(Path("locales") / "de-DE.po").translations
    assert shipped


def test_load_shipped_catalog_is_empty_for_a_language_that_does_not_exist():
    assert translation_center.load_shipped_catalog("xx-XX") == {}


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


def test_translation_center_validates_language_code_before_export():
    source = inspect.getsource(translation_center.TranslationCenterDialog._on_export)
    assert "validate_catalog_code(code)" in source
    assert "hyphenated BCP47-style subtags" in source
    assert "self.language_code.SetFocus()" in source


def test_center_seeds_from_the_shipped_catalog_before_the_local_draft():
    source = inspect.getsource(translation_center.TranslationCenterDialog._load_language)

    assert "load_shipped_catalog" in source
    assert "load_draft" in source
    # The contributor's own draft must win, or reopening would discard their work.
    assert source.index("load_shipped_catalog") < source.index("load_draft")


def test_center_imports_a_catalog_without_needing_the_portal():
    source = inspect.getsource(translation_center.TranslationCenterDialog._on_import)

    assert "load_po" in source
    assert "save_draft" in source
    assert "ONLINE_TRANSLATION_URL" not in source


def test_import_button_is_wired_and_the_portal_button_stays_available():
    source = inspect.getsource(translation_center.TranslationCenterDialog.__init__)

    assert 'label="&Import PO..."' in source
    assert "self.import_button.Bind(wx.EVT_BUTTON, self._on_import)" in source
    # The hosted portal remains an option for contributors who can use it.
    assert 'label="Open &online translation"' in source
    assert "self.online_button.Bind(wx.EVT_BUTTON, self._on_online)" in source



def test_translation_draft_read_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(translation_center, "_data_dir", lambda: tmp_path)
    monkeypatch.setattr(translation_center, "DRAFT_MAX_BYTES", 8)
    path = translation_center.draft_path("pt-BR")
    path.write_bytes(b"123456789")

    assert translation_center.load_draft("pt-BR") == {}


def test_translation_draft_save_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(translation_center, "_data_dir", lambda: tmp_path)

    path = translation_center.save_draft("pt-BR", "Portuguese", {"Settings": "Configurações"})

    assert path.is_file()
    assert not list(tmp_path.glob("pt-BR.json.*.tmp"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["translations"]["Settings"] == "Configurações"


def test_translation_draft_save_rejects_output_larger_than_read_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(translation_center, "_data_dir", lambda: tmp_path)
    monkeypatch.setattr(translation_center, "DRAFT_MAX_BYTES", 64)

    path = translation_center.draft_path("pt-BR")
    path.write_text('{"language":"pt-BR","translations":{}}', encoding="utf-8")

    with pytest.raises(ValueError, match="4 MB limit"):
        translation_center.save_draft(
            "pt-BR",
            "Português (Brasil)",
            {"Settings": "x" * 128},
        )

    assert path.read_text(encoding="utf-8") == '{"language":"pt-BR","translations":{}}'


def test_translation_draft_rejects_non_object_json(tmp_path, monkeypatch):
    monkeypatch.setattr(translation_center, "_data_dir", lambda: tmp_path)
    path = translation_center.draft_path("pt-BR")
    path.write_text("[]", encoding="utf-8")

    assert translation_center.load_draft("pt-BR") == {}


def test_translation_draft_rejects_non_object_translations(tmp_path, monkeypatch):
    monkeypatch.setattr(translation_center, "_data_dir", lambda: tmp_path)
    path = translation_center.draft_path("pt-BR")
    path.write_text(
        json.dumps({"translations": ["bad"]}),
        encoding="utf-8",
    )

    assert translation_center.load_draft("pt-BR") == {}


def test_translation_draft_save_feedback_handles_size_errors(monkeypatch):
    calls = []
    monkeypatch.setattr(
        translation_center,
        "save_draft",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("Translation draft exceeds the 4 MB limit.")),
    )
    monkeypatch.setattr(
        translation_center.wx,
        "MessageBox",
        lambda message, *args, **kwargs: calls.append(message),
    )

    assert translation_center._save_draft_with_feedback(
        None, "pt-BR", "Português (Brasil)", {"Settings": "Configurações"}
    ) is False
    assert "4 MB limit" in calls[0]


def test_translation_center_handlers_use_safe_draft_save_wrapper():
    source = inspect.getsource(translation_center.TranslationCenterDialog)
    assert source.count("_save_draft_with_feedback") >= 3


def test_translation_center_actions_have_contextual_accessible_names():
    source = inspect.getsource(translation_center.TranslationCenterDialog.__init__)

    for name in (
        "Previous translation entry",
        "Save current translation entry",
        "Next translation entry",
        "Export translation catalog as PO",
        "Import translation catalog from PO",
        "Open online translation portal",
        "Close Translation Center",
    ):
        assert f'SetName("{name}")' in source
