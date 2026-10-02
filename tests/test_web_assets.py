from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web_static"


def test_web_bootstrap_assets_are_local():
    index = (WEB / "index.html").read_text(encoding="utf-8")

    assert "vendor/bootstrap/bootstrap.min.css" in index
    assert "vendor/bootstrap/bootstrap.bundle.min.js" in index
    assert "cdn.jsdelivr.net/npm/bootstrap" not in index

    assert (WEB / "vendor/bootstrap/bootstrap.min.css").is_file()
    assert (WEB / "vendor/bootstrap/bootstrap.bundle.min.js").is_file()
    assert (WEB / "vendor/bootstrap/LICENSE").is_file()



def test_add_profile_icon_button_has_explicit_accessible_name():
    index = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'data-bs-target="#addProfileModal"' in index
    assert 'aria-label="Add Profile"' in index



def test_web_toolbar_icon_buttons_have_explicit_accessible_names():
    index = (WEB / "index.html").read_text(encoding="utf-8")

    for label in (
        "Add Torrent",
        "Refresh torrent list",
        "Start selected torrents",
        "Pause selected torrents",
        "Remove selected torrents",
    ):
        assert f'aria-label="{label}"' in index
