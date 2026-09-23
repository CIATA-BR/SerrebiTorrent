
import pytest
import sys
import os
import json
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import web_server

@pytest.fixture
def client():
    web_server.app.config['TESTING'] = True
    web_server.app.config['SECRET_KEY'] = 'test'
    with web_server.app.test_client() as client:
        yield client

@pytest.fixture
def auth_failures():
    """Keep throttle state out of the shared module-level cache."""
    with web_server._auth_lock:
        original = dict(web_server._auth_failures)
        web_server._auth_failures.clear()
    yield web_server._auth_failures
    with web_server._auth_lock:
        web_server._auth_failures.clear()
        web_server._auth_failures.update(original)

@pytest.fixture
def auth_client(client):
    # Perform login
    client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
    return client


def csrf_headers(client):
    with client.session_transaction() as session:
        return {'X-CSRF-Token': session['csrf_token']}

def test_login(client):
    rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
    assert b"Ok." in rv.data
    assert rv.status_code == 200
    
    rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'wrong'})
    assert rv.status_code == 403


def test_session_invalidates_after_credentials_change(client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG.update({'username': 'admin', 'password': 'password'})
        rv = client.post('/api/v2/auth/login', data={'username': 'admin', 'password': 'password'})
        assert rv.status_code == 200

        web_server.WEB_CONFIG.update({'password': 'new-secret'})
        rv = client.get('/api/v2/auth/csrf')

        assert rv.status_code == 403
        with client.session_transaction() as session:
            assert 'logged_in' not in session
            assert 'auth_fingerprint' not in session
    finally:
        web_server.WEB_CONFIG.update(original)


def test_web_ui_does_not_start_with_default_password(monkeypatch):
    original = web_server.WEB_CONFIG.copy()
    original_thread = web_server.server_thread
    thread_ctor = MagicMock()
    try:
        web_server.WEB_CONFIG.update({'password': 'password', 'enabled': True})
        web_server.server_thread = None
        monkeypatch.setattr(web_server.threading, 'Thread', thread_ctor)

        web_server.start_web_ui()

        thread_ctor.assert_not_called()
        assert web_server.server_thread is None
    finally:
        web_server.WEB_CONFIG.update(original)
        web_server.server_thread = original_thread

def test_profiles_endpoint(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {'p1': {'name': 'Profile 1'}}
    mock_app.current_profile_id = 'p1'
    
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/profiles')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'p1' in data['profiles']
    assert data['current_id'] == 'p1'

def test_torrents_info_endpoint(auth_client):
    mock_app = MagicMock()
    torrents_list = [
        {'hash': 'abc', 'name': 'Test', 'size': 1000, 'done': 500, 'state': 1}
    ]
    mock_app.all_torrents = torrents_list
    mock_app.get_all_torrents_safe.return_value = torrents_list
    
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/torrents/info')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert len(data['torrents']) == 1
    assert data['stats']['All'] == 1
    assert data['stats']['Downloading'] == 1

def test_torrents_add_endpoint(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client
    
    rv = auth_client.post(
        '/api/v2/torrents/add',
        data={'urls': 'magnet:?foo', 'savepath': '/tmp'},
        headers=csrf_headers(auth_client),
    )
    assert rv.status_code == 200
    mock_client.add_torrent_url.assert_called_with('magnet:?foo', sp='/tmp')

def test_torrents_delete_endpoint_uses_bulk_remove(auth_client):
    mock_client = MagicMock()
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': 'h1|h2', 'deleteFiles': 'true'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 200
    mock_client.remove_torrents.assert_called_once_with(['h1', 'h2'], True)

def test_torrents_delete_endpoint_reports_remove_errors(auth_client):
    mock_client = MagicMock()
    mock_client.remove_torrents.side_effect = RuntimeError("still present")
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': 'h1', 'deleteFiles': 'false'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to remove torrent(s)." in rv.data
    assert b"still present" not in rv.data

def test_rss_feeds_endpoint(auth_client):
    mock_app = MagicMock()
    mock_app.rss_panel.manager.feeds = {'http://feed': {'alias': 'Test'}}
    web_server.WEB_CONFIG['app'] = mock_app
    
    rv = auth_client.get('/api/v2/rss/feeds')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'http://feed' in data


def test_translation_catalogs_are_public_before_login(client):
    response = client.get('/locales/index.json')
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload.get('languages'), list)


def test_non_locale_static_assets_remain_protected_before_login(client):
    response = client.get('/app.js')
    assert response.status_code in (301, 302)
    assert response.headers['Location'].endswith('/login.html')


def _fail_login(client, attempts):
    for _ in range(attempts):
        assert client.post(
            '/api/v2/auth/login',
            data={'username': 'admin', 'password': 'wrong'},
        ).status_code == 403


def test_lockout_reports_retry_after_and_not_invalid_credentials(client, auth_failures):
    _fail_login(client, web_server._AUTH_FAIL_LIMIT)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 429
    assert b"Too many failed attempts. Try again later." in response.data
    retry_after = int(response.headers['Retry-After'])
    assert 0 < retry_after <= web_server._AUTH_LOCK_SECONDS


def test_successful_login_clears_throttle_state(client, auth_failures):
    _fail_login(client, web_server._AUTH_FAIL_LIMIT - 1)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 200
    assert web_server._auth_failures == {}


def test_expired_throttle_record_is_pruned_on_read(client, auth_failures):
    stale = time.time() - web_server._AUTH_LOCK_SECONDS - 1
    with web_server._auth_lock:
        web_server._auth_failures['10.0.0.1'] = (web_server._AUTH_FAIL_LIMIT, stale)

    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.status_code == 200
    assert '10.0.0.1' not in web_server._auth_failures


def test_throttle_cache_is_bounded_and_evicts_oldest(monkeypatch, auth_failures):
    monkeypatch.setattr(web_server, '_AUTH_MAX_TRACKED_IPS', 4)
    now = time.time()
    with web_server._auth_lock:
        for index in range(4):
            web_server._auth_failures[f'10.0.0.{index}'] = (1, now - 10 + index)

    web_server._record_auth_failure('10.0.0.9')

    assert len(web_server._auth_failures) == 4
    assert '10.0.0.0' not in web_server._auth_failures
    assert '10.0.0.9' in web_server._auth_failures


def test_baseline_security_headers_are_sent(client):
    response = client.get('/login.html')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=()'
    assert response.headers['Cache-Control'] == 'no-store'


def test_api_responses_are_not_cached(client, auth_failures):
    response = client.post(
        '/api/v2/auth/login',
        data={'username': 'admin', 'password': 'password'},
    )

    assert response.headers['Cache-Control'] == 'no-store'


def test_torrent_action_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.post(
            '/api/v2/torrents/pause',
            data={'hashes': 'h1'},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_recheck_reports_partial_failures(auth_client):
    mock_client = MagicMock()
    mock_client.recheck_torrent.side_effect = [None, RuntimeError("boom")]
    web_server.WEB_CONFIG['client'] = mock_client

    rv = auth_client.post(
        '/api/v2/torrents/recheck',
        data={'hashes': 'h1|h2'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 500
    assert b"Failed to recheck one or more torrents." in rv.data
    assert mock_client.recheck_torrent.call_count == 2


def test_openfolder_reports_missing_download_path(auth_client):
    mock_client = MagicMock()
    mock_client.get_torrent_save_path.return_value = ''
    web_server.WEB_CONFIG['client'] = mock_client
    web_server.WEB_CONFIG['app'] = MagicMock()

    rv = auth_client.post(
        '/api/v2/torrents/openfolder',
        data={'hashes': 'h1'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"Download folder is unavailable." in rv.data


def test_torrents_delete_requires_connected_client(auth_client):
    original = web_server.WEB_CONFIG.copy()
    try:
        web_server.WEB_CONFIG['client'] = None

        rv = auth_client.post(
            '/api/v2/torrents/delete',
            data={'hashes': 'h1', 'deleteFiles': 'false'},
            headers=csrf_headers(auth_client),
        )

        assert rv.status_code == 503
        assert b"No torrent client is connected." in rv.data
    finally:
        web_server.WEB_CONFIG.update(original)


def test_torrents_delete_requires_selection(auth_client):
    web_server.WEB_CONFIG['client'] = MagicMock()

    rv = auth_client.post(
        '/api/v2/torrents/delete',
        data={'hashes': '', 'deleteFiles': 'false'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"No torrents selected." in rv.data


def test_profile_switch_rejects_unknown_profile(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {
        'local': {'name': 'Local', 'type': 'local'}
    }
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/switch',
        data={'id': 'missing'},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 404
    assert b"Profile not found." in rv.data
    mock_app.connect_profile.assert_not_called()


def test_profile_switch_requires_profile_id(auth_client):
    mock_app = MagicMock()
    mock_app.config_manager.get_profiles.return_value = {
        'local': {'name': 'Local', 'type': 'local'}
    }
    web_server.WEB_CONFIG['app'] = mock_app

    rv = auth_client.post(
        '/api/v2/profiles/switch',
        data={'id': ''},
        headers=csrf_headers(auth_client),
    )

    assert rv.status_code == 400
    assert b"Profile id is required." in rv.data
    mock_app.connect_profile.assert_not_called()
