# Category model

What this app actually manages: a small, hand-curated tree that sits
*on top of* the provider's raw, unstable category list.

```
Live TV
├── USA LIVE
│   ├── General            <- raw: USA ENTERTAINMENT, USA KIDS, USA NEWS, ...
│   └── Locals              <- raw: USA ABC, USA CBS, USA FOX, USA NBC, USA THE CW, ...
├── Sports
│   ├── PPV                 <- raw: PPV - EVENTS, PPV (BACKUP)
│   ├── NFL                 <- raw: USA NFL GAMES, USA NFL TEAMS
│   ├── NBA / MLB / NHL / NCAAF / NCAAB / WNBA / MLS / RACING / COMBAT
│   └── International       <- raw: SKY SPORTS+ EVENTS, UK SPORTS, DAZN CANADA & UK, ...
├── Canada
│   └── ...                 <- raw: CANADA ENTERTAINMENT, CANADA LOCALS, CANADA FRENCH, CANADA SPORTS
└── International
    ├── Latin America        <- raw: MEXICO, ARGENTINA, PERU, COLOMBIA, ...
    ├── Europe                <- raw: FRANCE, ITALY, PORTUGAL, NETHERLANDS, ESPAÑA
    ├── UK                     <- raw: UK ENTERTAINMENT, UK SKY NETWORK
    └── Caribbean              <- raw: CARIBBEAN HUB, CUBA/MIAMI, PUERTO RICO, ...

On Demand
├── Streaming Services
│   ├── Netflix              <- raw: Netflix, Netflix Kids
│   ├── Hulu / Disney+ / HBO Max / Amazon Prime Video / Paramount+ / Peacock / ...
├── Genres
│   ├── Drama / Comedy / Action / Horror / Documentary / ...
└── International
    └── ...                  <- raw: KR: Korean TV Shows, IN: Indian Movies, ES: Series, ...
```

This is a first draft, seeded in `s1iptv/data/taxonomy.seed.json` from the
raw category dump gathered 2026-09-06 (see `docs/PROVIDER_NOTES.md`). It is
**not exhaustive** and is meant to be edited through the app, not by hand —
the seed file exists so the app doesn't launch to a totally empty tree.

## Data model

`category_store.py` persists the live taxonomy to `taxonomy.json`
(gitignored — it's the user's personal working curation, not shipped
project data; `taxonomy.seed.json` is the tracked starting point copied to
`taxonomy.json` on first run).

```json
{
  "live": [
    {
      "name": "Sports",
      "subcategories": [
        {"name": "NFL", "raw_categories": ["USA NFL GAMES", "USA NFL TEAMS"]}
      ]
    }
  ],
  "on_demand": [
    {
      "name": "Streaming Services",
      "subcategories": [
        {"name": "Netflix", "raw_categories": ["Netflix", "Netflix Kids"]}
      ]
    }
  ]
}
```

Rules:
- A raw category name should appear under at most one subcategory per
  content type (live/on_demand) — the store should warn, not silently
  duplicate, if the same raw name gets assigned twice.
- Matching a raw category name from a fresh API fetch against this file is
  **case-insensitive**, same as the old tool's `CATEGORY_MERGES` — the
  provider is inconsistent about casing between refreshes.
- A raw category present in a fresh fetch but absent from every
  `raw_categories` list anywhere in the file is "unassigned" — the UI's job
  is to surface these clearly (this is exactly the failure mode that made
  the old tool go silently wrong: a merge source that stopped matching
  nothing told anyone).
- A raw category listed in the taxonomy but absent from the latest fetch is
  "stale" — worth flagging too, but not an error; the provider may bring it
  back, or it may be gone for good.

## Why subcategories instead of a flat merge list

The old tool's `CATEGORY_MERGES` was flat: raw names → one target category
name. That's fine for "USA LIVE" but breaks down for something like Sports,
where you want both a single exportable group (all sports channels) *and*
the ability to browse/select at the league level (just NFL, just PPV). Two
levels (category → subcategory → raw names) covers both: export at the
category level, browse/toggle at the subcategory level.
