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

    index = json.loads((output.parent / "index.json").read_text(encoding="utf-8"))
    languages = {item["code"]: item["name"] for item in index["languages"]}
    assert languages["pt-BR"] == "Português (Brasil)"
    assert languages["es-ES"] == "Español (España)"
