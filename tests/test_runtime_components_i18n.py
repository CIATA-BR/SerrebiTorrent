from pathlib import Path

import runtime_components_i18n


def test_tray_labels_translate_to_pt_br():
    expected = {
        "Start All": "Iniciar todos",
        "Stop All": "Parar todos",
        "Current": "Atual",
        "Connection Manager...": "Gerenciador de conexões...",
        "Switch Profile": "Trocar perfil",
        "Local Session Settings...": "Configurações da sessão local...",
        "Settings": "Configurações",
        "Exit": "Sair",
    }
    for source, translated in expected.items():
        assert runtime_components_i18n.tr_runtime(source, "pt-BR") == translated


def test_open_app_label_preserves_application_name():
    assert (
        runtime_components_i18n.tr_runtime("Open {name}", "pt-BR").format(name="SerrebiTorrent")
        == "Abrir SerrebiTorrent"
    )


def test_detail_priority_labels_translate_to_pt_br():
    assert runtime_components_i18n.tr_runtime("Priority", "pt-BR") == "Prioridade"
    assert runtime_components_i18n.tr_runtime("High", "pt-BR") == "Alta"
    assert runtime_components_i18n.tr_runtime("Normal", "pt-BR") == "Normal"
    assert runtime_components_i18n.tr_runtime("Skip", "pt-BR") == "Ignorar"


def test_runtime_installer_wires_localized_detail_and_tray_components():
    source = Path("runtime_actions_i18n.py").read_text(encoding="utf-8")
    for assignment in (
        "legacy.FilesListCtrl = LocalizedFilesListCtrl",
        "legacy.PeersListCtrl = LocalizedPeersListCtrl",
        "legacy.TrackersListCtrl = LocalizedTrackersListCtrl",
        "legacy.TorrentDetailsPanel = LocalizedTorrentDetailsPanel",
        "legacy.TaskBarIcon = LocalizedTaskBarIcon",
    ):
        assert assignment in source
