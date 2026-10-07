# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Persistent profile-scoped recent torrent save paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading

from app_paths import get_state_dir


DEFAULT_MAX_PATHS = 10
MAX_PATH_CHARS = 2048


class RecentSavePaths:
    def __init__(self, path: str | None = None, max_paths: int = DEFAULT_MAX_PATHS):
        self.path = Path(path or os.path.join(get_state_dir(), "recent_save_paths.json"))
        self.max_paths = max(1, int(max_paths))
        self._lock = threading.RLock()

    @staticmethod
    def clean_path(value) -> str:
        return str(value or "").strip()[:MAX_PATH_CHARS]

    def _load_unlocked(self) -> dict[str, list[str]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if not isinstance(raw, dict):
            return {}

        result: dict[str, list[str]] = {}
        for profile_id, values in raw.items():
            if not isinstance(values, list):
                continue
            cleaned = []
            seen = set()
            for value in values:
                path = self.clean_path(value)
                if not path or path in seen:
                    continue
                seen.add(path)
                cleaned.append(path)
                if len(cleaned) >= self.max_paths:
                    break
            if cleaned:
                result[str(profile_id)] = cleaned
        return result

    def paths(self, profile_id) -> list[str]:
        profile = str(profile_id or "")
        if not profile:
            return []
        with self._lock:
            return list(self._load_unlocked().get(profile, []))

    def remember(self, profile_id, value) -> None:
        profile = str(profile_id or "")
        path = self.clean_path(value)
        if not profile or not path:
            return

        with self._lock:
            data = self._load_unlocked()
            previous = data.get(profile, [])
            paths = [path] + [item for item in previous if item != path]
            data[profile] = paths[: self.max_paths]
            self._write_unlocked(data)

    def clear(self, profile_id) -> None:
        profile = str(profile_id or "")
        if not profile:
            return
        with self._lock:
            data = self._load_unlocked()
            data.pop(profile, None)
            self._write_unlocked(data)

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
