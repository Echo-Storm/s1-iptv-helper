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
- `theme.py` — Echo/S1 QSS matching the sibling apps. Tabs are filled boxed
  pills (obvious active/inactive state), not a thin underline.
- `main_window.py` / `main.py` — running PyQt6 shell: banner, sidebar,
  Live/On Demand tabs, each showing raw categories grouped by the current
  taxonomy plus an "Unassigned" bucket, with a way to assign a raw category
  to a category/subcategory.
- `settings_tab.py` — server/username/password editable in-app (Test
  Connection + Save), instead of hand-editing config.json.
- `locals_tab.py` / `locals_data.py` — per-channel picker for the ~1000
  state-affiliate channels (ABC/CBS/FOX/NBC/CW/PBS/independents/
  Univision/Telemundo), grouped by state parsed from the channel name
  (never the category name — see docs/PROVIDER_NOTES.md). States list with
  selected/total counts on the left, flat checkable channel list on the
  right, "Defaults (IN, MI)" bulk action carried over from the old tool.
  Selections persist to locals_selection.json (gitignored).
- Seed taxonomy (`data/taxonomy.seed.json`) covering the major buckets
  identified from the 2026-09-06 raw fetch; USA PBS lives under the Locals
  subcategory (same state-coded format as the other affiliates).

## Next

- **M3U export** — generate `superone.m3u8` from the curated Live taxonomy
  plus the Locals selection. Design decision (2026-09-06): the Locals
  selection should feed into the **USA LIVE** category by default, but the
  destination category must be a user-configurable setting, not hardcoded
  — e.g. a dropdown on the Locals tab (or Settings) picking which taxonomy
  category the selected local channels get exported under, defaulting to
  "USA LIVE" but allowing a separate "LOCALS" category (or any other
  existing category) instead. Every other Live category exports all of its
  raw categories' channels unfiltered; Locals is the one category whose
  export set is the individual-channel selection from locals_tab.py rather
  than "everything in these raw categories."
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
