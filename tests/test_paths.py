# test_paths.py -- app_root()'s source-vs-frozen resolution, the fix for
# a real PyInstaller gotcha: __file__-based resolution lands inside the
# _internal/ extraction folder in a frozen build, not next to the real
# .exe, but sys.executable does sit next to it.

import os
import sys
import unittest

from _helpers import app  # noqa: F401

from s1iptv import paths


class TestAppRoot(unittest.TestCase):
    def test_not_frozen_resolves_to_repo_root(self):
        # sys.frozen is normally just absent (not False) when running from
        # source -- getattr(..., False) covers both cases.
        self.assertFalse(getattr(sys, 'frozen', False))
        root = paths.app_root()
        # Repo root is the parent of the s1iptv/ package directory.
        expected = os.path.dirname(os.path.dirname(os.path.abspath(paths.__file__)))
        self.assertEqual(root, expected)
        # Sanity check it's actually the repo root, not some unrelated path.
        self.assertTrue(os.path.isdir(os.path.join(root, 's1iptv')))

    def test_frozen_resolves_next_to_executable(self):
        original_frozen = getattr(sys, 'frozen', None)
        original_had_frozen = hasattr(sys, 'frozen')
        original_executable = sys.executable
        try:
            sys.frozen = True
            sys.executable = r'C:\Program Files\S1IptvHelper\S1IptvHelper.exe'
            root = paths.app_root()
            self.assertEqual(root, r'C:\Program Files\S1IptvHelper')
        finally:
            if original_had_frozen:
                sys.frozen = original_frozen
            else:
                del sys.frozen
            sys.executable = original_executable


if __name__ == '__main__':
    unittest.main()
