# SerrebiTorrent translations

SerrebiTorrent keeps English source strings as the canonical fallback and uses GNU gettext PO files as the community contribution format.

## In-app Translation Center

Open **Help -> Contribute Translation...** in the localized desktop runtime.

The Translation Center is designed for keyboard and screen-reader use. It provides:

- language code and native language name fields;
- filters for all, untranslated, needs-review and translated entries;
- a normal report list (not a virtual list) for predictable screen-reader navigation;
- source and translation editors;
- placeholder and keyboard-mnemonic validation;
- progress feedback;
- local draft persistence under `SerrebiTorrent_Data/translations/`;
- export to a standard `.po` file;
- import of any `.po` file, so a catalog produced elsewhere can be completed without a portal account.

The application does not request or store GitHub credentials.

## Adding a language

A reviewed `locales/<language>.po` file is discovered automatically by the desktop runtime. Its language code and native name come from PO metadata, it appears in the normal language selector, and missing messages fall back to English. Existing in-code pt-BR strings remain a compatibility fallback while that catalog is migrated.

The release build bundles the complete `locales/` directory, so reviewed catalogs are available in frozen Windows, macOS and Linux packages as well as source runs.

The same reviewed PO catalog is also compiled to `web_static/locales/<language>.json` for the Web UI. This includes pt-BR, so the reviewed PO is authoritative for both desktop and Web strings; the older in-code pt-BR maps remain fallback only during migration.

## Command-line maintenance

Whenever user-facing source strings change, run the single synchronization command:

```bash
python tools/translation_tool.py sync
```

It regenerates `locales/serrebitorrent.pot`, validates every reviewed PO catalog, compiles the Web JSON catalogs and rebuilds the language index. CI runs `python tools/translation_tool.py check` on every pull request and fails when a developer adds or changes a translatable string without updating these generated artifacts.

The lower-level `template`, `validate`, `compile-web` and `compile-all-web` commands remain available for focused maintenance.

Validate a contribution:

```bash
python tools/translation_tool.py validate locales/es-ES.po
```

Compile one PO catalog for the Web UI and update the language index:

```bash
python tools/translation_tool.py compile-web locales/es-ES.po
```

Compile every reviewed PO catalog:

```bash
python tools/translation_tool.py compile-all-web
```

Generated Web files are written to `web_static/locales/<language>.json` and `web_static/locales/index.json` unless other paths are supplied.

## Pull-request review flow

1. Export or edit a `.po` file.
2. Run `python tools/translation_tool.py validate <catalog.po>`.
3. Run `python tools/translation_tool.py sync`.
4. Keep the language code and native language name in PO metadata.
5. Open a pull request containing the catalog and generated Web JSON/index.
6. CI runs `python tools/translation_tool.py check` and blocks stale POT/JSON artifacts.
7. Reviewers check terminology, context, keyboard mnemonics and screen-reader wording before merge.

Translation pull requests should not include application credentials, Weblate tokens or unrelated code changes.

## Validation rules

A contribution fails validation when:

- a translated entry is empty;
- named Python format placeholders differ from the English source;
- an English source string contains a keyboard mnemonic marker (`&`) and the translation loses it.

Additional review is still required for accelerator collisions, terminology, grammar, punctuation and context.

## CIATA translation portal

Community translations are managed at https://torrent.ciata.org.br/. The portal keeps English as the canonical source, validates placeholders and keyboard mnemonics, exports standard PO catalogs, and opens pull requests for reviewed language updates.

SerrebiTorrent stores no portal or GitHub credentials. The desktop **Open online translation** action opens the configured translation portal URL. The default is the CIATA portal and can be overridden with:

```text
SERREBITORRENT_TRANSLATION_URL=https://<translation-service>/
```

## Migration note

Brazilian Portuguese remains available through its tested in-code fallback while PO migration proceeds incrementally. Community PO catalogs can already add new desktop languages without Python changes, and the same PO source compiles to the Web runtime. This keeps migration reviewable instead of replacing the stable localization stack in one large refactor.
