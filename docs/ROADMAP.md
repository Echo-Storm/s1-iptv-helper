# Roadmap

## Done

- Repo scaffold, gitignore, config template.
- Design system doc (`DESIGN_SYSTEM.md`) capturing the Echo/S1 house style
  from the two sibling apps. Tabs are filled boxed pills (obvious
  active/inactive state), not a thin underline.
- Provider notes (`PROVIDER_NOTES.md`) — live/VOD split, why raw category
  names can't be trusted, what stays stable.
- Category model doc + JSON schema (`CATEGORY_MODEL.md`).
- `xtream_client.py` — API client (live categories/streams, VOD
  categories/streams, series categories/series), URL classification
  (live/movie/series). `live_stream_url()` matches this provider's actual
  format (bare `{server}:443/{user}/{pass}/{stream_id}`, no `/live/`
  prefix, no extension — verified against a live fetch, don't "fix" this
  to match the generic Xtream convention without re-verifying first).
- `category_store.py` — taxonomy load/save, raw-category diffing
  (unassigned/stale detection), assign/unassign with automatic empty
  subcategory/category pruning. **Auto-syncs from a changed seed on every
  load**: if `data/taxonomy.seed.json` moves a raw category, the working
  `taxonomy.json` follows automatically, UNLESS the user already
  reassigned that raw category themselves (their placement always wins).
  Logged in-app per raw category moved, never silent.
- `theme.py` — Echo/S1 QSS.
- `main_window.py` / `main.py` — PyQt6 shell: banner, sidebar, tabs.
  Single-instance enforced via `QLockFile` (multiple copies writing the
  same JSON files concurrently could clobber each other). File logging to
  `S1_IPTV_Helper_Log.txt` (`logger.py`), matching the sibling apps.
- **Live TV / On Demand tabs**: checkable taxonomy tree (category,
  subcategory, raw-name level) with correct tri-state cascading, backed by
  `export_selection.py` (`export_selection.json`) tracking which raw
  categories are actually included in export — independent of the
  taxonomy structure (being organized into a subcategory isn't the same
  as being checked for export). Live "Will Export (N of M)" panel. Plus
  the original Unassigned/Stale triage panel with Assign flow.
- `settings_tab.py` — server/username/password editable in-app (Test
  Connection + Save), plus a "Default M3U path" field (auto-updated to
  whatever path was last used for a successful export).
- `locals_tab.py` / `locals_data.py` — per-channel picker for the ~1000
  state-affiliate channels, grouped by state parsed from the channel name
  (never the category name). States list with selected/total counts,
  flat checkable channel list, **user-configurable default states**
  ("Set Defaults..." dialog — no longer hardcoded IN/MI, that's just the
  first-run fallback), and a checkbox controlling whether Locals exports
  merged into its parent taxonomy category (default) or as its own
  standalone "LOCALS" category. Selections persist to
  `locals_selection.json`. The Live TV tab's "Will Export" preview shows
  Locals as a real per-state channel count via `LocalsTab.on_change`,
  not a misleading raw-category-name entry.
- `export.py` — **M3U export is live**: every checked raw category
  exports all its live streams under its top-level taxonomy category as
  group-title, except Locals raw categories (individual-channel selection
  only). EXTINF lines carry `tvg-id`/`tvg-name`/`tvg-logo` (verified
  byte-for-byte identical to the provider's own feed aside from the
  intentionally-curated group-title — an earlier version that dropped
  these was the likely cause of a real "channel list not loading right in
  Kodi" report). `count_channels()` / sidebar "Count Channels" button
  previews scale before committing to a full export.
- Seed taxonomy (`data/taxonomy.seed.json`), restructured 2026-09-06/07
  after real-world use: Music, PPV, and every individual
  sport/league (NFL/NBA/MLB/NHL/NCAAF/NCAAB/WNBA/MLS/Racing/Combat) are
  each their own top-level category rather than nested under one combined
  "Sports"; the old international-sports catch-all is its own "INTL
  SPORTS" category; UK consolidates entertainment + sports that used to
  be scattered across two other categories; Adult is its own category.
  General cable sports channels (`USA SPORTS`) live in `USA LIVE`, not a
  dedicated Sports category — there's no longer anything else to put in
  one. `US PARAMOUNT+` turned out to be live numbered soccer match feeds,
  not the streaming service — filed under `INTL SPORTS`, not `USA LIVE`.
- **Decided: On Demand does not need to feed back into
  `plugin.video.echoondemand`.** That addon is fully dynamic (queries the
  Xtream API live, builds its own menus, ignores this app entirely) and
  that's staying that way. The On Demand tab here is for this app's own
  visibility/organization only — it doesn't drive anything downstream.
  Practical effect: On Demand work is lower-priority than Live: keep its
  categories/taxonomy accurate and make sure nothing Live-side breaks it,
  but no export or deeper feature work is needed there.
- Search/filter box on the Live TV / On Demand taxonomy trees
  (`tree_filter_edit` / `_apply_tree_filter()`), matching the one already
  on the Locals tab.
- Backup rotation for `taxonomy.json` on save — `BACKUP_DIR` +
  `MAX_BACKUPS = 15` in `category_store.py`, oldest pruned first.
- Bulk/multi-select on the Assign flow (`_move_selected_tree_items()`) —
  move several selected raw categories to a new home in one action instead
  of one at a time.
- Real automated regression suite: 70 offscreen `unittest` tests across
  `tests/` (stdlib `unittest`, not pytest — matches TorBox_Manager's
  existing convention) covering the taxonomy store, export logic
  (including the blank-buffer trimming below), the Locals data layer, the
  category tree's tri-state cascading/filter/bulk-move, and the Xtream
  client's retry logic. Run with
  `venv\Scripts\python -m unittest discover -s tests -v`.
- Network resilience: `xtream_client.py`'s `_api_get()` retries transient
  failures (timeout, connection error, 5xx, unparseable response) up to
  `MAX_RETRIES = 3` times with exponential backoff before raising
  `NetworkError` with a plain-language message. A 4xx response fails
  immediately — retrying won't fix bad credentials.

### Blank event-slot trimming (2026-09-07)

Several provider categories — PPV backups, sport "EVENTS" feeds
(ESPN/Sky Sports/etc.) — reserve hundreds of numbered slots that only get
a real title once an event is actually scheduled on them; most sit blank
at any given time. A live check found 2,529 of 8,813 total taxonomy
channels (29%) were slots with nothing after the number, bloating the
exported M3U (and, per the report that started this, visibly slowing
Kodi's PVR load) for zero actual content.

`export.py`'s `_trim_blank_event_slots()` trims each raw category to its
last real (named) entry plus a configurable buffer of trailing blank
slots — the buffer means an event scheduled between now and the next
export already has a channel entry waiting for it, instead of only
appearing after a re-export. Verified against a live pull that real
(named) entries are always positioned as a contiguous block before every
blank one, never interspersed, across every category checked — so
trimming can never cut something that's actually airing. Configurable via
Settings tab → "Blank event-slot buffer" (default 20, range -1 to 500,
-1 disables trimming and exports every channel — the old behavior).

**Bug found and fixed after shipping the first version**: the
blank-detection regex only matched a single-word prefix before the number
(`ESPN 597:`), silently missing multi-word prefixes (`NFL Games 003:`).
This left `USA NFL GAMES` almost completely untrimmed — 198 of its 200
entries are the multi-word shape. Caught by explicitly re-checking NFL
after the feature shipped rather than assuming it worked; a full taxonomy
rescan found one other affected category (`INTL SPORTS` > `TENNIS
CHANNELS`, 5 entries). Fixed the regex to match any prefix, added
regression tests for exactly this gap (`tests/test_export.py`).

### Locals auto-load + Settings tab fixes (2026-09-07)

- `LocalsTab.refresh(silent=True)` now fires automatically from
  `MainWindow.__init__`, so the ~1000 local-affiliate channels are loaded
  on startup instead of needing a manual "Refresh Locals" click every
  session. `silent=True` swaps both popup dialogs (no "Locals"
  subcategory configured yet / fetch failed) for a status-label message
  and a log line instead, so a fresh install or a momentary network
  hiccup doesn't throw a dialog before the window is even shown. Manual
  clicks on the "Refresh Locals" button keep the original dialog
  behavior. Verified end-to-end against the real provider: 1,032 channels
  across 52 states load automatically with zero clicks.
- Fixed a `QSpinBox` stylesheet bug in `theme.py`: as soon as any QSS
  border/padding touches a `QAbstractSpinBox`, Qt needs the up/down
  sub-controls (`::up-button`/`::down-button`/arrows) styled explicitly,
  or their clickable hit-region collapses into the border/corner-radius
  — symptom was the new blank-buffer spinner's up arrow not responding to
  clicks. Added explicit sub-control rules matching the house theme.
- Moved the Settings tab's Save button to sit after the Export section
  fields instead of between Connection and Export — it previously read as
  "save the connection fields only," and a changed Export-section value
  (like the blank-buffer spinner) could silently fail to persist because
  it wasn't obvious the same button also covered it.

## Later, can wait

- Packaging: PyInstaller `.spec` + `launch.bat`-driven venv bootstrap,
  matching the sibling apps, once the feature set stabilizes.
- Decide on a remote (private GitHub repo) once the app is far enough
  along to be worth pushing — local-only on E: for now, single point of
  failure if that drive has a problem.
