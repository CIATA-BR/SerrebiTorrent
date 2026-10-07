from recent_save_paths import RecentSavePaths


def test_recent_save_paths_are_profile_scoped_and_most_recent_first(tmp_path):
    store = RecentSavePaths(path=str(tmp_path / "recent.json"), max_paths=3)

    store.remember("profile-a", "/downloads/one")
    store.remember("profile-a", "/downloads/two")
    store.remember("profile-b", "/remote/media")
    store.remember("profile-a", "/downloads/one")

    assert store.paths("profile-a") == ["/downloads/one", "/downloads/two"]
    assert store.paths("profile-b") == ["/remote/media"]


def test_recent_save_paths_cap_entries_without_touching_remote_paths(tmp_path):
    store = RecentSavePaths(path=str(tmp_path / "recent.json"), max_paths=2)

    store.remember("profile", r"Z:\\Media\\Movies")
    store.remember("profile", "/srv/downloads")
    store.remember("profile", "/mnt/archive")

    assert store.paths("profile") == ["/mnt/archive", "/srv/downloads"]


def test_recent_save_paths_clear_only_one_profile(tmp_path):
    store = RecentSavePaths(path=str(tmp_path / "recent.json"))
    store.remember("one", "/one")
    store.remember("two", "/two")

    store.clear("one")

    assert store.paths("one") == []
    assert store.paths("two") == ["/two"]
