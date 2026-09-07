"""
PyInstaller entry point.

Not launched directly during normal development (that's `launch.bat` /
`python -m s1iptv.main`) -- this exists only because a script with relative
imports (s1iptv/main.py uses `from .theme import ...` etc.) can't be run
directly by Python or by PyInstaller's bootloader as __main__; a normal
absolute import of the package resolves those relative imports correctly,
a direct execution of the file inside the package does not.
"""

from s1iptv.main import main

if __name__ == '__main__':
    main()
