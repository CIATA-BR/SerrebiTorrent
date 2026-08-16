"""Reproduce/verify SerrebiTorrent#1: added torrents missing from get_torrents_full().

Uses a throwaway state dir and a stub ConfigManager so nothing in the user's
real data directory is touched. Exits 0 when the added torrent shows up in the
GUI's list source, 1 otherwise.

The regression this guards: libtorrent 2.1 removed ``torrent_status.paused``
/``auto_managed`` (and ``session.status()``); the per-row build in
``LocalClient.get_torrents_full`` then raised for every torrent and the row
loop silently skipped them all, so the GUI showed an empty list while files
still downloaded.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libtorrent_env import prepare_libtorrent_dlls

prepare_libtorrent_dlls()

import libtorrent as lt  # noqa: E402
import session_manager as sm_mod  # noqa: E402
from clients import LocalClient  # noqa: E402

tmp = tempfile.mkdtemp(prefix="serrebi_repro_")
state_dir = os.path.join(tmp, "state")
download_dir = os.path.join(tmp, "downloads")
os.makedirs(state_dir, exist_ok=True)
os.makedirs(download_dir, exist_ok=True)

# Keep every write inside the temp dir.
sm_mod.get_state_dir = lambda: state_dir


class StubPrefs:
    def get_preferences(self):
        return {
            "enable_dht": False,
            "enable_lsd": False,
            "enable_upnp": False,
            "enable_natpmp": False,
            "listen_port": 16881,
        }


sm_mod.ConfigManager = lambda: StubPrefs()

from session_manager import SessionManager  # noqa: E402

SessionManager._instance = None
sm = SessionManager.get_instance()

# --- Build a small real torrent file -------------------------------------
seed_file = os.path.join(download_dir, "hello.txt")
with open(seed_file, "w", encoding="utf-8") as f:
    f.write("hello serrebi " * 200)

files = lt.list_files(seed_file)
ct = lt.create_torrent(files)
lt.set_piece_hashes(ct, download_dir)
torrent_bytes = lt.bencode(ct.generate())

info = lt.torrent_info(torrent_bytes)
print("torrent name:", info.name())
print("torrent v1 hash:", info.info_hashes().v1)

# --- Add it the same way the GUI does ------------------------------------
sm.add_torrent_file(torrent_bytes, download_dir)

# Let libtorrent spin a little so metadata/status settle.
deadline = time.time() + 3
while time.time() < deadline:
    sm.ses.wait_for_alert(100)
    sm.ses.pop_alerts()
    time.sleep(0.05)

# --- Read it back the way the GUI does ------------------------------------
client = LocalClient(download_dir)
rows = client.get_torrents_full()
print("get_torrents_full() returned", len(rows), "rows")
for row in rows:
    print("  row:", {k: row.get(k) for k in ("hash", "name", "size", "done", "state")})

found = any(str(row.get("hash", "")) == str(info.info_hashes().v1) for row in rows)
print("RESULT:", "FOUND" if found else "MISSING")
sm.running = False
sm.alert_thread.join(timeout=1)
sys.exit(0 if found else 1)
