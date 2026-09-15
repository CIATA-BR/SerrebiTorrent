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

import i18n  # noqa: E402
from translation_catalog import (  # noqa: E402
    load_po,
    render_pot,
    validate_catalog,
)


def source_messages() -> list[str]:
    messages: set[str] = set()
    for catalog in i18n.CATALOGS.values():
        messages.update(catalog.keys())
    return sorted(messages, key=str.casefold)


def cmd_template(args) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_pot(source_messages()), encoding="utf-8")
    print(f"Wrote {len(source_messages())} source messages to {output}")
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


def cmd_compile_web(args) -> int:
    info = load_po(Path(args.catalog))
    problems = validate_catalog(info.translations)
    if problems and not args.allow_invalid:
        print("Catalog has validation errors; run 'validate' first.", file=sys.stderr)
        return 1
    output = Path(args.output or ROOT / "web_static" / "locales" / f"{info.code}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "language": info.code,
        "name": info.name,
        "translations": dict(sorted(info.translations.items(), key=lambda item: item[0].casefold())),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compiled {len(info.translations)} entries to {output}")
    return 0


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
    compile_web.set_defaults(func=cmd_compile_web)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
