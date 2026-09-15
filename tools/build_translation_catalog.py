#!/usr/bin/env python3
# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Generate gettext template and browser JSON catalogs from SerrebiTorrent sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from translation_catalog import (  # noqa: E402
    CatalogEntry,
    extract_python_catalog_strings,
    extract_web_catalog_strings,
    load_po,
    merge_template,
    save_po,
    validate_catalog,
)


def source_strings() -> list[str]:
    strings = set(extract_python_catalog_strings(ROOT))
    web = ROOT / "web_static" / "i18n.js"
    if web.exists():
        strings.update(extract_web_catalog_strings(web))
    return sorted(strings, key=str.casefold)


def write_template(path: Path) -> None:
    entries = {text: CatalogEntry(text) for text in source_strings()}
    save_po(path, entries, "")


def refresh_po(path: Path) -> None:
    current = load_po(path)
    merged = merge_template(source_strings(), current)
    errors = validate_catalog(merged)
    if errors:
        for key, issues in errors.items():
            for issue in issues:
                print(f"{path}:{key}: {issue}", file=sys.stderr)
        raise SystemExit(2)
    save_po(path, merged, path.stem)


def export_json(po_path: Path, output: Path) -> None:
    entries = load_po(po_path)
    errors = validate_catalog(entries)
    if errors:
        for key, issues in errors.items():
            for issue in issues:
                print(f"{po_path}:{key}: {issue}", file=sys.stderr)
        raise SystemExit(2)
    mapping = {key: entry.msgstr for key, entry in entries.items() if entry.translated}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", action="store_true", help="write locales/serrebitorrent.pot")
    parser.add_argument("--refresh", metavar="PO", help="merge current source strings into a PO file")
    parser.add_argument("--json", metavar="PO", help="export translated messages from PO to browser JSON")
    parser.add_argument("--output", metavar="PATH", help="output path for --json")
    args = parser.parse_args()

    if args.template:
        write_template(ROOT / "locales" / "serrebitorrent.pot")
    if args.refresh:
        refresh_po(Path(args.refresh))
    if args.json:
        po = Path(args.json)
        output = Path(args.output) if args.output else ROOT / "web_static" / "locales" / f"{po.stem}.json"
        export_json(po, output)
    if not (args.template or args.refresh or args.json):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
