# Provider notes — blueonesuperoceanhere.com (Xtream Codes)

Carried forward from the old tool's `M3U_MAKER_NOTES.md` (Kodi
`custom/IPTV` folder) and expanded. Read this before writing any code that
touches the provider's raw category names.

## Two content types, one account

The Xtream Codes API (`player_api.php`) and the compiled `get.php` m3u_plus
export both mix two fundamentally different kinds of content:

1. **Live TV** — regular channels, no `/movie/` or `/series/` in the stream
   URL. Organized by `group-title` in the m3u export, or equivalently by
   `get_live_categories` / `get_live_streams` in the JSON API.
2. **VOD (movies/series)** — stream URLs contain `/movie/` or `/series/`.
   Organized via `get_vod_categories` / `get_vod_streams` and
   `get_series_categories` / `get_series` / `get_series_info`.

The existing Kodi addon (`plugin.video.echoondemand`) already handles VOD
completely dynamically — it calls the API live every time it's opened and
never hardcodes a category name. **This app's job is not to replace that.**
Its job is the thing the addon does NOT do: impose a stable, curated
grouping (category → subcategory) on top of the provider's raw category
list, for BOTH live and VOD, so that:
- the live-TV M3U export (feeding Kodi's PVR IPTV Simple Client) has a
  sane, stable structure instead of ~190 flat raw categories, and
- the VOD side *could* eventually use the same curated grouping if the addon
  is ever updated to consume it (out of scope for now — see
  `docs/ROADMAP.md`).

## Why raw category names can't be trusted long-term

The provider renames and restructures its raw category list periodically,
without a changelog. Confirmed history:

- **2026-09-06**: full overhaul. Examples: `NFL` → `USA NFL GAMES`, `ABC` →
  `USA ABC`, `USA` → `USA ENTERTAINMENT`. ~40 brand-new country and
  international-sports categories appeared (e.g. `ARGENTINA`, `SKY SPORTS+
  EVENTS`, `TUDN / ViX / BEIN SPORT EVENTS`). The old tool's hardcoded
  `CATEGORY_MERGES` kept the *old* names, so every merge/default silently
  stopped matching anything and the tool would have produced an
  almost-empty playlist with no error message.

**Design implication**: any persisted taxonomy in this app must map raw
provider category names → curated group/subcategory, and must be re-checked
against a fresh fetch periodically. Don't assume a raw name fetched today
will exist next month. `category_store.py` should make "this raw category
disappeared" and "this raw category is new and unassigned" both cheap to
detect (diff current fetch against the last-known raw name list).

## What has stayed stable

Per-channel **local network affiliate** naming, at the individual channel
level (not the category level), has kept the same format for years:
```
STATE | CITY | NETWORK - CALLSIGN
```
e.g. `IN | South Bend - Elkhart Area | CW - WCWW`. State-based filtering
logic should key off this text pattern in the channel name/title, never off
the category name — that's what let the old tool's locals filter survive
the 2026-09-06 rename untouched while everything else broke.

## Content-type detection reference

From a full raw fetch on 2026-09-06 (189 categories, ~627k channel entries)
via `get.php?...&type=m3u_plus&output=ts`:

- Everything under recognizable VOD genre/brand names (Drama, Comedy,
  Netflix, Hulu, Amazon Prime Video, Disney+, HBO Max, Paramount+, Peacock,
  ABC/CBS/FOX/NBC/The CW/BBC/A&E as *bare* category names — note these are
  the VOD/series versions, distinct from the live `USA ABC`/`USA CBS`/etc.
  categories — History, HBO, Starz, Showtime, etc.) was 100% `/movie/` or
  `/series/` URLs.
- Everything under `USA *`, `CANADA *`, country names (AUSTRALIA, FRANCE,
  BRASIL, ITALY, ...), and sports/events categories (`USA NFL GAMES`, `PPV -
  EVENTS`, `UFC EVENTS`, etc.) was 100% live — no VOD mixed in.
- No category currently mixes live and VOD content. This was NOT always
  true historically (`COMBAT`/`RACING` used to mix VOD reruns into live
  categories under the old taxonomy) — don't assume it stays true forever;
  re-verify with a fresh fetch if something looks off. See the
  `xtream_client.py` module for a `classify_url()` helper that does this
  live/movie/series classification — use it rather than re-implementing the
  `/movie/`/`/series/` substring check ad hoc.

## Credentials

`https://blueonesuperoceanhere.com`, this account's username/password live
in `config.json` (gitignored — see `config.example.json` for the shape).
Do not hardcode them directly in any tracked `.py` file — that was the old
tool's approach and is exactly the anti-pattern this rebuild should fix.
