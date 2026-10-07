from preferences_dialog import _language_index, _language_value


def test_language_index_finds_saved_preference():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_index(options, "pt-BR") == 2
    assert _language_index(options, "en") == 1


def test_language_index_falls_back_to_english_for_unknown_value():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_index(options, "es") == 1


def test_language_value_uses_stable_preference_value_not_display_label():
    options = [
        ("system", "Sistema"),
        ("en", "English"),
        ("pt-BR", "Português (Brasil)"),
    ]
    assert _language_value(options, 0) == "system"
    assert _language_value(options, 2) == "pt-BR"


def test_language_value_falls_back_to_system_for_invalid_selection():
    options = [("system", "Sistema"), ("en", "English")]
    assert _language_value(options, -1) == "system"
    assert _language_value(options, 99) == "system"



def test_main_preferences_save_has_ui_error_boundary():
    from pathlib import Path

    source = Path("app_entry.py").read_text(encoding="utf-8")
    start = source.index("    def on_prefs(self, event):")
    end = source.index("    def on_connect(self, event):", start)
    block = source[start:end]

    save = block.index("self.config_manager.set_preferences(prefs)")
    error_box = block.index("wx.MessageBox(", save)
    runtime_apply = block.index("session.apply_preferences(prefs)")

    assert "except Exception as exc" in block[save:error_box]
    assert error_box < runtime_apply
    assert 'self._("Failed to apply settings: {error}")' in block



def test_preferences_controls_have_explicit_accessible_names():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    for control in (
        "path_input", "watch_input", "move_completed_to_path", "pause_at_seed_ratio", "disk_space_reserve", "dl_limit", "ul_limit", "max_conn",
        "max_slots", "port_input", "announce_ip_input", "listen_interface_input",
        "track_url_input", "rss_interval", "web_host", "web_port", "web_user",
        "web_pass", "proxy_type", "proxy_host", "proxy_port", "proxy_user",
        "proxy_pass",
    ):
        assert f"self.{control}.SetName(" in source


def test_completion_announcement_preference_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Announce completed downloads to screen readers"' in source
    assert 'self.prefs.get("announce_download_complete", True)' in source
    assert '"announce_download_complete": self.announce_download_complete_chk.GetValue()' in source


def test_completion_system_notification_preference_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Show a system notification when downloads complete"' in source
    assert 'self.prefs.get("show_download_complete_notification", False)' in source
    assert '"show_download_complete_notification": self.show_download_complete_notification_chk.GetValue()' in source


def test_pause_on_completion_preference_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Pause torrents when downloads complete"' in source
    assert 'self.prefs.get("pause_on_download_complete", False)' in source
    assert '"pause_on_download_complete": self.pause_on_download_complete_chk.GetValue()' in source


def test_browse_buttons_have_contextual_accessible_names():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert 'browse_btn.SetName(self._("Browse default download path"))' in source
    assert 'watch_btn.SetName(self._("Browse watch folder"))' in source


def test_rss_reset_prefers_live_panel_manager():
    from pathlib import Path
    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert 'hasattr(parent, "rss_panel")' in source
    assert 'getattr(parent.rss_panel, "manager", None)' in source
    assert 'if manager is None:' in source


def test_app_entry_preferences_roll_back_when_runtime_apply_fails():
    from pathlib import Path
    source = Path("app_entry.py").read_text(encoding="utf-8")
    start = source.index("    def on_prefs(self, event):")
    end = source.index("    def on_connect(self, event):", start)
    block = source[start:end]

    assert "previous_prefs = self.config_manager.get_preferences()" in block
    assert "session.apply_preferences(prefs)" in block
    assert "self.config_manager.set_preferences(previous_prefs)" in block
    assert "session.apply_preferences(previous_prefs)" in block
    failure = block.index("except Exception as exc")
    assert "return" in block[failure:]


def test_disk_space_reserve_preference_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Minimum free space reserve (MiB, 0 disables protection):"' in source
    assert 'self.prefs.get("disk_space_reserve_mib", 0)' in source
    assert '"disk_space_reserve_mib": self.disk_space_reserve.GetValue()' in source
    assert "self.disk_space_reserve.SetName(disk_space_label)" in source


def test_completed_download_move_destination_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Move completed torrent data to (leave blank to disable; use a remote path for remote clients):"' in source
    assert 'self.prefs.get("move_completed_to_path", "")' in source
    assert '"move_completed_to_path": self.move_completed_to_path.GetValue().strip()' in source
    assert "self.move_completed_to_path.SetName(move_completed_label)" in source


def test_seed_ratio_pause_preference_is_exposed_and_saved():
    from pathlib import Path

    source = Path("preferences_dialog.py").read_text(encoding="utf-8")
    assert '"Pause seeding when ratio reaches (0 disables automation):"' in source
    assert 'self.prefs.get("pause_at_seed_ratio", 0.0)' in source
    assert '"pause_at_seed_ratio": self.pause_at_seed_ratio.GetValue()' in source
    assert "self.pause_at_seed_ratio.SetName(seed_ratio_label)" in source
