"""
Local network affiliate channels: fetching, state parsing, and the
selection persistence used by the Locals tab.

Channel names for local affiliates follow "STATE | CITY | NETWORK - CALLSIGN"
(e.g. "IN | South Bend - Elkhart Area | CW - WCWW") -- this format has stayed
stable across provider category renames (see docs/PROVIDER_NOTES.md), so
state grouping is done by parsing the channel NAME, never the category name.
"""

import json
import os

from .paths import app_root

US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY', 'DC',
}

ALL_STATES = [
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
    ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
    ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
    ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
    ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
    ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
    ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
    ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
    ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'), ('WY', 'Wyoming'), ('DC', 'Washington DC'),
]

OTHER_BUCKET = 'OTHER'
# Fallback only -- used the first time the app runs, before the user has ever
# saved a preferred default via the Locals tab's "Set Defaults..." dialog.
# Not meant to be hardcoded/assumed correct for anyone but the original user;
# LocalsSelectionStore.default_states is the actual source of truth.
FALLBACK_DEFAULT_STATES = {'IN', 'MI'}

ROOT_DIR = app_root()
DEFAULT_SELECTION_PATH = os.path.join(ROOT_DIR, 'locals_selection.json')


def parse_state(channel_name):
    """Return the 2-letter state code from a channel name, or None."""
    first = channel_name.split('|', 1)[0].strip().upper()
    return first if first in US_STATE_CODES else None


# Name of the subcategory that triggers the individual-channel-selection
# special case (see export.py), AND the group-title used for it on export
# when not merged into its parent category. Coincidentally the same string
# for both purposes today -- every "is this the Locals subcategory?" check
# anywhere in the app must go through is_locals_subcategory() below rather
# than re-comparing against a literal, so the two purposes can't drift out
# of sync with each other if this ever needs to change.
LOCALS_OWN_CATEGORY_NAME = 'LOCALS'


def is_locals_subcategory(name):
    return name.strip().upper() == LOCALS_OWN_CATEGORY_NAME


def find_locals_raw_categories(store):
    """
    Raw provider category names tagged as locals in the taxonomy -- any
    subcategory literally named "Locals" under any Live category.
    """
    names = []
    for cat in store.categories('live'):
        for sub in cat.get('subcategories', []):
            if is_locals_subcategory(sub['name']):
                names.extend(sub.get('raw_categories', []))
    return names


def find_locals_parent_category_name(store):
    """The taxonomy category that currently contains the "Locals"
    subcategory (e.g. "USA LIVE"), or None if there isn't one yet."""
    for cat in store.categories('live'):
        for sub in cat.get('subcategories', []):
            if is_locals_subcategory(sub['name']):
                return cat['name']
    return None


def fetch_locals(client, raw_category_names):
    """
    Fetch every stream in the given raw live categories and group by state.

    Returns {state_code_or_'OTHER': [{'name', 'stream_id', 'category_name',
    'tvg_id', 'stream_icon'}, ...]}
    """
    live_cats = {c['category_name'].strip().upper(): c['category_id'] for c in client.get_live_categories()}
    grouped = {}
    for raw_name in raw_category_names:
        cat_id = live_cats.get(raw_name.strip().upper())
        if cat_id is None:
            continue
        for stream in client.get_live_streams(cat_id):
            name = stream.get('name', '').strip()
            state = parse_state(name) or OTHER_BUCKET
            grouped.setdefault(state, []).append({
                'name': name,
                'stream_id': stream.get('stream_id'),
                'category_name': raw_name,
                'tvg_id': stream.get('epg_channel_id', ''),
                'stream_icon': stream.get('stream_icon', ''),
            })
    return grouped


class LocalsSelectionStore:
    """Persists which stream_ids are selected for the M3U export, plus the
    user's preferred default state set for the "Defaults" quick-select."""

    def __init__(self, path=DEFAULT_SELECTION_PATH):
        self.path = path
        self.selected_ids = set()
        self.default_states = set(FALLBACK_DEFAULT_STATES)
        # True (default): exported Locals channels use their parent
        # taxonomy category's name as group-title (USA LIVE today) -- same
        # as every other category. False: exported Locals channels get
        # their own group-title (LOCALS_OWN_CATEGORY_NAME) regardless of
        # where "Locals" sits in the taxonomy.
        self.merge_into_parent = True

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.selected_ids = set(data.get('selected_stream_ids', []))
                if 'default_states' in data:
                    self.default_states = set(data['default_states'])
                self.merge_into_parent = data.get('merge_into_parent', True)
            except (json.JSONDecodeError, OSError):
                self.selected_ids = set()
        return self

    def save(self):
        # key=str: stream_id has always been int on this provider (verified
        # against a live fetch across categories), but Xtream panels are
        # known to be inconsistent about quoting numeric fields -- a bare
        # sorted() would raise TypeError the moment two different fetches
        # ever produced a str id and an int id in the same selected_ids set.
        # Sorting by str is stable and correct either way.
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({
                'selected_stream_ids': sorted(self.selected_ids, key=str),
                'default_states': sorted(self.default_states),
                'merge_into_parent': self.merge_into_parent,
            }, f, indent=2)

    def set_merge_into_parent(self, merge):
        self.merge_into_parent = merge
        self.save()

    def is_selected(self, stream_id):
        return stream_id in self.selected_ids

    def set_selected(self, stream_id, selected):
        if selected:
            self.selected_ids.add(stream_id)
        else:
            self.selected_ids.discard(stream_id)

    def set_default_states(self, states):
        self.default_states = set(states)
        self.save()
