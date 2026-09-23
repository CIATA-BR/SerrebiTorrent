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
