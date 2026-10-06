"""Track torrents that transition from incomplete to complete.

The first snapshot establishes a baseline so opening SerrebiTorrent does not
announce every torrent that was already complete before this run.
"""

from __future__ import annotations


def _is_complete(torrent) -> bool:
    if not isinstance(torrent, dict):
        return False
    try:
        size = int(torrent.get("size") or 0)
        done = int(torrent.get("done") or 0)
    except (TypeError, ValueError):
        return False
    return size > 0 and done >= size


class CompletionTracker:
    def __init__(self):
        self._complete_by_hash = None

    def reset(self) -> None:
        self._complete_by_hash = None

    def update_events(self, torrents) -> list[dict[str, str]]:
        current = {}
        names = {}
        for torrent in torrents or []:
            if not isinstance(torrent, dict):
                continue
            info_hash = str(torrent.get("hash") or "").strip()
            if not info_hash:
                continue
            current[info_hash] = _is_complete(torrent)
            names[info_hash] = str(torrent.get("name") or info_hash)

        previous = self._complete_by_hash
        self._complete_by_hash = current
        if previous is None:
            return []

        return [
            {"hash": info_hash, "name": names[info_hash]}
            for info_hash, complete in current.items()
            if complete and previous.get(info_hash) is False
        ]

    def update(self, torrents) -> list[str]:
        return [event["name"] for event in self.update_events(torrents)]
