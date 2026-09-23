"""Run the packaged SerrebiTorrent diagnostics without developer runtimes."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--expected-libtorrent", required=True)
    args = parser.parse_args()

    executable = args.executable.resolve()
    report = args.report.resolve()
    if not executable.is_file():
        raise SystemExit(f"Packaged executable was not found: {executable}")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    # The app writes portable data (including the Web UI session key) next to
    # itself. Anything the self-test creates there must not reach the package.
    data_dir = executable.parent / "SerrebiTorrent_Data"
    if data_dir.exists():
        raise SystemExit(f"Package already contains user data: {data_dir}")

    try:
        with tempfile.TemporaryDirectory(prefix="SerrebiTorrent-self-test-") as temp:
            environment = os.environ.copy()
            if sys.platform == "win32":
                windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
                environment["PATH"] = os.pathsep.join(
                    str(path) for path in (windows / "System32", windows) if path.is_dir()
                )
            else:
                environment["PATH"] = "/usr/bin:/bin"
            environment["APPDATA"] = str(Path(temp) / "roaming")
            environment["LOCALAPPDATA"] = str(Path(temp) / "local")
            environment.pop("PYTHONHOME", None)
            environment.pop("PYTHONPATH", None)
            completed = subprocess.run(
                [str(executable), "--self-test", str(report)],
                cwd=executable.parent,
                env=environment,
                timeout=120,
                check=False,
            )
    finally:
        if data_dir.exists():
            shutil.rmtree(data_dir)

    if not report.is_file():
        raise SystemExit(
            f"Packaged self-test did not write a report (exit {completed.returncode})."
        )
    data = json.loads(report.read_text(encoding="utf-8"))
    if completed.returncode or not data.get("ok"):
        raise SystemExit("Packaged self-test failed: " + repr(data))
    packaged_libtorrent = data.get("results", {}).get("libtorrent", {})
    if packaged_libtorrent.get("version") != args.expected_libtorrent:
        raise SystemExit(
            "Packaged libtorrent version mismatch: "
            f"expected {args.expected_libtorrent}, got {packaged_libtorrent!r}"
        )
    print("Packaged self-test passed:")
    for name, value in sorted(data["results"].items()):
        print(f"- {name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
