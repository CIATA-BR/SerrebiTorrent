# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Install community PO catalogs into the existing i18n runtime.

This module intentionally extends the current localization implementation
instead of replacing it. Existing in-code catalogs remain fallback data while
reviewed PO files can introduce additional languages without Python changes.
"""

from __future__ import annotations

import i18n
from translation_catalog import discover_catalogs


_ORIGINAL_NORMALIZE = i18n.normalize_language
_INSTALLED_CODES: tuple[str, ...] = ()


def _canonical_key(value: str | None) -> str:
    return str(value or "").strip().replace("_", "-").lower()


def _normalize_external(value: str | None) -> str:
    raw = _canonical_key(value)

    # Preserve all aliases and behavior already supported by the application.
    legacy = _ORIGINAL_NORMALIZE(value)
    if legacy != i18n.DEFAULT_LANGUAGE:
        return legacy
    if raw in {"en", "en-us", "en-gb"} or raw.startswith("en-") or raw.startswith("en."):
        return i18n.DEFAULT_LANGUAGE

    for code in _INSTALLED_CODES:
        canonical = _canonical_key(code)
        if raw == canonical or raw.startswith(canonical + ".") or raw.startswith(canonical + "@"):
            return code
        # A language-only system locale may select a regional catalog when it is
        # the only available catalog for that language.
        if "-" not in raw and canonical.split("-", 1)[0] == raw:
            matches = [candidate for candidate in _INSTALLED_CODES if _canonical_key(candidate).split("-", 1)[0] == raw]
            if len(matches) == 1:
                return matches[0]

    return i18n.DEFAULT_LANGUAGE


def install_external_catalogs() -> tuple[str, ...]:
    """Discover PO files and extend the shared runtime registries in-place."""
    global _INSTALLED_CODES

    discovered = discover_catalogs()
    external_codes: list[str] = []

    for code, info in discovered.items():
        if not code or code in {"system", i18n.DEFAULT_LANGUAGE}:
            continue
        # Reviewed PO data takes precedence over the temporary in-code catalog
        # for entries it contains, while missing entries keep the old fallback.
        existing = dict(i18n.CATALOGS.get(code, {}))
        existing.update(info.translations)
        i18n.CATALOGS[code] = existing
        external_codes.append(code)

    _INSTALLED_CODES = tuple(sorted(set(external_codes), key=str.casefold))

    supported = [i18n.DEFAULT_LANGUAGE]
    for code in i18n.CATALOGS:
        if code not in supported:
            supported.append(code)
    i18n.SUPPORTED_LANGUAGES = tuple(supported)

    base_options = [("system", "System"), (i18n.DEFAULT_LANGUAGE, "English")]
    seen = {value for value, _label in base_options}

    # Keep the established pt-BR native label even while it remains partly
    # backed by the in-code catalog.
    if "pt-BR" in i18n.CATALOGS:
        base_options.append(("pt-BR", "Português (Brasil)"))
        seen.add("pt-BR")

    for code in _INSTALLED_CODES:
        if code in seen:
            continue
        info = discovered[code]
        base_options.append((code, info.name or code))
        seen.add(code)

    i18n.LANGUAGE_OPTIONS = tuple(base_options)
    i18n.normalize_language = _normalize_external
    return _INSTALLED_CODES


def installed_external_languages() -> tuple[str, ...]:
    return _INSTALLED_CODES
