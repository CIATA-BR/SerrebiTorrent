# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Portable translation catalog helpers used by the app and contributor UI.

The parser deliberately supports the PO subset SerrebiTorrent needs without
adding a runtime dependency. Files remain compatible with gettext/Weblate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
import ast
import json
import re


@dataclass
class CatalogEntry:
    msgid: str
    msgstr: str = ""
    context: str = ""
    comments: list[str] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)

    @property
    def translated(self) -> bool:
        return bool(self.msgstr.strip()) and "fuzzy" not in self.flags


def _unquote(value: str) -> str:
    value = value.strip()
    if not value.startswith('"'):
        return ""
    return json.loads(value)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_po(path: str | Path) -> dict[str, CatalogEntry]:
    """Load a gettext-compatible PO file keyed by msgid."""
    path = Path(path)
    if not path.exists():
        return {}
    entries: dict[str, CatalogEntry] = {}
    comments: list[str] = []
    flags: set[str] = set()
    context = ""
    msgid = None
    msgstr = ""
    active = None

    def flush():
        nonlocal comments, flags, context, msgid, msgstr, active
        if msgid not in (None, ""):
            entries[msgid] = CatalogEntry(msgid, msgstr, context, list(comments), set(flags))
        comments, flags, context, msgid, msgstr, active = [], set(), "", None, "", None

    for raw in path.read_text(encoding="utf-8-sig").splitlines() + [""]:
        line = raw.rstrip()
        if not line:
            flush()
            continue
        if line.startswith("#,"):
            flags.update(part.strip() for part in line[2:].split(",") if part.strip())
        elif line.startswith("#."):
            comments.append(line[2:].strip())
        elif line.startswith("msgctxt "):
            context = _unquote(line[8:])
            active = "context"
        elif line.startswith("msgid "):
            msgid = _unquote(line[6:])
            active = "msgid"
        elif line.startswith("msgstr "):
            msgstr = _unquote(line[7:])
            active = "msgstr"
        elif line.startswith('"'):
            value = _unquote(line)
            if active == "context":
                context += value
            elif active == "msgid" and msgid is not None:
                msgid += value
            elif active == "msgstr":
                msgstr += value
    return entries


def save_po(path: str | Path, entries: dict[str, CatalogEntry], language: str, project: str = "SerrebiTorrent") -> None:
    """Write a stable UTF-8 PO file suitable for Git/Weblate review."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'msgid ""',
        'msgstr ""',
        f'"Project-Id-Version: {project}\\n"',
        f'"Language: {language}\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        "",
    ]
    for key in sorted(entries, key=str.casefold):
        entry = entries[key]
        for comment in entry.comments:
            lines.append(f"#. {comment}")
        if entry.flags:
            lines.append("#, " + ", ".join(sorted(entry.flags)))
        if entry.context:
            lines.append("msgctxt " + _quote(entry.context))
        lines.append("msgid " + _quote(entry.msgid))
        lines.append("msgstr " + _quote(entry.msgstr))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def placeholders(value: str) -> set[str]:
    fields = set()
    for _, field_name, _, _ in Formatter().parse(value):
        if field_name:
            fields.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return fields


def validate_entry(entry: CatalogEntry) -> list[str]:
    """Validate placeholders and keyboard mnemonic preservation."""
    errors: list[str] = []
    if not entry.msgstr.strip():
        return errors
    src_fields = placeholders(entry.msgid)
    dst_fields = placeholders(entry.msgstr)
    if src_fields != dst_fields:
        errors.append(
            "Placeholder mismatch: source has " + repr(sorted(src_fields)) +
            ", translation has " + repr(sorted(dst_fields))
        )
    if "&" in entry.msgid and "&" not in entry.msgstr:
        errors.append("Keyboard mnemonic '&' is missing from the translation")
    return errors


def validate_catalog(entries: dict[str, CatalogEntry]) -> dict[str, list[str]]:
    return {key: errors for key, entry in entries.items() if (errors := validate_entry(entry))}


def catalog_stats(entries: dict[str, CatalogEntry]) -> tuple[int, int, int]:
    total = len(entries)
    translated = sum(entry.translated for entry in entries.values())
    review = sum("fuzzy" in entry.flags for entry in entries.values())
    return total, translated, review


def merge_template(source_strings: list[str], current: dict[str, CatalogEntry]) -> dict[str, CatalogEntry]:
    merged: dict[str, CatalogEntry] = {}
    for text in sorted(set(source_strings), key=str.casefold):
        old = current.get(text)
        merged[text] = CatalogEntry(
            msgid=text,
            msgstr=old.msgstr if old else "",
            context=old.context if old else "",
            comments=list(old.comments) if old else [],
            flags=set(old.flags) if old else set(),
        )
    return merged


def _add_string_sequence(node, strings: set[str]) -> None:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for value in node.elts:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                strings.add(value.value)


def extract_python_catalog_strings(root: str | Path) -> list[str]:
    """Extract source keys from Python catalogs and declared UI source lists without importing wx."""
    root = Path(root)
    strings: set[str] = set()
    for path in root.glob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                names = {t.id for t in node.targets if isinstance(t, ast.Name)}
                if names & {"_PT_BR", "PT_BR"} and isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            strings.add(key.value)
                if "TRANSLATABLE_STRINGS" in names:
                    _add_string_sequence(node.value, strings)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in {"_PT_BR", "PT_BR"} and isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            strings.add(key.value)
                elif node.target.id == "TRANSLATABLE_STRINGS":
                    _add_string_sequence(node.value, strings)
    return sorted(strings, key=str.casefold)


def extract_web_catalog_strings(path: str | Path) -> list[str]:
    """Extract canonical keys from the Web PT_BR object."""
    text = Path(path).read_text(encoding="utf-8")
    match = re.search(r"const\s+PT_BR\s*=\s*\{(.*?)\n\s*\};", text, re.S)
    if not match:
        return []
    keys = re.findall(r"^\s*'((?:\\'|[^'])*)'\s*:", match.group(1), re.M)
    return [bytes(key, "utf-8").decode("unicode_escape") for key in keys]
