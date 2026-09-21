import json
from pathlib import Path
import subprocess
import sys

from translation_catalog import render_po


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


def test_compile_all_web_rejects_duplicate_language_codes(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    first = render_po("es-ES", "Español", {"Settings": "Configuración"})
    second = render_po("es-ES", "Español alternativo", {"Search": "Buscar"})
    (locales / "es-ES.po").write_text(first, encoding="utf-8")
    (locales / "duplicate.po").write_text(second, encoding="utf-8")

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


def test_compile_all_web_rejects_case_insensitive_duplicate_codes(tmp_path):
    locales = tmp_path / "locales"
    output = tmp_path / "web"
    locales.mkdir()
    first = render_po("pt-BR", "Português", {"Settings": "Configurações"})
    second = render_po("PT-br", "Português alternativo", {"Search": "Pesquisar"})
    (locales / "pt-BR.po").write_text(first, encoding="utf-8")
    (locales / "duplicate.po").write_text(second, encoding="utf-8")

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
