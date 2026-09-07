# test_category_store.py -- taxonomy load/save, assign/unassign + pruning,
# diff, the auto-sync-from-seed reconciliation, and backup rotation.

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from _helpers import app  # noqa: F401

from s1iptv import category_store as cs
from s1iptv.category_store import CategoryStore, SNAPSHOT_KEY


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


class TestBasicMutation(unittest.TestCase):
    """assign/unassign/diff against an in-memory store, no seed involved."""

    def setUp(self):
        self.store = CategoryStore(path='<unused>')
        self.store.data = {'live': [], 'on_demand': []}

    def test_assign_creates_category_and_subcategory(self):
        self.store.assign('live', 'RAW A', 'Cat', 'Sub')
        self.assertEqual(self.store.find_assignment('live', 'RAW A'), ('Cat', 'Sub'))

    def test_assign_is_case_insensitive_for_existing_containers(self):
        self.store.assign('live', 'RAW A', 'Cat', 'Sub')
        self.store.assign('live', 'RAW B', 'cat', 'sub')  # different case, same containers
        cats = self.store.categories('live')
        self.assertEqual(len(cats), 1, "should reuse the existing category/subcategory, not duplicate")
        self.assertEqual(len(cats[0]['subcategories']), 1)

    def test_reassign_moves_without_duplicating(self):
        self.store.assign('live', 'RAW A', 'Cat1', 'Sub1')
        self.store.assign('live', 'RAW A', 'Cat2', 'Sub2')
        self.assertEqual(self.store.find_assignment('live', 'RAW A'), ('Cat2', 'Sub2'))
        # Cat1/Sub1 should have been pruned once empty
        names = [c['name'] for c in self.store.categories('live')]
        self.assertNotIn('Cat1', names)

    def test_unassign_prunes_empty_subcategory_and_category(self):
        self.store.assign('live', 'ONLY ONE', 'Solo Cat', 'Solo Sub')
        self.store.unassign('live', 'ONLY ONE')
        self.assertEqual(self.store.categories('live'), [])

    def test_unassign_leaves_sibling_subcategories_intact(self):
        self.store.assign('live', 'A', 'Cat', 'Sub1')
        self.store.assign('live', 'B', 'Cat', 'Sub2')
        self.store.unassign('live', 'A')
        cats = self.store.categories('live')
        self.assertEqual(len(cats), 1)
        sub_names = [s['name'] for s in cats[0]['subcategories']]
        self.assertEqual(sub_names, ['Sub2'])

    def test_diff_reports_unassigned_and_stale(self):
        self.store.assign('live', 'STILL THERE', 'Cat', 'Sub')
        self.store.assign('live', 'GONE NOW', 'Cat', 'Sub')
        diff = self.store.diff('live', ['STILL THERE', 'BRAND NEW'])
        self.assertEqual(diff['unassigned'], ['BRAND NEW'])
        self.assertEqual(diff['stale'], ['GONE NOW'])

    def test_diff_is_case_insensitive(self):
        self.store.assign('live', 'Some Raw', 'Cat', 'Sub')
        diff = self.store.diff('live', ['SOME RAW'])
        self.assertEqual(diff['unassigned'], [])
        self.assertEqual(diff['stale'], [])


class TestLoadSave(unittest.TestCase):
    def test_load_with_no_file_and_no_seed_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'taxonomy.json')
            with mock.patch.object(cs, 'SEED_PATH', os.path.join(tmp, 'nonexistent_seed.json')):
                store = CategoryStore(path=path).load()
            self.assertEqual(store.categories('live'), [])
            self.assertEqual(store.categories('on_demand'), [])

    def test_load_seeds_from_seed_file_on_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_path = os.path.join(tmp, 'seed.json')
            taxonomy_path = os.path.join(tmp, 'taxonomy.json')
            seed = {'live': [{'name': 'Cat', 'subcategories': [{'name': 'Sub', 'raw_categories': ['R']}]}],
                    'on_demand': []}
            write_json(seed_path, seed)
            with mock.patch.object(cs, 'SEED_PATH', seed_path):
                store = CategoryStore(path=taxonomy_path).load()
            self.assertEqual(store.find_assignment('live', 'R'), ('Cat', 'Sub'))
            # Snapshot should have been adopted for future diffing.
            self.assertIn(SNAPSHOT_KEY, store.data)

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'taxonomy.json')
            store = CategoryStore(path=path)
            store.data = {'live': [], 'on_demand': []}
            store.assign('live', 'R', 'Cat', 'Sub')
            store.save()

            with mock.patch.object(cs, 'SEED_PATH', os.path.join(tmp, 'nonexistent_seed.json')):
                reloaded = CategoryStore(path=path).load()
            self.assertEqual(reloaded.find_assignment('live', 'R'), ('Cat', 'Sub'))


class TestAutoSyncFromSeed(unittest.TestCase):
    """
    The reconciliation that fixes a real gap: editing the seed after
    taxonomy.json already exists used to do nothing until the file was
    deleted by hand. See docs/ROADMAP.md / category_store.py docstring.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.seed_path = os.path.join(self.tmp.name, 'seed.json')
        self.taxonomy_path = os.path.join(self.tmp.name, 'taxonomy.json')
        self.old_seed = {
            'live': [
                {'name': 'Sports', 'subcategories': [
                    {'name': 'PPV', 'raw_categories': ['PPV - EVENTS', 'PPV (BACKUP)']},
                ]},
            ],
            'on_demand': [],
        }

    def _write_working_file(self, seed_snapshot):
        working = json.loads(json.dumps(self.old_seed))  # deep copy
        working[SNAPSHOT_KEY] = seed_snapshot
        write_json(self.taxonomy_path, working)

    def test_untouched_item_follows_the_seed_move(self):
        self._write_working_file(self.old_seed)
        new_seed = json.loads(json.dumps(self.old_seed))
        new_seed['live'] = [{'name': 'PPV', 'subcategories': [
            {'name': 'General', 'raw_categories': ['PPV - EVENTS', 'PPV (BACKUP)']},
        ]}]
        write_json(self.seed_path, new_seed)

        with mock.patch.object(cs, 'SEED_PATH', self.seed_path):
            store = CategoryStore(path=self.taxonomy_path).load()

        self.assertEqual(store.find_assignment('live', 'PPV - EVENTS'), ('PPV', 'General'))
        names = [c['name'] for c in store.categories('live')]
        self.assertNotIn('Sports', names, "emptied-out Sports should have been pruned")
        self.assertEqual(len(store.last_sync_notes), 2)

    def test_user_reassigned_item_is_not_overridden(self):
        working = json.loads(json.dumps(self.old_seed))
        working[SNAPSHOT_KEY] = self.old_seed
        # User manually moved PPV - EVENTS to their own custom spot.
        working['live'][0]['subcategories'][0]['raw_categories'].remove('PPV - EVENTS')
        working['live'].append({'name': 'My Stuff', 'subcategories': [
            {'name': 'Custom', 'raw_categories': ['PPV - EVENTS']},
        ]})
        write_json(self.taxonomy_path, working)

        new_seed = json.loads(json.dumps(self.old_seed))
        new_seed['live'] = [{'name': 'PPV', 'subcategories': [
            {'name': 'General', 'raw_categories': ['PPV - EVENTS', 'PPV (BACKUP)']},
        ]}]
        write_json(self.seed_path, new_seed)

        with mock.patch.object(cs, 'SEED_PATH', self.seed_path):
            store = CategoryStore(path=self.taxonomy_path).load()

        # User's own placement wins...
        self.assertEqual(store.find_assignment('live', 'PPV - EVENTS'), ('My Stuff', 'Custom'))
        # ...but the untouched sibling still follows the seed.
        self.assertEqual(store.find_assignment('live', 'PPV (BACKUP)'), ('PPV', 'General'))

    def test_second_load_is_a_no_op(self):
        self._write_working_file(self.old_seed)
        new_seed = json.loads(json.dumps(self.old_seed))
        new_seed['live'] = [{'name': 'PPV', 'subcategories': [
            {'name': 'General', 'raw_categories': ['PPV - EVENTS', 'PPV (BACKUP)']},
        ]}]
        write_json(self.seed_path, new_seed)

        with mock.patch.object(cs, 'SEED_PATH', self.seed_path):
            CategoryStore(path=self.taxonomy_path).load()
            second = CategoryStore(path=self.taxonomy_path).load()

        self.assertEqual(second.last_sync_notes, [])
        ppv = [c for c in second.categories('live') if c['name'] == 'PPV']
        self.assertEqual(len(ppv), 1, "no duplication from re-syncing an already-synced file")

    def test_pre_existing_file_without_snapshot_adopts_baseline_untouched(self):
        write_json(self.taxonomy_path, json.loads(json.dumps(self.old_seed)))  # no SNAPSHOT_KEY at all
        write_json(self.seed_path, self.old_seed)

        with mock.patch.object(cs, 'SEED_PATH', self.seed_path):
            store = CategoryStore(path=self.taxonomy_path).load()

        self.assertEqual(store.last_sync_notes, [])
        self.assertIn(SNAPSHOT_KEY, store.data)
        # Data itself is unchanged.
        self.assertEqual(store.find_assignment('live', 'PPV - EVENTS'), ('Sports', 'PPV'))


class TestBackupRotation(unittest.TestCase):
    def test_save_backs_up_existing_file_and_prunes_old_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'taxonomy.json')
            backup_dir = os.path.join(tmp, 'backups')
            with mock.patch.object(cs, 'ROOT_DIR', tmp), mock.patch.object(cs, 'BACKUP_DIR', backup_dir), \
                 mock.patch.object(cs, 'MAX_BACKUPS', 3):
                store = CategoryStore(path=path)
                store.data = {'live': [], 'on_demand': []}
                store.save()  # file didn't exist yet -- no backup expected
                self.assertFalse(os.path.isdir(backup_dir))

                for i in range(5):
                    store.data['live'] = [{'name': f'Cat{i}', 'subcategories': []}]
                    store.save()

                backups = [f for f in os.listdir(backup_dir) if f.startswith('taxonomy_')]
                self.assertEqual(len(backups), 3, "should be pruned to MAX_BACKUPS")


if __name__ == '__main__':
    unittest.main()
