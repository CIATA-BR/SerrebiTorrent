
import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rss_manager import RSSManager

@pytest.fixture
def rss_manager():
    with patch('rss_manager.get_data_dir', return_value='.'):
        with patch('os.path.exists', return_value=False):
            manager = RSSManager()
            # Disable auto-saving during test setup if desired, or mock save
            manager.save = MagicMock()
            return manager

def test_downloaded_dedup(rss_manager):
    url = "http://feed.com/rss"
    rss_manager.add_feed(url)
    uid = "http://test.com/a.torrent"

    # Unknown uid is not yet downloaded
    assert rss_manager.is_downloaded(url, uid) is False
    # After marking, it is remembered (so the next poll skips it)
    rss_manager.mark_downloaded(url, uid)
    assert rss_manager.is_downloaded(url, uid) is True
    # Empty/None uids are ignored, not crashed on
    assert rss_manager.is_downloaded(url, "") is False
    rss_manager.mark_downloaded(url, None)
    # Unknown feed never reports downloaded
    assert rss_manager.is_downloaded("http://other/rss", uid) is False

def test_downloaded_list_is_bounded(rss_manager):
    url = "http://feed.com/rss"
    rss_manager.add_feed(url)
    for i in range(1200):
        rss_manager.mark_downloaded(url, f"uid-{i}")
    seen = rss_manager.feeds[url]['downloaded']
    assert len(seen) == 1000
    # Most recent retained, oldest evicted
    assert "uid-1199" in seen
    assert "uid-0" not in seen

def test_add_remove_feed(rss_manager):
    assert rss_manager.add_feed("http://test.com/rss", "Test Feed") is True
    assert "http://test.com/rss" in rss_manager.feeds
    assert rss_manager.feeds["http://test.com/rss"]['alias'] == "Test Feed"
    
    # Duplicate add
    assert rss_manager.add_feed("http://test.com/rss") is False
    
    rss_manager.remove_feed("http://test.com/rss")
    assert "http://test.com/rss" not in rss_manager.feeds

def test_add_rule(rss_manager):
    rss_manager.add_rule("test.*", "accept")
    assert len(rss_manager.rules) == 1
    assert rss_manager.rules[0]['pattern'] == "test.*"
    assert rss_manager.rules[0]['type'] == "accept"

def test_get_matches(rss_manager):
    rss_manager.add_rule("Linux", "accept")
    rss_manager.add_rule("Windows", "reject")
    
    articles = [
        {'title': 'Linux Distro ISO', 'link': 'link1'},
        {'title': 'Windows ISO', 'link': 'link2'},
        {'title': 'MacOS ISO', 'link': 'link3'}
    ]
    
    matches = rss_manager.get_matches(articles)
    assert len(matches) == 1
    assert matches[0]['title'] == 'Linux Distro ISO'

def test_get_matches_with_scope(rss_manager):
    rss_manager.add_rule("Common", "accept", scope=["feed1"])
    
    articles = [{'title': 'Common Thing', 'link': 'l'}]
    
    # Match for feed1
    assert len(rss_manager.get_matches(articles, feed_url="feed1")) == 1
    
    # No match for feed2 (rule not applicable)
    assert len(rss_manager.get_matches(articles, feed_url="feed2")) == 0

@patch('rss_manager._public_torrent_session')
def test_fetch_feed(mock_session_factory, rss_manager):
    rss_content = """
    <rss version="2.0">
    <channel>
        <item>
            <title>Test Torrent</title>
            <link>http://test.com/torrent.torrent</link>
        </item>
    </channel>
    </rss>
    """
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.iter_content = lambda chunk_size=8192: iter([rss_content.encode('utf-8')])
    mock_session_factory.return_value.__enter__.return_value = session
    session.get.return_value.__enter__.return_value = response

    url = "http://93.184.216.34/feed.xml"
    rss_manager.add_feed(url)
    articles = rss_manager.fetch_feed(url)

    assert len(articles) == 1
    assert articles[0]['title'] == "Test Torrent"
    assert articles[0]['link'] == "http://test.com/torrent.torrent"
    assert len(rss_manager.feeds[url]['articles']) == 1
    session.get.assert_called_once_with(
        url, timeout=10, stream=True, allow_redirects=False
    )


def test_fetch_feed_rejects_non_http_scheme(rss_manager):
    assert rss_manager.fetch_feed("file:///C:/secret.xml") == []


@patch('rss_manager._public_torrent_session')
def test_fetch_feed_rejects_private_network_target(mock_session_factory, rss_manager):
    url = "http://127.0.0.1/feed.xml"
    rss_manager.add_feed(url)

    assert rss_manager.fetch_feed(url) == []
    mock_session_factory.assert_not_called()


@patch('rss_manager._public_torrent_session')
def test_fetch_feed_rejects_redirect_to_private_network(mock_session_factory, rss_manager):
    session = MagicMock()
    response = MagicMock()
    response.status_code = 302
    response.headers = {'Location': 'http://127.0.0.1/private.xml'}
    mock_session_factory.return_value.__enter__.return_value = session
    session.get.return_value.__enter__.return_value = response

    url = "http://93.184.216.34/feed.xml"
    rss_manager.add_feed(url)

    assert rss_manager.fetch_feed(url) == []
    assert session.get.call_count == 1


def test_add_feed_rolls_back_when_save_fails(rss_manager):
    rss_manager.save.return_value = False

    assert rss_manager.add_feed("https://example.com/feed.xml", "Example") is False
    assert "https://example.com/feed.xml" not in rss_manager.feeds


def test_remove_feed_rolls_back_when_save_fails(rss_manager):
    url = "https://example.com/feed.xml"
    rss_manager.feeds = {
        url: {"alias": "Example", "last_update": 0, "articles": []}
    }
    rss_manager.save.return_value = False

    assert rss_manager.remove_feed(url) is False
    assert url in rss_manager.feeds


def test_add_rule_rolls_back_when_save_fails(rss_manager):
    rss_manager.rules = []
    rss_manager.save.return_value = False

    assert rss_manager.add_rule("ubuntu", "accept") is False
    assert rss_manager.rules == []


def test_update_rule_rolls_back_when_save_fails(rss_manager):
    rss_manager.rules = [
        {"pattern": "old", "enabled": True, "type": "accept", "scope": None}
    ]
    rss_manager.save.return_value = False

    assert rss_manager.update_rule(0, {"pattern": "new"}) is False
    assert rss_manager.rules[0]["pattern"] == "old"


def test_remove_rule_rolls_back_when_save_fails(rss_manager):
    rule = {"pattern": "ubuntu", "enabled": True, "type": "accept", "scope": None}
    rss_manager.rules = [rule.copy()]
    rss_manager.save.return_value = False

    assert rss_manager.remove_rule(0) is False
    assert rss_manager.rules == [rule]


def test_add_rule_preserves_disabled_state(rss_manager):
    rss_manager.save.return_value = True

    assert rss_manager.add_rule("ubuntu", "accept", enabled=False) is True
    assert rss_manager.rules[-1]["enabled"] is False


def test_flexget_import_rolls_back_when_rss_save_fails(rss_manager, tmp_path):
    config_path = tmp_path / "flexget.yml"
    config_path.write_text(
        """
tasks:
  example:
    qbittorrent:
      host: localhost
      port: 8080
      username: user
      password: secret
    rss: https://example.com/feed.xml
    regexp:
      accept:
        - Ubuntu
""",
        encoding="utf-8",
    )

    rss_manager.feeds = {}
    rss_manager.rules = []
    rss_manager.save.return_value = False

    mock_config = MagicMock()
    mock_config.get_profiles.return_value = {}
    mock_config.add_profile.return_value = "profile-1"

    with patch("config_manager.ConfigManager", return_value=mock_config):
        with pytest.raises(OSError):
            rss_manager.import_flexget_config(str(config_path))

    assert rss_manager.feeds == {}
    assert rss_manager.rules == []
    mock_config.delete_profile.assert_called_once_with("profile-1")


def test_flexget_import_avoids_duplicate_profiles_within_same_file(rss_manager, tmp_path):
    config_path = tmp_path / "flexget.yml"
    config_path.write_text(
        """
tasks:
  first:
    qbittorrent:
      host: localhost
      port: 8080
      username: user
      password: secret
  second:
    qbittorrent:
      host: localhost
      port: 8080
      username: user
      password: secret
""",
        encoding="utf-8",
    )

    rss_manager.save.return_value = True

    mock_config = MagicMock()
    mock_config.get_profiles.return_value = {}
    mock_config.add_profile.return_value = "profile-1"

    with patch("config_manager.ConfigManager", return_value=mock_config):
        rss_manager.import_flexget_config(str(config_path))

    assert mock_config.add_profile.call_count == 1



def test_reset_all_rolls_back_when_save_fails(rss_manager):
    rss_manager.feeds = {
        "https://example.com/feed.xml": {
            "alias": "Example",
            "last_update": 0,
            "articles": [],
        }
    }
    rss_manager.rules = [
        {"pattern": "ubuntu", "enabled": True, "type": "accept", "scope": None}
    ]
    before_feeds = rss_manager.feeds
    before_rules = rss_manager.rules
    rss_manager.save.return_value = False

    with pytest.raises(OSError, match="Failed to save reset RSS data"):
        rss_manager.reset_all()

    assert rss_manager.feeds is before_feeds
    assert rss_manager.rules is before_rules



@pytest.mark.parametrize(
    "url",
    [
        "file:///C:/secret.xml",
        "ftp://example.com/feed.xml",
        "https:///missing-host.xml",
        "not-a-url",
        "",
    ],
)
def test_add_feed_rejects_invalid_urls(rss_manager, url):
    rss_manager.save.return_value = True

    with pytest.raises(ValueError, match="RSS feed URL"):
        rss_manager.add_feed(url, "Invalid")

    assert rss_manager.feeds == {}
    rss_manager.save.assert_not_called()


def test_add_feed_normalizes_surrounding_whitespace(rss_manager):
    rss_manager.save.return_value = True

    assert rss_manager.add_feed("  https://example.com/feed.xml  ", "Example") is True

    assert "https://example.com/feed.xml" in rss_manager.feeds
