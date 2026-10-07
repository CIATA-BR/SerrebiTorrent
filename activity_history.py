# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Small persistent user-facing activity history."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import threading

from app_paths import get_state_dir


DEFAULT_MAX_ENTRIES = 500
MAX_MESSAGE_CHARS = 2000


class ActivityHistory:
    def __init__(self, path: str | None = None, max_entries: int = DEFAULT_MAX_ENTRIES):
        self.path = Path(path or os.path.join(get_state_dir(), "activity_history.json"))
        self.max_entries = max(1, int(max_entries))
        self._lock = threading.RLock()

    def _load_unlocked(self) -> list[dict[str, str]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        if not isinstance(raw, list):
            return []
        entries = []
        for item in raw[-self.max_entries :]:
            if not isinstance(item, dict):
                continue
            timestamp = str(item.get("timestamp") or "").strip()
            message = str(item.get("message") or "").strip()
            kind = str(item.get("kind") or "info").strip().lower()
            if not timestamp or not message:
                continue
            if kind not in {"info", "success", "error"}:
                kind = "info"
            entries.append(
                {
                    "timestamp": timestamp,
                    "kind": kind,
                    "message": message[:MAX_MESSAGE_CHARS],
                }
            )
        return entries

    def entries(self) -> list[dict[str, str]]:
        with self._lock:
            return list(self._load_unlocked())

    def append(
        self,
        message: str,
        *,
        kind: str = "info",
        timestamp: str | None = None,
    ) -> None:
        clean_message = str(message or "").strip()
        if not clean_message:
            return
        clean_kind = str(kind or "info").strip().lower()
        if clean_kind not in {"info", "success", "error"}:
            clean_kind = "info"
        stamp = timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
        entry = {
            "timestamp": stamp,
            "kind": clean_kind,
            "message": clean_message[:MAX_MESSAGE_CHARS],
        }

        with self._lock:
            entries = self._load_unlocked()
            entries.append(entry)
            self._write_unlocked(entries[-self.max_entries :])

    def clear(self) -> None:
        with self._lock:
            self._write_unlocked([])

    def _write_unlocked(self, entries: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        try:
            temp.write_text(
                json.dumps(entries, ensure_ascii=False, indent=2),
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
