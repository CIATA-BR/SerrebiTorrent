from translation_inventory import collect_source_messages, python_source_messages, web_source_messages


def test_inventory_collects_strings_outside_core_i18n_catalog():
    messages = python_source_messages()
    # main_ui_i18n.py, not the original i18n.py catalog.
    assert "&Add Torrent File...\tCtrl+O" in messages
    assert "Connected to {name}" in messages


def test_inventory_collects_web_catalog_source_strings():
    messages = web_source_messages()
    assert "Skip to torrent list" in messages
    assert "Torrent Actions" in messages
    assert "Language" in messages


def test_combined_inventory_is_unique_sorted_and_broad():
    messages = collect_source_messages()
    assert messages == sorted(set(messages), key=str.casefold)
    # Guard against accidentally regressing to the small central catalog only.
    assert len(messages) > 200
