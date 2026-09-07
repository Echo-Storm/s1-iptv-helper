# test_locals_data.py -- state parsing, the Locals selection store, and the
# "which subcategory is the special Locals one" helpers.

import os
import tempfile
import unittest

from _helpers import app  # noqa: F401

from s1iptv.category_store import CategoryStore
from s1iptv.locals_data import (
    parse_state, is_locals_subcategory, find_locals_raw_categories,
    find_locals_parent_category_name, LocalsSelectionStore, FALLBACK_DEFAULT_STATES,
)


class TestParseState(unittest.TestCase):
    def test_recognizes_a_valid_state_code(self):
        self.assertEqual(parse_state('IN | South Bend - Elkhart Area | CW - WCWW'), 'IN')

    def test_case_insensitive(self):
        self.assertEqual(parse_state('in | Indianapolis | ABC - WRTV'), 'IN')

    def test_no_pipe_still_checks_first_token(self):
        self.assertEqual(parse_state('AZ | KTVK 3TV Arizonas Family Phoenix'), 'AZ')

    def test_non_state_prefix_returns_none(self):
        self.assertIsNone(parse_state('LAT | Univision East HD'))
        self.assertIsNone(parse_state('US | A&E (East)'))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_state(''))


class TestIsLocalsSubcategory(unittest.TestCase):
    def test_matches_regardless_of_case(self):
        self.assertTrue(is_locals_subcategory('Locals'))
        self.assertTrue(is_locals_subcategory('LOCALS'))
        self.assertTrue(is_locals_subcategory('  locals  '))

    def test_does_not_match_other_names(self):
        self.assertFalse(is_locals_subcategory('General'))
        self.assertFalse(is_locals_subcategory('Local News'))  # substring, not exact


class TestFindLocalsHelpers(unittest.TestCase):
    def setUp(self):
        self.store = CategoryStore(path='<unused>')
        self.store.data = {
            'live': [
                {'name': 'USA LIVE', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['USA ENTERTAINMENT']},
                    {'name': 'Locals', 'raw_categories': ['USA ABC', 'USA CBS']},
                ]},
            ],
            'on_demand': [],
        }

    def test_find_locals_raw_categories(self):
        self.assertEqual(find_locals_raw_categories(self.store), ['USA ABC', 'USA CBS'])

    def test_find_locals_parent_category_name(self):
        self.assertEqual(find_locals_parent_category_name(self.store), 'USA LIVE')

    def test_no_locals_subcategory_returns_empty_and_none(self):
        store = CategoryStore(path='<unused>')
        store.data = {'live': [{'name': 'Cat', 'subcategories': [
            {'name': 'General', 'raw_categories': ['X']}
        ]}], 'on_demand': []}
        self.assertEqual(find_locals_raw_categories(store), [])
        self.assertIsNone(find_locals_parent_category_name(store))


class TestLocalsSelectionStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'locals_selection.json')

    def test_defaults_before_any_save(self):
        store = LocalsSelectionStore(path=self.path).load()
        self.assertEqual(store.default_states, set(FALLBACK_DEFAULT_STATES))
        self.assertEqual(store.selected_ids, set())
        self.assertTrue(store.merge_into_parent)

    def test_selection_and_default_states_round_trip(self):
        store = LocalsSelectionStore(path=self.path).load()
        store.set_selected(123, True)
        store.set_selected(456, True)
        store.set_selected(456, False)  # toggle back off
        store.set_default_states({'OH', 'KY'})

        reloaded = LocalsSelectionStore(path=self.path).load()
        self.assertEqual(reloaded.selected_ids, {123})
        self.assertEqual(reloaded.default_states, {'OH', 'KY'})

    def test_merge_into_parent_round_trips(self):
        store = LocalsSelectionStore(path=self.path).load()
        store.set_merge_into_parent(False)
        reloaded = LocalsSelectionStore(path=self.path).load()
        self.assertFalse(reloaded.merge_into_parent)


if __name__ == '__main__':
    unittest.main()
