"""
Category -> subcategory taxonomy store.

Persists the curated grouping described in docs/CATEGORY_MODEL.md to
taxonomy.json (gitignored — personal working data). If that file doesn't
exist yet, it's seeded from the tracked data/taxonomy.seed.json so the app
doesn't launch to a completely empty tree.

Raw provider category name matching is case-insensitive throughout, same as
the old tool's CATEGORY_MERGES — the provider is inconsistent about casing.

Once taxonomy.json exists, it's an independent copy -- editing the seed
afterwards (e.g. moving PPV out of Sports) does nothing to it on its own,
CategoryStore only copies the seed when there's no taxonomy.json yet. See
_sync_from_seed() below for the automatic 3-way reconciliation that fixes
this on every load: a raw category the seed has moved gets moved in the
working file too, UNLESS the user already moved it themselves, in which
case their placement wins.
"""

import datetime
import glob
import json
import os
import shutil

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
SEED_PATH = os.path.join(APP_DIR, 'data', 'taxonomy.seed.json')
DEFAULT_TAXONOMY_PATH = os.path.join(ROOT_DIR, 'taxonomy.json')
BACKUP_DIR = os.path.join(ROOT_DIR, 'backups')
MAX_BACKUPS = 15

CONTENT_TYPES = ('live', 'on_demand')
SNAPSHOT_KEY = '_seed_snapshot'


def _empty_taxonomy():
    return {'live': [], 'on_demand': []}


def _index_raw_categories(taxonomy_data, content_type):
    """{upper_raw_name: (category_name, subcategory_name)} for one content type."""
    index = {}
    for cat in taxonomy_data.get(content_type, []):
        for sub in cat.get('subcategories', []):
            for raw in sub.get('raw_categories', []):
                index[raw.strip().upper()] = (cat['name'], sub['name'])
    return index


class CategoryStore:
    def __init__(self, path=DEFAULT_TAXONOMY_PATH):
        self.path = path
        self.data = _empty_taxonomy()
        # Populated by _sync_from_seed() during load() -- one string per raw
        # category the seed moved and this file followed automatically.
        # Callers (MainWindow) can surface this in the log after loading.
        self.last_sync_notes = []

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------
    def load(self):
        freshly_seeded = False
        if not os.path.exists(self.path):
            if os.path.exists(SEED_PATH):
                shutil.copyfile(SEED_PATH, self.path)
                freshly_seeded = True
            else:
                self.data = _empty_taxonomy()
                return self
        with open(self.path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        for ct in CONTENT_TYPES:
            self.data.setdefault(ct, [])

        if freshly_seeded:
            # Just copied verbatim from the seed -- snapshot it as-is so a
            # later load() has a baseline to diff future seed edits against.
            self._save_seed_snapshot()
        else:
            self._sync_from_seed()
        return self

    def save(self):
        self._backup_before_overwrite()
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _backup_before_overwrite(self):
        """
        Snapshot whatever's currently on disk into backups/ before it gets
        overwritten -- taxonomy.json is hours of hand-curation with no undo,
        so this is cheap insurance against a bad edit or a sync gone wrong.
        Keeps the most recent MAX_BACKUPS copies, oldest pruned first.
        Silently skipped if there's nothing on disk yet, or if backing up
        fails for any reason (a permissions issue here shouldn't block the
        save itself).
        """
        if not os.path.exists(self.path):
            return
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            shutil.copyfile(self.path, os.path.join(BACKUP_DIR, f'taxonomy_{timestamp}.json'))
            backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'taxonomy_*.json')))
            for old in backups[:-MAX_BACKUPS]:
                os.remove(old)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Automatic reconciliation with a changed seed
    # ------------------------------------------------------------------
    def _save_seed_snapshot(self):
        try:
            with open(SEED_PATH, 'r', encoding='utf-8') as f:
                seed = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        self.data[SNAPSHOT_KEY] = seed
        self.save()

    def _sync_from_seed(self):
        """
        Compare the seed against the snapshot of it taken last time this
        file was synced. For any raw category the seed has since moved to a
        different category/subcategory, follow that move here too -- but
        only if the user's own placement for that raw category still
        matches where the OLD seed had it (i.e. they never manually moved
        it via Assign). A raw category the user *did* reassign keeps
        whatever the user chose, no matter what the seed does with it.

        No-ops entirely if there's no seed, no prior snapshot (an old
        taxonomy.json from before this existed), or the seed hasn't changed.
        """
        if not os.path.exists(SEED_PATH):
            return
        try:
            with open(SEED_PATH, 'r', encoding='utf-8') as f:
                new_seed = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        old_seed = self.data.get(SNAPSHOT_KEY)
        if old_seed is None or old_seed == new_seed:
            if old_seed is None:
                # Pre-existing taxonomy.json from before snapshotting existed --
                # adopt the current seed as the baseline so future edits can
                # be diffed, without changing any of the user's existing data.
                self._save_seed_snapshot()
            return

        self.last_sync_notes = []
        for ct in CONTENT_TYPES:
            old_index = _index_raw_categories(old_seed, ct)
            new_index = _index_raw_categories(new_seed, ct)
            user_index = _index_raw_categories(self.data, ct)

            for raw_upper, new_loc in new_index.items():
                old_loc = old_index.get(raw_upper)
                user_loc = user_index.get(raw_upper)
                if old_loc is not None and old_loc == user_loc and new_loc != old_loc:
                    # Untouched by the user since the last sync, and the
                    # seed moved it -- follow the seed.
                    original_raw_name = next(
                        (r for cat in self.data.get(ct, [])
                         for sub in cat.get('subcategories', [])
                         for r in sub.get('raw_categories', [])
                         if r.strip().upper() == raw_upper),
                        None,
                    )
                    if original_raw_name is not None:
                        self.unassign(ct, original_raw_name)
                        self.assign(ct, original_raw_name, new_loc[0], new_loc[1])
                        self.last_sync_notes.append(
                            f'{original_raw_name}: {old_loc[0]} → {old_loc[1]} '
                            f'moved to {new_loc[0]} → {new_loc[1]}'
                        )

        self.data[SNAPSHOT_KEY] = new_seed
        self.save()

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
        """
        Remove raw_name from wherever it's currently assigned. If that
        leaves its subcategory with no raw categories left, the subcategory
        is dropped too (and the category, if that empties it out) -- there's
        no supported way to create an intentionally-empty placeholder
        subcategory today (add_subcategory() is unused), so an empty one is
        always just unassign() leftovers, never something to preserve.
        """
        target = raw_name.strip().upper()
        for cat in self.data.get(content_type, []):
            for sub in cat.get('subcategories', []):
                sub['raw_categories'] = [
                    r for r in sub.get('raw_categories', []) if r.strip().upper() != target
                ]
            cat['subcategories'] = [s for s in cat['subcategories'] if s.get('raw_categories')]
        self.data[content_type] = [c for c in self.data.get(content_type, []) if c.get('subcategories')]

    def add_category(self, content_type, category_name):
        self._get_or_create_category(content_type, category_name)

    def add_subcategory(self, content_type, category_name, subcategory_name):
        cat = self._get_or_create_category(content_type, category_name)
        self._get_or_create_subcategory(cat, subcategory_name)
