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


def test_web_settings_load_failures_are_announced_and_visible():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    start = script.index("async function loadAppSettings")
    end = script.index("async function loadRemoteSettings", start)
    block = script[start:end]

    assert "Failed to load settings." in block
    assert "announceToSR(message, true)" in block
    assert "alert(message)" in block


def test_web_profile_load_failure_is_announced_once_until_success():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    start = script.index("window.fetchProfiles = async function()")
    end = script.index("async function switchProfile", start)
    block = script[start:end]

    assert "list.dataset.loadError !== 'true'" in block
    assert "list.dataset.loadError = 'true'" in block
    assert "delete list.dataset.loadError" in block
    assert "announceToSR(message, true)" in block



def test_remote_settings_load_failure_is_accessible():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    start = script.index("async function loadRemoteSettings")
    # loadRemoteSettings is the last function in app.js; slice to end of file
    block = script[start:]

    assert "alertBox.setAttribute('role', 'alert')" in block
    assert "announceToSR(message, true)" in block
    assert "Failed to load settings." in block



def test_web_form_actions_and_refresh_failures_are_announced():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    assert 'announceToSR("Torrent added.")' in script
    assert "Failed to add torrent:" in script
    assert "announceToSR(message, true)" in script
    assert "const message = 'Settings saved.'" in script
    assert "const message = 'Error saving settings.'" in script
    assert "const message = 'Remote settings saved.'" in script
    assert "Error saving remote settings:" in script
    assert "let refreshErrorActive = false;" in script
    assert "if (!refreshErrorActive)" in script
    assert "refreshErrorActive = false;" in script



def test_web_add_profile_form_posts_and_reports_failures():
    script = (ROOT / "web_static" / "app.js").read_text(encoding="utf-8")

    assert "document.getElementById('addProfileForm')" in script
    assert "apiFetch('/api/v2/profiles/add'" in script
    assert "formData.append('name'" in script
    assert "formData.append('type'" in script
    assert "formData.append('url'" in script
    assert "formData.append('user'" in script
    assert "formData.append('password'" in script
    assert "announceToSR('Profile created.')" in script
    assert "announceToSR(message, true)" in script
    assert "if (window.fetchProfiles) await window.fetchProfiles()" in script
