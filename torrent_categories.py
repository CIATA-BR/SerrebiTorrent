# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Persistent SerrebiTorrent-owned torrent categories."""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading

from app_paths import get_state_dir


MAX_CATEGORY_CHARS = 80


class TorrentCategoryStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.path.join(get_state_dir(), "torrent_categories.json"))
        self._lock = threading.RLock()

    def _load_unlocked(self) -> dict[str, dict[str, str]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if not isinstance(raw, dict):
            return {}

        result: dict[str, dict[str, str]] = {}
        for profile_id, mapping in raw.items():
            if not isinstance(mapping, dict):
                continue
            clean = {}
            for torrent_hash, category in mapping.items():
                h = str(torrent_hash or "").strip()
                c = self.clean_category(category)
                if h and c:
                    clean[h] = c
            if clean:
                result[str(profile_id)] = clean
        return result

    @staticmethod
    def clean_category(value) -> str:
        return " ".join(str(value or "").strip().split())[:MAX_CATEGORY_CHARS]

    def get(self, profile_id, torrent_hash) -> str:
        profile = str(profile_id or "")
        h = str(torrent_hash or "").strip()
        if not profile or not h:
            return ""
        with self._lock:
            return self._load_unlocked().get(profile, {}).get(h, "")

    def assign_many(self, profile_id, hashes, category) -> None:
        profile = str(profile_id or "")
        clean_category = self.clean_category(category)
        clean_hashes = [str(value or "").strip() for value in hashes]
        clean_hashes = [value for value in clean_hashes if value]
        if not profile or not clean_hashes:
            return

        with self._lock:
            data = self._load_unlocked()
            mapping = data.setdefault(profile, {})
            for torrent_hash in clean_hashes:
                if clean_category:
                    mapping[torrent_hash] = clean_category
                else:
                    mapping.pop(torrent_hash, None)
            if not mapping:
                data.pop(profile, None)
            self._write_unlocked(data)

    def categories(self, profile_id) -> list[str]:
        profile = str(profile_id or "")
        if not profile:
            return []
        with self._lock:
            values = self._load_unlocked().get(profile, {}).values()
            return sorted(set(values), key=lambda value: (value.casefold(), value))

    def counts(self, profile_id, hashes) -> dict[str, int]:
        profile = str(profile_id or "")
        wanted = {str(value or "").strip() for value in hashes if str(value or "").strip()}
        counts: dict[str, int] = {}
        if not profile or not wanted:
            return counts
        with self._lock:
            mapping = self._load_unlocked().get(profile, {})
            for torrent_hash in wanted:
                category = mapping.get(torrent_hash)
                if category:
                    counts[category] = counts.get(category, 0) + 1
        return counts

    def _write_unlocked(self, data) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        try:
            temp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(temp, self.path)
            if os.name != "nt":
                try:
                    os.chmod(self.path, 0o600)
                except OSError:
                    pass
        finally:
            try:
                if temp.exists():
                    temp.unlink()
            except OSError:
                pass
