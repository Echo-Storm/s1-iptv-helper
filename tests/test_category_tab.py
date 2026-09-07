# test_category_tab.py -- CategoryTab: tri-state checkbox cascading, the
# taxonomy tree filter, and bulk move/assign of raw categories.

import os
import tempfile
import unittest
from unittest import mock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from _helpers import app  # noqa: F401

from s1iptv.category_store import CategoryStore
from s1iptv.export_selection import ExportSelectionStore
from s1iptv.main_window import CategoryTab, RAW_NAME_ROLE


def find_leaf(item, raw_name):
    if item.data(0, RAW_NAME_ROLE) == raw_name:
        return item
    for i in range(item.childCount()):
        found = find_leaf(item.child(i), raw_name)
        if found:
            return found
    return None


def find_top_level(tree, name):
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.text(0) == name:
            return item
    return None


class CategoryTabTestBase(unittest.TestCase):
    """Shared setUp only -- has no test_* methods of its own, so unittest
    discovers it but silently finds zero tests to run in it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = CategoryStore(path=os.path.join(self.tmp.name, 'taxonomy.json'))
        self.store.data = {
            'live': [
                {'name': 'USA LIVE', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['USA ENTERTAINMENT', 'USA NEWS']},
                    {'name': 'Locals', 'raw_categories': ['USA ABC']},
                ]},
                {'name': 'NFL', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['USA NFL GAMES']},
                ]},
            ],
            'on_demand': [],
        }
        self.export_store = ExportSelectionStore(path=os.path.join(self.tmp.name, 'export_selection.json')).load()
        self.tab = CategoryTab('live', self.store, self.export_store, lambda msg: None)


class TestTriStateCascade(CategoryTabTestBase):
    def test_everything_checked_by_default(self):
        top = find_top_level(self.tab.tree, 'USA LIVE')
        self.assertEqual(top.checkState(0), Qt.CheckState.Checked)

    def test_unchecking_a_leaf_partially_checks_ancestors(self):
        leaf = find_leaf(self.tab.tree.topLevelItem(0), 'USA NEWS')
        leaf.setCheckState(0, Qt.CheckState.Unchecked)
        self.tab._on_tree_item_changed(leaf, 0)

        general = leaf.parent()
        usa_live = general.parent()
        self.assertEqual(general.checkState(0), Qt.CheckState.PartiallyChecked)
        self.assertEqual(usa_live.checkState(0), Qt.CheckState.PartiallyChecked)
        self.assertFalse(self.export_store.is_included('live', 'USA NEWS'))
        self.assertTrue(self.export_store.is_included('live', 'USA ENTERTAINMENT'))

    def test_unchecking_a_category_cascades_to_every_descendant(self):
        top = find_top_level(self.tab.tree, 'USA LIVE')
        top.setCheckState(0, Qt.CheckState.Unchecked)
        self.tab._on_tree_item_changed(top, 0)

        for raw in ('USA ENTERTAINMENT', 'USA NEWS', 'USA ABC'):
            self.assertFalse(self.export_store.is_included('live', raw))
        self.assertTrue(self.export_store.is_included('live', 'USA NFL GAMES'), "unrelated category untouched")

    def test_select_all_and_deselect_all(self):
        self.tab._set_all_checked(False)
        for raw in ('USA ENTERTAINMENT', 'USA NEWS', 'USA ABC', 'USA NFL GAMES'):
            self.assertFalse(self.export_store.is_included('live', raw))

        self.tab._set_all_checked(True)
        for raw in ('USA ENTERTAINMENT', 'USA NEWS', 'USA ABC', 'USA NFL GAMES'):
            self.assertTrue(self.export_store.is_included('live', raw))

    def test_will_export_preview_excludes_locals_raw_names(self):
        # USA ABC lives under a subcategory literally named "Locals" -- it
        # should never show up as a bare raw-category-name entry.
        preview_texts = [self.tab.export_preview_list.item(i).text()
                          for i in range(self.tab.export_preview_list.count())]
        self.assertNotIn('USA ABC', preview_texts)


class TestTreeFilter(CategoryTabTestBase):
    def test_filter_by_top_level_name_shows_whole_subtree(self):
        self.tab._apply_tree_filter('nfl')
        nfl = find_top_level(self.tab.tree, 'NFL')
        usa_live = find_top_level(self.tab.tree, 'USA LIVE')
        self.assertFalse(nfl.isHidden())
        self.assertTrue(usa_live.isHidden())

    def test_filter_by_deep_raw_name_keeps_ancestor_chain_visible(self):
        self.tab._apply_tree_filter('usa abc')
        usa_live = find_top_level(self.tab.tree, 'USA LIVE')
        self.assertFalse(usa_live.isHidden())

        general = next(usa_live.child(i) for i in range(usa_live.childCount()) if usa_live.child(i).text(0).startswith('General'))
        locals_sub = next(usa_live.child(i) for i in range(usa_live.childCount()) if usa_live.child(i).text(0).startswith('Locals'))
        self.assertTrue(general.isHidden(), "General has no match, should be hidden")
        self.assertFalse(locals_sub.isHidden())

        leaf = find_leaf(locals_sub, 'USA ABC')
        self.assertFalse(leaf.isHidden())

    def test_clearing_filter_shows_everything_again(self):
        self.tab._apply_tree_filter('nfl')
        self.tab._apply_tree_filter('')
        for name in ('USA LIVE', 'NFL'):
            self.assertFalse(find_top_level(self.tab.tree, name).isHidden())


class TestBulkMove(CategoryTabTestBase):
    def test_move_single_selected_leaf(self):
        leaf = find_leaf(self.tab.tree.topLevelItem(1), 'USA NFL GAMES')
        leaf.setSelected(True)
        self.tab.category_combo.setCurrentText('New Home')
        self.tab.subcategory_combo.setCurrentText('New Sub')
        self.tab._move_selected_tree_items()

        self.assertEqual(self.store.find_assignment('live', 'USA NFL GAMES'), ('New Home', 'New Sub'))
        names = [c['name'] for c in self.store.categories('live')]
        self.assertNotIn('NFL', names, "emptied-out source category should be pruned")

    def test_move_multiple_selected_leaves_at_once(self):
        leaf1 = find_leaf(self.tab.tree.topLevelItem(0), 'USA ENTERTAINMENT')
        leaf2 = find_leaf(self.tab.tree.topLevelItem(0), 'USA NEWS')
        leaf1.setSelected(True)
        leaf2.setSelected(True)
        self.tab.category_combo.setCurrentText('Bulk')
        self.tab.subcategory_combo.setCurrentText('Target')
        self.tab._move_selected_tree_items()

        self.assertEqual(self.store.find_assignment('live', 'USA ENTERTAINMENT'), ('Bulk', 'Target'))
        self.assertEqual(self.store.find_assignment('live', 'USA NEWS'), ('Bulk', 'Target'))

    def test_move_with_no_selection_does_not_raise(self):
        self.tab.category_combo.setCurrentText('Whatever')
        self.tab.subcategory_combo.setCurrentText('Whatever')
        # _move_selected_tree_items() shows a real QMessageBox.information()
        # when nothing's selected -- .exec() would block forever waiting for
        # a click that can never come under QT_QPA_PLATFORM=offscreen, so
        # this stands in for the user dismissing it (same pattern as
        # TorBox_Manager's tests/_helpers.py::always_yes).
        with mock.patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok):
            self.tab._move_selected_tree_items()
        self.assertIsNone(self.store.find_assignment('live', 'DOES NOT EXIST'))


if __name__ == '__main__':
    unittest.main()
