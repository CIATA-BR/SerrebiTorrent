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
