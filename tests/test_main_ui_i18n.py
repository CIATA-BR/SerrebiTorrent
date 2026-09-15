import main_ui_i18n


def test_main_menu_labels_translate_to_pt_br():
    expected = {
        "&File": "&Arquivo",
        "&Actions": "&Ações",
        "&Tools": "&Ferramentas",
        "&Help": "A&juda",
        "&Start\tCtrl+S": "&Iniciar\tCtrl+S",
        "&Pause\tCtrl+P": "&Pausar\tCtrl+P",
        "&Resume\tCtrl+R": "&Retomar\tCtrl+R",
    }
    for source, translated in expected.items():
        assert main_ui_i18n.tr_main(source, "pt-BR") == translated


def test_main_menu_shortcuts_are_preserved():
    source_strings = (
        "&Connect...\tCtrl+Shift+C",
        "&Add Torrent File...\tCtrl+O",
        "Add &URL/Magnet...\tCtrl+U",
        "Create &Torrent...\tCtrl+N",
        "&Start\tCtrl+S",
        "&Pause\tCtrl+P",
        "&Resume\tCtrl+R",
        "Copy &Info Hash\tCtrl+I",
        "Copy &Magnet Link\tCtrl+M",
        "&Remove\tDel",
        "Remove with &Data\tShift+Del",
        "Select &All\tCtrl+A",
        "&Search for Torrents...\tCtrl+F",
        "Check for &Updates...\tF5",
        "Local Session &Settings...\tCtrl+,",
    )
    for source in source_strings:
        translated = main_ui_i18n.tr_main(source, "pt-BR")
        assert "&" in translated
        if "\t" in source:
            assert translated.split("\t", 1)[1] == source.split("\t", 1)[1]


def test_sidebar_labels_keep_counts_separate_from_translation_key():
    assert main_ui_i18n.sidebar_label("All", 12, "pt-BR") == "Todos (12)"
    assert main_ui_i18n.sidebar_label("Downloading", 3, "pt-BR") == "Baixando (3)"
    assert main_ui_i18n.sidebar_label("Failed", 1, "pt-BR") == "Com falha (1)"


def test_main_status_formatting_preserves_values():
    assert (
        main_ui_i18n.formatted_status("Downloaded: {percent:.1f}%", "pt-BR", percent=42.25)
        == "Baixado: 42.2%"
    )


def test_unknown_main_text_falls_back_to_source():
    assert main_ui_i18n.tr_main("Future main label", "pt-BR") == "Future main label"
    assert main_ui_i18n.tr_main("Future main label", "en") == "Future main label"
