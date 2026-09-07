# test_export_selection.py -- which raw categories are checked for export,
# independent of the taxonomy structure.

import os
import tempfile
import unittest

from _helpers import app  # noqa: F401

from s1iptv.export_selection import ExportSelectionStore


class TestExportSelectionStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'export_selection.json')

    def test_everything_included_by_default(self):
        store = ExportSelectionStore(path=self.path).load()
        self.assertTrue(store.is_included('live', 'ANYTHING'))

    def test_exclude_then_include_round_trips(self):
        store = ExportSelectionStore(path=self.path).load()
        store.set_included('live', 'USA ABC', False)
        self.assertFalse(store.is_included('live', 'USA ABC'))
        store.set_included('live', 'USA ABC', True)
        self.assertTrue(store.is_included('live', 'USA ABC'))

    def test_matching_is_case_insensitive(self):
        store = ExportSelectionStore(path=self.path).load()
        store.set_included('live', 'USA ABC', False)
        self.assertFalse(store.is_included('live', 'usa abc'))
        store.set_included('live', 'usa abc', True)
        self.assertTrue(store.is_included('live', 'USA ABC'))

    def test_persists_across_reload(self):
        store = ExportSelectionStore(path=self.path).load()
        store.set_included('live', 'X', False)
        store.set_included('on_demand', 'Y', False)

        reloaded = ExportSelectionStore(path=self.path).load()
        self.assertFalse(reloaded.is_included('live', 'X'))
        self.assertFalse(reloaded.is_included('on_demand', 'Y'))
        self.assertTrue(reloaded.is_included('live', 'Y'), "content types shouldn't leak into each other")

    def test_missing_file_loads_as_everything_included(self):
        store = ExportSelectionStore(path=self.path).load()  # file doesn't exist
        self.assertTrue(store.is_included('live', 'ANYTHING'))
        self.assertTrue(store.is_included('on_demand', 'ANYTHING'))


if __name__ == '__main__':
    unittest.main()
