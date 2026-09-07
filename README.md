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

## Status

Past the early-scaffold stage: full category taxonomy management, live M3U
export (with automatic blank-event-slot trimming), a per-channel Locals
picker that auto-loads on startup, in-app settings, and a 70-test automated
regression suite. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full
feature history and what's still planned.

## Screenshots

| Live TV | On Demand |
|---|---|
| ![Live TV tab](docs/screenshots/live-tv-tab.png) | ![On Demand tab](docs/screenshots/on-demand-tab.png) |

| Locals | Settings |
|---|---|
| ![Locals tab](docs/screenshots/locals-tab.png) | ![Settings tab](docs/screenshots/settings-tab.png) |

## Why this exists

The previous tool (`superplayerone_gui.py`, still live in the Kodi
`custom/IPTV` folder) hardcoded raw provider category names directly in
Python constants. Every time the provider restructured its categories (it
did a full overhaul on 2026-09-06), the tool silently broke — merges and
defaults stopped matching anything, producing a near-empty playlist with no
error. See [`docs/PROVIDER_NOTES.md`](docs/PROVIDER_NOTES.md) for the full
history and the live/VOD split that shapes this app's design.

## Setup

1. Install Python 3.10+.
2. Copy `config.example.json` to `config.json` and fill in your IPTV
   username/password (or just run `launch.bat` once — it does this for you
   and pauses so you can edit it).
3. Run `launch.bat`.

`config.json` is gitignored — it holds your account's plaintext credentials
and is never committed.

## Testing

```bash
venv\Scripts\python -m unittest discover -s tests -v
```

Offscreen PyQt6 `unittest` tests, no extra dependency — see
[`tests/README.md`](tests/README.md) for what's covered.

## Design language

This app follows the same dark/green "Echo/S1" house style as its sibling
desktop tools (Echo Audio Converter, TorBox Manager EchoStorm Edition):
PyQt6, near-black background, `#7cb342` green accent, Segoe UI. See
[`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) for the exact palette and
layout conventions pulled from those apps.

## Project layout

```
s1iptv/             application package
  main.py           entry point
  theme.py          shared QSS (Echo/S1 dark+green house style)
  assets/           small bundled images (spinbox arrow icons)
  xtream_client.py  Xtream Codes API client (live + VOD categories/streams)
  category_store.py category -> subcategory taxonomy model, JSON-backed
  main_window.py    main window / UI
docs/                design & maintenance documentation
  banner.svg         README banner -- hand-edit the "v0.6.1" text here
                     when bumping APP_VERSION in main_window.py; nothing
                     generates this automatically
  screenshots/       README screenshots
config.example.json  credential template (tracked)
config.json           real credentials (gitignored)
```
