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
    load_po,
    normalize_catalog_code,
    render_pot,
    sort_key,
    validate_catalog,
)
from translation_inventory import collect_source_messages  # noqa: E402


def source_messages() -> list[str]:
    return collect_source_messages(ROOT, include_web=True)


def _discover_catalogs_strict(directory: Path):
    catalogs = {}
    errors: list[str] = []

    if not directory.exists():
        return catalogs, errors

    for path in sorted(directory.glob("*.po")):
        try:
            info = load_po(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: failed to parse catalog: {exc}")
            continue

        if path.stem != info.code:
            errors.append(
                f"{path.name}: filename must match Language header {info.code!r}; "
                f"rename the catalog to {info.code}.po"
            )
            continue

        normalized = normalize_catalog_code(info.code)
        duplicate = next(
            (existing for code, existing in catalogs.items()
             if normalize_catalog_code(code) == normalized),
            None,
        )
        if duplicate is not None:
            errors.append(
                f"{path.name}: duplicate normalized language code {info.code!r}; "
                f"already provided by {duplicate.path.name}"
            )
            continue

        catalogs[info.code] = info

    return catalogs, errors


def _report_catalog_errors(errors: list[str]) -> bool:
    for error in errors:
        print(error, file=sys.stderr)
    return bool(errors)


def render_web_catalog(info) -> str:
    payload = {
        "language": info.code,
        "name": info.name,
        "translations": dict(sorted(info.translations.items(), key=lambda item: sort_key(item[0]))),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_web_index(catalogs) -> str:
    payload = {
        "languages": [
            {"code": code, "name": catalogs[code].name}
            for code in sorted(catalogs, key=sort_key)
        ]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


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
    output.write_text(render_web_catalog(info), encoding="utf-8")


def _write_web_index(directory: Path, catalogs) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.json").write_text(render_web_index(catalogs), encoding="utf-8")


def _stale_web_catalogs(directory: Path, catalogs) -> list[Path]:
    expected = {f"{code}.json" for code in catalogs}
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.glob("*.json")
        if path.name != "index.json" and path.name not in expected
    )


def _remove_stale_web_catalogs(directory: Path, catalogs) -> None:
    for path in _stale_web_catalogs(directory, catalogs):
        path.unlink()
        print(f"Removed stale Web catalog: {path}")


def cmd_compile_web(args) -> int:
    info = load_po(Path(args.catalog))
    problems = validate_catalog(info.translations)
    if problems and not args.allow_invalid:
        print("Catalog has validation errors; run 'validate' first.", file=sys.stderr)
        return 1
    output = Path(args.output or ROOT / "web_static" / "locales" / f"{info.code}.json")
    catalogs = None
    if not args.no_index:
        catalogs, catalog_errors = _discover_catalogs_strict(ROOT / "locales")
        if _report_catalog_errors(catalog_errors):
            return 1
        if info.code not in catalogs:
            catalogs[info.code] = info

    _write_web_catalog(info, output)
    if catalogs is not None:
        _write_web_index(output.parent, catalogs)
    print(f"Compiled {len(info.translations)} entries to {output}")
    return 0


def cmd_compile_all_web(args) -> int:
    output_dir = Path(args.output_dir or ROOT / "web_static" / "locales")
    catalogs, catalog_errors = _discover_catalogs_strict(
        Path(args.locales_dir or ROOT / "locales")
    )
    failures = 1 if _report_catalog_errors(catalog_errors) else 0
    for code, info in catalogs.items():
        problems = validate_catalog(info.translations)
        if problems and not args.allow_invalid:
            print(f"{code}: validation failed; no Web catalogs were written.", file=sys.stderr)
            failures += 1

    if failures:
        return 1

    for code, info in catalogs.items():
        _write_web_catalog(info, output_dir / f"{code}.json")
        print(f"Compiled {code}: {len(info.translations)} entries")
    _remove_stale_web_catalogs(output_dir, catalogs)
    _write_web_index(output_dir, catalogs)
    return 0


def cmd_sync(_args) -> int:
    messages = source_messages()
    catalogs, catalog_errors = _discover_catalogs_strict(ROOT / "locales")
    failures = 1 if _report_catalog_errors(catalog_errors) else 0
    for code, info in catalogs.items():
        problems = validate_catalog(info.translations)
        if problems:
            print(f"{code}: {len(problems)} entries need review.", file=sys.stderr)
            failures += 1

    if failures:
        return 1

    pot_path = ROOT / "locales" / "serrebitorrent.pot"
    pot_path.write_text(render_pot(messages), encoding="utf-8")
    print(f"Updated {pot_path.relative_to(ROOT)}")

    output_dir = ROOT / "web_static" / "locales"
    for code, info in catalogs.items():
        _write_web_catalog(info, output_dir / f"{code}.json")
    _remove_stale_web_catalogs(output_dir, catalogs)
    _write_web_index(output_dir, catalogs)
    print(f"Compiled {len(catalogs)} Web catalog(s).")
    return 0


def cmd_check(_args) -> int:
    failures = 0
    messages = source_messages()

    pot_path = ROOT / "locales" / "serrebitorrent.pot"
    expected_pot = render_pot(messages)
    actual_pot = pot_path.read_text(encoding="utf-8") if pot_path.exists() else ""
    if actual_pot != expected_pot:
        print(
            "Translation template is out of date. Run: "
            "python tools/translation_tool.py sync",
            file=sys.stderr,
        )
        failures += 1

    catalogs, catalog_errors = _discover_catalogs_strict(ROOT / "locales")
    if _report_catalog_errors(catalog_errors):
        failures += 1
    output_dir = ROOT / "web_static" / "locales"

    for code, info in catalogs.items():
        problems = validate_catalog(info.translations)
        if problems:
            print(f"{code}: {len(problems)} invalid translation entries.", file=sys.stderr)
            failures += 1

        expected_json = json.loads(render_web_catalog(info))
        json_path = output_dir / f"{code}.json"
        try:
            actual_json = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            actual_json = None
        if actual_json != expected_json:
            print(
                f"{json_path.relative_to(ROOT)} is out of date. "
                "Run: python tools/translation_tool.py sync",
                file=sys.stderr,
            )
            failures += 1

    stale_catalogs = _stale_web_catalogs(output_dir, catalogs)
    for stale in stale_catalogs:
        print(
            f"{stale.relative_to(ROOT)} has no matching locales/*.po catalog. "
            "Run: python tools/translation_tool.py sync",
            file=sys.stderr,
        )
        failures += 1

    expected_index = json.loads(render_web_index(catalogs))
    index_path = output_dir / "index.json"
    try:
        actual_index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        actual_index = None
    if actual_index != expected_index:
        print(
            f"{index_path.relative_to(ROOT)} is out of date. "
            "Run: python tools/translation_tool.py sync",
            file=sys.stderr,
        )
        failures += 1

    if failures:
        return 1

    print(
        f"Translation pipeline is synchronized: "
        f"{len(messages)} source messages, {len(catalogs)} catalog(s)."
    )
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
    compile_web.add_argument("--no-index", action="store_true")
    compile_web.set_defaults(func=cmd_compile_web)

    compile_all = sub.add_parser("compile-all-web", help="compile all locales/*.po catalogs for the Web UI")
    compile_all.add_argument("--locales-dir")
    compile_all.add_argument("--output-dir")
    compile_all.add_argument("--allow-invalid", action="store_true")
    compile_all.set_defaults(func=cmd_compile_all_web)

    sync = sub.add_parser(
        "sync",
        help="regenerate POT and Web catalogs from the current source and PO files",
    )
    sync.set_defaults(func=cmd_sync)

    check = sub.add_parser(
        "check",
        help="fail when POT, PO validation or generated Web catalogs are out of sync",
    )
    check.set_defaults(func=cmd_check)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
