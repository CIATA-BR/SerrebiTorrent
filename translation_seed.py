# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Read existing in-code/Web translations as migration seeds for the PO editor."""

from __future__ import annotations

from pathlib import Path
import ast
import json
import re

from translation_catalog import CatalogEntry, load_po


def _python_pt_br_mapping(root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in root.glob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            value = None
            name = None
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                if names:
                    name = names[0]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                value = node.value
            if name not in {"_PT_BR", "PT_BR"} or not isinstance(value, ast.Dict):
                continue
            for key_node, value_node in zip(value.keys, value.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, str)
                ):
                    mapping[key_node.value] = value_node.value
    return mapping


def _js_string(value: str) -> str:
    # JSON decoding gives correct handling for escaped quotes/newlines after
    # converting the single-quoted JS literal to a JSON string.
    escaped = value.replace('"', '\\"')
    return json.loads('"' + escaped.replace("\\'", "'") + '"')


def _web_pt_br_mapping(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    match = re.search(r"const\s+PT_BR\s*=\s*\{(.*?)\n\s*\};", text, re.S)
    if not match:
        return {}
    mapping: dict[str, str] = {}
    pair = re.compile(
        r"^\s*'((?:\\.|[^'])*)'\s*:\s*'((?:\\.|[^'])*)'\s*,?\s*$",
        re.M,
    )
    for key, value in pair.findall(match.group(1)):
        try:
            mapping[_js_string(key)] = _js_string(value)
        except (ValueError, json.JSONDecodeError):
            continue
    return mapping


def seed_entries(root: str | Path, language: str) -> dict[str, CatalogEntry]:
    """Return built-in + packaged translations, with packaged PO taking precedence."""
    root = Path(root)
    result: dict[str, CatalogEntry] = {}
    if language == "pt-BR":
        mapping = _python_pt_br_mapping(root)
        mapping.update(_web_pt_br_mapping(root / "web_static" / "i18n.js"))
        result.update({key: CatalogEntry(key, value) for key, value in mapping.items() if value})

    packaged = load_po(root / "locales" / f"{language}.po")
    result.update(packaged)
    return result
