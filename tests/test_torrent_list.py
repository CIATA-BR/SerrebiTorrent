from pathlib import Path

from torrent_list import torrent_eta, torrent_status_text


def test_torrent_status_translates_stopped_and_checking():
    assert torrent_status_text({"state": 0}, "pt-BR") == "Parados"
    assert torrent_status_text({"state": 0, "hashing": 1}, "pt-BR") == "Verificando"


def test_torrent_status_translates_downloading_progress():
    row = {
        "state": 1,
        "size": 1000,
        "done": 425,
        "down_rate": 2048,
    }
    assert torrent_status_text(row, "pt-BR") == "Baixado: 42.5%; 2.0 KB/s"


def test_torrent_status_translates_seeding():
    row = {"state": 1, "size": 1000, "done": 1000}
    assert torrent_status_text(row, "pt-BR") == "Semeando"


def test_backend_message_is_preserved_when_meaningful():
    row = {"state": 0, "message": "Tracker timed out"}
    assert torrent_status_text(row, "pt-BR") == "Parados (Tracker timed out)"


def test_torrent_eta_uses_explicit_value_or_derives_from_rate():
    assert torrent_eta({"eta": 17}) == 17
    assert torrent_eta({"size": 1000, "done": 500, "down_rate": 100}) == 5
    assert torrent_eta({"size": 1000, "done": 500, "down_rate": 0}) == -1



def test_torrent_list_exposes_sortable_queue_column():
    source = Path("torrent_list.py").read_text(encoding="utf-8")
    assert "COL_QUEUE = 8" in source
    assert '(COL_QUEUE, "Queue", 80)' in source
    assert 'row.get("queue_position")' in source
    assert 'COL_QUEUE: "queue_position"' in source
