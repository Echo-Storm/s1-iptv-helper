# _helpers.py
# S1 IPTV Helper — test suite
#
# Shared fixtures for the offscreen PyQt6 test suite. Not a test module
# itself (leading underscore keeps unittest discovery from picking it up).
# Follows the same pattern as TorBox_Manager/tbm/tests/_helpers.py.
#
# Run the suite from the repo root:
#   venv\Scripts\python -m unittest discover -s tests -v
# or run a single file directly:
#   venv\Scripts\python tests\test_category_store.py

import os
import sys

# Must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from PyQt6.QtWidgets import QApplication  # noqa: E402

# QApplication can only be constructed once per process -- reuse if a prior
# test module in the same run already made one.
app = QApplication.instance() or QApplication(sys.argv)


class FakeXtreamClient:
    """
    A stand-in for xtream_client.XtreamClient that never touches the
    network. live_categories/live_streams_by_cat_id are keyed exactly like
    the real API: category_id is a string, streams are the raw dicts
    get_live_streams() would return (name/stream_id/epg_channel_id/
    stream_icon).
    """

    def __init__(self, live_categories, live_streams_by_cat_id, server='https://fake.test',
                 username='u', password='p'):
        self.server = server
        self.username = username
        self.password = password
        self._live_categories = live_categories
        self._live_streams_by_cat_id = live_streams_by_cat_id

    def get_live_categories(self):
        return self._live_categories

    def get_live_streams(self, category_id):
        return self._live_streams_by_cat_id.get(category_id, [])

    def live_stream_url(self, stream_id):
        return f'{self.server}:443/{self.username}/{self.password}/{stream_id}'


def make_stream(name, stream_id, tvg_id='', stream_icon=''):
    return {
        'name': name,
        'stream_id': stream_id,
        'epg_channel_id': tvg_id,
        'stream_icon': stream_icon,
    }
