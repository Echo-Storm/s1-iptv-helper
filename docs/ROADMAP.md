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

## Next (in progress, 2026-09-07)

1. ~~Catch this doc up to actual state~~ (this edit).
2. Search/filter box on the Live TV / On Demand taxonomy trees, matching
   the one already on the Locals tab — 18 top-level live categories deep
   now, hunting by eye doesn't scale.
3. Backup rotation for `taxonomy.json` on save (keep last N copies) — it's
   hand-curated with no undo today; cheap insurance against a bad edit.
4. Bulk/multi-select on the Assign flow — today it's one raw category at
   a time from Unassigned, fine for occasional triage, painful for a
   large batch (e.g. On Demand's 82 categories after a provider reshuffle).
5. Promote the ad hoc verification scripts written throughout this
   project's sessions (export logic, auto-sync, tri-state cascading,
   locals grouping) into a real pytest suite, so regressions get caught
   automatically instead of needing another one-off script each time.
6. Network resilience: `xtream_client.py` has no retry/backoff, and a
   flaky connection mid-fetch currently surfaces a raw traceback in a
   message box. Add basic retry-with-backoff and translate common
   failures (timeout, connection error, bad JSON/auth response) into
   plain-language messages.

## Later, can wait

- Packaging: PyInstaller `.spec` + `launch.bat`-driven venv bootstrap,
  matching the sibling apps, once the feature set stabilizes.
- Decide on a remote (private GitHub repo) once the app is far enough
  along to be worth pushing — local-only on E: for now, single point of
  failure if that drive has a problem.
