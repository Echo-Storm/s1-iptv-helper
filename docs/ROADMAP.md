# Roadmap

## Done

- Repo scaffold, gitignore, config template.
- Design system doc (`DESIGN_SYSTEM.md`) capturing the Echo/S1 house style
  from the two sibling apps.
- Provider notes (`PROVIDER_NOTES.md`) — live/VOD split, why raw category
  names can't be trusted, what stays stable.
- Category model doc + JSON schema (`CATEGORY_MODEL.md`).
- `xtream_client.py` — API client (live categories/streams, VOD
  categories/streams, series categories/series), URL classification
  (live/movie/series).
- `category_store.py` — taxonomy load/save, raw-category diffing
  (unassigned / stale detection).
- `theme.py` — Echo/S1 QSS matching the sibling apps.
- `main_window.py` / `main.py` — running PyQt6 shell: banner, sidebar,
  Live/On Demand tabs, each showing raw categories grouped by the current
  taxonomy plus an "Unassigned" bucket, with a way to assign a raw category
  to a category/subcategory.
- Seed taxonomy (`data/taxonomy.seed.json`) covering the major buckets
  identified from the 2026-09-06 raw fetch.

## Next

- M3U export: generate `superone.m3u8` from the curated Live taxonomy
  (port the per-channel local-affiliate state filter from the old tool
  unchanged — that logic never broke and doesn't need reinventing).
- Persist per-subcategory "included states" for locals (today the old tool
  has one global state selector; the new model could set it per-subcategory
  if that turns out to matter).
- Drag-and-drop or multi-select "assign to subcategory" instead of one
  raw-category-at-a-time.
- Decide whether On Demand curation ever needs to feed back into
  `plugin.video.echoondemand` (today that addon is fully dynamic and
  intentionally not driven by this app) — only worth doing if flat
  alphabetical VOD category lists become a real usability problem in Kodi.
- Packaging: PyInstaller `.spec` + `launch.bat`-driven venv bootstrap,
  matching the sibling apps, once the feature set stabilizes.
- Decide on a remote (private GitHub repo) once the app is far enough along
  to be worth pushing — local-only for now.
