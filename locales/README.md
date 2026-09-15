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
- export to a standard `.po` file.

The application does not request or store GitHub credentials.

## Adding a language

A reviewed `locales/<language>.po` file is discovered automatically by the desktop runtime. Its language code and native name come from PO metadata, it appears in the normal language selector, and missing messages fall back to English. Existing in-code pt-BR strings remain a compatibility fallback while that catalog is migrated.

The release build bundles the complete `locales/` directory, so reviewed catalogs are available in frozen Windows, macOS and Linux packages as well as source runs.

For the Web UI, compile the same PO catalog to JSON. The compiler updates `web_static/locales/index.json`, which is what the Web language selector uses to discover community languages.

## Command-line maintenance

Generate the complete source POT template. The inventory scans desktop localization dictionaries/calls and the Web localization catalog:

```bash
python tools/translation_tool.py template
```

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
3. Regenerate the POT when source strings changed.
4. Keep the language code and native language name in PO metadata.
5. Run `compile-web` for the contributed language.
6. Open a pull request containing the catalog, generated Web JSON/index and intentional translation metadata changes only.
7. Reviewers check terminology, context, keyboard mnemonics and screen-reader wording before merge.

Translation pull requests should not include application credentials, Weblate tokens or unrelated code changes.

## Validation rules

A contribution fails validation when:

- a translated entry is empty;
- named Python format placeholders differ from the English source;
- an English source string contains a keyboard mnemonic marker (`&`) and the translation loses it.

Additional review is still required for accelerator collisions, terminology, grammar, punctuation and context.

## Weblate

The PO/POT layout is intentionally compatible with Weblate. A deployment can point Weblate at this repository and use pull-request based synchronization instead of granting direct write access to `main`.

When an online translation service is configured, set:

```text
SERREBITORRENT_TRANSLATION_URL=https://<translation-service>/<project>/
```

The Translation Center then enables **Open online translation**. No token or account secret is stored by SerrebiTorrent.

## Migration note

Brazilian Portuguese remains available through its tested in-code fallback while PO migration proceeds incrementally. Community PO catalogs can already add new desktop languages without Python changes, and the same PO source compiles to the Web runtime. This keeps migration reviewable instead of replacing the stable localization stack in one large refactor.
