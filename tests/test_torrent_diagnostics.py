from torrent_diagnostics import diagnose_torrent


def test_complete_torrent_short_circuits_diagnosis():
    assert diagnose_torrent({"size": 100, "done": 100}) == [{"code": "complete"}]


def test_paused_torrent_is_reported():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 0,
        "active": False,
    })
    assert {"code": "paused"} in findings


def test_active_download_with_rate_is_healthy():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 1,
        "active": True,
        "down_rate": 1024,
        "seeds_connected": 1,
    })
    assert findings == [{"code": "receiving_data"}]


def test_stalled_torrent_reports_missing_seeds_and_no_data():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 1,
        "active": True,
        "down_rate": 0,
        "seeds_connected": 0,
        "seeds_total": 0,
    })
    assert {"code": "no_seeds"} in findings
    assert {"code": "active_no_data"} in findings


def test_tracker_or_client_error_is_preserved():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 1,
        "active": True,
        "message": "Tracker returned 404",
    })
    assert {"code": "client_error", "message": "Tracker returned 404"} in findings


def test_success_message_is_not_misdiagnosed_as_error():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 1,
        "active": True,
        "message": "The operation completed successfully.",
        "down_rate": 0,
        "seeds_connected": 0,
        "seeds_total": 0,
    })
    assert not any(item["code"] == "client_error" for item in findings)


def test_availability_below_one_is_reported():
    findings = diagnose_torrent({
        "size": 100,
        "done": 25,
        "state": 1,
        "active": True,
        "availability": 0.45,
        "seeds_connected": 0,
        "seeds_total": 2,
    })
    assert any(item["code"] == "incomplete_copy" for item in findings)
