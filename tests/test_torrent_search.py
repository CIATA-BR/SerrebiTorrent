"""Torrent search: result shaping, ranking, feeds and the search fan-out.

Nothing here touches the network -- each indexer's parser is fed a recorded
reply, and the fan-out is driven through fake searchers.
"""

import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torrent_search as ts


class _Response:
    def __init__(self, payload=None, text="", content=b"", headers=None):
        self._payload = payload
        self.text = text
        self.content = content
        self.headers = headers or {}
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]

    def close(self):
        return None


# -- result rows -------------------------------------------------------------


def test_a_bare_info_hash_becomes_a_magnet_with_open_trackers():
    item = ts._item(ts.SOURCE_PIRATEBAY, "A" * 40, "Some Release")

    assert item["magnet"].startswith("magnet:?xt=urn:btih:" + "a" * 40)
    # Without trackers a client has only the DHT to go on, and a cold start
    # can take minutes.
    for tracker in ts.TRACKERS:
        assert quote(tracker, safe="") in item["magnet"]


def test_a_tracker_file_row_gets_no_magnet_at_all():
    # Private trackers flag their torrents private: DHT and peer exchange are
    # off, and only the announce URL inside the file -- carrying the account's
    # passkey -- reaches the swarm. Bolting public trackers on would announce
    # a private torrent publicly, which is what gets an account banned.
    item = ts._item(ts.SOURCE_KNABEN, "B" * 40, "Private Release",
                    download_url="https://tracker.example/dl?passkey=x")

    assert item["magnet"] == ""
    assert ts.magnet_for(item) == ""


def test_an_indexers_own_magnet_is_kept_over_a_rebuilt_one():
    supplied = "magnet:?xt=urn:btih:" + "c" * 40 + "&tr=udp%3A%2F%2Fprivate"
    item = ts._item(ts.SOURCE_EZTV, "C" * 40, "Show", magnet=supplied)

    assert item["magnet"] == supplied


def test_a_byte_count_is_turned_into_something_readable():
    item = ts._item(ts.SOURCE_KNABEN, "D" * 40, "Film", size_bytes=1536)

    assert item["file_size"] == "1.5 KB"


# -- ranking -----------------------------------------------------------------


def test_ranking_puts_the_best_seeded_match_first():
    rows = [
        ts._item(ts.SOURCE_KNABEN, "1" * 40, "Ubuntu 24.04 Desktop", seeders=5),
        ts._item(ts.SOURCE_KNABEN, "2" * 40, "Ubuntu 24.04 Desktop", seeders=90),
    ]

    ranked = ts._rank(rows, "ubuntu 24.04")

    assert ranked[0]["seeders"] == 90


def test_ranking_drops_duplicate_info_hashes():
    rows = [
        ts._item(ts.SOURCE_KNABEN, "9" * 40, "Ubuntu 24.04", seeders=10),
        ts._item(ts.SOURCE_PIRATEBAY, "9" * 40, "Ubuntu 24.04", seeders=10),
    ]

    assert len(ts._rank(rows, "ubuntu")) == 1


def test_a_strict_indexer_returns_nothing_rather_than_the_wrong_show():
    # EZTV cannot be given the query at all, so an unmatched row is not a near
    # miss worth showing -- it is a different programme.
    rows = [ts._item(ts.SOURCE_EZTV, "8" * 40, "Some Other Show S01E01")]

    assert ts._rank(rows, "the office", strict=True) == []
    assert ts._rank(rows, "the office", strict=False) != []


def test_ranking_caps_how_much_one_indexer_can_contribute():
    rows = [ts._item(ts.SOURCE_KNABEN, f"{index:040d}", "Ubuntu", seeders=index)
            for index in range(ts.MAX_RESULTS_PER_SOURCE + 20)]

    assert len(ts._rank(rows, "ubuntu")) == ts.MAX_RESULTS_PER_SOURCE


def test_a_release_name_still_matches_the_plain_title():
    assert ts.score_match("the office", "The Office S03E12 1080p WEB-DL") >= 70


# -- indexer parsers ---------------------------------------------------------


def test_piratebay_skips_its_empty_result_placeholder():
    payload = [
        {"info_hash": "0" * 40, "name": "No results returned", "seeders": "0"},
        {"info_hash": "e" * 40, "name": "Real Release", "seeders": "12",
         "leechers": "3", "size": "1048576", "category": "201", "id": "5"},
    ]
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=_Response(payload)))):
        items = ts.search_piratebay("anything")

    assert [item["title"] for item in items] == ["Real Release"]
    assert items[0]["format"] == "Video"
    assert items[0]["seeders"] == 12


def test_knaben_reports_the_indexer_each_row_came_from():
    payload = {"hits": [{
        "hash": "f" * 40, "title": "Release", "tracker": "1337x",
        "seeders": 40, "peers": 55, "bytes": 2048,
        "date": "2026-01-02T03:04:05Z", "details": "https://example/1",
    }]}
    with patch.object(ts, '_http', return_value=MagicMock(
            post=MagicMock(return_value=_Response(payload)))):
        items = ts.search_knaben("release")

    assert items[0]["uploader"] == "1337x"
    # Knaben reports total peers, so leechers are what is left after seeders.
    assert items[0]["leechers"] == 15
    assert items[0]["posted"] > 0


def test_eztv_looks_the_programme_up_by_name_first():
    torrents = {"torrents": [{
        "hash": "a" * 40, "title": "The Office S03E12",
        "magnet_url": "magnet:?xt=urn:btih:" + "a" * 40,
        "seeds": 9, "peers": 2, "size_bytes": "1024",
        "date_released_unix": 1700000000, "id": 7,
    }]}
    http = MagicMock(get=MagicMock(return_value=_Response(torrents)))
    with patch.object(ts, '_http', return_value=http), \
            patch.object(ts, 'imdb_id_for', return_value="tt0386676"):
        items = ts.search_eztv("the office")

    # The tt prefix is stripped: EZTV's API wants the bare number.
    assert http.get.call_args.kwargs["params"]["imdb_id"] == "0386676"
    assert items[0]["seeders"] == 9


def test_a_broken_name_lookup_does_not_fail_the_eztv_search():
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(side_effect=RuntimeError("down")))):
        assert ts.imdb_id_for("anything") == ""


# -- user feeds --------------------------------------------------------------


def test_a_half_filled_feed_is_skipped_rather_than_searched():
    prefs = {"torznab_feeds": [
        {"name": "Prowlarr", "url": "http://localhost:9696/api/v1/search"},
        {"name": "", "url": "http://nowhere"},
        {"name": "No URL", "url": ""},
        "not a dict",
    ]}

    assert [feed["name"] for feed in ts.feeds(prefs)] == ["Prowlarr"]


def test_feeds_join_the_built_in_indexers():
    prefs = {"torznab_feeds": [{"name": "Jackett", "url": "http://x"}]}

    assert "Jackett" in ts.all_sources(prefs)
    assert ts.SOURCE_KNABEN in ts.all_sources(prefs)


def test_nothing_private_ships_in_the_defaults():
    # A fresh install must arrive with no indexer of anybody's, and every
    # public one switched on.
    from config_manager import DEFAULT_PREFERENCES

    assert DEFAULT_PREFERENCES["torznab_feeds"] == []
    assert DEFAULT_PREFERENCES["disabled_torrent_sources"] == []


def test_blinddl_feeds_are_adopted_when_there_are_none_here(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"torznab_feeds": [
        {"name": "My Prowlarr", "url": "http://localhost:9696/api/v1/search",
         "api_key": "secret"},
    ]}), encoding="utf-8")
    prefs = {"torznab_feeds": []}

    with patch.object(ts, 'blinddl_config_path', return_value=str(config)):
        added = ts.import_blinddl_feeds(prefs)

    assert [feed["name"] for feed in added] == ["My Prowlarr"]
    assert prefs["torznab_feeds"][0]["api_key"] == "secret"


def test_adopting_twice_adds_nothing_the_second_time(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"torznab_feeds": [
        {"name": "My Prowlarr", "url": "http://x", "api_key": "k"},
    ]}), encoding="utf-8")
    prefs = {"torznab_feeds": []}

    with patch.object(ts, 'blinddl_config_path', return_value=str(config)):
        ts.import_blinddl_feeds(prefs)
        assert ts.import_blinddl_feeds(prefs) == []

    assert len(prefs["torznab_feeds"]) == 1


def test_an_indexer_edited_here_is_never_overwritten(tmp_path):
    # The search dialog runs this every time it opens, so a URL or key
    # changed in SerrebiTorrent has to survive.
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"torznab_feeds": [
        {"name": "My Prowlarr", "url": "http://blinddl", "api_key": "old"},
    ]}), encoding="utf-8")
    prefs = {"torznab_feeds": [
        {"name": "My Prowlarr", "url": "http://edited", "api_key": "new"},
    ]}

    with patch.object(ts, 'blinddl_config_path', return_value=str(config)):
        assert ts.import_blinddl_feeds(prefs) == []

    assert prefs["torznab_feeds"][0]["url"] == "http://edited"
    assert prefs["torznab_feeds"][0]["api_key"] == "new"


def test_a_feed_may_not_shadow_a_built_in_indexer(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"torznab_feeds": [
        {"name": ts.SOURCE_NYAA, "url": "http://x", "api_key": ""},
    ]}), encoding="utf-8")
    prefs = {"torznab_feeds": []}

    with patch.object(ts, 'blinddl_config_path', return_value=str(config)):
        assert ts.import_blinddl_feeds(prefs) == []


def test_no_blinddl_installed_is_not_an_error(tmp_path):
    prefs = {"torznab_feeds": []}
    missing = str(tmp_path / "nothing" / "config.json")

    with patch.object(ts, 'blinddl_config_path', return_value=missing):
        assert ts.import_blinddl_feeds(prefs) == []

    assert prefs["torznab_feeds"] == []


def test_a_corrupt_blinddl_config_is_not_an_error(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{not json", encoding="utf-8")

    with patch.object(ts, 'blinddl_config_path', return_value=str(config)):
        assert ts.blinddl_feeds() == []


def test_the_switched_off_list_decides_what_is_searched():
    enabled = ts.enabled_sources([ts.SOURCE_EZTV, ts.SOURCE_NYAA])

    assert ts.SOURCE_EZTV not in enabled
    assert ts.SOURCE_KNABEN in enabled


def test_a_torznab_feed_keeps_its_authenticated_torrent_link():
    body = """<?xml version="1.0"?>
    <rss xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
      <item>
        <title>Private Release</title>
        <link>https://tracker.example/dl/1?passkey=secret</link>
        <size>2048</size>
        <torznab:attr name="seeders" value="30"/>
        <torznab:attr name="peers" value="35"/>
        <torznab:attr name="infohash" value="{hash}"/>
      </item>
    </channel></rss>""".format(hash="b" * 40)
    response = _Response(text=body, content=body.encode())
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=response))):
        items = ts.search_feed("release", {"name": "Prowlarr",
                                           "url": "http://x", "api_key": "k"})

    assert items[0]["download_url"] == "https://tracker.example/dl/1?passkey=secret"
    assert items[0]["magnet"] == ""
    assert items[0]["leechers"] == 5


def test_prowlarr_json_skips_usenet_releases():
    payload = [
        {"protocol": "usenet", "title": "NZB Release", "infoHash": ""},
        {"protocol": "torrent", "title": "Torrent Release",
         "infoHash": "c" * 40, "seeders": 4, "leechers": 1, "size": 1024,
         "indexer": "SomeTracker", "categories": [{"name": "Movies"}]},
    ]
    response = _Response(payload, text="[{}]")
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=response))):
        items = ts.search_feed("release", {"name": "Prowlarr",
                                           "url": "http://x", "api_key": ""})

    assert [item["title"] for item in items] == ["Torrent Release"]
    assert items[0]["uploader"] == "SomeTracker"
    assert items[0]["format"] == "Movies"


# -- fetching a tracker's own .torrent ---------------------------------------


def test_an_html_error_page_is_not_mistaken_for_a_torrent_file():
    # A spent or unauthorised link often answers with a login page and a 200.
    response = _Response(content=b"<!DOCTYPE html><html>Login</html>")
    item = ts._item(ts.SOURCE_KNABEN, "", "X",
                    download_url="https://tracker.example/dl")
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=response))):
        with pytest.raises(RuntimeError, match="did not return a torrent file"):
            ts.fetch_torrent_bytes(item)


def test_resolve_prefers_a_magnet_and_fetches_nothing():
    item = ts._item(ts.SOURCE_KNABEN, "d" * 40, "Release")

    kind, payload = ts.resolve(item)

    assert kind == "magnet"
    assert payload.startswith("magnet:")


def test_resolve_downloads_the_tracker_file_when_there_is_no_magnet():
    item = ts._item(ts.SOURCE_KNABEN, "", "Release",
                    download_url="https://tracker.example/dl")
    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=_Response(content=b"d4:infod")))):
        kind, payload = ts.resolve(item)

    assert kind == "file"
    assert payload.startswith(b"d")


def test_a_row_with_neither_is_refused_clearly():
    with pytest.raises(RuntimeError, match="no magnet link or info hash"):
        ts.resolve(ts._item(ts.SOURCE_KNABEN, "", "Release"))


# -- the fan-out -------------------------------------------------------------


def test_one_broken_indexer_does_not_take_the_others_down():
    def good(query, timeout=None):
        return [ts._item(ts.SOURCE_NYAA, "1" * 40, "Ubuntu", seeders=5)]

    def bad(query, timeout=None):
        raise RuntimeError("indexer down")

    with patch.dict(ts._SEARCHERS, {ts.SOURCE_NYAA: good,
                                    ts.SOURCE_KNABEN: bad}, clear=True):
        items, answered, asked = ts.search(
            "ubuntu", timeout_s=5,
            sources=[ts.SOURCE_KNABEN, ts.SOURCE_NYAA])

    assert len(items) == 1
    assert sorted(answered) == sorted(asked)


def test_results_are_reported_per_indexer_as_they_arrive():
    seen = []

    def good(query, timeout=None):
        return [ts._item(ts.SOURCE_NYAA, "2" * 40, "Ubuntu", seeders=1)]

    with patch.dict(ts._SEARCHERS, {ts.SOURCE_NYAA: good}, clear=True):
        ts.search("ubuntu", timeout_s=5, sources=[ts.SOURCE_NYAA],
                  on_site=lambda source, items: seen.append((source, len(items))))

    assert seen == [(ts.SOURCE_NYAA, 1)]


def test_a_stopped_search_reports_nothing_more():
    stop = threading.Event()
    stop.set()
    seen = []

    with patch.dict(ts._SEARCHERS, {ts.SOURCE_NYAA: lambda q, timeout=None: []},
                    clear=True):
        ts.search("ubuntu", timeout_s=5, sources=[ts.SOURCE_NYAA], stop=stop,
                  on_site=lambda source, items: seen.append(source))

    assert seen == []


def test_a_slow_indexer_does_not_hold_the_search_past_its_deadline():
    release = threading.Event()

    def slow(query, timeout=None):
        release.wait(10)
        return []

    with patch.dict(ts._SEARCHERS, {ts.SOURCE_NYAA: slow}, clear=True):
        items, answered, asked = ts.search(
            "ubuntu", timeout_s=0.2, sources=[ts.SOURCE_NYAA])

    release.set()
    assert items == []
    assert answered == []
    assert asked == [ts.SOURCE_NYAA]


def test_an_unknown_source_name_is_ignored():
    items, answered, asked = ts.search(
        "ubuntu", timeout_s=1, sources=["Not An Indexer"])

    assert asked == []
    assert items == []



def test_feeds_rejects_non_object_preferences():
    import torrent_search

    assert torrent_search.feeds([]) == []
    assert torrent_search.feeds("broken") == []


def test_blinddl_feeds_returns_empty_for_non_object_config(tmp_path, monkeypatch):
    import json
    import torrent_search

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(["unexpected"]), encoding="utf-8")
    monkeypatch.setattr(torrent_search, "blinddl_config_path", lambda: str(config_path))

    assert torrent_search.blinddl_feeds() == []



def test_search_dialog_blinddl_import_treats_persistence_as_optional():
    from pathlib import Path

    source = Path("search_dialog.py").read_text(encoding="utf-8")
    block = source[source.index("def _adopt_blinddl_feeds"):source.index("# -- searching")]
    assert "self.config_manager.set_preferences(prefs)" in block
    assert "except Exception" in block



def test_tracker_file_download_rejects_oversized_content_length():
    response = _Response(
        content=b"d4:infod",
        headers={"Content-Length": str(ts.TORRENT_MAX_DOWNLOAD_BYTES + 1)},
    )
    item = ts._item(
        ts.SOURCE_KNABEN, "", "X",
        download_url="https://tracker.example/dl",
    )

    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=response))):
        with pytest.raises(RuntimeError, match="16 MB download limit"):
            ts.fetch_torrent_bytes(item)


def test_tracker_file_download_stops_when_stream_exceeds_limit(monkeypatch):
    monkeypatch.setattr(ts, "TORRENT_MAX_DOWNLOAD_BYTES", 8)
    response = _Response(content=b"d12345678")
    item = ts._item(
        ts.SOURCE_KNABEN, "", "X",
        download_url="https://tracker.example/dl",
    )

    with patch.object(ts, '_http', return_value=MagicMock(
            get=MagicMock(return_value=response))):
        with pytest.raises(RuntimeError, match="download limit"):
            ts.fetch_torrent_bytes(item)
