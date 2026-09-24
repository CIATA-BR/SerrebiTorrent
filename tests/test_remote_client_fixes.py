import pytest
from unittest.mock import MagicMock

import clients


class FakeRTorrentD:
    def __init__(self):
        self.erase_calls = []
        self.calls = []

    def multicall2(self, *args):
        return [[
            "a" * 40,
            50,
            5,
            1000,
            1,
            1,
            0,
            "",
            5,
            2,
            "Test",
            100,
            50,
            "seed",   # d.connection_seed: string constant, NOT a peer count
            "leech",  # d.connection_leech: string constant, NOT a peer count
            10,       # d.peers_complete: seeders
            12,       # d.peers_accounted: leechers
            "C:\\Downloads",
        ]]

    def open(self, h):
        self.calls.append(("open", h))

    def start(self, h):
        self.calls.append(("start", h))

    def stop(self, h):
        self.calls.append(("stop", h))

    def close(self, h):
        self.calls.append(("close", h))

    def erase(self, h):
        self.erase_calls.append(h)
        self.calls.append(("erase", h))

    def check_hash(self, h):
        self.calls.append(("check_hash", h))

    def tracker_announce(self, h):
        self.calls.append(("tracker_announce", h))


class FakeRTorrentServer:
    def __init__(self):
        self.d = FakeRTorrentD()


def test_rtorrent_seed_leecher_indices_are_mapped_correctly():
    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = FakeRTorrentServer()

    torrents = client.get_torrents_full()

    # rTorrent exposes peers_complete (seeders) / peers_accounted (leechers) but
    # no separate connected-vs-total split, so both map to those counts. The
    # connection_seed/connection_leech columns are string constants ("seed"/
    # "leech") and must never be read as peer counts.
    assert torrents[0]["seeds_connected"] == 10
    assert torrents[0]["leechers_connected"] == 12
    assert torrents[0]["seeds_total"] == 10
    assert torrents[0]["leechers_total"] == 12


def test_rtorrent_remove_with_data_is_unsupported():
    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = FakeRTorrentServer()

    with pytest.raises(NotImplementedError):
        client.remove_torrent_with_data("a" * 40)

    assert client.srv.d.erase_calls == []


def test_rtorrent_actions_normalize_raw_hash_bytes():
    raw_hash = b"\x04" * 20
    expected_hash = raw_hash.hex()
    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = FakeRTorrentServer()

    client.start_torrent(raw_hash)
    client.stop_torrent(raw_hash)
    client.remove_torrent(raw_hash)
    client.recheck_torrent(raw_hash)
    client.reannounce_torrent(raw_hash)

    assert client.srv.d.calls == [
        ("open", expected_hash),
        ("start", expected_hash),
        ("stop", expected_hash),
        ("close", expected_hash),
        ("erase", expected_hash),
        ("check_hash", expected_hash),
        ("tracker_announce", expected_hash),
    ]


def test_rtorrent_set_preferences_propagates_rpc_errors():
    class FailingServer:
        def __getattr__(self, name):
            def fail(*args):
                raise RuntimeError("rpc failed")
            return fail

    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = FailingServer()

    with pytest.raises(RuntimeError, match="rpc failed"):
        client.set_app_preferences({"dl_limit": 100})


def test_base_client_batch_delete_continues_after_failure():
    class FakeClient(clients.BaseClient):
        def test_connection(self):
            return True

        def get_torrents_full(self):
            return []

        def start_torrent(self, h):
            pass

        def stop_torrent(self, h):
            pass

        def remove_torrent(self, h):
            self.calls.append(h)
            if h == "bad":
                raise RuntimeError("delete failed")

        def remove_torrent_with_data(self, h):
            self.remove_torrent(h)

        def add_torrent_url(self, u, sp=None):
            pass

        def add_torrent_file(self, c, sp=None, p=None):
            pass

        def get_global_stats(self):
            return 0, 0

        def get_torrent_save_path(self, h):
            return None

        def get_files(self, h):
            return []

        def set_file_priority(self, h, i, p):
            pass

        def get_peers(self, h):
            return []

        def get_trackers(self, h):
            return []

    client = FakeClient.__new__(FakeClient)
    client.calls = []

    with pytest.raises(RuntimeError, match="one or more torrents"):
        client.remove_torrents(["first", "bad", "last"])

    assert client.calls == ["first", "bad", "last"]


def test_transmission_batch_delete_continues_after_failure():
    class FakeTransmissionRpc:
        def __init__(self):
            self.calls = []

        def remove_torrent(self, h, delete_data=False):
            self.calls.append((h, delete_data))
            if h == 2:
                raise RuntimeError("delete failed")

    client = clients.TransmissionClient.__new__(clients.TransmissionClient)
    client.c = FakeTransmissionRpc()

    with pytest.raises(RuntimeError, match="one or more torrents"):
        client.remove_torrents([1, 2, 3], df=True)

    assert client.c.calls == [(1, True), (2, True), (3, True)]


def test_rtorrent_snapshot_failure_is_not_reported_as_empty_list():
    class FailingD:
        def multicall2(self, *args):
            raise RuntimeError("rpc unavailable")

    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = type("Server", (), {"d": FailingD()})()

    with pytest.raises(RuntimeError, match="rpc unavailable"):
        client.get_torrents_full()


def test_qbittorrent_snapshot_failure_is_not_reported_as_empty_list():
    client = clients.QBittorrentClient.__new__(clients.QBittorrentClient)
    client.c = type(
        "FailingQbit",
        (),
        {"torrents_info": lambda self, *args, **kwargs: (_ for _ in ()).throw(RuntimeError("api unavailable"))},
    )()

    with pytest.raises(RuntimeError, match="api unavailable"):
        client.get_torrents_full()


def test_transmission_snapshot_failure_is_not_reported_as_empty_list():
    client = clients.TransmissionClient.__new__(clients.TransmissionClient)
    client.c = type(
        "FailingTransmission",
        (),
        {"get_torrents": lambda self: (_ for _ in ()).throw(RuntimeError("rpc unavailable"))},
    )()

    with pytest.raises(RuntimeError, match="rpc unavailable"):
        client.get_torrents_full()


def test_local_snapshot_failure_is_not_reported_as_empty_list():
    client = clients.LocalClient.__new__(clients.LocalClient)
    client.m = type(
        "FailingSessionManager",
        (),
        {"get_torrents": lambda self: (_ for _ in ()).throw(RuntimeError("session unavailable"))},
    )()

    with pytest.raises(RuntimeError, match="session unavailable"):
        client.get_torrents_full()


def test_qbittorrent_preference_read_failure_is_not_reported_as_none():
    client = object.__new__(clients.QBittorrentClient)
    client.c = MagicMock()
    client.c.app_preferences.side_effect = RuntimeError("qbit unavailable")

    with pytest.raises(RuntimeError, match="qbit unavailable"):
        client.get_app_preferences()


def test_transmission_preference_read_failure_is_not_reported_as_none():
    client = object.__new__(clients.TransmissionClient)
    client.c = MagicMock()
    client.c.get_session.side_effect = RuntimeError("transmission unavailable")

    with pytest.raises(RuntimeError, match="transmission unavailable"):
        client.get_app_preferences()


@pytest.mark.parametrize("detail", ["files", "peers", "trackers"])
def test_rtorrent_detail_failure_is_not_reported_as_empty_list(detail):
    class FailingMulticall:
        def multicall(self, *args):
            raise RuntimeError("rpc unavailable")

    client = clients.RTorrentClient("http://localhost/RPC2")
    client.srv = type(
        "Server",
        (),
        {
            "f": FailingMulticall(),
            "p": FailingMulticall(),
            "t": FailingMulticall(),
        },
    )()

    method = {
        "files": client.get_files,
        "peers": client.get_peers,
        "trackers": client.get_trackers,
    }[detail]

    with pytest.raises(RuntimeError, match="rpc unavailable"):
        method("a" * 40)



@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("start_torrent", ("missing",)),
        ("stop_torrent", ("missing",)),
        ("recheck_torrent", ("missing",)),
        ("reannounce_torrent", ("missing",)),
        ("set_file_priority", ("missing", 0, 1)),
    ],
)
def test_local_mutating_actions_fail_when_torrent_is_missing(method_name, args):
    client = clients.LocalClient.__new__(clients.LocalClient)
    client.m = MagicMock()
    client.m._find_handle.return_value = None

    with pytest.raises(LookupError, match="Torrent not found"):
        getattr(client, method_name)(*args)
