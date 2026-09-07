"""
M3U export: build the live-TV playlist from the curated taxonomy plus the
Locals per-channel selection.

Every checked raw category exports all of its live streams under its
top-level taxonomy category as the group-title -- EXCEPT raw categories
inside a subcategory literally named "Locals", where only the individually
selected channels (from the Locals tab) are exported, still gated by that
raw category's own checkbox. See docs/CATEGORY_MODEL.md and
docs/ROADMAP.md for why Locals needs this special case.

The "destination category" for Locals (which top-level category it exports
under -- USA LIVE by default) is not a separate setting: it's just whatever
category currently contains the subcategory named "Locals" in the taxonomy.
Moving Locals to export under a different category means reassigning it
there via the normal Assign flow on the Live TV tab.
Blank event-slot trimming: several provider categories (PPV backups, sport
"EVENTS" feeds like ESPN/Sky Sports/etc.) are pre-provisioned with hundreds
of numbered slots -- "SKYEVENTS 001:", "ESPN 597:" -- that only get a real
title when an event is actually scheduled on them. Checked against a live
pull on 2026-09-07: 2,529 of 8,813 total channels (29%) were slots with
nothing after the number, and in every one of 99 categories sampled the
real (named) entries were always a contiguous run at the front with every
blank strictly after them -- never interspersed. So trimming to "last real
entry + a small buffer" removes the dead weight without any risk of
cutting a real, currently-scheduled event. See _trim_blank_event_slots().
"""

import os
import re

from .locals_data import (
    find_locals_raw_categories, fetch_locals, is_locals_subcategory, LOCALS_OWN_CATEGORY_NAME,
)
from .paths import app_root

KODI_IPTV_DEFAULT_DIR = os.path.expandvars(r'%APPDATA%\Kodi\custom\IPTV')
_APP_ROOT = app_root()

# Default number of trailing blank slots to keep past the last real event in
# a category, so an event scheduled between now and the next export already
# has a channel entry waiting for it instead of only appearing after a
# re-export. None disables trimming entirely (old behavior: export everything).
DEFAULT_BLANK_BUFFER = 20

# Matches a bare numbered placeholder slot with nothing after the number,
# e.g. "SKYEVENTS 001:", "ESPN 597:", "PPV2 300:", "NFL Games 003:" -- an
# optional prefix of any characters ending in whitespace (single-word like
# "ESPN" or multi-word like "NFL Games"), then digits, a colon, and nothing
# but whitespace to the end. A real event fills in text after the colon (or
# doesn't use this shape at all), so this never matches a populated channel.
#
# FIXED: the first version of this regex was `^\S+\s+\d+:\s*$` -- exactly
# one non-space token before the number -- which matched "ESPN 597:" fine
# but silently missed every multi-word prefix like "NFL Games 003:" (two
# words before the number). That left USA NFL GAMES almost entirely
# untrimmed: 198 of its 200 entries are blank slots in this shape, and the
# old regex saw 0 of them as blank. Caught by checking NFL specifically
# after the buffer feature shipped; a full taxonomy rescan found the same
# gap (smaller) in one other category (INTL SPORTS > TENNIS CHANNELS).
_BLANK_EVENT_SLOT_RE = re.compile(r'^(?:.+\s)?\d+:\s*$')


def _is_blank_event_slot(name):
    return bool(_BLANK_EVENT_SLOT_RE.match(name.strip()))


def _trim_blank_event_slots(streams, buffer_size):
    """
    Return streams with trailing blank numbered slots trimmed, keeping
    `buffer_size` of them past the last real (named) entry as headroom for
    events that get scheduled before the next export.

    buffer_size=None disables trimming -- returns streams unchanged. A
    category with zero real entries right now is trimmed to just the
    buffer (or to nothing if buffer_size is 0).
    """
    if buffer_size is None:
        return streams
    last_real = -1
    for i, stream in enumerate(streams):
        name = (stream.get('name') or '').strip()
        if name and not _is_blank_event_slot(name):
            last_real = i
    keep = last_real + 1 + buffer_size
    return streams if keep >= len(streams) else streams[:keep]


def default_export_path():
    """
    Best-guess default export destination: the Kodi custom/IPTV folder this
    app's predecessor (superplayerone_gui.py) already wrote superone.m3u8
    into, if that folder exists on this machine -- so Kodi's PVR IPTV Simple
    Client picks up the new export without any reconfiguration. Falls back
    to the repo root if that folder isn't present (e.g. a fresh machine).
    """
    if os.path.isdir(KODI_IPTV_DEFAULT_DIR):
        return os.path.join(KODI_IPTV_DEFAULT_DIR, 'superone.m3u8')
    return os.path.join(_APP_ROOT, 'superone.m3u8')


def _extinf_line(entry, group_title):
    """
    Matches the attribute set/order the provider's own feed uses (and that
    the old tool preserved verbatim): tvg-id, tvg-name, tvg-logo, group-title,
    then the display name after the comma. The old tool's export -- known to
    work in Kodi -- always had these; a version of this file that dropped
    tvg-id/tvg-logo (group-title + name only) did NOT work correctly in
    Kodi's PVR IPTV Simple Client. Don't strip these back out.
    """
    name = entry['name']
    tvg_id = entry.get('tvg_id', '')
    tvg_logo = entry.get('tvg_logo', '')
    return (
        f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" tvg-logo="{tvg_logo}" '
        f'group-title="{group_title}",{name}'
    )


def build_m3u(store, export_store, locals_store, client, blank_buffer=DEFAULT_BLANK_BUFFER):
    """
    Returns (m3u_text, channel_count, locals_channel_count).

    blank_buffer controls trimming of blank numbered event slots (see the
    module docstring) -- None exports every channel a raw category has,
    matching the tool's original behavior.
    """
    live_cats_by_name = {
        c['category_name'].strip().upper(): c['category_id']
        for c in client.get_live_categories()
    }

    locals_raw_names = find_locals_raw_categories(store)
    locals_included = any(export_store.is_included('live', r) for r in locals_raw_names)
    locals_by_raw_category = {}
    locals_channel_count = 0
    if locals_included:
        grouped = fetch_locals(client, locals_raw_names)
        for channels in grouped.values():
            for ch in channels:
                if locals_store.is_selected(ch['stream_id']):
                    locals_by_raw_category.setdefault(ch['category_name'].strip().upper(), []).append(ch)
                    locals_channel_count += 1

    locals_group_title = (
        None if locals_store.merge_into_parent else LOCALS_OWN_CATEGORY_NAME
    )

    lines = ['#EXTM3U']
    channel_count = 0
    standalone_locals_entries = []  # entries that use locals_group_title, only when not merging

    for cat in store.categories('live'):
        cat_entries = []  # entries that use this category's own name
        for sub in cat.get('subcategories', []):
            is_locals = is_locals_subcategory(sub['name'])
            for raw in sub.get('raw_categories', []):
                if not export_store.is_included('live', raw):
                    continue
                if is_locals:
                    channels = locals_by_raw_category.get(raw.strip().upper(), [])
                    entries = [
                        {'name': ch['name'], 'stream_id': ch['stream_id'],
                         'tvg_id': ch.get('tvg_id', ''), 'tvg_logo': ch.get('stream_icon', '')}
                        for ch in channels
                    ]
                    if locals_group_title is None:
                        cat_entries.extend(entries)
                    else:
                        standalone_locals_entries.extend(entries)
                else:
                    cat_id = live_cats_by_name.get(raw.strip().upper())
                    if cat_id is None:
                        continue
                    streams = _trim_blank_event_slots(
                        client.get_live_streams(cat_id), blank_buffer
                    )
                    for stream in streams:
                        name = stream.get('name', '').strip()
                        if name:
                            cat_entries.append({
                                'name': name,
                                'stream_id': stream.get('stream_id'),
                                'tvg_id': stream.get('epg_channel_id', ''),
                                'tvg_logo': stream.get('stream_icon', ''),
                            })

        for entry in cat_entries:
            url = client.live_stream_url(entry['stream_id'])
            lines.append(_extinf_line(entry, cat['name']))
            lines.append(url)
            channel_count += 1

    for entry in standalone_locals_entries:
        url = client.live_stream_url(entry['stream_id'])
        lines.append(_extinf_line(entry, locals_group_title))
        lines.append(url)
        channel_count += 1

    return '\n'.join(lines) + '\n', channel_count, locals_channel_count


def count_channels(store, export_store, locals_store, client, blank_buffer=DEFAULT_BLANK_BUFFER):
    """Same result as build_m3u() minus the built text -- for a "how many
    channels would this export?" preview without writing anything to disk."""
    _, channel_count, locals_channel_count = build_m3u(
        store, export_store, locals_store, client, blank_buffer=blank_buffer
    )
    return channel_count, locals_channel_count
