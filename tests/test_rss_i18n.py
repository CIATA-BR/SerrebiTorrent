from pathlib import Path

import rss_i18n


def test_rss_labels_translate_to_pt_br():
    source_strings = (
        "RSS Articles",
        "RSS Feeds",
        "Title",
        "Add Feed",
        "Remove Feed",
        "Refresh All",
        "Rules",
        "Import FlexGet",
        "Enter RSS Feed URL:",
        "Import FlexGet Config",
        "Import Complete",
        "Edit RSS Rule",
        "Add RSS Rule",
        "Regex Pattern:",
        "Rule Type:",
        "RSS Rules Manager",
        "Type",
        "Pattern",
        "Scope",
        "Enabled",
        "Yes",
        "No",
    )
    for source in source_strings:
        assert rss_i18n.tr_rss(source, "pt-BR") != source


def test_rss_dynamic_messages_preserve_values():
    assert (
        rss_i18n.tr_rss("Remove feed {url}?", "pt-BR").format(url="https://example.test/feed")
        == "Remover o feed https://example.test/feed?"
    )
    assert (
        rss_i18n.tr_rss("Imported {feeds} feeds and {rules} rules.", "pt-BR").format(
            feeds=2, rules=3
        )
        == "Importados 2 feeds e 3 regras."
    )
    assert (
        rss_i18n.tr_rss("Adding torrent: {title}...", "pt-BR").format(title="Ubuntu")
        == "Adicionando torrent: Ubuntu..."
    )


def test_runtime_installer_wires_localized_rss_components():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    for assignment in (
        "legacy.ArticleListCtrl = LocalizedArticleListCtrl",
        "legacy.RuleEditDialog = LocalizedRuleEditDialog",
        "legacy.RulesManagerDialog = LocalizedRulesManagerDialog",
        "legacy.RSSPanel = LocalizedRSSPanel",
    ):
        assert assignment in source


def test_localized_rss_buttons_receive_contextual_accessible_names():
    from pathlib import Path
    source = Path("rss_i18n.py").read_text(encoding="utf-8")
    assert '"Delete": "Delete selected RSS rule"' in source
    assert '"Toggle": "Toggle selected RSS rule"' in source
    assert '"Remove Feed": "Remove selected RSS feed"' in source
    assert '"Import FlexGet": "Import RSS feeds and rules from FlexGet"' in source
    assert "child.SetName(tr_rss(rule_button_names[source], self._rss_language))" in source
    assert "child.SetName(tr_rss(feed_button_names[source], self._rss_language))" in source
