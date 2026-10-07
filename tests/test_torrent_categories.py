from torrent_categories import TorrentCategoryStore


def test_assign_clear_and_count_categories(tmp_path):
    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))

    store.assign_many("profile-a", ["h1", "h2"], " Movies ")
    store.assign_many("profile-a", ["h3"], "Linux")

    assert store.get("profile-a", "h1") == "Movies"
    assert store.categories("profile-a") == ["Linux", "Movies"]
    assert store.counts("profile-a", ["h1", "h2", "h3", "other"]) == {
        "Movies": 2,
        "Linux": 1,
    }

    store.assign_many("profile-a", ["h2"], "")
    assert store.get("profile-a", "h2") == ""


def test_categories_are_profile_scoped(tmp_path):
    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))

    store.assign_many("one", ["hash"], "Work")
    store.assign_many("two", ["hash"], "Personal")

    assert store.get("one", "hash") == "Work"
    assert store.get("two", "hash") == "Personal"


def test_category_cleanup_collapses_whitespace_and_caps_length(tmp_path):
    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))

    store.assign_many("profile", ["hash"], "  A   very   spaced   category  ")

    assert store.get("profile", "hash") == "A very spaced category"
