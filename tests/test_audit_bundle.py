import json
from pathlib import Path
import subprocess
import sys


def _make_bundle(root: Path, *, include_json: bool = True) -> Path:
    bundle = root / "bundle"
    (bundle / "locales").mkdir(parents=True)
    (bundle / "web_static" / "locales").mkdir(parents=True)
    (bundle / "libtorrent.so").write_bytes(b"binary")
    (bundle / "locales" / "pt-BR.po").write_text(
        'msgid ""\nmsgstr ""\n"Language: pt-BR\\n"\n',
        encoding="utf-8",
    )
    (bundle / "web_static" / "locales" / "index.json").write_text(
        json.dumps({
            "languages": [{"code": "pt-BR", "name": "Português (Brasil)"}]
        }),
        encoding="utf-8",
    )
    if include_json:
        (bundle / "web_static" / "locales" / "pt-BR.json").write_text(
            json.dumps({
                "language": "pt-BR",
                "name": "Português (Brasil)",
                "translations": {},
            }),
            encoding="utf-8",
        )
    return bundle


def test_bundle_audit_accepts_complete_translation_assets(tmp_path):
    bundle = _make_bundle(tmp_path)

    result = subprocess.run(
        [sys.executable, "tools/audit_bundle.py", str(bundle)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "translation catalogs: 1" in result.stdout


def test_bundle_audit_rejects_missing_web_translation_asset(tmp_path):
    bundle = _make_bundle(tmp_path, include_json=False)

    result = subprocess.run(
        [sys.executable, "tools/audit_bundle.py", str(bundle)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Expected one bundled Web catalog for pt-BR" in (result.stderr + result.stdout)
