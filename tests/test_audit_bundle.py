import json
from pathlib import Path
import subprocess
import sys

from tools import audit_bundle

REQUIRED_MESSAGE = audit_bundle.REQUIRED_WEB_MESSAGES[0]


def _make_bundle(root: Path, *, include_json: bool = True, translations=None) -> Path:
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
                "translations": (
                    {REQUIRED_MESSAGE: "Traduzido"} if translations is None else translations
                ),
            }),
            encoding="utf-8",
        )
    return bundle


def _audit(bundle: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "tools/audit_bundle.py", str(bundle)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_bundle_audit_accepts_complete_translation_assets(tmp_path):
    bundle = _make_bundle(tmp_path)

    result = _audit(bundle)

    assert result.returncode == 0, result.stderr
    assert "translation catalogs: 1" in result.stdout


def test_bundle_audit_rejects_missing_web_translation_asset(tmp_path):
    bundle = _make_bundle(tmp_path, include_json=False)

    result = _audit(bundle)

    assert result.returncode != 0
    assert "Expected one bundled Web catalog for pt-BR" in (result.stderr + result.stdout)


def test_bundle_audit_rejects_catalog_missing_a_required_message(tmp_path):
    bundle = _make_bundle(tmp_path, translations={"Some other string": "Outra string"})

    result = _audit(bundle)

    assert result.returncode != 0
    assert "missing required messages" in (result.stderr + result.stdout)
    assert REQUIRED_MESSAGE in (result.stderr + result.stdout)


def test_bundle_audit_rejects_catalog_without_translations_object(tmp_path):
    bundle = _make_bundle(tmp_path)
    (bundle / "web_static" / "locales" / "pt-BR.json").write_text(
        json.dumps({"language": "pt-BR", "name": "Português (Brasil)"}),
        encoding="utf-8",
    )

    result = _audit(bundle)

    assert result.returncode != 0
    assert "has no translations object" in (result.stderr + result.stdout)


def test_bundle_audit_rejects_non_object_web_catalog(tmp_path):
    # json.loads accepts a bare null, which used to reach a .get() call and
    # report an AttributeError traceback instead of the reason for the stop.
    bundle = _make_bundle(tmp_path)
    (bundle / "web_static" / "locales" / "pt-BR.json").write_text("null", encoding="utf-8")

    result = _audit(bundle)

    assert result.returncode != 0
    assert "is not a JSON object" in (result.stderr + result.stdout)
    assert "Traceback" not in (result.stderr + result.stdout)


def test_bundle_audit_rejects_non_object_locale_index(tmp_path):
    bundle = _make_bundle(tmp_path)
    (bundle / "web_static" / "locales" / "index.json").write_text(
        "[]", encoding="utf-8"
    )

    result = _audit(bundle)

    assert result.returncode != 0
    assert "Bundled Web locale index is not a JSON object" in (result.stderr + result.stdout)
    assert "Traceback" not in (result.stderr + result.stdout)


def test_bundle_audit_rejects_unparseable_locale_index(tmp_path):
    bundle = _make_bundle(tmp_path)
    (bundle / "web_static" / "locales" / "index.json").write_text(
        "{not json", encoding="utf-8"
    )

    result = _audit(bundle)

    assert result.returncode != 0
    assert "Bundled Web locale index is invalid" in (result.stderr + result.stdout)
    assert "Traceback" not in (result.stderr + result.stdout)
