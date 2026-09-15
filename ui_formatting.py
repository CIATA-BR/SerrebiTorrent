"""Pure formatting helpers shared by torrent and detail-list UI controls."""

from __future__ import annotations


def fmt_size(size):
    if size == 0:
        return ""
    try:
        size = float(size)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def fmt_ratio(ratio_val):
    try:
        if ratio_val is None:
            return ""
        value = float(ratio_val)
    except (TypeError, ValueError):
        return ""
    if value < 0:
        value = 0.0
    if value > 50.0:
        value /= 1000.0
    return f"{value:.2f}"


def fmt_availability(avail_val):
    try:
        if avail_val is None:
            return "—"
        value = float(avail_val)
    except (TypeError, ValueError):
        return "—"
    if value < 0:
        return "—"
    return f"{value:.2f}"


def fmt_eta(seconds):
    try:
        if seconds is None:
            return "—"
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "—"

    if seconds < 0:
        return "—"
    if seconds == 0:
        return "0s"

    remaining = seconds
    days = remaining // 86400
    remaining %= 86400
    hours = remaining // 3600
    remaining %= 3600
    minutes = remaining // 60
    remaining %= 60

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {remaining}s"
    return f"{remaining}s"


def fmt_pair(connected, total):
    def to_int_or_none(value):
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    connected_value = to_int_or_none(connected)
    total_value = to_int_or_none(total)
    connected_text = str(connected_value) if connected_value is not None else "?"
    total_text = str(total_value) if total_value is not None else "?"
    return f"{connected_text}/{total_text}"


def clean_status_message(msg):
    """Drop noisy success/invalid-handle messages returned as pseudo-errors."""
    if msg is None:
        return ""
    try:
        message = str(msg).strip()
    except Exception:
        return ""
    if not message:
        return ""

    low = message.lower().strip()
    phrase = "the operation completed successfully"
    if low.rstrip(".").strip() == phrase:
        return ""
    if phrase in low:
        remainder = low.replace(phrase, "").strip(" -;:().[]{}\t\r\n")
        if not remainder:
            return ""
    if "the handle is invalid" in low:
        return ""
    if low in ("success", "ok", "no error", "none"):
        return ""
    return message
