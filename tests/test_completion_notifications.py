from completion_notifications import CompletionTracker


def _torrent(info_hash, done, size=100, name=None):
    return {
        "hash": info_hash,
        "name": name or info_hash,
        "done": done,
        "size": size,
    }


def test_first_snapshot_is_baseline_only():
    tracker = CompletionTracker()

    assert tracker.update([
        _torrent("a", 100, name="Already done"),
        _torrent("b", 25, name="Downloading"),
    ]) == []


def test_incomplete_to_complete_is_reported_once():
    tracker = CompletionTracker()
    tracker.update([_torrent("a", 90, name="Example")])

    assert tracker.update([_torrent("a", 100, name="Example")]) == ["Example"]
    assert tracker.update([_torrent("a", 100, name="Example")]) == []


def test_new_already_complete_torrent_is_not_false_positive():
    tracker = CompletionTracker()
    tracker.update([_torrent("a", 50)])

    assert tracker.update([
        _torrent("a", 50),
        _torrent("b", 100, name="New complete"),
    ]) == []


def test_reset_requires_a_new_baseline():
    tracker = CompletionTracker()
    tracker.update([_torrent("a", 90)])
    tracker.reset()

    assert tracker.update([_torrent("a", 100)]) == []


def test_zero_size_and_missing_hash_are_ignored():
    tracker = CompletionTracker()
    tracker.update([
        _torrent("a", 0, size=0),
        {"name": "No hash", "size": 100, "done": 50},
    ])

    assert tracker.update([
        _torrent("a", 100, size=0),
        {"name": "No hash", "size": 100, "done": 100},
    ]) == []


def test_update_events_exposes_hash_and_name():
    tracker = CompletionTracker()
    tracker.update_events([_torrent("abc", 50, name="Example")])

    assert tracker.update_events([_torrent("abc", 100, name="Example")]) == [
        {"hash": "abc", "name": "Example"}
    ]
