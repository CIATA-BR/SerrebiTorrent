from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_torrent_rows_show_upload_speed_for_seeding():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    assert "progress >= 100" in script
    assert "UL: ${fmtSize(t.up_rate)}/s" in script
    assert "DL: ${fmtSize(t.down_rate)}/s | UL: ${fmtSize(t.up_rate)}/s" in script


def test_web_delete_actions_confirm_and_report_failures():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    assert "confirmDeleteAction(deleteFiles)" in script
    assert "window.confirm(`Remove ${count} ${label}${dataText}?`)" in script
    assert "announceToSR(message, true)" in script
    assert "alert(message)" in script


def test_web_modal_controls_have_explicit_accessible_labels():
    markup = (ROOT / "web_static" / "index.html").read_text(encoding="utf-8")

    expected = [
        'aria-labelledby="addProfileModalLabel"',
        'for="profName"',
        'for="profType"',
        'for="profUrl"',
        'for="profUser"',
        'for="profPass"',
        'aria-labelledby="addTorrentModalLabel"',
        'for="torrentUrls"',
        'for="torrentFiles"',
        'for="torrentSavePath"',
        'aria-labelledby="settingsModalLabel"',
        'for="settingsDownloadPath"',
        'for="settingsRssInterval"',
        'for="settingsDlLimit"',
        'for="settingsUlLimit"',
        'for="webTheme"',
        'for="webRefreshRate"',
    ]

    for token in expected:
        assert token in markup


def test_web_status_filters_use_single_delegated_activation_path():
    markup = (ROOT / "web_static" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    assert 'onclick="setFilter(' not in markup
    assert "const link = e.target.closest('.sidebar-link');" in script
    assert "activateSidebarLink(link, e);" in script



def test_web_profile_switch_reports_http_and_network_failures():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    start = script.index("async function switchProfile")
    end = script.index("function updateDetailsDebounced", start)
    block = script[start:end]

    assert "if (!res.ok)" in block
    assert "await res.text()" in block
    assert "announceToSR(message, true)" in block
    assert "alert(message)" in block
    assert "catch (err)" in block



def test_web_clipboard_failures_are_announced_and_visible():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    start = script.index("function copyToClipboard")
    end = script.index("async function loadAppSettings", start)
    block = script[start:end]

    assert ".catch(err =>" in block
    assert "announceToSR(message, true)" in block
    assert "alert(message)" in block
    assert "Failed to copy to clipboard." in block
