from pathlib import Path


def test_pyinstaller_bundles_locales_directory():
    spec = Path("SerrebiTorrent.spec").read_text(encoding="utf-8")
    assert "os.path.isdir('locales')" in spec
    assert "(os.path.abspath('locales'), 'locales')" in spec


def test_translation_docs_keep_credentials_out_of_app_flow():
    docs = Path("locales/README.md").read_text(encoding="utf-8")
    assert "does not request or store GitHub credentials" in docs
    assert "SERREBITORRENT_TRANSLATION_URL" in docs
