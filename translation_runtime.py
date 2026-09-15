# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Runtime overlay for external gettext-compatible SerrebiTorrent catalogs."""

from __future__ import annotations

from pathlib import Path
import os
import sys

import i18n
from translation_catalog import load_po

_INSTALLED = False
_SESSION_LANGUAGE: str | None = None
_SESSION_CATALOGS: dict[str, dict[str, str]] = {}
_CATALOGS: dict[str, dict[str, str]] = {}
_LANGUAGE_NAMES: dict[str, str] = {}


def _normalize_tag(value: str | None) -> str:
    raw = str(value or "").strip().replace("_", "-")
    if not raw:
        return "en"
    if raw.lower() == "system":
        return "system"
    parts = raw.split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return parts[0].lower() + "-" + parts[1].upper() + ("-" + "-".join(parts[2:]) if len(parts) > 2 else "")


def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _user_locale_root() -> Path:
    try:
        from app_paths import get_data_dir
        return Path(get_data_dir()) / "locales"
    except Exception:
        return Path.home() / ".serrebitorrent" / "locales"


def locale_roots() -> tuple[Path, ...]:
    return (_bundle_root() / "locales", _user_locale_root())


def _display_name(tag: str) -> str:
    known = {
        "en": "English",
        "pt-BR": "Português (Brasil)",
        "es": "Español",
        "es-ES": "Español (España)",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
    }
    return known.get(tag, tag)


def reload_catalogs() -> None:
    _CATALOGS.clear()
    _LANGUAGE_NAMES.clear()
    for root in locale_roots():
        if not root.exists():
            continue
        for path in sorted(root.glob("*.po")):
            tag = _normalize_tag(path.stem)
            entries = load_po(path)
            mapping = {key: entry.msgstr for key, entry in entries.items() if entry.translated}
            if mapping:
                _CATALOGS.setdefault(tag, {}).update(mapping)
                _LANGUAGE_NAMES[tag] = _display_name(tag)


def available_languages() -> list[tuple[str, str]]:
    values = {"en": "English", "pt-BR": "Português (Brasil)"}
    values.update(_LANGUAGE_NAMES)
    return sorted(values.items(), key=lambda pair: pair[1].casefold())


def install_session_catalog(language: str, mapping: dict[str, str]) -> None:
    tag = _normalize_tag(language)
    _SESSION_CATALOGS[tag] = dict(mapping)
    _LANGUAGE_NAMES[tag] = _display_name(tag)


def set_session_language(language: str | None) -> None:
    global _SESSION_LANGUAGE
    _SESSION_LANGUAGE = _normalize_tag(language) if language else None


def clear_session_language() -> None:
    global _SESSION_LANGUAGE
    _SESSION_LANGUAGE = None


def install_runtime_catalogs() -> None:
    """Patch i18n before UI modules import its callables."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    reload_catalogs()

    original_translate = i18n.translate
    original_system_language = i18n.system_language

    def normalize_language(value):
        tag = _normalize_tag(value)
        if tag == "system":
            return "system"
        if tag in {"en", "pt-BR"} or tag in _CATALOGS or tag in _SESSION_CATALOGS:
            return tag
        # Keep existing aliases such as Portuguese_Brazil.
        legacy = i18n._serrebi_original_normalize(value)  # type: ignore[attr-defined]
        if legacy != "en" or str(value or "").lower().startswith("en"):
            return legacy
        return tag if tag in _LANGUAGE_NAMES else "en"

    def resolved_language(language=None):
        if _SESSION_LANGUAGE:
            return _SESSION_LANGUAGE
        if language in (None, "", "system"):
            return _normalize_tag(original_system_language())
        return normalize_language(language)

    def translate(text, language=None):
        tag = resolved_language(language)
        if tag == "en":
            return text
        session = _SESSION_CATALOGS.get(tag, {})
        if text in session:
            return session[text]
        external = _CATALOGS.get(tag, {})
        if text in external:
            return external[text]
        return original_translate(text, tag if tag in {"pt-BR", "en"} else "en")

    def translator(language=None):
        return lambda text: translate(text, language)

    def language_options(language=None):
        tr = translator(language)
        options = [("system", tr("System"))]
        options.extend((tag, name) for tag, name in available_languages())
        return options

    i18n._serrebi_original_normalize = i18n.normalize_language  # type: ignore[attr-defined]
    i18n.normalize_language = normalize_language
    i18n.translate = translate
    i18n.translator = translator
    i18n.language_options = language_options
    i18n.SUPPORTED_LANGUAGES = tuple(tag for tag, _ in available_languages())


def user_catalog_path(language: str) -> Path:
    root = _user_locale_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{_normalize_tag(language)}.po"
