# test_locals_tab.py -- LocalsTab.refresh()'s silent mode, used for the
# automatic fetch on app startup (see MainWindow.__init__). Covers only the
# "no Locals subcategory configured yet" path, which is the one guaranteed
# to fire with no network/credentials required -- the fetch-success/failure
# paths go through a real QThread hitting the network and aren't covered
# here (see LocalsFetchWorker; MainWindow wires it up with silent=True).

import os
import tempfile
import unittest
from unittest import mock

from PyQt6.QtWidgets import QMessageBox

from _helpers import app  # noqa: F401

from s1iptv.category_store import CategoryStore
from s1iptv.locals_data import LocalsSelectionStore
from s1iptv.locals_tab import LocalsTab


class TestRefreshSilentMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.store = CategoryStore(path=os.path.join(self.tmp.name, 'taxonomy.json'))
        # No subcategory named "Locals" anywhere -- this is the "not set up
        # yet" state find_locals_raw_categories() reports as empty.
        self.store.data = {
            'live': [
                {'name': 'USA LIVE', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['USA ENTERTAINMENT']},
                ]},
            ],
            'on_demand': [],
        }
        self.selection_store = LocalsSelectionStore(
            path=os.path.join(self.tmp.name, 'locals_selection.json')
        ).load()
        self.tab = LocalsTab(self.store, log_fn=lambda msg: None, selection_store=self.selection_store)

    def test_silent_refresh_skips_dialog_when_no_locals_subcategory(self):
        with mock.patch.object(QMessageBox, 'information') as mocked:
            self.tab.refresh(silent=True)
        mocked.assert_not_called()
        self.assertIn('taxonomy', self.tab.status_label.text().lower())

    def test_non_silent_refresh_shows_dialog_when_no_locals_subcategory(self):
        with mock.patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok) as mocked:
            self.tab.refresh(silent=False)
        mocked.assert_called_once()

    def test_default_refresh_is_not_silent(self):
        """refresh() with no argument must keep the pre-existing (manual
        button click) behavior -- only the explicit MainWindow startup call
        passes silent=True."""
        with mock.patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok) as mocked:
            self.tab.refresh()
        mocked.assert_called_once()


if __name__ == '__main__':
    unittest.main()
