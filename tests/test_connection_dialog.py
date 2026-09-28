import i18n
from connection_dialog import profile_display_label


def test_profile_display_label_marks_default_in_pt_br():
    tr = i18n.translator("pt-BR")
    assert profile_display_label({"name": "Casa"}, is_default=True, translate=tr) == "Casa (Padrão)"


def test_profile_display_label_preserves_name_without_default_marker():
    tr = i18n.translator("pt-BR")
    assert profile_display_label({"name": "Servidor"}, is_default=False, translate=tr) == "Servidor"


def test_connection_dialog_strings_have_pt_br_translations():
    source_strings = (
        "Connection Manager",
        "Connection profiles",
        "Choose a profile, then connect or manage it with the buttons below.",
        "Add Profile",
        "Edit Profile",
        "Profile Name:",
        "Profile Name",
        "Client Type:",
        "Client Type",
        "URL (e.g. scgi://... or http://...):",
        "URL or download path",
        "Download Path:",
        "Choose Download Folder",
        "Delete this profile?",
        "Please select a profile to connect.",
        "Set Default",
        "Default",
    )
    for source in source_strings:
        assert i18n.translate(source, "pt-BR") != source



def test_connection_manager_wraps_profile_mutations_in_ui_error_boundary():
    from pathlib import Path

    source = Path("connection_dialog.py").read_text(encoding="utf-8")
    assert "def _run_config_change" in source
    assert "self.cm.add_profile(" in source
    assert "self.cm.update_profile(" in source
    assert "self.cm.delete_profile(pid)" in source
    assert "self.cm.set_default_profile_id(pid)" in source
    assert source.count("_run_config_change(") >= 5



def test_connection_manager_enter_connects_from_profile_list():
    from pathlib import Path

    source = Path("connection_dialog.py").read_text(encoding="utf-8")
    start = source.index("    def on_char_hook(self, event):")
    end = source.index("    def refresh_list", start)
    block = source[start:end]

    assert "WXK_RETURN" in block
    assert "WXK_NUMPAD_ENTER" in block
    assert "wx.Window.FindFocus() is self.list_box" in block
    assert "self.on_connect(event)" in block



def test_connection_dialogs_set_predictable_initial_focus():
    profile_source = inspect.getsource(connection_dialog.ProfileDialog.__init__)
    connect_source = inspect.getsource(connection_dialog.ConnectDialog.__init__)

    assert "self.name_input.SetFocus()" in profile_source
    assert "self.list_box.SetFocus()" in connect_source
