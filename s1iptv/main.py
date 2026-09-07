import sys

from PyQt6.QtWidgets import QApplication

from .theme import build_stylesheet
from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
