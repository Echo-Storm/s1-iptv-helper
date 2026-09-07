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
"""

import os

from .locals_data import (
    find_locals_raw_categories, fetch_locals, is_locals_subcategory, LOCALS_OWN_CATEGORY_NAME,
)

KODI_IPTV_DEFAULT_DIR = os.path.expandvars(r'%APPDATA%\Kodi\custom\IPTV')
_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def build_m3u(store, export_store, locals_store, client):
    """
    Returns (m3u_text, channel_count, locals_channel_count).
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
                    for stream in client.get_live_streams(cat_id):
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


def count_channels(store, export_store, locals_store, client):
    """Same result as build_m3u() minus the built text -- for a "how many
    channels would this export?" preview without writing anything to disk."""
    _, channel_count, locals_channel_count = build_m3u(store, export_store, locals_store, client)
    return channel_count, locals_channel_count
