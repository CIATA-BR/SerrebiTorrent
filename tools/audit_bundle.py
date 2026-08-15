"""Reject incomplete or unnecessarily bloated standalone bundles."""

from __future__ import annotations

import argparse
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
