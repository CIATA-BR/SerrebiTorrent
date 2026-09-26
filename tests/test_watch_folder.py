import os

import watch_folder


def test_import_folder_marks_success_and_failure(tmp_path):
    good = tmp_path / "good.torrent"
    bad = tmp_path / "bad.torrent"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")
    for path in (good, bad):
        os.utime(path, (0, 0))

    def add(data):
        if data == b"bad":
            raise ValueError("invalid")

    added, failed = watch_folder.import_folder(tmp_path, add, now=watch_folder.SETTLE_SECONDS + 1)

    assert added == ["good.torrent"]
    assert failed == [("bad.torrent", "invalid")]
    assert (tmp_path / "good.torrent.added").is_file()
    assert (tmp_path / "bad.torrent.failed").is_file()


def test_missing_folder_is_reported(tmp_path):
    missing = tmp_path / "gone"
    added, failed = watch_folder.import_folder(missing, lambda data: None)
    assert added == []
    assert failed and failed[0][0] == str(missing)


def test_future_mtime_file_is_ready_once_unchanged(tmp_path):
    path = tmp_path / "skew.torrent"
    path.write_bytes(b"x")
    os.utime(path, (5000, 5000))  # "now" is 1000: share clock runs ahead
    assert watch_folder.ready_torrent_files(tmp_path, now=1000) == []
    assert watch_folder.ready_torrent_files(tmp_path, now=1060) == [str(path)]


def test_clean_folder_path_strips_copy_as_path_quotes():
    assert watch_folder.clean_folder_path(' "C:\Torrents" ') == "C:\Torrents"



def test_watch_folder_rejects_oversized_torrent(tmp_path, monkeypatch):
    path = tmp_path / "large.torrent"
    path.write_bytes(b"123456789")
    os.utime(path, (0, 0))
    monkeypatch.setattr(watch_folder, "TORRENT_MAX_BYTES", 8)
    added_payloads = []

    added, failed = watch_folder.import_folder(
        tmp_path,
        added_payloads.append,
        now=watch_folder.SETTLE_SECONDS + 1,
    )

    assert added == []
    assert failed == [("large.torrent", "Torrent file exceeds the 16 MB limit.")]
    assert added_payloads == []
    assert (tmp_path / "large.torrent.failed").is_file()
