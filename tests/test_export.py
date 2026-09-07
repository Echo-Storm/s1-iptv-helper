# test_export.py -- M3U building: group-title routing, the Locals special
# case (merged vs standalone), EXTINF attribute fidelity, and count_channels.

import os
import tempfile
import unittest
from unittest import mock

from _helpers import app, FakeXtreamClient, make_stream  # noqa: F401

from s1iptv import export as export_module
from s1iptv.category_store import CategoryStore
from s1iptv.export_selection import ExportSelectionStore
from s1iptv.locals_data import LocalsSelectionStore


class TestBuildM3u(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.store = CategoryStore(path=os.path.join(self.tmp.name, 'taxonomy.json'))
        self.store.data = {
            'live': [
                {'name': 'USA LIVE', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['USA ENTERTAINMENT']},
                    {'name': 'Locals', 'raw_categories': ['USA ABC']},
                ]},
            ],
            'on_demand': [],
        }
        self.export_store = ExportSelectionStore(path=os.path.join(self.tmp.name, 'export_selection.json')).load()
        self.locals_store = LocalsSelectionStore(path=os.path.join(self.tmp.name, 'locals_selection.json')).load()

        self.client = FakeXtreamClient(
            live_categories=[
                {'category_name': 'USA ENTERTAINMENT', 'category_id': '1'},
                {'category_name': 'USA ABC', 'category_id': '2'},
            ],
            live_streams_by_cat_id={
                '1': [make_stream('US | A&E (East)', 999, tvg_id='ae.us', stream_icon='https://x/ae.png')],
                '2': [make_stream('IN | INDIANAPOLIS | ABC - WRTV', 5001, tvg_id='wrtv.us')],
            },
        )

    def test_normal_category_exports_under_top_level_group_title(self):
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertIn('group-title="USA LIVE",US | A&E (East)', content)
        self.assertIn('tvg-id="ae.us"', content)
        self.assertIn('tvg-name="US | A&E (East)"', content)
        self.assertIn('tvg-logo="https://x/ae.png"', content)
        self.assertIn('https://fake.test:443/u/p/999', content)

    def test_locals_channel_excluded_unless_individually_selected(self):
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertNotIn('WRTV', content, "not selected in the Locals tab, must not export")
        self.assertEqual(locals_count, 0)

    def test_locals_channel_included_once_selected(self):
        self.locals_store.set_selected(5001, True)
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertIn('WRTV', content)
        self.assertIn('group-title="USA LIVE"', content)  # merged into parent by default
        self.assertEqual(locals_count, 1)

    def test_locals_standalone_category_when_not_merged(self):
        self.locals_store.set_selected(5001, True)
        self.locals_store.merge_into_parent = False
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertIn('group-title="LOCALS",IN | INDIANAPOLIS | ABC - WRTV', content)

    def test_excluded_raw_category_is_skipped_entirely(self):
        self.export_store.set_included('live', 'USA ENTERTAINMENT', False)
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertNotIn('A&E', content)

    def test_count_channels_matches_build_m3u(self):
        self.locals_store.set_selected(5001, True)
        content, count, locals_count = export_module.build_m3u(
            self.store, self.export_store, self.locals_store, self.client
        )
        count2, locals_count2 = export_module.count_channels(
            self.store, self.export_store, self.locals_store, self.client
        )
        self.assertEqual((count, locals_count), (count2, locals_count2))


class TestBlankEventSlotTrimming(unittest.TestCase):
    def test_is_blank_event_slot_matches_numbered_placeholder(self):
        self.assertTrue(export_module._is_blank_event_slot('SKYEVENTS 001:'))
        self.assertTrue(export_module._is_blank_event_slot('ESPN 597:'))
        self.assertTrue(export_module._is_blank_event_slot('PPV2 300:  '))

    def test_is_blank_event_slot_matches_multi_word_prefix(self):
        # Regression test: a prior version of the regex only allowed exactly
        # one word before the number (\S+), which matched "ESPN 597:" fine
        # but missed "NFL Games 003:" (two words) entirely -- that left the
        # real USA NFL GAMES category (198 of 200 entries are this shape)
        # almost completely untrimmed regardless of buffer size.
        self.assertTrue(export_module._is_blank_event_slot('NFL Games 003:'))
        self.assertTrue(export_module._is_blank_event_slot('NFL Games 200:'))
        self.assertTrue(export_module._is_blank_event_slot('003:'))  # bare, no prefix at all

    def test_is_blank_event_slot_does_not_match_real_channel_or_event(self):
        self.assertFalse(export_module._is_blank_event_slot('US | A&E (East)'))
        self.assertFalse(export_module._is_blank_event_slot(
            'ESPN 001: Soccer: Groningen vs. Twente (2026-09-06 06:10:00)'
        ))
        self.assertFalse(export_module._is_blank_event_slot('IN | INDIANAPOLIS | ABC - WRTV'))
        self.assertFalse(export_module._is_blank_event_slot(
            'NFL Games 002: 6PM Chicago Bears vs Tennessee Titans'
        ))
        self.assertFalse(export_module._is_blank_event_slot('NFL | Chicago Bears'))
        self.assertFalse(export_module._is_blank_event_slot('NFL Network'))

    def test_trim_keeps_real_entries_plus_buffer(self):
        streams = (
            [make_stream(f'ESPN {i:03d}: Real Event {i}', i) for i in range(1, 4)]
            + [make_stream(f'ESPN {i:03d}:', i) for i in range(4, 21)]
        )
        trimmed = export_module._trim_blank_event_slots(streams, buffer_size=5)
        # 3 real entries (indices 0-2) + 5 buffer = keep through index 7 (8 entries)
        self.assertEqual(len(trimmed), 8)
        self.assertEqual(trimmed[-1]['name'], 'ESPN 008:')

    def test_trim_buffer_none_disables_trimming(self):
        streams = [make_stream(f'ESPN {i:03d}:', i) for i in range(1, 21)]
        trimmed = export_module._trim_blank_event_slots(streams, buffer_size=None)
        self.assertEqual(len(trimmed), 20)

    def test_trim_never_grows_past_original_length(self):
        streams = [make_stream('Real Channel', 1)]
        trimmed = export_module._trim_blank_event_slots(streams, buffer_size=500)
        self.assertEqual(len(trimmed), 1)

    def test_trim_all_blank_category_with_zero_buffer_empties_it(self):
        streams = [make_stream(f'NHL {i:03d}:', i) for i in range(1, 61)]
        trimmed = export_module._trim_blank_event_slots(streams, buffer_size=0)
        self.assertEqual(trimmed, [])

    def test_build_m3u_applies_blank_buffer_to_live_categories(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = CategoryStore(path=os.path.join(tmp.name, 'taxonomy.json'))
        store.data = {
            'live': [
                {'name': 'INTL SPORTS', 'subcategories': [
                    {'name': 'General', 'raw_categories': ['SKY SPORTS+ EVENTS']},
                ]},
            ],
            'on_demand': [],
        }
        export_store = ExportSelectionStore(path=os.path.join(tmp.name, 'export_selection.json')).load()
        locals_store = LocalsSelectionStore(path=os.path.join(tmp.name, 'locals_selection.json')).load()
        streams = (
            [make_stream(f'SKYEVENTS {i:03d}: Real Match {i}', i) for i in range(1, 4)]
            + [make_stream(f'SKYEVENTS {i:03d}:', i) for i in range(4, 201)]
        )
        client = FakeXtreamClient(
            live_categories=[{'category_name': 'SKY SPORTS+ EVENTS', 'category_id': '1'}],
            live_streams_by_cat_id={'1': streams},
        )
        content, count, _ = export_module.build_m3u(
            store, export_store, locals_store, client, blank_buffer=10
        )
        self.assertEqual(count, 13)  # 3 real + 10 buffer
        self.assertIn('Real Match 3', content)
        self.assertNotIn('SKYEVENTS 200:', content)


class TestDefaultExportPath(unittest.TestCase):
    def test_falls_back_to_app_root_when_kodi_dir_absent(self):
        with mock.patch.object(export_module, 'KODI_IPTV_DEFAULT_DIR', 'Z:\\definitely\\not\\real\\path'):
            path = export_module.default_export_path()
        self.assertTrue(path.endswith('superone.m3u8'))
        self.assertNotIn('definitely', path)


if __name__ == '__main__':
    unittest.main()
