# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Pick up .torrent files dropped into a watched folder (no wx)."""

from __future__ import annotations

import os
import time

SCAN_INTERVAL_SECONDS = 60
# A file still being copied onto a share would fail to parse; wait until it
# has not been modified for this long.
SETTLE_SECONDS = 10


def ready_torrent_files(folder, now=None, settle=SETTLE_SECONDS):
    now = time.time() if now is None else now
    found = []
    try:
        entries = os.scandir(folder)
    except OSError:
        return found
    with entries:
        for entry in entries:
            if not entry.name.lower().endswith(".torrent"):
                continue
            try:
                if entry.is_file() and now - entry.stat().st_mtime >= settle:
                    found.append(entry.path)
            except OSError:
                continue
    return sorted(found)


def mark(path, suffix):
    """Rename so the file is not picked up again, keeping it for the user."""
    target = path + suffix
    n = 1
    while os.path.exists(target):
        target = f"{path}.{n}{suffix}"
        n += 1
    os.rename(path, target)
    return target


def import_folder(folder, add, now=None):
    """Call add(data) for each ready file.

    Added files become ``name.torrent.added`` and failures
    ``name.torrent.failed``. Returns (added names, [(name, error)]).
    """
    added, failed = [], []
    for path in ready_torrent_files(folder, now):
        name = os.path.basename(path)
        try:
            with open(path, "rb") as handle:
                add(handle.read())
        except Exception as exc:  # noqa: BLE001 - client and file boundary
            failed.append((name, str(exc)))
            suffix = ".failed"
        else:
            added.append(name)
            suffix = ".added"
        try:
            mark(path, suffix)
        except OSError:
            pass
    return added, failed
