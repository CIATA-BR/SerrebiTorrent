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



def test_rename_category_updates_all_hashes_in_one_profile(tmp_path):
    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))
    store.assign_many("one", ["a", "b", "hidden"], "Work")
    store.assign_many("one", ["other"], "Personal")
    store.assign_many("two", ["a"], "Work")

    assert store.rename_category("one", "Work", "Projects") == 3
    assert store.get("one", "hidden") == "Projects"
    assert store.categories("one") == ["Personal", "Projects"]
    assert store.get("two", "a") == "Work"
    assert TorrentCategoryStore(path=str(tmp_path / "categories.json")).get("one", "a") == "Projects"


def test_rename_rejects_name_collision_without_mutation(tmp_path):
    import pytest

    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))
    store.assign_many("profile", ["a"], "Movies")
    store.assign_many("profile", ["b"], "Other")
    with pytest.raises(ValueError, match="already exists"):
        store.rename_category("profile", "Movies", "other")
    assert store.get("profile", "a") == "Movies"
    assert store.get("profile", "b") == "Other"
    assert store.rename_category("profile", "Movies", "movies") == 1
    assert store.get("profile", "a") == "movies"


def test_delete_category_only_removes_matching_assignments(tmp_path):
    store = TorrentCategoryStore(path=str(tmp_path / "categories.json"))
    store.assign_many("one", ["a", "b"], "Old")
    store.assign_many("one", ["c"], "Keep")
    store.assign_many("two", ["a"], "Old")

    assert store.delete_category("one", "Old") == 2
    assert store.get("one", "a") == ""
    assert store.get("one", "c") == "Keep"
    assert store.get("two", "a") == "Old"
    assert store.delete_category("one", "Old") == 0
    assert store.rename_category("one", "Missing", "New") == 0
