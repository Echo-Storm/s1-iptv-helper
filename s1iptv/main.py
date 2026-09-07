import sys
import tempfile
import os

from PyQt6.QtCore import QLockFile
from PyQt6.QtWidgets import QApplication, QMessageBox

from .theme import build_stylesheet
from .main_window import MainWindow
from .logger import setup_logging

LOCK_PATH = os.path.join(tempfile.gettempdir(), 's1iptv_helper.lock')


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())

    # Only one instance at a time -- multiple copies writing taxonomy.json /
    # export_selection.json / locals_selection.json / config.json
    # concurrently could clobber each other's changes. QLockFile detects and
    # clears a stale lock left behind by a crashed previous instance on its
    # own, so this doesn't get in the way of a normal restart.
    lock = QLockFile(LOCK_PATH)
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.warning(
            None, "S1 IPTV Helper",
            "S1 IPTV Helper is already running.\n\n"
            "Only one instance can run at a time (it avoids two copies "
            "overwriting each other's saved taxonomy/selection files)."
        )
        sys.exit(1)

    setup_logging()

    window = MainWindow()
    window.show()
    exit_code = app.exec()
    lock.unlock()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
