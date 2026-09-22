import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from translation_catalog import load_po, render_po


def test_compile_web_emits_catalog_and_language_index(tmp_path):
    catalog = tmp_path / "es-ES.po"
    output = tmp_path / "web" / "es-ES.json"
    catalog.write_text(
        render_po(
            "es-ES",
            "Español (España)",
            {"Settings": "Configuración", "Search": "Buscar"},
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-web",
            str(catalog),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["language"] == "es-ES"
    assert payload["name"] == "Español (España)"
    assert payload["translations"]["Settings"] == "Configuración"


def test_checked_in_translation_artifacts_are_synchronized():
    result = subprocess.run(
        [sys.executable, "tools/translation_tool.py", "check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_compile_all_web_rejects_malformed_catalog(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    (locales / "broken.po").write_text(
        'msgid "Settings"\nmsgstr "unterminated\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "failed to parse catalog" in result.stderr


@pytest.mark.skipif(sys.platform != "linux", reason="case-only catalog filenames collide on this filesystem")
def test_compile_all_web_rejects_duplicate_language_codes(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    first = render_po("es-ES", "Español", {"Settings": "Configuración"})
    second = render_po("ES-es", "Español alternativo", {"Search": "Buscar"})
    (locales / "es-ES.po").write_text(first, encoding="utf-8")
    (locales / "ES-es.po").write_text(second, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "duplicate normalized language code" in result.stderr


def test_compile_all_web_rejects_unsafe_language_code(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    (locales / "unsafe.po").write_text(
        'msgid ""\nmsgstr ""\n"Language: ../escape\\n"\n\nmsgid "Settings"\nmsgstr "Safe"\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "invalid catalog language code" in result.stderr
    assert not (tmp_path / "escape.json").exists()


@pytest.mark.skipif(sys.platform != "linux", reason="case-only catalog filenames collide on this filesystem")
def test_compile_all_web_rejects_case_insensitive_duplicate_codes(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    first = render_po("pt-BR", "Português", {"Settings": "Configurações"})
    second = render_po("PT-br", "Português alternativo", {"Search": "Pesquisar"})
    (locales / "pt-BR.po").write_text(first, encoding="utf-8")
    (locales / "PT-br.po").write_text(second, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "duplicate normalized language code" in result.stderr


def test_compile_all_web_does_not_partially_write_on_validation_failure(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    output.mkdir()

    valid = render_po("es-ES", "Español", {"Settings": "Configuración"})
    invalid = render_po(
        "fr-FR",
        "Français",
        {"Connected to {name}": "Connecté"},
    )
    (locales / "es-ES.po").write_text(valid, encoding="utf-8")
    (locales / "fr-FR.po").write_text(invalid, encoding="utf-8")
    existing = output / "es-ES.json"
    existing.write_text("sentinel\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert existing.read_text(encoding="utf-8") == "sentinel\n"
    assert not (output / "fr-FR.json").exists()
    assert not (output / "index.json").exists()


def test_compile_all_web_removes_stale_generated_catalog(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    output.mkdir()

    (locales / "es-ES.po").write_text(
        render_po("es-ES", "Español", {"Settings": "Configuración"}),
        encoding="utf-8",
    )
    stale = output / "fr-FR.json"
    stale.write_text('{"language":"fr-FR"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    assert (output / "es-ES.json").exists()
    index = json.loads((output / "index.json").read_text(encoding="utf-8"))
    assert index["languages"] == [{"code": "es-ES", "name": "Español"}]


def test_compile_all_web_rejects_filename_header_mismatch(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()

    (locales / "wrong-name.po").write_text(
        render_po("fr-FR", "Français", {"Settings": "Paramètres"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "tools/translation_tool.py",
            "compile-all-web",
            "--locales-dir",
            str(locales),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "filename must match Language header" in result.stderr
    assert "fr-FR.po" in result.stderr
    assert not (output / "fr-FR.json").exists()


def _coverage(*args):
    return subprocess.run(
        [sys.executable, "tools/translation_tool.py", "coverage", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_coverage_reports_every_catalog_and_does_not_block_by_default():
    result = _coverage()

    assert result.returncode == 0, result.stderr
    for catalog in Path("locales").glob("*.po"):
        assert f"{catalog.stem}:" in result.stdout


def test_coverage_json_arithmetic_is_consistent():
    result = _coverage("--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["total_source_messages"] > 200
    for row in payload["locales"]:
        assert row["translated"] + row["missing"] == row["total"]
        assert row["total"] == payload["total_source_messages"]
        assert 0 <= row["percent"] <= 100


def test_coverage_threshold_only_fails_when_requested():
    assert _coverage("--min-percent", "0").returncode == 0

    result = _coverage("--min-percent", "100.1")
    assert result.returncode == 1
    assert "below the required" in result.stderr


def test_coverage_counts_fuzzy_entries_as_needs_review(tmp_path):
    from tools.translation_tool import _needs_review_count

    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "es-ES.po").write_text(
        render_po("es-ES", "Español", {"Settings": "Configuración"})
        + '\n#, fuzzy\nmsgid "Search"\nmsgstr "Buscar"\n',
        encoding="utf-8",
    )

    info = load_po(locales / "es-ES.po")
    assert _needs_review_count(info) == 1
    # A fuzzy entry is excluded from the runtime translations.
    assert "Search" not in info.translations


def test_coverage_needs_review_matches_each_catalog():
    payload = json.loads(_coverage("--json").stdout)

    for row in payload["locales"]:
        po_text = (Path("locales") / f"{row['code']}.po").read_text(encoding="utf-8")
        expected = len(re.findall(r"^#,\s*.*\bfuzzy\b", po_text, re.MULTILINE))
        assert row["needs_review"] == expected


def test_every_catalog_translates_the_login_lockout_message():
    # The message explains why a correct password was rejected, so a locale that
    # silently falls back to English hides the reason from that user.
    message = "Too many failed attempts. Try again later."
    catalogs = sorted(Path("locales").glob("*.po"))

    assert catalogs
    for path in catalogs:
        info = load_po(path)
        assert info.translations.get(message), f"{path.name} is missing the lockout message"
