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

## Command-line maintenance

Generate the source POT template:

```bash
python tools/translation_tool.py template
```

Validate a contribution:

```bash
python tools/translation_tool.py validate locales/es-ES.po
```

Compile a PO catalog for the Web UI:

```bash
python tools/translation_tool.py compile-web locales/es-ES.po
```

The generated Web file is written to `web_static/locales/<language>.json` unless another output path is supplied.

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

The existing Brazilian Portuguese dictionaries remain a runtime fallback while the catalogs are migrated incrementally. This avoids a large translation refactor in the same change that introduces contributor tooling. New PO catalogs can be reviewed and compiled independently while the runtime migration proceeds in small, tested steps.
