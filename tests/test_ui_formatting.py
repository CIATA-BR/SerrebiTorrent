import ui_formatting


def test_fmt_size_uses_binary_steps():
    assert ui_formatting.fmt_size(1024) == "1.0 KB"
    assert ui_formatting.fmt_size(1024 * 1024) == "1.0 MB"


def test_fmt_eta_stays_compact_for_screen_readers():
    assert ui_formatting.fmt_eta(0) == "0s"
    assert ui_formatting.fmt_eta(65) == "1m 5s"
    assert ui_formatting.fmt_eta(3665) == "1h 1m"
    assert ui_formatting.fmt_eta(90000) == "1d 1h"
    assert ui_formatting.fmt_eta(-1) == "—"


def test_fmt_pair_marks_unknown_values():
    assert ui_formatting.fmt_pair(3, 10) == "3/10"
    assert ui_formatting.fmt_pair(None, 10) == "?/10"
    assert ui_formatting.fmt_pair(3, -1) == "3/?"


def test_ratio_supports_scaled_and_float_values():
    assert ui_formatting.fmt_ratio(1500) == "1.50"
    assert ui_formatting.fmt_ratio(1.5) == "1.50"
    assert ui_formatting.fmt_ratio(-10) == "0.00"


def test_clean_status_message_removes_known_noise():
    assert ui_formatting.clean_status_message("The operation completed successfully.") == ""
    assert ui_formatting.clean_status_message("The handle is invalid") == ""
    assert ui_formatting.clean_status_message("Success") == ""
    assert ui_formatting.clean_status_message("Tracker timed out") == "Tracker timed out"
