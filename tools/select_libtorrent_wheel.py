"""Select the newest stable libtorrent wheel built for this release host."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


WHEEL_RE = re.compile(
    r"^libtorrent-(?P<version>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"\+(?P<stamp>\d+)-(?P<python>cp\d+)-(?P<abi>cp\d+)-(?P<platform>.+)\.whl$"
)


def select_wheel(wheel_dir: Path, python_tag: str, platform_pattern: str):
    candidates = []
    for path in wheel_dir.glob("libtorrent-*.whl"):
        match = WHEEL_RE.match(path.name)
        if not match or match["python"] != python_tag or match["abi"] != python_tag:
            continue
        if not re.search(platform_pattern, match["platform"]):
            continue
        key = (
            int(match["version"]),
            int(match["minor"]),
            int(match["patch"]),
            int(match["stamp"]),
        )
        version = ".".join((match["version"], match["minor"], match["patch"]))
        candidates.append((key, path.resolve(), version))
    if not candidates:
        raise SystemExit(
            f"No {python_tag} libtorrent wheel matching {platform_pattern!r} "
            f"was found in {wheel_dir.resolve()}"
        )
    _, path, version = max(candidates)
    return path, version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--python-tag", default="cp314")
    parser.add_argument("--platform-pattern", required=True)
    parser.add_argument("--format", choices=("lines", "cmd"), default="lines")
    args = parser.parse_args()
    path, version = select_wheel(
        args.wheel_dir, args.python_tag, args.platform_pattern
    )
    if args.format == "cmd":
        print(f"LIBTORRENT_WHEEL={path}")
        print(f"LIBTORRENT_VERSION={version}")
    else:
        print(path)
        print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
