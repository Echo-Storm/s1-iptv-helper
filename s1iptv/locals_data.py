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

US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY', 'DC',
}

OTHER_BUCKET = 'OTHER'
DEFAULT_SELECTED_STATES = {'IN', 'MI'}

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
DEFAULT_SELECTION_PATH = os.path.join(ROOT_DIR, 'locals_selection.json')


def parse_state(channel_name):
    """Return the 2-letter state code from a channel name, or None."""
    first = channel_name.split('|', 1)[0].strip().upper()
    return first if first in US_STATE_CODES else None


def find_locals_raw_categories(store):
    """
    Raw provider category names tagged as locals in the taxonomy -- any
    subcategory literally named "Locals" under any Live category.
    """
    names = []
    for cat in store.categories('live'):
        for sub in cat.get('subcategories', []):
            if sub['name'].strip().upper() == 'LOCALS':
                names.extend(sub.get('raw_categories', []))
    return names


def fetch_locals(client, raw_category_names):
    """
    Fetch every stream in the given raw live categories and group by state.

    Returns {state_code_or_'OTHER': [{'name', 'stream_id', 'category_name'}, ...]}
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
            })
    return grouped


class LocalsSelectionStore:
    """Persists which stream_ids are selected for the M3U export."""

    def __init__(self, path=DEFAULT_SELECTION_PATH):
        self.path = path
        self.selected_ids = set()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.selected_ids = set(data.get('selected_stream_ids', []))
            except (json.JSONDecodeError, OSError):
                self.selected_ids = set()
        return self

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({'selected_stream_ids': sorted(self.selected_ids)}, f, indent=2)

    def is_selected(self, stream_id):
        return stream_id in self.selected_ids

    def set_selected(self, stream_id, selected):
        if selected:
            self.selected_ids.add(stream_id)
        else:
            self.selected_ids.discard(stream_id)
