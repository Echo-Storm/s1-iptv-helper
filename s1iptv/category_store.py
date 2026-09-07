"""
Category -> subcategory taxonomy store.

Persists the curated grouping described in docs/CATEGORY_MODEL.md to
taxonomy.json (gitignored — personal working data). If that file doesn't
exist yet, it's seeded from the tracked data/taxonomy.seed.json so the app
doesn't launch to a completely empty tree.

Raw provider category name matching is case-insensitive throughout, same as
the old tool's CATEGORY_MERGES — the provider is inconsistent about casing.
"""

import json
import os
import shutil

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
SEED_PATH = os.path.join(APP_DIR, 'data', 'taxonomy.seed.json')
DEFAULT_TAXONOMY_PATH = os.path.join(ROOT_DIR, 'taxonomy.json')

CONTENT_TYPES = ('live', 'on_demand')


class DuplicateAssignmentError(ValueError):
    pass


def _empty_taxonomy():
    return {'live': [], 'on_demand': []}


class CategoryStore:
    def __init__(self, path=DEFAULT_TAXONOMY_PATH):
        self.path = path
        self.data = _empty_taxonomy()

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            if os.path.exists(SEED_PATH):
                shutil.copyfile(SEED_PATH, self.path)
            else:
                self.data = _empty_taxonomy()
                return self
        with open(self.path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        for ct in CONTENT_TYPES:
            self.data.setdefault(ct, [])
        return self

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def categories(self, content_type):
        return self.data.get(content_type, [])

    def find_assignment(self, content_type, raw_name):
        """Return (category_name, subcategory_name) or None."""
        target = raw_name.strip().upper()
        for cat in self.data.get(content_type, []):
            for sub in cat.get('subcategories', []):
                if target in (r.strip().upper() for r in sub.get('raw_categories', [])):
                    return cat['name'], sub['name']
        return None

    def assigned_raw_names(self, content_type):
        """Upper-cased set of every raw category name assigned anywhere."""
        names = set()
        for cat in self.data.get(content_type, []):
            for sub in cat.get('subcategories', []):
                names.update(r.strip().upper() for r in sub.get('raw_categories', []))
        return names

    def diff(self, content_type, fetched_raw_names):
        """
        Compare a fresh fetch of raw category names against the taxonomy.

        Returns {'unassigned': [...], 'stale': [...]} using the ORIGINAL
        casing from fetched_raw_names for 'unassigned', and from the stored
        taxonomy for 'stale'.
        """
        fetched_upper = {n.strip().upper(): n for n in fetched_raw_names}
        assigned_upper = self.assigned_raw_names(content_type)

        unassigned = [orig for upper, orig in fetched_upper.items() if upper not in assigned_upper]

        stale = []
        for cat in self.data.get(content_type, []):
            for sub in cat.get('subcategories', []):
                for raw in sub.get('raw_categories', []):
                    if raw.strip().upper() not in fetched_upper:
                        stale.append(raw)
        return {'unassigned': sorted(unassigned, key=str.upper), 'stale': sorted(stale, key=str.upper)}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def _get_or_create_category(self, content_type, category_name):
        for cat in self.data[content_type]:
            if cat['name'].strip().upper() == category_name.strip().upper():
                return cat
        cat = {'name': category_name, 'subcategories': []}
        self.data[content_type].append(cat)
        return cat

    def _get_or_create_subcategory(self, category, subcategory_name):
        for sub in category['subcategories']:
            if sub['name'].strip().upper() == subcategory_name.strip().upper():
                return sub
        sub = {'name': subcategory_name, 'raw_categories': []}
        category['subcategories'].append(sub)
        return sub

    def assign(self, content_type, raw_name, category_name, subcategory_name):
        """
        Assign raw_name to category_name/subcategory_name, creating either
        if they don't exist yet. Removes any prior assignment of the same
        raw_name first, so a raw category never ends up listed twice.
        """
        self.unassign(content_type, raw_name)
        cat = self._get_or_create_category(content_type, category_name)
        sub = self._get_or_create_subcategory(cat, subcategory_name)
        sub['raw_categories'].append(raw_name)

    def unassign(self, content_type, raw_name):
        target = raw_name.strip().upper()
        for cat in self.data.get(content_type, []):
            for sub in cat.get('subcategories', []):
                sub['raw_categories'] = [
                    r for r in sub.get('raw_categories', []) if r.strip().upper() != target
                ]

    def add_category(self, content_type, category_name):
        self._get_or_create_category(content_type, category_name)

    def add_subcategory(self, content_type, category_name, subcategory_name):
        cat = self._get_or_create_category(content_type, category_name)
        self._get_or_create_subcategory(cat, subcategory_name)
