import json
import os
import re
import shutil
import threading
from urllib.parse import urljoin, urlparse
from defusedxml import ElementTree as ET
from app_paths import get_data_dir

FLEXGET_CONFIG_MAX_BYTES = 2 * 1024 * 1024
from clients import _public_torrent_session, safe_encode_url, validate_public_torrent_url

RSS_FILE = os.path.join(get_data_dir(), "rss.json")
RSS_STATE_MAX_BYTES = 16 * 1024 * 1024
RSS_MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
RSS_MAX_REDIRECTS = 5
_RSS_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def _fetch_public_feed(url):
    current = url
    for _ in range(RSS_MAX_REDIRECTS + 1):
        try:
            validate_public_torrent_url(current)
        except ValueError as exc:
            raise ValueError("RSS feed URL must use a public http/https address") from exc

        content = b""
        with _public_torrent_session() as session, session.get(
            safe_encode_url(current), timeout=10, stream=True, allow_redirects=False
        ) as response:
            if response.status_code in _RSS_REDIRECT_STATUSES:
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("RSS feed redirect missing Location header")
                current = urljoin(current, location)
                continue

            response.raise_for_status()
            for chunk in response.iter_content(8192):
                if not chunk:
                    continue
                content += chunk
                if len(content) > RSS_MAX_DOWNLOAD_BYTES:
                    raise ValueError("RSS feed exceeds 10 MB limit")
        return content

    raise ValueError("RSS feed redirected too many times")

def _normalize_feed_url(url):
    normalized = str(url or "").strip()
    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
        raise ValueError("RSS feed URL must use http or https and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("RSS feed URL must not contain embedded credentials")
    try:
        validate_public_torrent_url(normalized)
    except ValueError as exc:
        raise ValueError("RSS feed URL must use a public http/https address") from exc
    return parsed.geturl()


class RSSManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.feeds = {} # url -> {'alias': str, 'last_update': float, 'articles': []}
        self.rules = [] # list of {'pattern': str, 'enabled': bool}
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(RSS_FILE):
                try:
                    with open(RSS_FILE, 'rb') as f:
                        raw = f.read(RSS_STATE_MAX_BYTES + 1)
                    if len(raw) > RSS_STATE_MAX_BYTES:
                        raise ValueError("rss.json exceeds the 16 MB state limit")
                    data = json.loads(raw.decode('utf-8'))
                    if not isinstance(data, dict):
                        raise ValueError("rss.json root must be an object")
                    feeds = data.get('feeds', {})
                    rules = data.get('rules', [])
                    if not isinstance(feeds, dict) or not isinstance(rules, list):
                        raise ValueError("rss.json has invalid feeds or rules")
                    normalized_feeds = {}
                    for url, feed in feeds.items():
                        if not isinstance(feed, dict):
                            continue
                        normalized = dict(feed)
                        if not isinstance(normalized.get('alias', ''), str):
                            normalized['alias'] = ''
                        articles = normalized.get('articles', [])
                        if not isinstance(articles, list):
                            articles = []
                        normalized_articles = []
                        for article in articles:
                            if not isinstance(article, dict):
                                continue
                            title = article.get('title')
                            link = article.get('link')
                            uid = article.get('uid', link)
                            if not isinstance(title, str) or not isinstance(link, str):
                                continue
                            if not isinstance(uid, str):
                                uid = link
                            normalized_articles.append({
                                'title': title,
                                'link': link,
                                'uid': uid,
                            })
                        normalized['articles'] = normalized_articles
                        downloaded = normalized.get('downloaded', [])
                        if not isinstance(downloaded, list):
                            downloaded = []
                        normalized['downloaded'] = [
                            uid for uid in downloaded if isinstance(uid, str)
                        ]
                        last_update = normalized.get('last_update', 0)
                        if isinstance(last_update, bool) or not isinstance(last_update, (int, float)):
                            normalized['last_update'] = 0
                        last_error = normalized.get('last_error')
                        if last_error is not None and not isinstance(last_error, str):
                            normalized['last_error'] = str(last_error)
                        normalized_feeds[str(url)] = normalized

                    normalized_rules = []
                    for rule in rules:
                        if not isinstance(rule, dict):
                            continue
                        pattern = rule.get('pattern')
                        if not isinstance(pattern, str) or not pattern:
                            continue
                        rule_type = rule.get('type', 'accept')
                        if rule_type not in {'accept', 'reject'}:
                            rule_type = 'accept'
                        enabled = rule.get('enabled', True)
                        if not isinstance(enabled, bool):
                            enabled = True
                        normalized_rule = {
                            'pattern': pattern,
                            'enabled': enabled,
                            'type': rule_type,
                        }
                        if 'scope' in rule:
                            scope = rule.get('scope')
                            if not isinstance(scope, list) or not all(isinstance(item, str) for item in scope):
                                scope = None
                            normalized_rule['scope'] = scope
                        normalized_rules.append(normalized_rule)

                    self.feeds = normalized_feeds
                    self.rules = normalized_rules
                except Exception as exc:
                    print(f"Failed to load RSS data: {exc}")
                    backup = RSS_FILE + ".corrupt"
                    try:
                        shutil.copy2(RSS_FILE, backup)
                        if os.name != "nt":
                            try:
                                os.chmod(backup, 0o600)
                            except OSError:
                                pass
                        print(f"Preserved unreadable rss.json as {backup}")
                    except OSError as backup_error:
                        print(f"Could not preserve unreadable rss.json: {backup_error}")

    def save(self):
        with self.lock:
            data = {'feeds': self.feeds, 'rules': self.rules}
            try:
                encoded = json.dumps(data, indent=4).encode('utf-8')
                if len(encoded) > RSS_STATE_MAX_BYTES:
                    raise ValueError("rss.json exceeds the 16 MB state limit")
                # Atomic write: a direct open('w') truncates rss.json immediately,
                # so a crash mid-write loses all feeds/rules. Write a temp + rename.
                tmp = f"{RSS_FILE}.{os.getpid()}.tmp"
                try:
                    with open(tmp, 'wb') as f:
                        f.write(encoded)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp, RSS_FILE)
                    if os.name != "nt":
                        try:
                            os.chmod(RSS_FILE, 0o600)
                        except OSError:
                            pass
                finally:
                    if os.path.exists(tmp):
                        try:
                            os.remove(tmp)
                        except OSError:
                            pass
            except Exception as e:
                print(f"Failed to save RSS: {e}")
                return False
            return True

    def add_feed(self, url, alias=""):
        url = _normalize_feed_url(url)

        with self.lock:
            if url in self.feeds:
                return False
            self.feeds[url] = {'alias': alias, 'last_update': 0, 'articles': []}
            if self.save():
                return True
            del self.feeds[url]
            return False

    def remove_feed(self, url):
        with self.lock:
            if url not in self.feeds:
                return False
            previous = self.feeds.pop(url)
            if self.save():
                return True
            self.feeds[url] = previous
            return False

    def add_rule(self, pattern, rule_type="accept", scope=None, enabled=True):
        """
        Add a rule.
        scope: None for global, or a list of feed URLs this rule applies to.
        """
        with self.lock:
            self.rules.append({'pattern': pattern, 'enabled': bool(enabled), 'type': rule_type, 'scope': scope})
            if self.save():
                return True
            self.rules.pop()
            return False

    def remove_rule(self, index):
        with self.lock:
            if not 0 <= index < len(self.rules):
                return False
            previous = self.rules.pop(index)
            if self.save():
                return True
            self.rules.insert(index, previous)
            return False

    def update_rule(self, index, data):
        with self.lock:
            if not 0 <= index < len(self.rules):
                return False
            previous = dict(self.rules[index])
            self.rules[index].update(data)
            if self.save():
                return True
            self.rules[index] = previous
            return False

    def reset_all(self):
        with self.lock:
            previous_feeds = self.feeds
            previous_rules = self.rules
            self.feeds = {}
            self.rules = []
            if self.save():
                return
            self.feeds = previous_feeds
            self.rules = previous_rules
            raise OSError("Failed to save reset RSS data.")

    def is_downloaded(self, url, uid):
        """True if `uid` from feed `url` has already been auto-downloaded."""
        if not uid:
            return False
        with self.lock:
            feed = self.feeds.get(url)
            if not feed:
                return False
            return uid in feed.get('downloaded', [])

    def mark_downloaded(self, url, uid):
        """Record `uid` as auto-downloaded so it is not re-added on the next poll."""
        if not uid:
            return
        with self.lock:
            feed = self.feeds.get(url)
            if feed is None:
                return
            previous = list(feed.get('downloaded', []))
            seen = feed.setdefault('downloaded', [])
            if uid in seen:
                return
            seen.append(uid)
            # Bound growth: stale items drop out of the feed and never recur.
            if len(seen) > 1000:
                del seen[:-1000]
            if self.save():
                return
            feed['downloaded'] = previous
            raise OSError("Failed to save RSS download history.")

    def fetch_feed(self, url):
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ('http', 'https'):
                raise ValueError("RSS feed URL must use http or https")
            content = _fetch_public_feed(url)

            # Simple RSS/Atom parser (defusedxml blocks XXE / entity expansion)
            root = ET.fromstring(content)
            articles = []
            
            # Handle RSS 2.0
            for item in root.findall('./channel/item'):
                title = item.find('title')
                link = item.find('link') # usually web link
                enclosure = item.find('enclosure') # usually torrent url
                
                # Torrent link might be in link or enclosure
                t_url = ""
                if enclosure is not None and enclosure.get('type') == 'application/x-bittorrent':
                    t_url = enclosure.get('url')
                elif link is not None:
                    t_url = link.text
                
                if title is not None and t_url:
                    articles.append({
                        'title': title.text or "",  # avoid None -> re.search TypeError
                        'link': t_url,
                        'uid': t_url # simplified UID
                    })

            # Handle Atom feeds as well. Prefer torrent enclosures, then alternate links.
            atom_ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', atom_ns):
                title = entry.find('atom:title', atom_ns)
                t_url = ""
                links = entry.findall('atom:link', atom_ns)
                for atom_link in links:
                    href = (atom_link.get('href') or '').strip()
                    rel = (atom_link.get('rel') or 'alternate').lower()
                    mime = (atom_link.get('type') or '').lower()
                    if href and (mime == 'application/x-bittorrent' or rel == 'enclosure'):
                        t_url = href
                        break
                if not t_url:
                    for atom_link in links:
                        href = (atom_link.get('href') or '').strip()
                        rel = (atom_link.get('rel') or 'alternate').lower()
                        if href and rel == 'alternate':
                            t_url = href
                            break
                if title is not None and t_url:
                    uid = entry.findtext('atom:id', default=t_url, namespaces=atom_ns) or t_url
                    articles.append({
                        'title': title.text or "",
                        'link': t_url,
                        'uid': uid,
                    })
            
            with self.lock:
                if url in self.feeds:
                    previous = dict(self.feeds[url])
                    self.feeds[url]['articles'] = articles
                    import time
                    self.feeds[url]['last_update'] = time.time()
                    self.feeds[url]['last_error'] = None # Clear error
                    if not self.save():
                        self.feeds[url] = previous
                        raise OSError("Failed to save refreshed RSS state.")
            
            return articles
        except Exception as e:
            err_msg = str(e)
            print(f"RSS Fetch Error {url}: {err_msg}")
            with self.lock:
                if url in self.feeds:
                    previous = dict(self.feeds[url])
                    self.feeds[url]['last_error'] = err_msg
                    if not self.save():
                        self.feeds[url] = previous
            return []

    def get_matches(self, articles, feed_url=None):
        matches = []
        # Rules and feeds might change, so capture a snapshot or lock?
        # get_matches is read-only usually, but accessing self.rules needs safety if modified elsewhere
        with self.lock:
            current_rules = list(self.rules) # Copy

        for a in articles:
            # Filter rules applicable to this feed
            applicable_rules = []
            for r in current_rules:
                if not r.get('enabled', True):
                    continue
                scope = r.get('scope')
                # If scope is None, it's global. If feed_url matches scope, it applies.
                if scope is None or (feed_url and feed_url in scope):
                    applicable_rules.append(r)

            # 1. Reject Check
            rejected = False
            for rule in applicable_rules:
                if rule.get('type') == 'reject':
                    try:
                        if re.search(rule['pattern'], a['title'], re.IGNORECASE):
                            rejected = True
                            break
                    except re.error:
                        continue
            if rejected:
                continue

            # 2. Accept Check
            for rule in applicable_rules:
                if rule.get('type', 'accept') == 'accept':
                    try:
                        if re.search(rule['pattern'], a['title'], re.IGNORECASE):
                            matches.append(a)
                            break
                    except re.error:
                        continue
        return matches

    def import_flexget_config(self, path, config_manager=None):
        try:
            import yaml
        except ImportError:
            raise Exception("PyYAML is required to import FlexGet configs.")

        try:
            with open(path, 'rb') as f:
                raw_config = f.read(FLEXGET_CONFIG_MAX_BYTES + 1)
        except Exception as e:
            raise ValueError("Invalid FlexGet configuration.") from e

        if len(raw_config) > FLEXGET_CONFIG_MAX_BYTES:
            raise ValueError("FlexGet configuration exceeds the 2 MB limit.")

        try:
            config = yaml.safe_load(raw_config.decode('utf-8'))
        except Exception as e:
            raise ValueError("Invalid FlexGet configuration.") from e

        if not config or 'tasks' not in config:
            return 0, 0

        if config_manager is None:
            from config_manager import ConfigManager
            config_manager = ConfigManager()
        cm = config_manager
        existing_profiles = cm.get_profiles()
        
        tasks = config.get('tasks', {})
        count_feeds = 0
        count_rules = 0
        previous_feeds = None
        previous_rules = None
        created_profile_ids = []
        
        # Helper to avoid dupes
        def profile_exists(url, user):
            for pid, p in existing_profiles.items():
                if p.get('url') == url and p.get('user') == user:
                    return True
            return False

        with self.lock:
            previous_feeds = dict(self.feeds)
            previous_rules = [dict(rule) for rule in self.rules]
            try:
                for task_name, task_config in tasks.items():
                    if not isinstance(task_config, dict):
                        continue

                    # 0. Profile (qBittorrent)
                    qbit = task_config.get('qbittorrent')
                    if qbit and isinstance(qbit, dict):
                        host = qbit.get('host', 'localhost')
                        port = qbit.get('port', 8080)
                        user = qbit.get('username', '')
                        pw = qbit.get('password', '')
                        
                        url = f"http://{host}:{port}"
                        if not profile_exists(url, user):
                            pid = cm.add_profile(
                                f"{task_name} qBit", "qbittorrent", url, user, pw
                            )
                            created_profile_ids.append(pid)
                            existing_profiles[pid] = {
                                'name': f"{task_name} qBit",
                                'type': 'qbittorrent',
                                'url': url,
                                'user': user,
                                'password': pw,
                            }

                    # 1. RSS Feeds (Collect task URLs for scoping)
                    task_feed_urls = []
                    
                    rss_entry = task_config.get('rss')
                    if rss_entry:
                        url = ""
                        if isinstance(rss_entry, str):
                            url = rss_entry
                        elif isinstance(rss_entry, dict):
                            url = rss_entry.get('url')
                        
                        if url:
                            url = _normalize_feed_url(url)
                            task_feed_urls.append(url)
                            # Avoid nested lock if add_feed uses it.
                            # Since we are holding lock, we should manually manipulate dict or make add_feed reentrant (RLock handles this).
                            if url not in self.feeds:
                                self.feeds[url] = {'alias': f"{task_name} RSS", 'last_update': 0, 'articles': []}
                                count_feeds += 1
                    
                    inputs = task_config.get('inputs', [])
                    if isinstance(inputs, list):
                        for inp in inputs:
                            if isinstance(inp, dict) and 'rss' in inp:
                                val = inp['rss']
                                url = ""
                                if isinstance(val, str):
                                    url = val
                                elif isinstance(val, dict):
                                    url = val.get('url')
                                
                                if url:
                                    url = _normalize_feed_url(url)
                                    task_feed_urls.append(url)
                                    if url not in self.feeds:
                                        self.feeds[url] = {'alias': f"{task_name} RSS", 'last_update': 0, 'articles': []}
                                        count_feeds += 1

                    # 2. Rules (Regex) - Scope them to task_feed_urls
                    regexp = task_config.get('regexp', {})
                    if isinstance(regexp, dict):
                        # Accept
                        accept = regexp.get('accept', [])
                        if isinstance(accept, list):
                            for pattern in accept:
                                self.rules.append({'pattern': str(pattern), 'enabled': True, 'type': 'accept', 'scope': task_feed_urls})
                                count_rules += 1
                        # Reject
                        reject = regexp.get('reject', [])
                        if isinstance(reject, list):
                            for pattern in reject:
                                self.rules.append({'pattern': str(pattern), 'enabled': True, 'type': 'reject', 'scope': task_feed_urls})
                                count_rules += 1
                    
                    # 3. Series - Scope them to task_feed_urls
                    series = task_config.get('series', [])
                    if isinstance(series, list):
                        for s in series:
                            name = ""
                            if isinstance(s, str):
                                name = s
                            elif isinstance(s, dict):
                                name = list(s.keys())[0] if s else ""
                            
                            if name:
                                pattern = re.escape(name).replace(r"\ ", ".*")
                                self.rules.append({'pattern': pattern, 'enabled': True, 'type': 'accept', 'scope': task_feed_urls})
                                count_rules += 1
                                
                    # 4. Accept All - Scope them to task_feed_urls
                    if task_config.get('accept_all'):
                         self.rules.append({'pattern': ".*", 'enabled': True, 'type': 'accept', 'scope': task_feed_urls})
                         count_rules += 1
                

                if not self.save():
                    raise OSError("Failed to save imported RSS data.")
            except Exception:
                self.feeds = previous_feeds
                self.rules = previous_rules
                for pid in reversed(created_profile_ids):
                    try:
                        cm.delete_profile(pid)
                    except Exception:
                        pass
                raise
        
        return count_feeds, count_rules
