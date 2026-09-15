from pathlib import Path

import runtime_actions_i18n


def test_association_messages_translate_to_pt_br():
    source_strings = (
        "Association is only supported on Windows for now.",
        "Info",
        "Torrent File",
        "URL:Magnet Link",
        "Associations registered successfully!",
        "Success",
        "Failed to register associations: {error}",
    )
    for source in source_strings:
        assert runtime_actions_i18n.tr_action(source, "pt-BR") != source


def test_association_error_preserves_error_text():
    assert (
        runtime_actions_i18n.tr_action(
            "Failed to register associations: {error}", "pt-BR"
        ).format(error="boom")
        == "Falha ao registrar associações: boom"
    )


def test_runtime_uses_localized_association_action():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "from runtime_actions_i18n import register_associations" in source
    assert "register_associations(self._language())" in source


def test_runtime_component_installation_is_deferred_to_localized_subclass():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    assert "def install_localized_runtime_components():" in source
    assert "def _localized_init_subclass(cls, **kwargs):" in source
    assert 'if cls.__name__ != "LocalizedMainFrame":' in source
    assert "install_localized_runtime_components()" in source
    assert "legacy.MainFrame.__init__ =" not in source
