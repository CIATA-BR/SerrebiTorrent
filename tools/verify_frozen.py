"""Run the packaged SerrebiTorrent diagnostics without developer runtimes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    executable = args.executable.resolve()
    report = args.report.resolve()
    if not executable.is_file():
        raise SystemExit(f"Packaged executable was not found: {executable}")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="SerrebiTorrent-self-test-") as temp:
        environment = os.environ.copy()
        windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        environment["PATH"] = os.pathsep.join(
            str(path) for path in (windows / "System32", windows) if path.is_dir()
        )
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

    if not report.is_file():
        raise SystemExit(
            f"Packaged self-test did not write a report (exit {completed.returncode})."
        )
    data = json.loads(report.read_text(encoding="utf-8"))
    if completed.returncode or not data.get("ok"):
        raise SystemExit("Packaged self-test failed: " + repr(data))
    print("Packaged self-test passed:")
    for name, value in sorted(data["results"].items()):
        print(f"- {name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
