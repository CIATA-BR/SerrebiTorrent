import json
import os
import re
import shutil
import threading
from urllib.parse import urljoin, urlparse
from defusedxml import ElementTree as ET
from app_paths import get_data_dir
from clients import _public_torrent_session, safe_encode_url, validate_public_torrent_url

RSS_FILE = os.path.join(get_data_dir(), "rss.json")
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
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
        raise ValueError("RSS feed URL must use http or https and include a host")
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
                    with open(RSS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("rss.json root must be an object")
                    feeds = data.get('feeds', {})
                    rules = data.get('rules', [])
                    if not isinstance(feeds, dict) or not isinstance(rules, list):
                        raise ValueError("rss.json has invalid feeds or rules")
                    self.feeds = feeds
                    self.rules = rules
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
                # Atomic write: a direct open('w') truncates rss.json immediately,
                # so a crash mid-write loses all feeds/rules. Write a temp + rename.
                tmp = f"{RSS_FILE}.{os.getpid()}.tmp"
                try:
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
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
            
            with self.lock:
                if url in self.feeds:
                    self.feeds[url]['articles'] = articles
                    import time
                    self.feeds[url]['last_update'] = time.time()
                    self.feeds[url]['last_error'] = None # Clear error
            
            return articles
        except Exception as e:
            err_msg = str(e)
            print(f"RSS Fetch Error {url}: {err_msg}")
            with self.lock:
                if url in self.feeds:
                    self.feeds[url]['last_error'] = err_msg
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

    def import_flexget_config(self, path):
        try:
            import yaml
        except ImportError:
            raise Exception("PyYAML is required to import FlexGet configs.")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ValueError("Invalid FlexGet configuration.") from e

        if not config or 'tasks' not in config:
            return 0, 0

        from config_manager import ConfigManager
        cm = ConfigManager()
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
