# SerrebiTorrent translations

SerrebiTorrent uses gettext-compatible `.po` files so translations can be edited in the app, in a text editor, or by services such as Weblate.

## Contributing from the app

Open **Help > Contribute Translations...**.

1. Enter or select a BCP-47 language tag such as `es-ES`, `fr`, `de`, or `pt-BR`.
2. Filter by untranslated, needs review, translated, or all entries.
3. Edit the translation. The editor checks placeholders such as `{name}` and keyboard mnemonics (`&`) before saving.
4. Use **Test in this session** to preview the catalog without changing the saved application language.
5. Use **Export...** to create a `.po` file for a pull request or Weblate upload.

User-edited catalogs are stored in the SerrebiTorrent data directory under `locales/`. Packaged catalogs live in this repository under `locales/`. User catalogs override packaged messages for the same language.

## Command-line workflow

Generate or refresh the canonical template:

```bash
python tools/build_translation_catalog.py --template
```

Refresh an existing language while keeping its translations:

```bash
python tools/build_translation_catalog.py --refresh locales/es-ES.po
```

Generate browser JSON from a PO catalog:

```bash
python tools/build_translation_catalog.py --json locales/es-ES.po
```

The default JSON destination is `web_static/locales/<language>.json`.

## Translation rules

- Do not translate identifiers, API values, torrent names, hashes, URLs, or placeholders.
- Preserve every placeholder exactly, for example `{count}`, `{name}`, and `{error}`.
- If the English source contains `&`, preserve a keyboard mnemonic in the translation.
- Mark uncertain translations as **Needs review** instead of guessing.
- Keep terminology consistent across desktop and Web UI.

## Weblate

The files in this directory are intentionally standard gettext PO files. A Weblate project can point directly at `locales/*.po` and submit translation updates through pull requests. No GitHub token is stored by SerrebiTorrent itself.
