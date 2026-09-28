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


def test_menu_help_text_translates_to_pt_br():
    source_strings = (
        "Connect to this profile",
        "Add/edit/delete profiles and connect",
        "Connect or switch profile",
        "Manage Profiles & Connect",
        "Add a torrent from a local file",
        "Add a torrent from a URL or Magnet link",
        "Create a .torrent file from a file or folder",
        "Exit application",
        "Start selected torrents",
        "Pause selected torrents",
        "Resume selected torrents",
        "Force a recheck/verification (if supported)",
        "Force an immediate tracker announce (if supported)",
        "Copy the info hash for selected torrents",
        "Copy a magnet link for selected torrents",
        "Open the download folder (if available)",
        "Remove selected torrents",
        "Remove selected torrents and data",
        "Select all torrents",
        "Search torrent indexers and add what you find",
        "Associate .torrent and magnet links with this app",
        "Check for updates",
        "Edit connected qBittorrent settings",
        "Edit connected Transmission settings",
        "Edit connected rTorrent settings",
        "Configure local session and application settings",
        "About this application",
    )
    for source in source_strings:
        assert main_ui_i18n.tr_main(source, "pt-BR") != source


def test_context_menu_labels_translate_to_pt_br():
    expected = {
        "Start": "Iniciar",
        "Pause": "Pausar",
        "Resume": "Retomar",
        "Force Recheck": "Forçar reverificação",
        "Force Reannounce": "Forçar novo anúncio",
        "Copy Info Hash": "Copiar info hash",
        "Copy Magnet Link": "Copiar link magnet",
        "Open Download Folder": "Abrir pasta de download",
        "Remove": "Remover",
        "Remove with Data": "Remover com dados",
    }
    for source, translated in expected.items():
        assert main_ui_i18n.tr_main(source, "pt-BR") == translated


def test_sidebar_labels_keep_counts_separate_from_translation_key():
    assert main_ui_i18n.sidebar_label("All", 12, "pt-BR") == "Todos (12)"
    assert main_ui_i18n.sidebar_label("Downloading", 3, "pt-BR") == "Baixando (3)"
    assert main_ui_i18n.sidebar_label("Failed", 1, "pt-BR") == "Com falha (1)"


def test_main_status_formatting_preserves_values():
    assert (
        main_ui_i18n.formatted_status("Downloaded: {percent:.1f}%", "pt-BR", percent=42.25)
        == "Baixado: 42.2%"
    )
    assert (
        main_ui_i18n.formatted_status("Connected to {name}", "pt-BR", name="Servidor")
        == "Conectado a Servidor"
    )
    assert (
        main_ui_i18n.formatted_status(
            "Failed to apply settings: {error}", "pt-BR", error="boom"
        )
        == "Falha ao aplicar as configurações: boom"
    )


def test_connection_and_about_labels_translate_to_pt_br():
    assert main_ui_i18n.tr_main("Connecting...", "pt-BR") == "Conectando..."
    assert main_ui_i18n.tr_main("Connection Failed", "pt-BR") == "Falha na conexão"
    assert main_ui_i18n.tr_main("Local session active", "pt-BR") == "Sessão local ativa"
    assert main_ui_i18n.tr_main("Profile", "pt-BR") == "Perfil"
    assert (
        main_ui_i18n.tr_main(
            "Another instance of SerrebiTorrent is already running.", "pt-BR"
        )
        == "Outra instância do SerrebiTorrent já está em execução."
    )
    assert main_ui_i18n.tr_main("Error", "pt-BR") == "Erro"
    assert (
        main_ui_i18n.tr_main(
            "A Windows desktop torrent manager designed for keyboard-first use and screen readers.",
            "pt-BR",
        )
        == "Um gerenciador de torrents para Windows projetado para uso prioritário pelo teclado e leitores de tela."
    )


def test_unknown_main_text_falls_back_to_source():
    assert main_ui_i18n.tr_main("Future main label", "pt-BR") == "Future main label"
    assert main_ui_i18n.tr_main("Future main label", "en") == "Future main label"


def test_active_preferences_controls_have_accessible_names():
    from pathlib import Path
    source = Path("main.py").read_text(encoding="utf-8")
    for snippet in [
        'self.path_input.SetName("Default Download Path")',
        'browse_btn.SetName("Browse default download path")',
        'self.dl_limit.SetName("Download Rate (bytes/s)")',
        'self.ul_limit.SetName("Upload Rate (bytes/s)")',
        'self.max_conn.SetName("Max Connections")',
        'self.max_slots.SetName("Max Upload Slots")',
        'self.port_input.SetName("Listening Port")',
    ]:
        assert snippet in source


def test_active_preferences_remaining_controls_have_accessible_names():
    from pathlib import Path
    source = Path("main.py").read_text(encoding="utf-8")
    for snippet in [
        'self.announce_ip_input.SetName("Announce IP")',
        'self.listen_interface_input.SetName("Listen interface")',
        'self.track_url_input.SetName("Tracker List URL")',
        'self.rss_interval.SetName("RSS Update Interval (seconds)")',
        'self.web_host.SetName("Web UI Bind Host")',
        'self.web_port.SetName("Web UI Port")',
        'self.web_user.SetName("Web UI Username")',
        'self.web_pass.SetName("Web UI Password")',
        'self.proxy_type.SetName("Proxy Type")',
        'self.proxy_host.SetName("Proxy Host")',
        'self.proxy_port.SetName("Proxy Port")',
        'self.proxy_user.SetName("Proxy Username")',
        'self.proxy_pass.SetName("Proxy Password")',
    ]:
        assert snippet in source


def test_active_profile_dialog_controls_have_accessible_names():
    from pathlib import Path
    source = Path("main.py").read_text(encoding="utf-8")
    for snippet in [
        'self.name_input.SetName("Profile Name")',
        'self.type_input.SetName("Client Type")',
        'self.url_input.SetName("URL or download path")',
        'self.url_browse_btn.SetName("Browse local download path")',
        'self.user_input.SetName("Username")',
        'self.pass_input.SetName("Password")',
    ]:
        assert snippet in source


def test_connection_manager_action_buttons_have_contextual_accessible_names():
    from pathlib import Path
    source = Path("main.py").read_text(encoding="utf-8")
    for snippet in [
        'add_btn.SetName("Add connection profile")',
        'edit_btn.SetName("Edit selected connection profile")',
        'del_btn.SetName("Delete selected connection profile")',
        'set_def_btn.SetName("Set selected connection profile as default")',
        'connect_btn.SetName("Connect using selected profile")',
    ]:
        assert snippet in source


def test_rss_rule_action_buttons_have_contextual_accessible_names():
    from pathlib import Path
    source = Path("main.py").read_text(encoding="utf-8")
    for snippet in [
        'add_btn.SetName("Add RSS rule")',
        'edit_btn.SetName("Edit selected RSS rule")',
        'del_btn.SetName("Delete selected RSS rule")',
        'toggle_btn.SetName("Toggle selected RSS rule")',
    ]:
        assert snippet in source
