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
TORRENT_MAX_BYTES = 16 * 1024 * 1024
# path -> (size, mtime) from the previous scan. A file unchanged across two
# scans is ready even when its mtime is in the future: a network share whose
# clock runs ahead of this PC would otherwise hold it back indefinitely.
_last_seen = {}
# Files successfully/unsuccessfully processed but not renamed are suppressed
# until their size/mtime changes, so a transient rename failure cannot import
# the same torrent on every scan.
_processed = {}


def clean_folder_path(folder):
    """Explorer's "Copy as path" wraps the path in quotes."""
    return str(folder or "").strip().strip('"').strip()


def ready_torrent_files(folder, now=None, settle=SETTLE_SECONDS):
    """Raises OSError when the folder itself cannot be read."""
    now = time.time() if now is None else now
    found = []
    seen = {}
    with os.scandir(folder) as entries:
        for entry in entries:
            if not entry.name.lower().endswith(".torrent"):
                continue
            try:
                if not entry.is_file():
                    continue
                st = entry.stat()
            except OSError:
                continue
            sig = seen[entry.path] = (st.st_size, st.st_mtime)
            processed_sig = _processed.get(entry.path)
            if processed_sig == sig:
                continue
            if processed_sig is not None:
                _processed.pop(entry.path, None)
            if now - st.st_mtime >= settle or _last_seen.get(entry.path) == sig:
                found.append(entry.path)
    for path in list(_processed):
        if path not in seen:
            _processed.pop(path, None)
    _last_seen.clear()
    _last_seen.update(seen)
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
    try:
        paths = ready_torrent_files(folder, now)
    except OSError as exc:
        # Say so: a missing or unreadable folder used to fail without a word.
        return added, [(str(folder), exc.strerror or str(exc))]
    for path in paths:
        name = os.path.basename(path)
        try:
            with open(path, "rb") as handle:
                data = handle.read(TORRENT_MAX_BYTES + 1)
            if len(data) > TORRENT_MAX_BYTES:
                raise ValueError("Torrent file exceeds the 16 MB limit.")
            add(data)
        except Exception as exc:  # noqa: BLE001 - client and file boundary
            failed.append((name, str(exc)))
            suffix = ".failed"
        else:
            added.append(name)
            suffix = ".added"
        _processed[path] = _last_seen.get(path)
        try:
            mark(path, suffix)
        except OSError:
            pass
        else:
            _processed.pop(path, None)
    return added, failed
