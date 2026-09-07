# S1 IPTV Helper

**Version:** 0.6.0

A PyQt6 desktop tool for organizing the IPTV service's live-TV and on-demand
(movies/series) categories into a curated **category → subcategory**
structure, replacing the old tkinter-based `superplayerone_gui.py` M3U
filter.

This is *not* a per-channel picker. The goal is to group the provider's raw,
frequently-renamed category list (e.g. `USA NFL GAMES`, `UFC EVENTS`,
`Netflix`, `Hulu`) under stable umbrella categories with subcategories (e.g.
Live → **Sports** → PPV / NFL / NBA / ...; On Demand → **Streaming
Services** → Netflix / Hulu / ...), so the curation survives the provider
renaming things underneath it.

## Status

Past the early-scaffold stage: full category taxonomy management, live M3U
export (with automatic blank-event-slot trimming), a per-channel Locals
picker that auto-loads on startup, in-app settings, and a 70-test automated
regression suite. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full
feature history and what's still planned.

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

`config.json` is gitignored — it holds this account's plaintext credentials
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
  xtream_client.py  Xtream Codes API client (live + VOD categories/streams)
  category_store.py category -> subcategory taxonomy model, JSON-backed
  main_window.py    main window / UI
docs/                design & maintenance documentation
config.example.json  credential template (tracked)
config.json           real credentials (gitignored)
```
