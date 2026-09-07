"""
Export selection: which raw categories are actually included in the M3U
export, independent of the taxonomy structure itself. A raw category being
assigned to a category/subcategory just means it's organized -- this store
tracks the separate on/off decision for export.

Default is "everything included" (an empty exclusion set) so a freshly
assigned raw category starts checked, matching what a user expects when
they haven't excluded anything yet.
"""

import json
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
DEFAULT_PATH = os.path.join(ROOT_DIR, 'export_selection.json')

CONTENT_TYPES = ('live', 'on_demand')


class ExportSelectionStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.excluded = {ct: set() for ct in CONTENT_TYPES}

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for ct in CONTENT_TYPES:
                    self.excluded[ct] = set(data.get(ct, {}).get('excluded_raw', []))
            except (json.JSONDecodeError, OSError):
                pass
        return self

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(
                {ct: {'excluded_raw': sorted(self.excluded[ct])} for ct in CONTENT_TYPES},
                f, indent=2, ensure_ascii=False,
            )

    def is_included(self, content_type, raw_name):
        target = raw_name.strip().upper()
        return target not in {x.strip().upper() for x in self.excluded[content_type]}

    def set_included(self, content_type, raw_name, included):
        excluded = self.excluded[content_type]
        target = raw_name.strip().upper()
        if included:
            self.excluded[content_type] = {x for x in excluded if x.strip().upper() != target}
        elif target not in {x.strip().upper() for x in excluded}:
            excluded.add(raw_name)
        self.save()

    def included_raw_names(self, content_type, all_raw_names):
        """Given every raw category name currently in the taxonomy for this
        content type, return just the ones not excluded."""
        return [n for n in all_raw_names if self.is_included(content_type, n)]
