#!/usr/bin/env python3
# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Maintain SerrebiTorrent translation catalogs without third-party packages."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from translation_catalog import (  # noqa: E402
    discover_catalogs,
    load_po,
    render_pot,
    validate_catalog,
)
from translation_inventory import collect_source_messages  # noqa: E402


def source_messages() -> list[str]:
    return collect_source_messages(ROOT, include_web=True)


def cmd_template(args) -> int:
    messages = source_messages()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_pot(messages), encoding="utf-8")
    print(f"Wrote {len(messages)} source messages to {output}")
    return 0


def cmd_validate(args) -> int:
    info = load_po(Path(args.catalog))
    problems = validate_catalog(info.translations)
    if problems:
        for source, errors in problems.items():
            print(source)
            for error in errors:
                print(f"  - {error}")
        print(f"{len(problems)} entries need review.", file=sys.stderr)
        return 1
    print(f"{info.code}: {len(info.translations)} translated entries; validation passed.")
    return 0


def _write_web_catalog(info, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "language": info.code,
        "name": info.name,
        "translations": dict(sorted(info.translations.items(), key=lambda item: item[0].casefold())),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_web_index(directory: Path, code: str, name: str) -> None:
    path = directory / "index.json"
    languages: dict[str, str] = {"pt-BR": "Português (Brasil)"}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            for item in existing.get("languages", []):
                if item.get("code") and item.get("name"):
                    languages[str(item["code"])] = str(item["name"])
        except (OSError, ValueError, TypeError):
            pass
    languages[code] = name
    payload = {
        "languages": [
            {"code": language_code, "name": languages[language_code]}
            for language_code in sorted(languages, key=str.casefold)
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_compile_web(args) -> int:
    info = load_po(Path(args.catalog))
    problems = validate_catalog(info.translations)
    if problems and not args.allow_invalid:
        print("Catalog has validation errors; run 'validate' first.", file=sys.stderr)
        return 1
    output = Path(args.output or ROOT / "web_static" / "locales" / f"{info.code}.json")
    _write_web_catalog(info, output)
    if not args.no_index:
        _update_web_index(output.parent, info.code, info.name)
    print(f"Compiled {len(info.translations)} entries to {output}")
    return 0


def cmd_compile_all_web(args) -> int:
    output_dir = Path(args.output_dir or ROOT / "web_static" / "locales")
    catalogs = discover_catalogs(Path(args.locales_dir or ROOT / "locales"))
    failures = 0
    for code, info in catalogs.items():
        problems = validate_catalog(info.translations)
        if problems and not args.allow_invalid:
            print(f"{code}: validation failed; skipping Web catalog.", file=sys.stderr)
            failures += 1
            continue
        _write_web_catalog(info, output_dir / f"{code}.json")
        _update_web_index(output_dir, code, info.name)
        print(f"Compiled {code}: {len(info.translations)} entries")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    template = sub.add_parser("template", help="generate a POT template from current source strings")
    template.add_argument("--output", default=str(ROOT / "locales" / "serrebitorrent.pot"))
    template.set_defaults(func=cmd_template)

    validate = sub.add_parser("validate", help="validate placeholders and keyboard mnemonics in a PO file")
    validate.add_argument("catalog")
    validate.set_defaults(func=cmd_validate)

    compile_web = sub.add_parser("compile-web", help="compile a PO catalog to Web UI JSON")
    compile_web.add_argument("catalog")
    compile_web.add_argument("--output")
    compile_web.add_argument("--allow-invalid", action="store_true")
    compile_web.add_argument("--no-index", action="store_true")
    compile_web.set_defaults(func=cmd_compile_web)

    compile_all = sub.add_parser("compile-all-web", help="compile all locales/*.po catalogs for the Web UI")
    compile_all.add_argument("--locales-dir")
    compile_all.add_argument("--output-dir")
    compile_all.add_argument("--allow-invalid", action="store_true")
    compile_all.set_defaults(func=cmd_compile_all_web)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
