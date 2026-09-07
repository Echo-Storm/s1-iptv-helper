"""Settings tab: IPTV provider connection (server/username/password)."""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QLabel, QFileDialog,
)

from .xtream_client import XtreamClient, load_config_or_blank, save_config, CONFIG_PATH
from .category_store import DEFAULT_TAXONOMY_PATH
from .export import default_export_path


class TestConnectionWorker(QThread):
    """Tries the given (unsaved) credentials against the API off the UI thread."""
    succeeded = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, server, username, password):
        super().__init__()
        self.server = server
        self.username = username
        self.password = password

    def run(self):
        try:
            client = XtreamClient(self.server, self.username, self.password)
            cats = client.get_live_categories()
            self.succeeded.emit(len(cats))
        except Exception as e:
            self.failed.emit(str(e))


def _section_label(text):
    lbl = QLabel(text)
    lbl.setProperty('role', 'section')
    return lbl


class SettingsTab(QWidget):
    def __init__(self, log_fn):
        super().__init__()
        self.log = log_fn
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(_section_label("IPTV Provider Connection"))

        form = QFormLayout()
        form.setSpacing(10)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText("https://example.com")
        form.addRow("Server:", self.server_edit)

        self.username_edit = QLineEdit()
        form.addRow("Username:", self.username_edit)

        pw_row = QHBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pw_row.addWidget(self.password_edit)
        self.show_pw_check = QCheckBox("Show")
        self.show_pw_check.toggled.connect(self._toggle_password_visibility)
        pw_row.addWidget(self.show_pw_check)
        form.addRow("Password:", pw_row)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        button_row.addWidget(self.test_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty('role', 'primary')
        save_btn.clicked.connect(self._save)
        button_row.addWidget(save_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.addWidget(_section_label("Export"))
        export_form = QFormLayout()
        export_form.setSpacing(10)
        export_row = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        export_row.addWidget(self.export_path_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_export_path)
        export_row.addWidget(browse_btn)
        export_form.addRow("Default M3U path:", export_row)
        layout.addLayout(export_form)

        layout.addWidget(_section_label("File Locations"))
        paths_form = QFormLayout()
        paths_form.setSpacing(6)
        config_path_lbl = QLabel(CONFIG_PATH)
        config_path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        paths_form.addRow("Config file:", config_path_lbl)
        taxonomy_path_lbl = QLabel(DEFAULT_TAXONOMY_PATH)
        taxonomy_path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        paths_form.addRow("Taxonomy file:", taxonomy_path_lbl)
        layout.addLayout(paths_form)

        layout.addStretch(1)

        self._load()

    def _toggle_password_visibility(self, checked):
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _load(self):
        cfg = load_config_or_blank()
        self.server_edit.setText(cfg['server'])
        self.username_edit.setText(cfg['username'])
        self.password_edit.setText(cfg['password'])
        self.export_path_edit.setText(cfg.get('export_path') or default_export_path())

    def _browse_export_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Default M3U export path", self.export_path_edit.text(),
            "M3U Playlist (*.m3u8 *.m3u);;All Files (*)"
        )
        if path:
            self.export_path_edit.setText(path)

    def refresh_export_path_field(self, path):
        """Called by MainWindow after a successful export, so this field
        reflects the path that was actually just used (which becomes the
        new default)."""
        self.export_path_edit.setText(path)

    def _current_values(self):
        return (
            self.server_edit.text().strip(),
            self.username_edit.text().strip(),
            self.password_edit.text().strip(),
        )

    def _test_connection(self):
        server, username, password = self._current_values()
        if not all((server, username, password)):
            self.status_label.setText("Fill in server, username, and password first.")
            return
        self.test_btn.setEnabled(False)
        self.status_label.setText("Testing connection...")
        self._worker = TestConnectionWorker(server, username, password)
        self._worker.succeeded.connect(self._on_test_succeeded)
        self._worker.failed.connect(self._on_test_failed)
        self._worker.start()

    def _on_test_succeeded(self, category_count):
        self.test_btn.setEnabled(True)
        message = f"Connection OK — {category_count} live categories found."
        self.status_label.setText(message)
        self.log(message)

    def _on_test_failed(self, error):
        self.test_btn.setEnabled(True)
        message = f"Connection failed: {error}"
        self.status_label.setText(message)
        self.log(message)

    def _save(self):
        server, username, password = self._current_values()
        if not all((server, username, password)):
            self.status_label.setText("Fill in server, username, and password before saving.")
            return
        save_config(server, username, password, export_path=self.export_path_edit.text().strip())
        message = f"Saved settings to {CONFIG_PATH}"
        self.status_label.setText(message)
        self.log(message)
