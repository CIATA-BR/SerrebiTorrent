import json

from activity_history import ActivityHistory


def test_activity_history_persists_and_caps_entries(tmp_path):
    path = tmp_path / "activity.json"
    history = ActivityHistory(path=str(path), max_entries=2)

    history.append("one", kind="info", timestamp="2026-01-01T10:00:00+00:00")
    history.append("two", kind="success", timestamp="2026-01-01T10:01:00+00:00")
    history.append("three", kind="error", timestamp="2026-01-01T10:02:00+00:00")

    entries = history.entries()
    assert [entry["message"] for entry in entries] == ["two", "three"]
    assert entries[-1]["kind"] == "error"

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved) == 2


def test_activity_history_recovers_from_invalid_file(tmp_path):
    path = tmp_path / "activity.json"
    path.write_text("{broken", encoding="utf-8")
    history = ActivityHistory(path=str(path))

    assert history.entries() == []

    history.append("recovered", timestamp="2026-01-01T10:00:00+00:00")
    assert history.entries()[0]["message"] == "recovered"


def test_activity_history_clear(tmp_path):
    path = tmp_path / "activity.json"
    history = ActivityHistory(path=str(path))
    history.append("one", timestamp="2026-01-01T10:00:00+00:00")

    history.clear()

    assert history.entries() == []
