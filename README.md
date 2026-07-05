# SerrebiTorrent

A vibe-coded, keyboard-first, screen-reader-friendly torrent manager for Windows. Manage torrents locally with built-in libtorrent, or drive a remote client — qBittorrent, Transmission, or rTorrent — from the same interface.

[![Join SerrebiProjects on Telegram](https://img.shields.io/badge/Telegram-SerrebiProjects-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/SerrebiProjects)

**Have a question, hit a bug, or want early word on new releases?** Join the [SerrebiProjects Telegram group](https://t.me/SerrebiProjects) — the community hub for SerrebiTorrent and my other projects, and the fastest place to get help.

## Features

- Connects to local libtorrent, or a remote qBittorrent, Transmission, or rTorrent (SCGI/XML-RPC) client, all from one interface.
- Live download/upload speeds, progress, ratio, tracker host, and status messages for each torrent.
- Creates torrents.
- Responsive UI: remote operations run in the background so the app never freezes.
- Quick filters (All, Downloading, Complete, Active) plus a tracker tree in the sidebar.
- Full keyboard workflow and tray support, built and tested with NVDA.
- Built-in updater that verifies SHA-256 and Authenticode before applying an update, with automatic backup and rollback.

## Download and install

Grab the latest build from the [Releases page](https://github.com/serrebidev/SerrebiTorrent/releases). Latest: **v1.7.10**.

**Windows portable**

1. Download the latest ZIP.
2. Extract the entire `SerrebiTorrent` folder somewhere (example: `C:\Portable\SerrebiTorrent\`).
3. Run `SerrebiTorrent.exe` — don't move the EXE out of its folder.

Portable data (profiles, preferences, resume data, logs) lives next to the app in `SerrebiTorrent_Data\`. Updating in place keeps this data untouched.

## First-time setup

- Open Connection Manager: `Ctrl+Shift+C` (or tray icon -> Switch Profile -> Connection Manager...).
- Add a profile and connect:
  - **Local** — manages torrents via libtorrent on this PC (default profile on first run).
  - **Remote** — point at qBittorrent, Transmission, or rTorrent and enter credentials if needed.

## Settings

- Local session + app settings: Tools -> Local Session Settings... (`Ctrl+,`) (or tray icon -> Settings -> Local Session Settings...).
- Remote client settings (enabled only when connected): Tools -> qBittorrent/Transmission/rTorrent Remote Settings... (or tray icon -> Settings -> ...).

## Run from source (developers)

1. Install Python 3.14.
2. `git clone https://github.com/serrebidev/SerrebiTorrent`
3. `python -m pip install -r requirements.txt`
4. Ensure the Python 3.14 Windows `libtorrent` extension and its DLLs are installed or available on `PATH` — it isn't published on PyPI.
5. Launch it: `python main.py`

## Building

`build_exe.bat` drives the whole release pipeline: PyInstaller packaging, Authenticode signing, and GitHub release publishing.

Prereqs:
- Python 3.14 + dependencies from `requirements.txt`
- Git + GitHub CLI (`gh auth login` completed)
- Code signing cert installed
- SignTool available (default path used, or set `SIGNTOOL_PATH`)

Commands:
- `build_exe.bat build` — builds, signs, and zips locally.
- `build_exe.bat release` — auto-bumps version, builds, signs, zips, tags, pushes, creates the GitHub release, and uploads the update manifest.
- `build_exe.bat dry-run` — shows what it would do without modifying anything.

Versioning uses the latest `vMAJOR.MINOR.PATCH` tag as the base. If none exists, it starts at `v1.0.0`. Commits with `BREAKING CHANGE` or `!:` bump major; commits starting with `feat` (or containing `feature`) bump minor; otherwise it bumps patch.

Build output lands in `dist\SerrebiTorrent\`. For distribution, zip the entire `SerrebiTorrent` folder, not just the EXE.

## Auto-updater

The app checks GitHub Releases for updates. Enable or disable the startup check in Local Session Settings, or run Tools -> Check for Updates at any time.

Update flow:
1. Downloads the release ZIP using the update manifest asset (`SerrebiTorrent-update.json`).
2. Verifies the ZIP's SHA-256 against the manifest.
3. Verifies the Authenticode signature on the new `SerrebiTorrent.exe`.
4. Runs a hidden helper script that waits for the app to exit, backs up the current install to `<install_dir>_backup_<timestamp>`, swaps in the new files, and restarts the app.

Backup cleanup runs automatically:
- **Default** — keeps 1 backup (newest); cleanup starts after a 5-minute grace period.
- **Immediate** — set `SERREBITORRENT_KEEP_BACKUPS=0` to delete the backup right after a successful update.
- **Multiple** — set `SERREBITORRENT_KEEP_BACKUPS=N` to keep N most recent backups.

Other environment variables:
- `SERREBITORRENT_TRUSTED_SIGNING_THUMBPRINTS` — comma-separated list of trusted certificate thumbprints.

If an update fails, the backup is restored automatically. Check the updater log in `%TEMP%\SerrebiTorrent_update_*.log` if something goes wrong. The update process runs completely hidden — no console windows appear, and user data in `SerrebiTorrent_Data` is preserved throughout.

## Accessibility and shortcuts

Everything stays reachable by keyboard:

- `Ctrl+Shift+C` — Connection Manager
- `Ctrl+O` / `Ctrl+U` — Add torrent file / Add URL or magnet
- `Ctrl+S` / `Ctrl+P` — Start / Stop selected torrents
- `Delete` / `Shift+Delete` — Remove / Remove with data
- `Ctrl+A` — Select all
- `Ctrl+N` — Create a torrent
- `Tab` — Toggle focus between the sidebar and torrent list; double-clicking the tray icon restores the window.

Logs live under `SerrebiTorrent_Data\logs`, next to the EXE/script in portable mode (or in per-user app data in installed mode).

## Contributing

Pull requests are welcome. If SerrebiTorrent has been useful to you, open a PR with a fix or feature and I'll review it.

## Community and support

Report bugs and request features in [Issues](https://github.com/serrebidev/SerrebiTorrent/issues). For questions, feedback, and release news, join the [SerrebiProjects Telegram group](https://t.me/SerrebiProjects).
