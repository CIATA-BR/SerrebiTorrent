#!/usr/bin/env python3
"""Prepend a human-readable entry to CHANGELOG.md from release notes.

Mirrors the changelog behavior of BlindRSS (tools/release.py update-changelog):
structured release notes go in, one readable bullet per change comes out,
conventional-commit prefixes are stripped, and chore/ci/docs/test commits are
omitted. Updating the same version tag twice replaces the old entry instead of
duplicating it, so re-running a release is safe.

Usage:
    python tools/update_changelog.py --version-tag v1.22.29 --notes-file notes.txt
        [--output CHANGELOG.md] [--date 2026-09-29]
"""

import argparse
import os
import re
from datetime import datetime, timezone

CONVENTIONAL_PREFIX_RE = re.compile(r"^([a-zA-Z]+)(?:\([^)]*\))?!?:\s*(.+)$")
OMIT_COMMIT_TYPES = {"chore", "ci", "docs", "test"}
SECTION_HEADERS = {"breaking", "features", "fixes", "other"}
HEADER = "# Changelog\n\nAll notable changes to SerrebiTorrent are recorded here.\n"


def _readable_item(raw):
    text = str(raw or "").strip()
    if text.startswith("- "):
        text = text[2:].strip()
    text = text.lstrip("@").strip()
    match = CONVENTIONAL_PREFIX_RE.match(text)
    if match:
        text = match.group(2).strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


def items_from_notes(notes_text):
    items = []
    seen = set()
    for line in str(notes_text or "").splitlines():
        text = line.strip().lstrip("\ufeff")
        if not text or text == "- None":
            continue
        if text.startswith("#") or text.casefold() in SECTION_HEADERS:
            continue
        if not text.startswith("- "):
            continue
        raw_item = text[2:].strip()
        match = CONVENTIONAL_PREFIX_RE.match(raw_item)
        if match and match.group(1).lower() in OMIT_COMMIT_TYPES:
            continue
        item = _readable_item(raw_item)
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def entry_from_notes(version_tag, notes_text, release_date=None):
    release_date = release_date or datetime.now(timezone.utc).date().isoformat()
    lines = [f"## {version_tag} - {release_date}", ""]
    items = items_from_notes(notes_text) or ["Maintenance update."]
    lines.extend(f"- {item}" for item in items)
    return "\n".join(lines).rstrip() + "\n"


def update_changelog(version_tag, notes_text, changelog_path, release_date=None):
    entry = entry_from_notes(version_tag, notes_text, release_date=release_date)
    if os.path.isfile(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = HEADER
    if not existing.strip():
        existing = HEADER
    if not existing.startswith("# Changelog"):
        existing = "# Changelog\n\n" + existing.lstrip()

    heading_re = re.compile(
        rf"^##\s+{re.escape(version_tag)}(?:\s+-[^\n]*)?$", re.MULTILINE
    )
    match = heading_re.search(existing)
    if match:
        next_match = re.search(r"^##\s+", existing[match.end():], re.MULTILINE)
        end = match.end() + next_match.start() if next_match else len(existing)
        updated = existing[: match.start()].rstrip() + "\n\n" + entry + "\n" + existing[end:].lstrip()
    else:
        first_version = re.search(r"^##\s+", existing, re.MULTILINE)
        insert_at = first_version.start() if first_version else len(existing)
        updated = existing[:insert_at].rstrip() + "\n\n" + entry + "\n" + existing[insert_at:].lstrip()

    with open(changelog_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated.rstrip() + "\n")
    return entry


def main():
    parser = argparse.ArgumentParser(description="Prepend a release entry to CHANGELOG.md.")
    parser.add_argument("--version-tag", required=True, help="e.g. v1.22.29")
    parser.add_argument("--notes-file", required=True, help="Release notes written by release_tools.ps1")
    parser.add_argument("--output", default="CHANGELOG.md")
    parser.add_argument("--date", default=None, help="Release date YYYY-MM-DD (default: today UTC)")
    args = parser.parse_args()

    with open(args.notes_file, "r", encoding="utf-8-sig") as f:
        notes_text = f.read()
    entry = update_changelog(args.version_tag, notes_text, args.output, release_date=args.date)
    print(f"CHANGELOG.md updated for {args.version_tag}:")
    print(entry)


if __name__ == "__main__":
    main()
