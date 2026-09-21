# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Dependency-free PO catalog support used by desktop and translation tooling.

The runtime deliberately accepts a conservative subset of GNU gettext PO that
covers normal msgid/msgstr catalogs, metadata and translator comments. English
source strings remain canonical and unknown/missing entries always fall back to
English (or to the legacy in-code catalog during migration).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Formatter
import json
import os
import re


@dataclass(frozen=True)
class CatalogInfo:
    code: str
    name: str
    path: Path
    metadata: dict[str, str]
    translations: dict[str, str]


_PLACEHOLDER_RE = Formatter()
_PRINTF_RE = re.compile(
    r"%(?:\([A-Za-z_][A-Za-z0-9_]*\))?(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[diouxXeEfFgGcrsab]"
)
_MNEMONIC_RE = re.compile(r"(?<!&)&(?!&)")


def _bundle_root() -> Path:
    try:
        import sys

        root = getattr(sys, "_MEIPASS", None)
        if root:
            return Path(root)
    except Exception:
        pass
    return Path(__file__).resolve().parent


def locales_dir() -> Path:
    override = os.environ.get("SERREBITORRENT_LOCALES_DIR")
    return Path(override) if override else _bundle_root() / "locales"


def sort_key(value: str) -> tuple[str, str]:
    """Total ordering for catalog entries.

    Casefolding alone ties on entries such as "Torrents"/"torrents", which makes
    the rendered order depend on set iteration order and therefore on
    PYTHONHASHSEED. The trailing raw value breaks those ties deterministically.
    """
    return (value.casefold(), value)


def _decode_po_string(token: str) -> str:
    token = token.strip()
    if not token.startswith('"'):
        raise ValueError(f"invalid PO string: {token!r}")
    # strict=False accepts raw control characters (notably tabs in wx keyboard
    # accelerator labels) that hand-authored and portal-exported PO files carry.
    return json.loads(token, strict=False)


def _parse_metadata(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    # render_po/render_pot intentionally emit compact header strings. Accept
    # both normal decoded newlines and literal backslash-n separators so PO
    # files from other editors and our deterministic renderer round-trip.
    normalized = value.replace("\\n", "\n")
    for line in normalized.splitlines():
        if ":" not in line:
            continue
        key, item = line.split(":", 1)
        result[key.strip()] = item.strip()
    return result


def parse_po_text(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Parse the PO subset used by SerrebiTorrent.

    Fuzzy entries are ignored. Plural forms are intentionally not consumed yet;
    they remain available in PO for future ngettext support without changing the
    current singular source-string API.
    """
    translations: dict[str, str] = {}
    metadata: dict[str, str] = {}
    msgid: list[str] | None = None
    msgstr: list[str] | None = None
    target: list[str] | None = None
    fuzzy = False

    def flush() -> None:
        nonlocal msgid, msgstr, target, fuzzy, metadata
        if msgid is None or msgstr is None:
            msgid = msgstr = target = None
            fuzzy = False
            return
        source = "".join(msgid)
        translated = "".join(msgstr)
        if not fuzzy:
            if source == "":
                metadata = _parse_metadata(translated)
            elif translated:
                translations[source] = translated
        msgid = msgstr = target = None
        fuzzy = False

    for raw in text.splitlines() + [""]:
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue
        if line.startswith("#"):
            continue
        if line.startswith("msgid_plural") or line.startswith("msgstr["):
            target = None
            continue
        if line.startswith("msgid "):
            if msgid is not None and msgstr is not None:
                flush()
            msgid = [_decode_po_string(line[6:])]
            msgstr = None
            target = msgid
            continue
        if line.startswith("msgstr "):
            msgstr = [_decode_po_string(line[7:])]
            target = msgstr
            continue
        if line.startswith('"') and target is not None:
            target.append(_decode_po_string(line))

    return metadata, translations


def load_po(path: Path) -> CatalogInfo:
    metadata, translations = parse_po_text(path.read_text(encoding="utf-8"))
    code = metadata.get("Language") or path.stem
    name = metadata.get("X-Language-Name") or metadata.get("Language-Team") or code
    return CatalogInfo(code=code, name=name, path=path, metadata=metadata, translations=translations)


def discover_catalogs(directory: Path | None = None) -> dict[str, CatalogInfo]:
    directory = directory or locales_dir()
    if not directory.exists():
        return {}
    result: dict[str, CatalogInfo] = {}
    for path in sorted(directory.glob("*.po")):
        try:
            info = load_po(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        result[info.code] = info
    return result


def catalog_for(language: str) -> CatalogInfo | None:
    wanted = str(language or "").replace("_", "-").lower()
    for code, info in discover_catalogs().items():
        if code.replace("_", "-").lower() == wanted:
            return info
    return None


def _fields(value: str) -> set[str]:
    fields: set[str] = set()
    for _literal, field, _spec, _conversion in _PLACEHOLDER_RE.parse(value):
        if field:
            fields.add(field.split(".", 1)[0].split("[", 1)[0])
    return fields


def _printf_placeholders(value: str) -> list[str]:
    cleaned = value.replace("%%", "")
    return sorted(_PRINTF_RE.findall(cleaned))


def _tab_suffixes(value: str) -> list[str]:
    return sorted(item.strip() for item in re.findall(r"\t([^\r\n]+)", value))


def _mnemonic_count(value: str) -> int:
    return len(_MNEMONIC_RE.findall(value))


def validate_translation(source: str, translated: str) -> list[str]:
    """Return contributor-facing validation messages for one translation."""
    errors: list[str] = []
    if not translated.strip():
        errors.append("Translation is empty.")
    source_fields = _fields(source)
    translated_fields = _fields(translated)
    if source_fields != translated_fields:
        errors.append(
            "Placeholders differ: expected "
            f"{sorted(source_fields)}, got {sorted(translated_fields)}."
        )
    source_printf = _printf_placeholders(source)
    translated_printf = _printf_placeholders(translated)
    if source_printf != translated_printf:
        errors.append(
            "Printf placeholders differ: expected "
            f"{source_printf}, got {translated_printf}."
        )

    source_shortcuts = _tab_suffixes(source)
    translated_shortcuts = _tab_suffixes(translated)
    if source_shortcuts != translated_shortcuts:
        errors.append(
            "Keyboard shortcuts differ: expected "
            f"{source_shortcuts}, got {translated_shortcuts}."
        )

    source_newlines = source.count("\n")
    translated_newlines = translated.count("\n")
    if source_newlines != translated_newlines:
        errors.append(
            "Newline count differs: expected "
            f"{source_newlines}, got {translated_newlines}."
        )

    source_mnemonics = _mnemonic_count(source)
    translated_mnemonics = _mnemonic_count(translated)
    if source_mnemonics > 0 and translated_mnemonics == 0:
        errors.append("Keyboard mnemonic marker '&' is missing.")
    elif source_mnemonics == 0 and translated_mnemonics > 0:
        errors.append("Keyboard mnemonic marker '&' is unexpected.")
    return errors


def validate_catalog(translations: dict[str, str]) -> dict[str, list[str]]:
    problems: dict[str, list[str]] = {}
    for source, translated in translations.items():
        errors = validate_translation(source, translated)
        if errors:
            problems[source] = errors
    return problems


def _quote_po(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_po(
    language: str,
    language_name: str,
    entries: dict[str, str],
    *,
    project: str = "SerrebiTorrent",
) -> str:
    """Render a deterministic contributor-friendly PO file."""
    header = (
        f"Project-Id-Version: {project}\\n"
        f"Language: {language}\\n"
        f"X-Language-Name: {language_name}\\n"
        "MIME-Version: 1.0\\n"
        "Content-Type: text/plain; charset=UTF-8\\n"
        "Content-Transfer-Encoding: 8bit\\n"
    )
    lines = [
        "# SerrebiTorrent translation catalog.",
        "# SPDX-License-Identifier: MIT",
        'msgid ""',
        'msgstr ""',
        _quote_po(header),
        "",
    ]
    for source in sorted(entries, key=sort_key):
        lines.extend((f"msgid {_quote_po(source)}", f"msgstr {_quote_po(entries[source])}", ""))
    return "\n".join(lines)


def render_pot(messages: list[str], *, project: str = "SerrebiTorrent") -> str:
    header = (
        f"Project-Id-Version: {project}\\n"
        "MIME-Version: 1.0\\n"
        "Content-Type: text/plain; charset=UTF-8\\n"
        "Content-Transfer-Encoding: 8bit\\n"
    )
    lines = [
        "# SerrebiTorrent translation template.",
        "# SPDX-License-Identifier: MIT",
        'msgid ""',
        'msgstr ""',
        _quote_po(header),
        "",
    ]
    for source in sorted(set(messages), key=sort_key):
        lines.extend((f"msgid {_quote_po(source)}", 'msgstr ""', ""))
    return "\n".join(lines)
