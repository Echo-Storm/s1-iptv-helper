"""
Resolves the app's "root" directory -- where personal data files
(config.json, taxonomy.json, export/locals selection JSON, the log file,
taxonomy backups) live.

Every one of those previously computed this independently as
`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` -- the
parent of the s1iptv/ package directory. That's correct when running from
source, but breaks under a PyInstaller frozen build: __file__ then points
somewhere inside the `_internal/` extraction folder PyInstaller creates,
not next to the actual .exe. `sys.executable` is what actually sits next
to the exe in a frozen build. Matches Echo Audio Converter's
`core/paths.py`, which solves the identical problem the identical way.

Deliberately NOT used by theme.py's bundled asset paths (spinbox arrow
icons) -- those live inside the package and get bundled into
`_internal/s1iptv/assets/` either way, so __file__-relative resolution is
correct for them and shouldn't route through this.
"""

import os
import sys


def app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
