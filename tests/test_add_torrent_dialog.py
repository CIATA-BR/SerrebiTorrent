from pathlib import Path

import add_torrent_dialog


def test_add_torrent_dialog_strings_translate_to_pt_br():
    expected = {
        "Save Path:": "Salvar caminho:",
        "Save Path": "Salvar caminho",
        "Files:": "Arquivos:",
        "Files": "Arquivos",
        "Select All": "Selecionar tudo",
        "Deselect All": "Desmarcar tudo",
        "Choose Download Directory": "Selecione o diretório de download",
        "Check": "Marcar",
        "Uncheck": "Desmarcar",
        "Check All": "Marcar todos",
        "Uncheck All": "Desmarcar todos",
    }
    for source, translated in expected.items():
        assert add_torrent_dialog.tr_add(source, "pt-BR") == translated


def test_add_torrent_title_preserves_torrent_name():
    assert (
        add_torrent_dialog.tr_add("Add Torrent: {name}", "pt-BR").format(name="Ubuntu")
        == "Adicionar torrent: Ubuntu"
    )


def test_dialog_source_has_explicit_accessible_names():
    source = Path("add_torrent_dialog.py").read_text(encoding="utf-8")
    assert 'self.path_input.SetName(self._("Save Path"))' in source
    assert 'self.tree.SetName(self._("Files"))' in source


def test_runtime_wires_localized_add_torrent_dialog():
    source = Path("app_entry.py").read_text(encoding="utf-8")
    assert "from add_torrent_dialog import AddTorrentDialog as LocalizedAddTorrentDialog" in source
    assert "legacy.AddTorrentDialog = LocalizedAddTorrentDialog" in source
