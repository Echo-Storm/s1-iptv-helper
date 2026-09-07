<p align="center">
  <img src="docs/banner.svg" alt="S1 IPTV Helper" width="100%">
</p>

A PyQt6 desktop tool for organizing an **Xtream Codes-compatible IPTV
service's** live-TV and on-demand (movies/series) categories into a curated
**category → subcategory** structure. Works with any Xtream Codes API
(`player_api.php`) provider — it doesn't target, endorse, or bundle access
to any specific service. Bring your own subscription's server/username/
password; this tool only organizes what that account's API already exposes.

This is *not* a per-channel picker for Live TV/On Demand. The goal is to
group the provider's raw, frequently-renamed category list (e.g. `USA NFL
GAMES`, `UFC EVENTS`, `Netflix`, `Hulu`) under stable umbrella categories
with subcategories (e.g. Live → **Sports** → PPV / NFL / NBA / ...; On
Demand → **Streaming Services** → Netflix / Hulu / ...), so the curation
survives the provider renaming things underneath it. The **Locals** tab is
the one place that *is* a per-channel picker, for state-affiliate channels
specifically.

## Features

- **Curated taxonomy that survives provider reshuffles** — raw categories
  map to stable category → subcategory groups, with an Unassigned/Stale
  panel that flags anything the provider renamed or removed on the next
  fetch instead of silently breaking.
- **Live M3U export** with automatic blank-event-slot trimming — many
  providers reserve hundreds of numbered placeholder slots per sport/PPV
  category that only get a real title once an event airs; this trims each
  category down to its real content plus a configurable buffer, instead of
  exporting hundreds of dead rows.
- **Locals tab** — a dedicated per-channel picker for state/local-affiliate
  channels (grouped automatically by state), separate from the
  category-level taxonomy. Auto-loads on startup.
- **In-app settings** — provider credentials, export path, and export
  behavior are all editable from the app; no manual JSON editing required
  day to day.
- **Automated test suite** — 70 tests covering the taxonomy store, export
  logic, and UI behavior.

## Screenshots

| Live TV | On Demand |
|---|---|
| ![Live TV tab](docs/screenshots/live-tv-tab.png) | ![On Demand tab](docs/screenshots/on-demand-tab.png) |

| Locals | Settings |
|---|---|
| ![Locals tab](docs/screenshots/locals-tab.png) | ![Settings tab](docs/screenshots/settings-tab.png) |

## Download

Prebuilt Windows binary: see the [Releases page](../../releases/latest) —
download `S1IptvHelper-vX.Y.Z-win64.zip`, extract it anywhere, and run
`S1IptvHelper.exe`. No Python install required. Enter your provider's
server/username/password in the Settings tab on first launch.

## Running from source

1. Install Python 3.10+.
2. Copy `config.example.json` to `config.json` and fill in your IPTV
   username/password (or just run `launch.bat` once — it does this for you
   and pauses so you can edit it).
3. Run `launch.bat`.

`config.json` is gitignored — it holds your account's plaintext credentials
and is never committed.

## Building the EXE

A standalone build (no Python install required to run it) via
[PyInstaller](https://pyinstaller.org/), configured in `S1IptvHelper.spec`:

```bash
venv\Scripts\pip install pyinstaller
venv\Scripts\pyinstaller S1IptvHelper.spec --clean
```

Output lands in `dist\S1IptvHelper\` — that whole folder is the
distributable (onedir build: `S1IptvHelper.exe` + a `_internal\` folder of
PyQt6/Python runtime files next to it). Zip the folder to hand it to
someone; there's nothing else to install. Personal data files
(`config.json`, `taxonomy.json`, the log, backups) are written next to the
`.exe`, not inside `_internal\` — see `s1iptv/paths.py`.

## Testing

```bash
venv\Scripts\python -m unittest discover -s tests -v
```

Offscreen PyQt6 `unittest` tests, no extra dependency — see
[`tests/README.md`](tests/README.md) for what's covered.

## Project layout

```
s1iptv/                  application package
  main.py                entry point
  paths.py               resolves personal-data paths (source vs. frozen exe)
  theme.py                shared QSS (dark/green theme)
  xtream_client.py        Xtream Codes API client (live + VOD categories/streams)
  category_store.py       category -> subcategory taxonomy model, JSON-backed
  main_window.py          main window / UI
run_s1_iptv_helper.py     PyInstaller entry point (see Building the EXE)
S1IptvHelper.spec         PyInstaller build config
docs/                     design & maintenance documentation
config.example.json       credential template (tracked)
config.json               real credentials (gitignored)
```
