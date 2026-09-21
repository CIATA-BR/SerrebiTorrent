"""Reject incomplete or unnecessarily bloated standalone bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


FORBIDDEN_PARTS = {
    "hypothesis",
    "pip",
    "pyinstaller",
    "pytest",
    "setuptools",
    "wheel",
}
LEGACY_OPENSSL_PREFIXES = ("libcrypto-1_1", "libssl-1_1")

# Messages a shipped Web catalog must carry in every language. These explain
# state the user cannot otherwise infer, so falling back to English would hide
# the reason a request was refused.
REQUIRED_WEB_MESSAGES = (
    "Too many failed attempts. Try again later.",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise SystemExit(f"Bundle directory was not found: {bundle}")

    # A macOS .app keeps one real copy of each binary under Contents/Frameworks
    # and symlinks it elsewhere in the bundle. Counting symlinks would report
    # the libtorrent extension twice and double its contribution to the total.
    files = [
        path
        for path in bundle.rglob("*")
        if path.is_file() and not path.is_symlink()
    ]
    relative = [path.relative_to(bundle) for path in files]
    lowered_parts = {
        part.lower().split("-", 1)[0]
        for path in relative
        for part in path.parts[:-1]
    }
    included_build_tools = sorted(FORBIDDEN_PARTS & lowered_parts)
    if included_build_tools:
        raise SystemExit(
            "Build/development packages leaked into the bundle: "
            + ", ".join(included_build_tools)
        )

    extensions = [
        path for path in relative
        if path.name.startswith("libtorrent") and path.suffix in {".pyd", ".so"}
    ]
    if len(extensions) != 1:
        raise SystemExit(f"Expected one bundled libtorrent extension, found: {extensions}")

    def find_relative_suffix(*parts: str) -> list[Path]:
        wanted = tuple(parts)
        return [
            path for path in relative
            if len(path.parts) >= len(wanted) and tuple(path.parts[-len(wanted):]) == wanted
        ]

    index_files = find_relative_suffix("web_static", "locales", "index.json")
    if len(index_files) != 1:
        raise SystemExit(
            "Expected one bundled web_static/locales/index.json, found: "
            + repr(index_files)
        )

    try:
        language_index = json.loads((bundle / index_files[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit(f"Bundled Web locale index is invalid: {exc}") from exc

    languages = language_index.get("languages")
    if not isinstance(languages, list) or not languages:
        raise SystemExit("Bundled Web locale index contains no languages.")

    for item in languages:
        if not isinstance(item, dict) or not isinstance(item.get("code"), str):
            raise SystemExit(f"Bundled Web locale index entry is invalid: {item!r}")
        code = item["code"]
        po_files = find_relative_suffix("locales", f"{code}.po")
        json_files = find_relative_suffix("web_static", "locales", f"{code}.json")
        if len(po_files) != 1:
            raise SystemExit(
                f"Expected one bundled PO catalog for {code}, found: {po_files}"
            )
        if len(json_files) != 1:
            raise SystemExit(
                f"Expected one bundled Web catalog for {code}, found: {json_files}"
            )

        try:
            web_catalog = json.loads((bundle / json_files[0]).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise SystemExit(
                f"Bundled Web catalog for {code} is invalid: {exc}"
            ) from exc

        translations = web_catalog.get("translations")
        if not isinstance(translations, dict):
            raise SystemExit(
                f"Bundled Web catalog for {code} has no translations object."
            )
        missing = [message for message in REQUIRED_WEB_MESSAGES if not translations.get(message)]
        if missing:
            raise SystemExit(
                f"Bundled Web catalog for {code} is missing required messages: {missing}"
            )

    if sys.platform == "win32":
        names = {path.name.lower() for path in relative}
        legacy = sorted(
            name for name in names if name.startswith(LEGACY_OPENSSL_PREFIXES)
        )
        if legacy:
            raise SystemExit("Legacy OpenSSL DLLs leaked into the bundle: " + ", ".join(legacy))
        redundant = sorted(
            names
            & {
                "libcrypto-3-x64.dll",
                "libssl-3-x64.dll",
                "torrent-rasterbar.dll",
            }
        )
        if redundant:
            raise SystemExit(
                "Unvendored duplicate libtorrent DLLs leaked into the bundle: "
                + ", ".join(redundant)
            )

    total = sum(path.stat().st_size for path in files)
    print(f"Bundle audit passed: {len(files)} files, {total / (1024 * 1024):.1f} MiB")
    print(f"- libtorrent extension: {extensions[0].as_posix()}")
    print(f"- translation catalogs: {len(languages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
