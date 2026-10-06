"""Client-agnostic torrent health diagnostics.

The diagnostic engine only interprets fields already normalized by SerrebiTorrent
clients. It never performs network or filesystem I/O.
"""

from __future__ import annotations

_SUCCESS_MESSAGES = {
    "",
    "ok",
    "success",
    "the operation completed successfully",
}


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _meaningful_message(value) -> str:
    text = str(value or "").strip()
    normalized = text.lower().rstrip(".!")
    if normalized in _SUCCESS_MESSAGES:
        return ""
    return text


def diagnose_torrent(torrent) -> list[dict[str, object]]:
    if not isinstance(torrent, dict):
        return [{"code": "unavailable"}]

    findings: list[dict[str, object]] = []
    size = _number(torrent.get("size"))
    done = _number(torrent.get("done"))
    down_rate = _number(torrent.get("down_rate"))
    seeds_connected = int(_number(torrent.get("seeds_connected")))
    seeds_total = int(_number(torrent.get("seeds_total")))
    availability_raw = torrent.get("availability")
    availability = None if availability_raw is None else _number(availability_raw, -1)

    if size > 0 and done >= size:
        return [{"code": "complete"}]

    error_message = _meaningful_message(torrent.get("message"))
    if error_message:
        findings.append({"code": "client_error", "message": error_message})

    if bool(torrent.get("hashing")):
        findings.append({"code": "checking"})
        return findings

    state = torrent.get("state")
    active = bool(torrent.get("active"))
    if state == 0 and not active:
        findings.append({"code": "paused"})
        return findings

    if down_rate > 0:
        findings.append({"code": "receiving_data"})
        return findings

    if seeds_connected <= 0:
        if seeds_total <= 0:
            findings.append({"code": "no_seeds"})
        else:
            findings.append({"code": "seeds_not_connected", "count": seeds_total})

    if availability is not None and availability >= 0 and availability < 1:
        if availability == 0:
            findings.append({"code": "no_complete_copy"})
        else:
            findings.append({"code": "incomplete_copy", "availability": availability})

    if active:
        findings.append({"code": "active_no_data"})

    if not findings:
        findings.append({"code": "no_clear_cause"})

    return findings
