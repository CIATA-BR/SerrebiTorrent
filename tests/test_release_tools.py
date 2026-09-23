import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh") or shutil.which("powershell")

pytestmark = pytest.mark.skipif(PWSH is None, reason="PowerShell is required")


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.test", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _release_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / "app_version.py").write_text('APP_VERSION = "0.0.1"\n', encoding="utf-8")
    shutil.copy(ROOT / "tools" / "release_tools.ps1", repo / "tools" / "release_tools.ps1")

    _git(repo, "init", "-b", "main")
    for message in ("chore: initial", "feat: add a feature", "i18n: sync casing", "i18n: sync casing"):
        _git(repo, "commit", "--allow-empty", "-m", message)
    _git(repo, "tag", "v0.0.1", "HEAD~3")

    _git(repo, "checkout", "-b", "side")
    _git(repo, "commit", "--allow-empty", "-m", "test: cover the side branch")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "-m", "Merge pull request #7 from fork/side", "side")
    return repo


def _run(repo, tmp_path, *extra):
    notes_path = tmp_path / "notes.txt"
    result = subprocess.run(
        [
            PWSH,
            "-NoProfile",
            "-File",
            str(repo / "tools" / "release_tools.ps1"),
            "-NotesPath",
            str(notes_path),
            *extra,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return notes_path.read_text(encoding="utf-8-sig"), result.stdout


def test_release_notes_dedupe_subjects_and_skip_merges(tmp_path):
    repo = _release_repo(tmp_path)

    notes, stdout = _run(repo, tmp_path)

    assert notes.count("- i18n: sync casing") == 1
    assert "Merge pull request" not in notes
    assert "- feat: add a feature" in notes
    assert "- test: cover the side branch" in notes
    assert "NEXT_VERSION=0.1.0" in stdout


def test_release_notes_range_override_reaches_tagged_commits(tmp_path):
    repo = _release_repo(tmp_path)

    default_notes, _ = _run(repo, tmp_path)
    ranged_notes, _ = _run(repo, tmp_path, "-Range", "HEAD")

    assert "- chore: initial" not in default_notes
    assert "- chore: initial" in ranged_notes
