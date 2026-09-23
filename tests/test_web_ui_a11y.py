import threading

import pytest
from werkzeug.serving import make_server

import web_server

pytest.importorskip("pytest_playwright")
pytest.importorskip("axe_playwright_python")

from axe_playwright_python.sync_playwright import Axe

pytestmark = pytest.mark.e2e


class DummyConfigManager:
    def __init__(self, profiles):
        self._profiles = profiles
        self._preferences = {"language": "pt-BR"}

    def get_profiles(self):
        return self._profiles

    def get_preferences(self):
        return dict(self._preferences)


class DummyApp:
    def __init__(self, torrents, profiles, current_profile_id):
        self.all_torrents = torrents
        self.config_manager = DummyConfigManager(profiles)
        self.current_profile_id = current_profile_id

    def _open_path(self, path):
        return None


class DummyClient:
    def __init__(self, torrents):
        self._torrents = torrents

    def get_torrents_full(self):
        return list(self._torrents)

    def get_files(self, h):
        return []


@pytest.fixture(scope="session")
def web_ui_server():
    torrents = [
        {
            "hash": "a" * 40,
            "name": "Alpha",
            "size": 1000,
            "done": 250,
            "state": 1,
            "message": "",
            "tracker_domain": "tracker.one",
            "down_rate": 0,
            "up_rate": 0,
            "save_path": "C:\\Downloads",
        },
        {
            "hash": "b" * 40,
            "name": "Beta",
            "size": 1000,
            "done": 1000,
            "state": 1,
            "message": "",
            "tracker_domain": "tracker.two",
            "down_rate": 0,
            "up_rate": 0,
            "save_path": "C:\\Downloads",
        },
    ]
    profiles = {
        "local": {
            "name": "Local",
            "type": "local",
            "url": "C:\\Downloads",
            "user": "",
            "password": "",
        }
    }
    app_ref = DummyApp(torrents, profiles, "local")
    client = DummyClient(torrents)

    original_config = web_server.WEB_CONFIG.copy()
    web_server.WEB_CONFIG.update(
        {
            "app": app_ref,
            "client": client,
            "username": "admin",
            "password": "password",
        }
    )

    server = make_server("127.0.0.1", 0, web_server.app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"

    try:
        yield url
    finally:
        server.shutdown()
        thread.join()
        web_server.WEB_CONFIG.update(original_config)


def _block_cdn(route):
    route.fulfill(status=200, body="")


def _login(page, base_url, expected_language="pt-BR"):
    page.route("https://cdn.jsdelivr.net/**", _block_cdn)
    page.goto(f"{base_url}/login.html")
    page.fill("#username", "admin")
    page.fill("#password", "password")
    page.click("button[type=submit]")
    page.wait_for_url(f"{base_url}/")
    page.wait_for_selector("#torrentTable")
    page.wait_for_selector("tr[data-hash]")
    if expected_language:
        page.wait_for_function(
            "(lang) => document.documentElement.lang === lang",
            arg=expected_language,
        )


def test_web_ui_axe(page, web_ui_server):
    _login(page, web_ui_server)
    axe = Axe()
    results = axe.run(page)
    assert results.violations_count == 0, results.generate_report()


def test_web_ui_keyboard_navigation(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")
    page.wait_for_function("document.activeElement && document.activeElement.matches('tr[data-hash]')")
    first_hash = page.evaluate("document.activeElement.getAttribute('data-hash')")
    page.keyboard.press("ArrowDown")
    page.wait_for_function(
        "(prev) => document.activeElement && document.activeElement.getAttribute('data-hash') !== prev",
        arg=first_hash,
    )
    active_hash = page.evaluate("document.activeElement.getAttribute('data-hash')")
    assert active_hash and active_hash != first_hash


def test_web_ui_landmarks(page, web_ui_server):
    _login(page, web_ui_server)
    assert page.locator("header[role='banner']").count() == 1
    assert page.locator("main[role='main']").count() == 1
    assert page.locator("nav[aria-label='Navegação']").count() == 1


def test_web_ui_pt_br_accessible_labels(page, web_ui_server):
    _login(page, web_ui_server)
    assert page.locator("html").get_attribute("lang") == "pt-BR"
    assert page.locator("a[href='#torrentTable']").inner_text() == "Pular para a lista de torrents"
    assert page.locator("#contextMenu").get_attribute("aria-label") == "Ações do torrent"
    assert page.locator("#torrentTable").get_attribute("aria-label") == "torrents"


def test_web_ui_loads_community_catalog_and_keeps_user_data(page, web_ui_server):
    def prefs(route):
        route.fulfill(status=200, content_type="application/json", body='{"language":"es-ES"}')

    def language_index(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"languages":[{"code":"es-ES","name":"Español (España)"}]}',
        )

    def catalog(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"language":"es-ES","name":"Español (España)","translations":{"Navigation":"Navegación","Torrent Actions":"Acciones del torrent","Settings":"Configuración"}}',
        )

    page.route("**/api/v2/app/prefs", prefs)
    page.route("**/locales/index.json", language_index)
    page.route("**/locales/es-ES.json", catalog)
    _login(page, web_ui_server, expected_language="es-ES")

    assert page.locator("nav").first.get_attribute("aria-label") == "Navegación"
    assert page.locator("#torrentActionsBtn").inner_text() == "Acciones del torrent"
    # Torrent names are data, not localization source strings.
    assert page.locator("tr[data-hash] .col-name").first.inner_text() == "Alpha"
    assert page.locator("#appLanguage option[value='es-ES']").count() == 1


def test_web_ui_refresh_moves_focus_when_focused_torrent_disappears(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")

    page.locator('tr[data-hash="' + "b" * 40 + '"]').focus()
    assert page.evaluate("document.activeElement.dataset.hash") == "b" * 40

    page.route(
        "**/api/v2/torrents/all",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"hash":"' + "a" * 40 + '","name":"Alpha","size":1000,"done":250,"state":1,"message":"","tracker_domain":"tracker.one","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"}]',
        ),
    )

    page.evaluate("refreshData(true)")
    page.wait_for_function(
        "(hash) => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.hash === hash",
        arg="a" * 40,
    )

    page.wait_for_function(
        "(message) => document.getElementById('aria-announcer').textContent === message",
        arg="O torrent em foco não está mais disponível. Foco movido para Alpha.",
    )


def test_web_ui_refresh_keeps_focus_in_grid_when_last_torrent_disappears(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_selector("tr[data-hash]")

    page.locator('tr[data-hash="' + "a" * 40 + '"]').focus()
    assert page.evaluate("document.activeElement.dataset.hash") == "a" * 40

    page.route(
        "**/api/v2/torrents/all",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="[]",
        ),
    )

    page.evaluate("refreshData(true)")
    page.wait_for_function("document.activeElement && document.activeElement.id === 'torrentTable'")

    assert page.locator("#torrentTable").get_attribute("tabindex") == "0"
    page.wait_for_function(
        "(message) => document.getElementById('aria-announcer').textContent === message",
        arg="O torrent em foco não está mais disponível. A lista de torrents está vazia. 1 torrent removido.",
    )


def test_web_ui_space_toggles_focused_torrent_selection(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.activeElement && document.activeElement.matches('tr[data-hash]')")

    focused_hash = page.evaluate("document.activeElement.dataset.hash")
    focused_name = page.locator(f'tr[data-hash="{focused_hash}"] .col-name').inner_text()

    page.keyboard.press("Space")
    page.wait_for_function(
        "(hash) => document.querySelector(`tr[data-hash='${hash}']`)?.getAttribute('aria-selected') === 'true'",
        arg=focused_hash,
    )
    assert page.evaluate("document.activeElement.dataset.hash") == focused_hash
    page.wait_for_function(
        "(message) => document.getElementById('aria-announcer').textContent === message",
        arg=f"Selecionado: {focused_name}",
    )

    page.keyboard.press("Space")
    page.wait_for_function(
        "(hash) => document.querySelector(`tr[data-hash='${hash}']`)?.getAttribute('aria-selected') === 'false'",
        arg=focused_hash,
    )
    assert page.evaluate("document.activeElement.dataset.hash") == focused_hash
    page.wait_for_function(
        "(message) => document.getElementById('aria-announcer').textContent === message",
        arg=f"Desmarcado: {focused_name}",
    )


def test_web_ui_modal_returns_focus_to_trigger(page, web_ui_server):
    _login(page, web_ui_server)

    trigger = page.locator('[data-bs-target="#addTorrentModal"]')
    trigger.focus()
    assert page.evaluate("document.activeElement === document.querySelector('[data-bs-target=\"#addTorrentModal\"]')")

    page.evaluate(
        """() => {
            const trigger = document.querySelector('[data-bs-target="#addTorrentModal"]');
            const modal = document.getElementById('addTorrentModal');
            const showEvent = new Event('show.bs.modal');
            Object.defineProperty(showEvent, 'relatedTarget', { value: trigger });
            modal.dispatchEvent(showEvent);
            modal.dispatchEvent(new Event('hidden.bs.modal'));
        }"""
    )

    page.wait_for_function(
        "document.activeElement === document.querySelector('[data-bs-target=\"#addTorrentModal\"]')"
    )


def test_web_ui_action_menu_returns_focus_to_originating_row(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.activeElement && document.activeElement.matches('tr[data-hash]')")

    focused_hash = page.evaluate("document.activeElement.dataset.hash")
    page.evaluate(
        """() => {
            window.bootstrap = {
                Dropdown: {
                    getOrCreateInstance: () => ({ show() {} }),
                    getInstance: () => ({ hide() {} }),
                },
            };
        }"""
    )
    page.evaluate(
        """(hash) => {
            const row = document.querySelector(`tr[data-hash="${hash}"]`);
            showContextMenu({ target: row }, row);
            document.getElementById('torrentActionsBtn').dispatchEvent(new Event('hidden.bs.dropdown'));
        }""",
        focused_hash,
    )

    page.wait_for_function(
        "(hash) => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.hash === hash",
        arg=focused_hash,
    )


def test_web_ui_action_menu_returns_focus_to_actions_button(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.activeElement && document.activeElement.matches('tr[data-hash]')")
    focused_hash = page.evaluate("document.activeElement.dataset.hash")
    page.evaluate("(hash) => selectByHash(hash)", focused_hash)

    button = page.locator("#torrentActionsBtn")
    button.focus()
    page.evaluate(
        """() => {
            const button = document.getElementById('torrentActionsBtn');
            button.dispatchEvent(new Event('show.bs.dropdown'));
            button.dispatchEvent(new Event('hidden.bs.dropdown'));
        }"""
    )

    page.wait_for_function("document.activeElement && document.activeElement.id === 'torrentActionsBtn'")


def test_web_ui_modals_focus_useful_entry_controls(page, web_ui_server):
    _login(page, web_ui_server)

    cases = [
        ("#addProfileModal", "#profName"),
        ("#addTorrentModal", "#torrentUrls"),
        ("#settingsModal", "#app-settings-tab"),
    ]

    for modal_selector, target_selector in cases:
        page.evaluate(
            """({modalSelector}) => {
                const modal = document.querySelector(modalSelector);
                // Bootstrap fires show (which lifts inert) before shown.
                modal.dispatchEvent(new Event('show.bs.modal'));
                modal.dispatchEvent(new Event('shown.bs.modal'));
            }""",
            {"modalSelector": modal_selector},
        )
        page.wait_for_function(
            "(selector) => document.activeElement === document.querySelector(selector)",
            arg=target_selector,
        )


def test_web_ui_modal_escape_path_returns_focus_to_trigger(page, web_ui_server):
    _login(page, web_ui_server)

    trigger_selector = '[data-bs-target="#addTorrentModal"]'
    page.locator(trigger_selector).focus()

    page.evaluate(
        """({triggerSelector}) => {
            const trigger = document.querySelector(triggerSelector);
            const modal = document.getElementById('addTorrentModal');

            const showEvent = new Event('show.bs.modal');
            Object.defineProperty(showEvent, 'relatedTarget', { value: trigger });
            modal.dispatchEvent(showEvent);
            modal.dispatchEvent(new Event('shown.bs.modal'));

            const escapeEvent = new KeyboardEvent('keydown', {
                key: 'Escape',
                bubbles: true,
            });
            modal.dispatchEvent(escapeEvent);

            // Bootstrap owns Escape -> hide; hidden.bs.modal is the lifecycle
            // event our focus restoration intentionally depends on.
            modal.dispatchEvent(new Event('hidden.bs.modal'));
        }""",
        {"triggerSelector": trigger_selector},
    )

    page.wait_for_function(
        "(selector) => document.activeElement === document.querySelector(selector)",
        arg=trigger_selector,
    )


def test_web_ui_background_refresh_pauses_while_modal_is_open(page, web_ui_server):
    _login(page, web_ui_server)

    calls = {"all": 0}

    def torrents_all(route):
        calls["all"] += 1
        route.continue_()

    page.route("**/api/v2/torrents/all", torrents_all)

    page.evaluate(
        """() => {
            const modal = document.getElementById('addTorrentModal');
            modal.classList.add('show');
        }"""
    )
    page.evaluate("refreshData()")
    page.wait_for_timeout(150)
    assert calls["all"] == 0

    page.evaluate("refreshData(true)")
    page.wait_for_timeout(150)
    assert calls["all"] >= 1


def test_web_ui_announces_material_torrent_list_changes(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")

    def three_torrents(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='['
                 '{"hash":"' + "a" * 40 + '","name":"Alpha","size":1000,"done":250,"state":1,"message":"","tracker_domain":"tracker.one","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"},'
                 '{"hash":"' + "b" * 40 + '","name":"Beta","size":1000,"done":1000,"state":1,"message":"","tracker_domain":"tracker.two","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"},'
                 '{"hash":"' + "c" * 40 + '","name":"Gamma","size":1000,"done":100,"state":1,"message":"","tracker_domain":"tracker.three","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"}'
                 ']',
        )

    page.route("**/api/v2/torrents/all", three_torrents)
    page.evaluate("refreshData(true)")
    page.wait_for_function(
        "() => document.getElementById('aria-announcer').textContent === '1 torrent adicionado.'"
    )

    def swapped_torrents(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='['
                 '{"hash":"' + "a" * 40 + '","name":"Alpha","size":1000,"done":250,"state":1,"message":"","tracker_domain":"tracker.one","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"},'
                 '{"hash":"' + "c" * 40 + '","name":"Gamma","size":1000,"done":100,"state":1,"message":"","tracker_domain":"tracker.three","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"},'
                 '{"hash":"' + "d" * 40 + '","name":"Delta","size":1000,"done":100,"state":1,"message":"","tracker_domain":"tracker.four","down_rate":0,"up_rate":0,"save_path":"C:\\\\Downloads"}'
                 ']',
        )

    page.unroute("**/api/v2/torrents/all")
    page.route("**/api/v2/torrents/all", swapped_torrents)
    page.evaluate("refreshData(true)")
    page.wait_for_function(
        "() => document.getElementById('aria-announcer').textContent === '1 torrent adicionado. 1 torrent removido.'"
    )


def test_web_ui_initial_load_does_not_announce_list_population(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")

    assert page.locator("#aria-announcer").inner_text() == ""


def test_web_ui_expired_session_redirects_with_accessible_login_feedback(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/app/prefs",
        lambda route: route.fulfill(
            status=403,
            content_type="text/plain",
            body="Unauthorized",
        ),
    )

    page.evaluate("apiFetch('/api/v2/app/prefs')")
    page.wait_for_url(f"{web_ui_server}/login.html")
    page.wait_for_function(
        "() => document.getElementById('errorMsg').textContent === 'Sessão expirada. Entre novamente.'"
    )

    assert page.locator("#errorMsg").is_visible()
    assert page.evaluate("document.activeElement && document.activeElement.id === 'errorMsg'")


def test_web_ui_non_auth_403_does_not_fake_session_expiry(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/app/prefs",
        lambda route: route.fulfill(
            status=403,
            content_type="text/plain",
            body="CSRF token missing or invalid.",
        ),
    )

    status = page.evaluate(
        """async () => {
            const response = await apiFetch('/api/v2/app/prefs');
            return response.status;
        }"""
    )

    assert status == 403
    assert page.url == f"{web_ui_server}/"
    assert page.evaluate(
        "sessionStorage.getItem('serrebitorrent-session-expired')"
    ) is None


def test_web_ui_grid_shortcuts_do_not_capture_toolbar_keys(page, web_ui_server):
    _login(page, web_ui_server)

    settings = page.locator('[data-bs-target="#settingsModal"]')
    settings.focus()
    assert page.evaluate(
        "document.activeElement === document.querySelector('[data-bs-target=\"#settingsModal\"]')"
    )

    page.keyboard.press("ArrowDown")
    assert page.evaluate(
        "document.activeElement === document.querySelector('[data-bs-target=\"#settingsModal\"]')"
    )

    page.keyboard.press("Control+A")
    assert page.locator('tr[data-hash][aria-selected="true"]').count() == 0


def test_web_ui_grid_shortcuts_do_not_capture_actions_button_keys(page, web_ui_server):
    _login(page, web_ui_server)

    actions = page.locator("#torrentActionsBtn")
    actions.focus()
    assert page.evaluate("document.activeElement && document.activeElement.id === 'torrentActionsBtn'")

    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement && document.activeElement.id === 'torrentActionsBtn'")

    page.keyboard.press("Control+A")
    assert page.locator('tr[data-hash][aria-selected="true"]').count() == 0


def test_web_ui_arrow_from_focused_grid_enters_first_row(page, web_ui_server):
    # The grid itself takes focus when the list empties; arrows must still reach the rows.
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")
    page.evaluate("() => { const t = document.getElementById('torrentTable'); t.tabIndex = 0; t.focus(); }")

    page.keyboard.press("ArrowDown")

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]') && document.activeElement === document.querySelector('tr[data-hash]')"
    )


def test_web_ui_sidebar_arrows_move_focus_without_activating_filter(page, web_ui_server):
    _login(page, web_ui_server)

    all_filter = page.locator('#filterList .sidebar-link[data-filter="All"]')
    downloading_filter = page.locator('#filterList .sidebar-link[data-filter="Downloading"]')

    all_filter.focus()
    assert all_filter.get_attribute("aria-selected") == "true"

    page.keyboard.press("ArrowDown")

    assert page.evaluate(
        "document.activeElement && document.activeElement.dataset.filter === 'Downloading'"
    )
    assert all_filter.get_attribute("aria-selected") == "true"
    assert downloading_filter.get_attribute("aria-selected") == "false"

    page.keyboard.press("Enter")
    page.wait_for_function(
        "() => document.querySelector('#filterList .sidebar-link[data-filter=\"Downloading\"]')?.getAttribute('aria-selected') === 'true'"
    )
    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )


def test_web_ui_tracker_refresh_preserves_roving_focus(page, web_ui_server):
    _login(page, web_ui_server)

    page.wait_for_selector('#trackerList .sidebar-link[data-filter="tracker.two"]')
    tracker = page.locator('#trackerList .sidebar-link[data-filter="tracker.two"]')
    tracker.focus()
    assert tracker.get_attribute("aria-selected") == "false"

    page.evaluate(
        """() => updateSidebarStats(
            {all: 2},
            {'tracker.one': 2, 'tracker.two': 1}
        )"""
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.dataset.filter === 'tracker.two'"
    )
    refreshed = page.locator('#trackerList .sidebar-link[data-filter="tracker.two"]')
    assert refreshed.get_attribute("tabindex") == "0"
    assert refreshed.get_attribute("aria-selected") == "false"


def test_web_ui_profile_refresh_preserves_roving_focus(page, web_ui_server):
    _login(page, web_ui_server)

    calls = {"n": 0}

    def profiles(route):
        # The second response differs, so the list is really rebuilt.
        calls["n"] += 1
        body = ('{"profiles":{'
                 '"local":{"name":"Local","type":"local","url":"C:\\\\Downloads","user":"","password":""},'
                 '"remote":{"name":"Remote","type":"qbittorrent","url":"https://example.invalid","user":"","password":""}'
                 '},"current_id":"local"}')
        route.fulfill(status=200, content_type="application/json",
                      body=body.replace('"Local"', '"Local %d"' % calls["n"]))

    page.route("**/api/v2/profiles", profiles)

    page.evaluate("fetchProfiles()")
    page.wait_for_selector('#profileList .sidebar-link[data-profile-id="remote"]')
    remote = page.locator('#profileList .sidebar-link[data-profile-id="remote"]')
    remote.focus()
    assert remote.get_attribute("aria-selected") == "false"

    page.evaluate("fetchProfiles()")

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.dataset.profileId === 'remote'"
    )
    refreshed = page.locator('#profileList .sidebar-link[data-profile-id="remote"]')
    assert refreshed.get_attribute("tabindex") == "0"
    assert refreshed.get_attribute("aria-selected") == "false"


def test_web_ui_unchanged_refresh_keeps_the_same_focused_tracker_node(page, web_ui_server):
    # Re-focusing a rebuilt node makes screen readers announce it again every refresh.
    _login(page, web_ui_server)
    page.wait_for_function("document.activeElement && document.activeElement.matches('tr[data-hash]')")
    page.evaluate(
        """() => {
            const link = document.querySelector('#trackerList .sidebar-link');
            link.focus();
            window.__focusedTrackerNode = link;
        }"""
    )

    page.evaluate("refreshData(true)")
    page.wait_for_timeout(300)
    page.evaluate("refreshData(true)")
    page.wait_for_timeout(300)

    assert page.evaluate("document.activeElement === window.__focusedTrackerNode")
    assert page.evaluate("window.__focusedTrackerNode.isConnected")


def test_web_ui_successful_torrent_action_announces_completion(page, web_ui_server):
    _login(page, web_ui_server)

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")
    # Let the selection announcement finish so it is not queued with the next one.
    page.wait_for_function(
        "() => document.getElementById('aria-announcer').textContent.startsWith('Selecionado')"
    )

    page.route(
        "**/api/v2/torrents/pause",
        lambda route: route.fulfill(
            status=200,
            content_type="text/plain",
            body="Ok.",
        ),
    )

    # The title is translated on the pt-BR test page, so select by action.
    page.locator(".btn-group button[onclick*='pause']").click()

    page.wait_for_function(
        "() => document.getElementById('aria-announcer').textContent === 'Pausar concluído'"
    )


def test_web_ui_sidebar_roving_focus_stays_within_current_listbox(page, web_ui_server):
    _login(page, web_ui_server)

    rss = page.locator('#filterList .sidebar-link[data-filter="RSS"]')
    all_filter = page.locator('#filterList .sidebar-link[data-filter="All"]')
    active_profile = page.locator('#profileList .sidebar-link[aria-selected="true"]')

    rss.focus()
    assert page.evaluate(
        "document.activeElement && document.activeElement.dataset.filter === 'RSS'"
    )

    page.keyboard.press("ArrowDown")

    assert page.evaluate(
        "document.activeElement && document.activeElement.dataset.filter === 'All'"
    )
    assert all_filter.get_attribute("tabindex") == "0"
    assert active_profile.get_attribute("tabindex") == "0"


def test_web_ui_every_sidebar_listbox_keeps_a_tab_stop(page, web_ui_server):
    # Arrows no longer cross listboxes, so each one must stay reachable with Tab.
    _login(page, web_ui_server)
    page.wait_for_selector("#trackerList .sidebar-link")
    page.wait_for_selector("#profileList .sidebar-link")

    def tab_stops():
        return page.evaluate(
            """() => ['profileList', 'filterList', 'trackerList'].map(id =>
                document.querySelectorAll('#' + id + ' .sidebar-link[tabindex="0"]').length)"""
        )

    assert tab_stops() == [1, 1, 1]

    page.evaluate("setFilter('tracker.one')")
    assert tab_stops() == [1, 1, 1]
    assert page.locator('#filterList .sidebar-link[tabindex="0"]').get_attribute("data-filter") == "All"

    page.evaluate("setFilter('Seeding')")
    assert tab_stops() == [1, 1, 1]


def test_web_ui_serializes_overlapping_refreshes(page, web_ui_server):
    _login(page, web_ui_server)

    page.evaluate(
        """() => {
            clearInterval(refreshIntervalId);
            window.__refreshCalls = 0;
            window.__releaseFirstRefresh = null;
            const originalFetch = window.fetch.bind(window);
            window.fetch = (...args) => {
                const url = String(args[0]);
                if (url === '/api/v2/torrents/all') {
                    window.__refreshCalls += 1;
                    if (window.__refreshCalls === 1) {
                        return new Promise((resolve, reject) => {
                            window.__releaseFirstRefresh = () => {
                                originalFetch(...args).then(resolve, reject);
                            };
                        });
                    }
                }
                return originalFetch(...args);
            };
        }"""
    )

    page.evaluate("void refreshData(true)")
    page.wait_for_function("() => window.__refreshCalls === 1")

    page.evaluate("void refreshData()")
    page.evaluate("void refreshData(true)")
    assert page.evaluate("window.__refreshCalls") == 1

    page.evaluate("window.__releaseFirstRefresh()")
    page.wait_for_function("() => window.__refreshCalls === 2")
    page.wait_for_function("() => !refreshInFlight && !forcedRefreshPending")


def test_web_ui_files_tab_loads_selected_torrent_files(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/files?hash=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='['
                 '{"index":0,"name":"folder/example.txt","size":2048,"progress":0.5,"priority":1},'
                 '{"index":1,"name":"movie.mkv","size":1048576,"progress":1.0,"priority":2}'
                 ']',
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('files-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    page.wait_for_selector('#details-files table[aria-label="Arquivos torrent"]')
    rows = page.locator("#details-files tbody tr")
    assert rows.count() == 2
    assert rows.nth(0).locator("td").nth(0).inner_text() == "folder/example.txt"
    assert rows.nth(0).locator("td").nth(1).inner_text() == "2 KB"
    assert rows.nth(0).locator("td").nth(2).inner_text() == "50%"
    assert rows.nth(1).locator("td").nth(3).inner_text() == "Alta"
    headers = page.locator("#details-files thead th")
    assert headers.all_inner_texts() == ["Nome", "Tamanho", "Progresso", "Prioridade"]
    assert page.locator("#details-files").get_attribute("aria-labelledby") == "files-tab"


def test_web_ui_files_tab_reports_load_errors(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/files?hash=*",
        lambda route: route.fulfill(
            status=500,
            content_type="text/plain",
            body="Failed",
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('files-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    error = page.locator("#details-files [role=alert]")
    error.wait_for()
    assert error.inner_text() == "Falha ao carregar os arquivos do torrent."


def test_web_ui_files_tab_ignores_stale_response_after_selection_changes(page, web_ui_server):
    _login(page, web_ui_server)

    page.evaluate(
        """() => {
            window.__filesCallCount = 0;
            window.__releaseStaleFiles = null;
            const originalFetch = window.fetch.bind(window);
            window.fetch = (...args) => {
                const url = String(args[0]);
                if (!url.startsWith('/api/v2/torrents/files?hash=')) {
                    return originalFetch(...args);
                }
                window.__filesCallCount += 1;
                if (window.__filesCallCount === 1) {
                    return new Promise((resolve) => {
                        window.__releaseStaleFiles = () => resolve(new Response(
                            JSON.stringify([
                                {index: 0, name: 'stale.txt', size: 1, progress: 1, priority: 1}
                            ]),
                            {status: 200, headers: {'Content-Type': 'application/json'}}
                        ));
                    });
                }
                return Promise.resolve(new Response(
                    JSON.stringify([
                        {index: 0, name: 'current.txt', size: 2, progress: 1, priority: 1}
                    ]),
                    {status: 200, headers: {'Content-Type': 'application/json'}}
                ));
            };
        }"""
    )

    page.wait_for_function("() => torrentsMap.size >= 2")
    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[0]);
            const tab = document.getElementById('files-tab');
            tab.classList.add('active');
            void updateFilesDetails();
        }"""
    )
    page.wait_for_function("() => window.__filesCallCount === 1")

    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[1]);
            void updateFilesDetails();
        }"""
    )

    page.wait_for_function(
        "() => document.querySelector('#details-files tbody td')?.textContent === 'current.txt'"
    )
    page.evaluate("window.__releaseStaleFiles()")
    page.wait_for_timeout(100)

    assert page.locator("#details-files tbody td").first.inner_text() == "current.txt"
    assert page.locator("#details-files").inner_text().find("stale.txt") == -1


def test_web_ui_peers_tab_loads_selected_torrent_peers(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/peers?hash=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='['
                 '{"address":"203.0.113.10:51413","client":"ExampleClient","progress":0.75,"down_rate":2048,"up_rate":1024}'
                 ']',
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('peers-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    page.wait_for_selector('#details-peers table[aria-label="Peers do torrent"]')
    row = page.locator("#details-peers tbody tr").first
    cells = row.locator("td")
    assert cells.nth(0).inner_text() == "203.0.113.10:51413"
    assert cells.nth(1).inner_text() == "ExampleClient"
    assert cells.nth(2).inner_text() == "75%"
    assert cells.nth(3).inner_text() == "2 KB/s"
    assert cells.nth(4).inner_text() == "1 KB/s"
    headers = page.locator("#details-peers thead th")
    assert headers.all_inner_texts() == [
        "Endereço",
        "Cliente",
        "Progresso",
        "Velocidade de download",
        "Velocidade de upload",
    ]


def test_web_ui_peers_tab_reports_load_errors(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/peers?hash=*",
        lambda route: route.fulfill(
            status=500,
            content_type="text/plain",
            body="Failed",
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('peers-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    error = page.locator("#details-peers [role=alert]")
    error.wait_for()
    assert error.inner_text() == "Falha ao carregar os peers do torrent."


def test_web_ui_peers_tab_ignores_stale_response_after_selection_changes(page, web_ui_server):
    _login(page, web_ui_server)

    page.evaluate(
        """() => {
            window.__peerCalls = 0;
            window.__releaseStalePeers = null;
            const originalFetch = window.fetch.bind(window);
            window.fetch = (...args) => {
                const url = String(args[0]);
                if (!url.startsWith('/api/v2/torrents/peers?hash=')) {
                    return originalFetch(...args);
                }
                window.__peerCalls += 1;
                if (window.__peerCalls === 1) {
                    return new Promise((resolve) => {
                        window.__releaseStalePeers = () => resolve(new Response(
                            JSON.stringify([
                                {address:'stale:1',client:'Old',progress:1,down_rate:0,up_rate:0}
                            ]),
                            {status:200,headers:{'Content-Type':'application/json'}}
                        ));
                    });
                }
                return Promise.resolve(new Response(
                    JSON.stringify([
                        {address:'current:2',client:'Current',progress:1,down_rate:0,up_rate:0}
                    ]),
                    {status:200,headers:{'Content-Type':'application/json'}}
                ));
            };
        }"""
    )

    page.wait_for_function("() => torrentsMap.size >= 2")
    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[0]);
            const tab = document.getElementById('peers-tab');
            tab.classList.add('active');
            void updatePeersDetails();
        }"""
    )
    page.wait_for_function("() => window.__peerCalls === 1")

    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[1]);
            void updatePeersDetails();
        }"""
    )

    page.wait_for_function(
        "() => document.querySelector('#details-peers tbody td')?.textContent === 'current:2'"
    )
    page.evaluate("window.__releaseStalePeers()")
    page.wait_for_timeout(100)

    assert page.locator("#details-peers tbody td").first.inner_text() == "current:2"
    assert "stale:1" not in page.locator("#details-peers").inner_text()


def test_web_ui_trackers_tab_loads_selected_torrent_trackers(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/trackers?hash=*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='['
                 '{"url":"https://tracker.example/announce","status":"Working","peers":42,"message":"OK"}'
                 ']',
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('trackers-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    page.wait_for_selector('#details-trackers table[aria-label="Trackers do torrent"]')
    row = page.locator("#details-trackers tbody tr").first
    cells = row.locator("td")
    assert cells.nth(0).inner_text() == "https://tracker.example/announce"
    assert cells.nth(1).inner_text() == "Working"
    assert cells.nth(2).inner_text() == "42"
    assert cells.nth(3).inner_text() == "OK"
    headers = page.locator("#details-trackers thead th")
    assert headers.all_inner_texts() == ["URL do tracker", "Status", "Peers", "Mensagem"]


def test_web_ui_trackers_tab_reports_load_errors(page, web_ui_server):
    _login(page, web_ui_server)

    page.route(
        "**/api/v2/torrents/trackers?hash=*",
        lambda route: route.fulfill(
            status=500,
            content_type="text/plain",
            body="Failed",
        ),
    )

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.matches('tr[data-hash]')"
    )
    page.keyboard.press("Space")

    page.evaluate(
        """() => {
            const tab = document.getElementById('trackers-tab');
            tab.classList.add('active');
            tab.dispatchEvent(new Event('shown.bs.tab'));
        }"""
    )

    error = page.locator("#details-trackers [role=alert]")
    error.wait_for()
    assert error.inner_text() == "Falha ao carregar os trackers do torrent."


def test_web_ui_trackers_tab_ignores_stale_response_after_selection_changes(page, web_ui_server):
    _login(page, web_ui_server)

    page.evaluate(
        """() => {
            window.__trackerCalls = 0;
            window.__releaseStaleTrackers = null;
            const originalFetch = window.fetch.bind(window);
            window.fetch = (...args) => {
                const url = String(args[0]);
                if (!url.startsWith('/api/v2/torrents/trackers?hash=')) {
                    return originalFetch(...args);
                }
                window.__trackerCalls += 1;
                if (window.__trackerCalls === 1) {
                    return new Promise((resolve) => {
                        window.__releaseStaleTrackers = () => resolve(new Response(
                            JSON.stringify([
                                {url:'https://stale.invalid/announce',status:'Old',peers:1,message:''}
                            ]),
                            {status:200,headers:{'Content-Type':'application/json'}}
                        ));
                    });
                }
                return Promise.resolve(new Response(
                    JSON.stringify([
                        {url:'https://current.example/announce',status:'Working',peers:2,message:''}
                    ]),
                    {status:200,headers:{'Content-Type':'application/json'}}
                ));
            };
        }"""
    )

    page.wait_for_function("() => torrentsMap.size >= 2")
    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[0]);
            const tab = document.getElementById('trackers-tab');
            tab.classList.add('active');
            void updateTrackersDetails();
        }"""
    )
    page.wait_for_function("() => window.__trackerCalls === 1")

    page.evaluate(
        """() => {
            const hashes = Array.from(torrentsMap.keys());
            selectedHashes.clear();
            selectedHashes.add(hashes[1]);
            void updateTrackersDetails();
        }"""
    )

    page.wait_for_function(
        "() => document.querySelector('#details-trackers tbody td')?.textContent === 'https://current.example/announce'"
    )
    page.evaluate("window.__releaseStaleTrackers()")
    page.wait_for_timeout(100)

    assert page.locator("#details-trackers tbody td").first.inner_text() == "https://current.example/announce"
    assert "stale.invalid" not in page.locator("#details-trackers").inner_text()


def test_web_ui_refresh_error_preserves_current_torrent_list(page, web_ui_server):
    _login(page, web_ui_server)
    page.wait_for_function("document.querySelectorAll('tr[data-hash]').length >= 2")

    before_hashes = page.evaluate(
        "() => Array.from(document.querySelectorAll('tr[data-hash]')).map(row => row.dataset.hash)"
    )
    focused = page.locator('tr[data-hash="' + before_hashes[0] + '"]')
    focused.focus()
    assert page.evaluate("document.activeElement.dataset.hash") == before_hashes[0]

    page.route(
        "**/api/v2/torrents/all",
        lambda route: route.fulfill(
            status=503,
            content_type="text/plain",
            body="No torrent client is connected.",
        ),
    )

    page.evaluate("refreshData(true)")
    page.wait_for_timeout(150)

    after_hashes = page.evaluate(
        "() => Array.from(document.querySelectorAll('tr[data-hash]')).map(row => row.dataset.hash)"
    )
    assert after_hashes == before_hashes
    assert page.evaluate("document.activeElement.dataset.hash") == before_hashes[0]
    assert "torrent removido" not in page.locator("#aria-announcer").inner_text()


def test_web_ui_app_settings_load_error_preserves_form_state(page, web_ui_server):
    _login(page, web_ui_server)

    refresh_input = page.locator('#settingsForm input[name="refresh_rate"]')
    refresh_input.fill("4321")

    page.route(
        "**/api/v2/app/prefs",
        lambda route: route.fulfill(
            status=503,
            content_type="text/plain",
            body="Application context is unavailable.",
        ),
    )

    page.evaluate("loadAppSettings()")
    page.wait_for_timeout(150)

    assert refresh_input.input_value() == "4321"
