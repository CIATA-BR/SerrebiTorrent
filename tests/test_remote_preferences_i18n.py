from pathlib import Path

import remote_preferences_i18n


def test_remote_preferences_categories_translate_to_pt_br():
    expected = {
        "General": "Geral",
        "Connection": "Conexão",
        "Speed": "Velocidade",
        "Network": "Rede",
        "Limits": "Limites",
        "Queue": "Fila",
        "Files": "Arquivos",
        "Notifications": "Notificações",
        "Other": "Outros",
        "Preferences": "Preferências",
        "Web UI": "Interface Web",
    }
    for source, translated in expected.items():
        assert remote_preferences_i18n.tr_remote(source, "pt-BR") == translated


def test_remote_choice_labels_translate_without_changing_values():
    expected = {
        "Every day": "Todos os dias",
        "Prefer encryption": "Preferir criptografia",
        "Proxy disabled": "Proxy desativado",
        "Pause torrent": "Pausar torrent",
        "TCP and uTP": "TCP e uTP",
        "Fixed slots": "Slots fixos",
        "On": "Ativado",
        "Off": "Desativado",
    }
    for source, translated in expected.items():
        assert remote_preferences_i18n.tr_remote(source, "pt-BR") == translated


def test_remote_dynamic_messages_preserve_values():
    assert (
        remote_preferences_i18n.tr_remote("{client} Remote Settings", "pt-BR").format(
            client="qBittorrent"
        )
        == "Configurações remotas do qBittorrent"
    )
    assert (
        remote_preferences_i18n.tr_remote("Fetching {name} preferences...", "pt-BR").format(
            name="Transmission"
        )
        == "Obtendo preferências do Transmission..."
    )
    assert (
        remote_preferences_i18n.tr_remote("{name} preferences saved", "pt-BR").format(
            name="rTorrent"
        )
        == "Preferências do rTorrent salvas"
    )


def test_remote_field_label_translation_keeps_technical_terms():
    assert remote_preferences_i18n._translate_field_label("Web UI Port", "pt-BR") == "Web UI Porta"
    assert remote_preferences_i18n._translate_field_label("Proxy Password", "pt-BR") == "Proxy Senha"
    assert remote_preferences_i18n._translate_field_label("Max Connections", "pt-BR") == "Máx. Conexões"


def test_runtime_installer_defers_remote_preferences_patch():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    assert "install_remote_preferences_localization()" in source
    assert "def install_localized_runtime_components():" in source


def test_importing_runtime_does_not_replace_detail_class_immediately():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    before_installer = source.split("def install_localized_runtime_components():", 1)[0]
    assert "legacy.TorrentDetailsPanel = LocalizedTorrentDetailsPanel" not in before_installer
