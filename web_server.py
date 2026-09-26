import os
import threading
import sys
import hmac
import hashlib
import ipaddress
import socket
import time
import tempfile
from flask import Flask, request, jsonify, send_from_directory, session, redirect
from werkzeug.utils import secure_filename
from urllib.parse import urlparse

from clients import download_torrent_url

def get_bundle_dir():
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

static_dir = os.path.join(get_bundle_dir(), 'web_static')
app = Flask(__name__, static_folder=static_dir)

# v1.16.8 accidentally published this shared session key.
_COMPROMISED_SECRET_KEY_SHA256 = "235913427a91431f02c54460026b545ee2e1ad7e1fac34591031eb38a4a45687"


def _load_or_create_secret_key():
    """Persist the Flask secret key so sessions survive restarts.

    Regenerating os.urandom() every launch silently invalidates all sessions on
    restart. Store the key under the app data dir (best-effort)."""
    try:
        from app_paths import get_data_dir
        key_path = os.path.join(get_data_dir(), 'web_secret.key')
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                data = f.read()
            if len(data) >= 16 and hashlib.sha256(data).hexdigest() != _COMPROMISED_SECRET_KEY_SHA256:
                return data
        key = os.urandom(32)
        tmp = f"{key_path}.{os.getpid()}.tmp"
        try:
            with open(tmp, 'wb') as f:
                f.write(key)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, key_path)
            if os.name != "nt":
                try:
                    os.chmod(key_path, 0o600)
                except OSError:
                    pass
        except OSError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        return key
    except Exception:
        return os.urandom(32)


app.secret_key = _load_or_create_secret_key()
# Harden the session cookie and cap request bodies.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',  # blocks cross-site POST -> mitigates CSRF
    PERMANENT_SESSION_LIFETIME=43200,  # 12h idle session lifetime
    MAX_CONTENT_LENGTH=64 * 1024 * 1024,  # 64 MB cap on request bodies
)

# --- Login brute-force throttling (per client IP) ---
_AUTH_FAIL_LIMIT = 8
_AUTH_LOCK_SECONDS = 300
_AUTH_MAX_TRACKED_IPS = 1024
_auth_lock = threading.Lock()
_auth_failures = {}  # ip -> (fail_count, window_start_ts)


def _client_ip():
    return request.remote_addr or 'unknown'


def _prune_auth_failures(now):
    """Drop records past their lock window. Caller must hold _auth_lock."""
    expired = [
        ip for ip, (_count, first) in _auth_failures.items()
        if now - first >= _AUTH_LOCK_SECONDS
    ]
    for ip in expired:
        _auth_failures.pop(ip, None)


def _evict_oldest_auth_failures():
    """Cap tracked addresses so rotating sources cannot grow this forever.

    Caller must hold _auth_lock. The newest records survive, so an attacker
    cannot evict the lock held against their own current address.
    """
    overflow = len(_auth_failures) - _AUTH_MAX_TRACKED_IPS
    if overflow <= 0:
        return
    oldest = sorted(_auth_failures.items(), key=lambda item: item[1][1])[:overflow]
    for ip, _record in oldest:
        _auth_failures.pop(ip, None)


def _auth_retry_after(ip):
    """Seconds this address must wait, or 0 when it is not locked out."""
    with _auth_lock:
        now = time.time()
        _prune_auth_failures(now)
        record = _auth_failures.get(ip)
        if not record or record[0] < _AUTH_FAIL_LIMIT:
            return 0
        return max(1, int(record[1] + _AUTH_LOCK_SECONDS - now))


def _record_auth_failure(ip):
    with _auth_lock:
        now = time.time()
        _prune_auth_failures(now)
        count, first = _auth_failures.get(ip, (0, now))
        _auth_failures[ip] = (count + 1, first)
        _evict_oldest_auth_failures()


def _clear_auth_failures(ip):
    with _auth_lock:
        _auth_failures.pop(ip, None)


def _weak_web_credentials():
    """True when the Web UI password is still the default/empty (unsafe to expose)."""
    pw = WEB_CONFIG.get('password') or ''
    return pw == '' or pw == 'password'


def _credentials_fingerprint():
    key = app.secret_key
    if not isinstance(key, bytes):
        key = str(key).encode('utf-8')
    user = str(WEB_CONFIG.get('username') or '')
    pw = str(WEB_CONFIG.get('password') or '')
    return hmac.new(key, f"{user}\0{pw}".encode('utf-8'), hashlib.sha256).hexdigest()


def _clear_web_session():
    session.pop('logged_in', None)
    session.pop('csrf_token', None)
    session.pop('auth_fingerprint', None)


def _is_authenticated_session():
    if not session.get('logged_in'):
        return False
    actual = session.get('auth_fingerprint')
    expected = _credentials_fingerprint()
    if not actual or not hmac.compare_digest(str(actual), expected):
        _clear_web_session()
        return False
    return True


def _is_blocked_add_ip(ip):
    mapped = getattr(ip, 'ipv4_mapped', None)
    if mapped:
        ip = mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    )


def _resolve_add_host(host, port):
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("host could not be resolved") from exc
    addresses = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0]))
        except (IndexError, ValueError):
            continue
    if not addresses:
        raise ValueError("host did not resolve to an IP address")
    return tuple(addresses)


def _validate_public_add_http_url(u):
    parsed = urlparse(u)
    if parsed.scheme.lower() not in ('http', 'https'):
        raise ValueError("unsupported URL scheme")
    host = parsed.hostname
    if not host:
        raise ValueError("URL host is required")
    host_check = host.rstrip('.').lower()
    if host_check == 'localhost' or host_check.endswith('.localhost'):
        raise ValueError("localhost URLs are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid URL port") from exc
    if port is None:
        port = 443 if parsed.scheme.lower() == 'https' else 80

    try:
        addresses = (ipaddress.ip_address(host_check),)
    except ValueError:
        addresses = _resolve_add_host(host, port)
    if any(_is_blocked_add_ip(ip) for ip in addresses):
        raise ValueError("private or local network URLs are not allowed")
    return parsed


def _validate_add_url(u):
    parsed = urlparse(u)
    scheme = parsed.scheme.lower()
    if scheme == 'magnet':
        return
    if scheme not in ('http', 'https'):
        raise ValueError("unsupported URL scheme")
    _validate_public_add_http_url(u)


def _allowed_add_url(u):
    """Allow only network/magnet torrent sources; block file://, UNC, SSRF schemes."""
    try:
        _validate_add_url(u)
        return True
    except ValueError:
        return False


def _csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = os.urandom(16).hex()
        session['csrf_token'] = token
    return token


@app.before_request
def protect_mutating_requests():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    if not request.path.startswith('/api/'):
        return None
    if request.endpoint == 'api_login':
        return None
    if not _is_authenticated_session():
        return None
    expected = session.get('csrf_token')
    supplied = request.headers.get('X-CSRF-Token') or request.form.get('_csrf')
    if not expected or not supplied or not hmac.compare_digest(str(supplied), str(expected)):
        return "CSRF token missing or invalid.", 403
    return None


@app.after_request
def add_baseline_security_headers(response):
    # Defense in depth for the embedded UI. No CSP here: the shell relies on
    # inline scripts from the CDN-hosted Bootstrap bundle.
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if request.path.startswith('/api/') or request.path == '/login.html':
        response.headers['Cache-Control'] = 'no-store'
    return response

# Global context to hold reference to the active torrent client and credentials
# These are updated by the MainFrame when the Web UI is enabled or settings change.
WEB_CONFIG = {
    'app': None, # Reference to MainFrame
    'client': None,
    'username': 'admin',
    'password': 'password',
    'host': '127.0.0.1',
    'port': 8080,
    'enabled': False
}

def login_required(f):
    def wrapper(*args, **kwargs):
        if not _is_authenticated_session():
            if request.path.startswith('/api/'):
                return "Unauthorized", 403
            return redirect('/login.html')
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
@login_required
def index():
    return send_from_directory(static_dir, 'index.html')

@app.route('/login.html')
def login_page():
    return send_from_directory(static_dir, 'login.html')

@app.route('/locales/<path:filename>')
def public_locale(filename):
    # Translation catalogs contain presentation strings only and must be
    # available before authentication so the login page can localize itself.
    if filename != 'index.json' and not filename.endswith('.json'):
        return "Not Found", 404
    return send_from_directory(os.path.join(static_dir, 'locales'), filename)

@app.route('/<path:filename>')
def serve_static(filename):
    # login.html is the only public page; everything else (app.js, index.html,
    # style.css) is part of the authenticated app shell.
    if filename != 'login.html' and not _is_authenticated_session():
        return redirect('/login.html')
    return send_from_directory(static_dir, filename)

@app.route('/api/v2/auth/login', methods=['POST'])
def api_login():
    ip = _client_ip()
    retry_after = _auth_retry_after(ip)
    if retry_after:
        return (
            "Too many failed attempts. Try again later.",
            429,
            {'Retry-After': str(retry_after)},
        )
    user = (request.form.get('username') or '').encode('utf-8')
    pw = (request.form.get('password') or '').encode('utf-8')
    exp_user = (WEB_CONFIG.get('username') or '').encode('utf-8')
    exp_pw = (WEB_CONFIG.get('password') or '').encode('utf-8')
    # Constant-time comparison avoids a timing side-channel on the password.
    if hmac.compare_digest(user, exp_user) and hmac.compare_digest(pw, exp_pw):
        session['logged_in'] = True
        session['csrf_token'] = os.urandom(16).hex()
        session['auth_fingerprint'] = _credentials_fingerprint()
        session.permanent = True
        _clear_auth_failures(ip)
        return "Ok."
    _record_auth_failure(ip)
    return "Fails.", 403

@app.route('/api/v2/auth/csrf')
@login_required
def api_csrf():
    return jsonify({'csrf_token': _csrf_token()})

@app.route('/api/v2/auth/logout', methods=['POST'])
@login_required
def api_logout():
    _clear_web_session()
    return "Ok."

@app.route('/api/v2/profiles')
@login_required
def get_profiles():
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503
    try:
        profiles = app_ref.config_manager.get_profiles()
    except Exception:
        return "Failed to load profiles.", 500
    safe_profiles = {
        pid: {key: value for key, value in profile.items() if key != 'password'}
        for pid, profile in profiles.items()
        if isinstance(profile, dict)
    }
    current_id = app_ref.current_profile_id
    return jsonify({
        'profiles': safe_profiles,
        'current_id': current_id
    })

@app.route('/api/v2/profiles/switch', methods=['POST'])
@login_required
def switch_profile():
    pid = request.form.get('id')
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503
    if not pid:
        return "Profile id is required.", 400

    try:
        profiles = app_ref.config_manager.get_profiles()
    except Exception:
        return "Failed to load profiles.", 500
    if pid not in profiles:
        return "Profile not found.", 404

    import wx
    wx.CallAfter(app_ref.connect_profile, pid)
    return "Profile switch started.", 202

@app.route('/api/v2/profiles/add', methods=['POST'])
@login_required
def add_profile():
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503

    name = (request.form.get('name') or '').strip()
    client_type = (request.form.get('type') or '').strip().lower()
    url = (request.form.get('url') or '').strip()
    user = request.form.get('user', '')
    pw = request.form.get('password', '')

    if not name or not client_type or not url:
        return "Missing data", 400

    supported_types = {'local', 'rtorrent', 'qbittorrent', 'transmission'}
    if client_type not in supported_types:
        return "Unsupported profile type.", 400

    try:
        app_ref.config_manager.add_profile(name, client_type, url, user, pw)
    except Exception:
        return "Failed to create profile.", 500
    return "Ok."

@app.route('/api/v2/torrents/info')
@login_required
def torrents_info():
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503

    # Use all_torrents for stats but allow the info call to return what's actually there
    # Use thread-safe copy if available
    try:
        if hasattr(app_ref, 'get_all_torrents_safe'):
            torrents = app_ref.get_all_torrents_safe()
        else:
            torrents = list(app_ref.all_torrents)
    except Exception:
        return "Failed to load torrent stats.", 500
    if not _valid_torrent_snapshot(torrents):
        return "Failed to load torrent stats.", 500

    stats = {"All": 0, "Downloading": 0, "Finished": 0, "Seeding": 0, "Stopped": 0, "Failed": 0}
    tracker_counts = {}
    
    for t in torrents:
        size = t.get('size', 0)
        done = t.get('done', 0)
        pct = (done / size * 100) if size > 0 else 0
        state = t.get('state', 0)
        msg = t.get('message', '')
        tracker_domain = t.get('tracker_domain', 'Unknown') or 'Unknown'
        
        is_seeding = (state == 1 and pct >= 100)
        is_stopped = (state == 0)
        is_error = bool(msg and "success" not in msg.lower() and "ok" not in msg.lower())
        
        stats["All"] += 1
        if state == 1 and pct < 100:
            stats["Downloading"] += 1
        if pct >= 100:
            stats["Finished"] += 1
        if is_seeding:
            stats["Seeding"] += 1
        if is_stopped:
            stats["Stopped"] += 1
        if is_error:
            stats["Failed"] += 1
        
        tracker_counts[tracker_domain] = tracker_counts.get(tracker_domain, 0) + 1

    return jsonify({
        'torrents': torrents,
        'stats': stats,
        'trackers': tracker_counts
    })

@app.route('/api/v2/torrents/all')
@login_required
def torrents_all():
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503
    try:
        torrents = client.get_torrents_full()
    except Exception as e:
        print(f"torrents/all error: {e}")
        return "Failed to fetch torrents.", 500
    if not _valid_torrent_snapshot(torrents):
        return "Failed to fetch torrents.", 500
    return jsonify(torrents)

@app.route('/api/v2/torrents/files')
@login_required
def torrents_files():
    torrent_hash = (request.args.get('hash') or '').strip()
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503
    if not torrent_hash:
        return "Torrent hash is required.", 400
    try:
        files = client.get_files(torrent_hash)
    except Exception:
        return "Failed to load torrent files.", 500
    if not isinstance(files, list):
        return "Failed to load torrent files.", 500
    return jsonify(files)


@app.route('/api/v2/torrents/peers')
@login_required
def torrents_peers():
    torrent_hash = (request.args.get('hash') or '').strip()
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503
    if not torrent_hash:
        return "Torrent hash is required.", 400
    try:
        peers = client.get_peers(torrent_hash)
    except Exception:
        return "Failed to load torrent peers.", 500
    if not isinstance(peers, list):
        return "Failed to load torrent peers.", 500
    return jsonify(peers)


@app.route('/api/v2/torrents/trackers')
@login_required
def torrents_trackers():
    torrent_hash = (request.args.get('hash') or '').strip()
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503
    if not torrent_hash:
        return "Torrent hash is required.", 400
    try:
        trackers = client.get_trackers(torrent_hash)
    except Exception:
        return "Failed to load torrent trackers.", 500
    if not isinstance(trackers, list):
        return "Failed to load torrent trackers.", 500
    return jsonify(trackers)


def _valid_torrent_snapshot(torrents):
    if not isinstance(torrents, list):
        return False
    return all(
        isinstance(torrent, dict)
        and bool(str(torrent.get('hash') or '').strip())
        for torrent in torrents
    )


def _requested_torrent_hashes():
    return [h for h in (request.form.get('hashes') or '').split('|') if h]


def _torrent_action_context():
    client = WEB_CONFIG['client']
    hashes = _requested_torrent_hashes()
    if not client:
        return None, hashes, ("No torrent client is connected.", 503)
    if not hashes:
        return client, hashes, ("No torrents selected.", 400)
    return client, hashes, None


@app.route('/api/v2/torrents/resume', methods=['POST'])
@login_required
def torrents_resume():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    failed = False
    for h in hashes:
        try:
            client.start_torrent(h)
        except Exception:
            failed = True
    if failed:
        return "Failed to resume one or more torrents.", 500
    return "Ok."


@app.route('/api/v2/torrents/pause', methods=['POST'])
@login_required
def torrents_pause():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    failed = False
    for h in hashes:
        try:
            client.stop_torrent(h)
        except Exception:
            failed = True
    if failed:
        return "Failed to pause one or more torrents.", 500
    return "Ok."


@app.route('/api/v2/torrents/recheck', methods=['POST'])
@login_required
def torrents_recheck():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    failed = False
    for h in hashes:
        try:
            client.recheck_torrent(h)
        except Exception:
            failed = True
    if failed:
        return "Failed to recheck one or more torrents.", 500
    return "Ok."


@app.route('/api/v2/torrents/reannounce', methods=['POST'])
@login_required
def torrents_reannounce():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    failed = False
    for h in hashes:
        try:
            client.reannounce_torrent(h)
        except Exception:
            failed = True
    if failed:
        return "Failed to reannounce one or more torrents.", 500
    return "Ok."


@app.route('/api/v2/torrents/openfolder', methods=['POST'])
@login_required
def torrents_openfolder():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Failed to open download folder.", 500
    try:
        path = client.get_torrent_save_path(hashes[0])
        if not path:
            return "Download folder is unavailable.", 404
        import wx
        wx.CallAfter(app_ref._open_path, path)
    except Exception:
        return "Failed to open download folder.", 500
    return "Open folder request started.", 202

@app.route('/api/v2/torrents/delete', methods=['POST'])
@login_required
def torrents_delete():
    client, hashes, error = _torrent_action_context()
    if error:
        return error
    delete_files = request.form.get('deleteFiles') == 'true'
    try:
        if hasattr(client, 'remove_torrents'):
            client.remove_torrents(hashes, delete_files)
        else:
            for h in hashes:
                if delete_files:
                    client.remove_torrent_with_data(h)
                else:
                    client.remove_torrent(h)
    except Exception:
        return "Failed to remove torrent(s).", 500
    return "Ok."

@app.route('/api/v2/torrents/add', methods=['POST'])
@login_required
def torrents_add():
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503
    
    urls = request.form.get('urls')
    save_path = request.form.get('savepath')
    errors = []
    attempted = 0
    
    if urls:
        for url in urls.split('\n'):
            u = url.strip()
            if u:
                try:
                    _validate_add_url(u)
                except ValueError as e:
                    errors.append("rejected-url")
                    print(f"Web add: rejected URL {u[:80]!r}: {e}")
                    continue
                try:
                    attempted += 1
                    if urlparse(u).scheme.lower() == 'magnet':
                        client.add_torrent_url(u, sp=save_path)
                    else:
                        content = download_torrent_url(u)
                        client.add_torrent_file(content, sp=save_path)
                except Exception as e:
                    errors.append("url-failed")
                    print(f"Web add URL error for {u[:80]!r}: {e}")

    if 'torrents' in request.files:
        files = request.files.getlist('torrents')
        for f in files:
            content = f.read()
            if content:
                try:
                    attempted += 1
                    client.add_torrent_file(content, sp=save_path)
                except Exception as e:
                    errors.append("file-failed")
                    print(f"Web add file error for {f.filename!r}: {e}")

    if attempted == 0 and not errors:
        return "No torrents provided", 400
    if errors:
        if attempted == 0 and all(error == "rejected-url" for error in errors):
            return "Invalid torrent URL.", 400
        # Detail is logged server-side; don't leak exception text to clients.
        return "Failed to add torrents.", 500
    return "Ok."

@app.route('/api/v2/rss/feeds')
@login_required
def rss_feeds():
    app_ref = WEB_CONFIG['app']
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503
    return jsonify(app_ref.rss_panel.manager.feeds)

@app.route('/api/v2/rss/add_feed', methods=['POST'])
@login_required
def rss_add_feed():
    app_ref = WEB_CONFIG['app']
    url = (request.form.get('url') or '').strip()
    alias = request.form.get('alias', '')
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503
    if not url:
        return "RSS feed URL is required.", 400
    try:
        added = app_ref.rss_panel.manager.add_feed(url, alias)
    except ValueError:
        return "RSS feed URL must use http or https and include a host.", 400
    if not added:
        if url in app_ref.rss_panel.manager.feeds:
            return "RSS feed already exists.", 409
        return "Failed to save RSS feed.", 500
    return "Ok."

@app.route('/api/v2/rss/remove_feed', methods=['POST'])
@login_required
def rss_remove_feed():
    app_ref = WEB_CONFIG['app']
    url = (request.form.get('url') or '').strip()
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503
    if not url:
        return "RSS feed URL is required.", 400
    manager = app_ref.rss_panel.manager
    existed = url in manager.feeds
    if not existed:
        return "RSS feed not found.", 404
    if not manager.remove_feed(url):
        return "Failed to remove RSS feed.", 500
    return "Ok."

@app.route('/api/v2/rss/rules')
@login_required
def rss_rules():
    app_ref = WEB_CONFIG['app']
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503
    return jsonify(app_ref.rss_panel.manager.rules)

@app.route('/api/v2/rss/set_rule', methods=['POST'])
@login_required
def rss_set_rule():
    app_ref = WEB_CONFIG['app']
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503

    index = request.form.get('index', type=int)
    pattern = (request.form.get('pattern') or '').strip()
    rule_type = (request.form.get('type') or 'accept').strip().lower()
    enabled = request.form.get('enabled') == 'true'

    if not pattern:
        return "Rule pattern is required.", 400
    if rule_type not in {'accept', 'reject'}:
        return "Unsupported rule type.", 400

    manager = app_ref.rss_panel.manager
    if index is not None and index >= 0:
        if index >= len(manager.rules):
            return "RSS rule not found.", 404
        if not manager.update_rule(
            index,
            {'pattern': pattern, 'type': rule_type, 'enabled': enabled},
        ):
            return "Failed to save RSS rule.", 500
    else:
        if not manager.add_rule(pattern, rule_type, enabled=enabled):
            return "Failed to save RSS rule.", 500
    return "Ok."

@app.route('/api/v2/rss/remove_rule', methods=['POST'])
@login_required
def rss_remove_rule():
    app_ref = WEB_CONFIG['app']
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503

    index = request.form.get('index', type=int)
    if index is None or index < 0:
        return "RSS rule index is required.", 400

    manager = app_ref.rss_panel.manager
    if index >= len(manager.rules):
        return "RSS rule not found.", 404
    if not manager.remove_rule(index):
        return "Failed to remove RSS rule.", 500
    return "Ok."

@app.route('/api/v2/rss/import_flexget', methods=['POST'])
@login_required
def rss_import_flexget():
    app_ref = WEB_CONFIG['app']
    if not app_ref or not hasattr(app_ref, 'rss_panel'):
        return "Application context is unavailable.", 503
    if 'config' not in request.files:
        return "FlexGet configuration file is required.", 400

    upload = request.files['config']
    filename = secure_filename(upload.filename or '') or 'flexget.yml'
    suffix = os.path.splitext(filename)[1] or '.yml'
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="serrebitorrent_flexget_",
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
        upload.save(temp_path)
        feeds, rules = app_ref.rss_panel.manager.import_flexget_config(temp_path)
    except ValueError:
        return "Invalid FlexGet configuration.", 400
    except Exception as e:
        print(f"Import error: {e}")
        return "Failed to import FlexGet configuration.", 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return jsonify({
        'status': 'Import complete',
        'feeds': feeds,
        'rules': rules,
    })

@app.route('/api/v2/app/prefs')
@login_required
def get_app_prefs():
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503
    try:
        prefs = app_ref.config_manager.get_preferences()
    except Exception:
        return "Failed to load settings.", 500
    web_fields = {
        'download_path',
        'rss_update_interval',
        'dl_limit',
        'ul_limit',
        'min_to_tray',
        'language',
    }
    return jsonify({key: prefs[key] for key in web_fields if key in prefs})

@app.route('/api/v2/app/prefs', methods=['POST'])
@login_required
def set_app_prefs():
    app_ref = WEB_CONFIG['app']
    if not app_ref:
        return "Application context is unavailable.", 503

    new_prefs = request.get_json(silent=True)
    if not isinstance(new_prefs, dict) or not new_prefs:
        return "Preferences object is required.", 400

    try:
        prefs = app_ref.config_manager.get_preferences()
        prefs.update(new_prefs)
        app_ref.config_manager.set_preferences(prefs)
    except Exception:
        return "Failed to save settings.", 500

    import wx
    wx.CallAfter(app_ref._update_client_default_save_path)
    wx.CallAfter(app_ref._update_web_ui)
    return "Ok."

def _is_sensitive_remote_pref_key(key):
    normalized = str(key or '').strip().lower()
    return any(token in normalized for token in (
        'password',
        'passwd',
        'secret',
        'token',
        'api_key',
        'apikey',
    ))


@app.route('/api/v2/app/remote_prefs')
@login_required
def get_remote_prefs():
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503

    # We also return the client name to determine schema on frontend
    name = "Other"
    from clients import LocalClient, QBittorrentClient, RTorrentClient, TransmissionClient
    if isinstance(client, LocalClient):
        return jsonify({'name': 'local', 'prefs': None})
    if isinstance(client, QBittorrentClient):
        name = "qbittorrent"
    elif isinstance(client, RTorrentClient):
        name = "rtorrent"
    elif isinstance(client, TransmissionClient):
        name = "transmission"

    try:
        prefs = client.get_app_preferences()
    except Exception:
        return "Failed to load remote preferences.", 500
    if prefs is None:
        return "Failed to load remote preferences.", 500

    if isinstance(prefs, dict):
        prefs = {
            key: value for key, value in prefs.items()
            if not _is_sensitive_remote_pref_key(key)
        }

    return jsonify({
        'name': name,
        'prefs': prefs
    })

@app.route('/api/v2/app/remote_prefs', methods=['POST'])
@login_required
def set_remote_prefs():
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503

    from clients import LocalClient
    if isinstance(client, LocalClient):
        return "Local client settings are managed as application preferences.", 400

    new_prefs = request.get_json(silent=True)
    if not isinstance(new_prefs, dict) or not new_prefs:
        return "Remote preferences object is required.", 400

    try:
        client.set_app_preferences(new_prefs)
    except Exception as e:
        print(f"remote_prefs error: {e}")
        return "Failed to update remote preferences.", 500
    return "Ok."

@app.route('/api/v2/sync/maindata')
@login_required
def sync_maindata():
    client = WEB_CONFIG['client']
    if not client:
        return "No torrent client is connected.", 503

    try:
        torrents = client.get_torrents_full()
    except Exception:
        return "Failed to load torrent sync data.", 500
    if not _valid_torrent_snapshot(torrents):
        return "Failed to load torrent sync data.", 500

    # qBit sync format is a dict indexed by hash
    t_dict = {t['hash']: t for t in torrents}
    return jsonify({
        'torrents': t_dict,
        'full_update': True
    })

# Server Threading
server_thread = None

def run_server():
    host = WEB_CONFIG.get('host') or '127.0.0.1'
    app.run(host=host, port=WEB_CONFIG['port'], threaded=True)

def start_web_ui():
    global server_thread
    if server_thread and server_thread.is_alive():
        return
    if _weak_web_credentials():
        print("Web UI not started: change the default Web UI password first.")
        return
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"Web UI started on port {WEB_CONFIG['port']}")
