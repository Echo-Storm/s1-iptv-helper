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

### GUI polish pass (2026-09-07)

- **Banner**: had a `role="banner"` property set but no matching QSS rule
  at all, so it had no background/border and just blended into the rest
  of the window. Now a fixed-height (64px) panel-colored bar with a
  bright accent top/bottom border, a larger bold title flanked by
  vertical `|` separator glyphs and thin accent lines running to the
  edges — matches the sibling apps' actual rendered header treatment
  (see `TorBox_Manager/tbm/ui.py`'s `_build_header()`).
- **Sidebar**: also had no background/border before this and blended into
  the window the same way. Now a distinct panel with a right border,
  plus icon glyphs on every action button (⟳ 💾 🔢 ↑) and a green
  left-border highlight on hover, matching the sibling apps' left-panel
  convention.
- **Donate button**: added a Ko-fi link (`donate ♥ ko-fi`) as a permanent
  widget in the status bar, same URL and treatment as Echo Audio
  Converter's own donate button (`https://ko-fi.com/xechostormx/tip`).
- **Fixed the spinbox arrows for real**: the previous session's QSpinBox
  fix (CSS border-triangle trick for `::up-arrow`/`::down-arrow`) turned
  out to render as a plain filled square in Qt's QSS engine, not a
  triangle — confirmed by rendering the actual window and zooming into
  the control, not just by reasoning about the CSS. Removing the custom
  arrow rule entirely made it render nothing at all (once any QSS touches
  a spin box, Qt stops falling back to its native arrow glyph too). Fixed
  properly with two tiny generated PNG triangles (`s1iptv/assets/spin_up.png`,
  `spin_down.png`) referenced via `image: url(...)` — the only reliable
  way to customize this particular subcontrol in Qt's stylesheet engine.
- Added `docs/screenshots/` (Live TV tab, Settings tab with credentials
  redacted) and a Screenshots section in `README.md`.
- Verification method for this whole pass: rendered the real `MainWindow`
  with the real theme applied (not the offscreen QPA platform, which has
  no usable fonts in this environment and renders all text as tofu boxes)
  and grabbed actual screenshots to check layout/spacing/colors, rather
  than just reading the QSS and assuming it would look right.

### Bugsweep + GitHub prep (2026-09-07)

Read every line of all 8 `s1iptv/*.py` modules (2700+ lines total) looking
for bugs before going public. Found one real, if currently dormant, one:

- `LocalsSelectionStore.save()` called bare `sorted()` on the set of
  selected stream IDs. Verified against a live fetch that this provider's
  `stream_id` is consistently `int` across every category checked, so
  this isn't firing today -- but Xtream panels are known to be
  inconsistent about quoting numeric fields between endpoints, and a
  mixed str/int set would raise `TypeError` the moment it happened.
  Changed to `sorted(..., key=str)`, which sorts identically for a
  uniform-type set and can't crash on a mixed one.
- Investigated `QLockFile.setStaleLockTime(0)` in `main.py` as a possible
  bug (worried it might disable stale-lock detection entirely, defeating
  the single-instance guarantee) -- checked Qt's actual source
  (`qlockfile.cpp`) rather than trusting memory of the API: `0` only
  disables the *timestamp* heuristic, the *process-liveness* check (is
  the PID that owns the lock still running) always still applies. This is
  correct as written, not a bug.

**Made the repo safe to make public**: grepped tracked files (and the
*entire* git history, via `git log --all --name-only`, not just the
current tree) for the real IPTV provider's domain and this account's
credentials. History was clean, but the domain was hardcoded in two
tracked files (`docs/PROVIDER_NOTES.md`, a docstring in
`xtream_client.py`) and, worse, baked into the checked-in
`config.example.json` template as its example server value. All three
now use a generic placeholder or no domain at all -- the point of a
`config.example.json` is to show the *shape*, not carry a real value
someone would copy-paste. Real domain/credentials only ever live in the
gitignored `config.json`.

Version bumped 0.6.0 -> 0.6.1. Pushed to GitHub as a public repo,
`s1-iptv-helper`.

README.md trimmed to public-facing content right after -- moved the
personal migration history ("Why this exists") and sibling-app branding
details out of the hero section; a Features list replaced the "Status"
progress-report framing.

### Packaging + first release (2026-09-07)

Added Windows exe packaging via PyInstaller, matching
`EchoAudioConverter.spec`'s onedir approach:
- `run_s1_iptv_helper.py` -- a thin entry point PyInstaller can execute
  directly. `s1iptv/main.py` itself can't be that entry point: it uses
  relative imports (`from .theme import ...`), which only resolve when the
  module is imported normally as part of the package, not when executed
  directly as `__main__` (true for both plain Python and PyInstaller's
  bootloader).
- `S1IptvHelper.spec` -- onedir build, bundles `data/taxonomy.seed.json`
  and the two spinbox arrow PNGs via explicit `datas` entries (PyInstaller
  can't discover non-Python files referenced only by a file path, not an
  import).
- **Found and fixed a real bug before it ever shipped**: every module that
  computed "the app's root directory" (`category_store.py`,
  `export.py`, `export_selection.py`, `locals_data.py`, `logger.py`,
  `xtream_client.py`) did it independently via
  `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`. That's
  correct from source, but in a frozen build `__file__` resolves inside
  PyInstaller's `_internal\` extraction folder, not next to the real
  `.exe` -- so personal data (`config.json`, `taxonomy.json`, the log,
  backups) would have been written into `_internal\` instead of sitting
  next to the exe where a user would look for it. Caught by actually
  building and running the exe, then checking where the files landed --
  not by reasoning about the code alone. Fixed with one shared
  `s1iptv/paths.py::app_root()` (checks `sys.frozen`/`sys.executable`),
  replacing all 6 independent copies -- matches Echo Audio Converter's own
  `core/paths.py`, which solves the identical problem the identical way.
  Verified end to end: built the exe, ran it, confirmed `taxonomy.json` /
  the log / `backups/` all landed next to `S1IptvHelper.exe`, not in
  `_internal\`.
- Also fixed `load_config()`'s "no config.json" error message, which told
  every reader to "copy config.example.json" -- true from source, useless
  advice for an exe-only user with no source checkout. Now points at the
  Settings tab first.
- README: added Download (points at the GitHub Releases page) and
  Building the EXE sections.

Version bumped 0.6.1 -> 0.7.0 -- first packaged release. Tagged and
published as a GitHub Release with `S1IptvHelper-v0.7.0-win64.zip`
attached. Repo topics added for discoverability.

## Later, can wait

(nothing currently)
