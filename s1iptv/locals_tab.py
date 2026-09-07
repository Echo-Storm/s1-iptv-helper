"""
Locals tab: ~1000 individual local-affiliate channels (ABC/CBS/FOX/NBC/CW/
PBS/etc. plus Univision/Telemundo/independent locals), grouped by state,
each with its own checkbox. Separate from the category-level taxonomy tabs
because this operates at the individual-channel level, not the category
level -- see docs/CATEGORY_MODEL.md for why locals don't fit the
category/subcategory model.
"""

import traceback

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QLineEdit, QMessageBox,
    QDialog, QCheckBox, QDialogButtonBox,
)

from .locals_data import (
    find_locals_raw_categories, fetch_locals, LocalsSelectionStore,
    OTHER_BUCKET, ALL_STATES,
)
from .xtream_client import XtreamClient, ConfigError

STREAM_ID_ROLE = Qt.ItemDataRole.UserRole
STATE_COLUMNS = 8


def _section_label(text):
    lbl = QLabel(text)
    lbl.setProperty('role', 'section')
    return lbl


class SetDefaultsDialog(QDialog):
    """Lets the user pick which states "Defaults" selects, instead of a
    hardcoded pair baked into the code."""

    def __init__(self, current_defaults, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Default States")
        self.resize(520, 320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("States selected here are what \"Defaults\" applies on the Locals tab."))

        toolbar = QHBoxLayout()
        all_btn = QPushButton("Select All")
        all_btn.clicked.connect(lambda: self._set_all(True))
        toolbar.addWidget(all_btn)
        none_btn = QPushButton("Select None")
        none_btn.clicked.connect(lambda: self._set_all(False))
        toolbar.addWidget(none_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        grid = QGridLayout()
        self.checkboxes = {}
        for idx, (code, name) in enumerate(ALL_STATES):
            cb = QCheckBox(code)
            cb.setToolTip(name)
            cb.setChecked(code in current_defaults)
            self.checkboxes[code] = cb
            grid.addWidget(cb, idx // STATE_COLUMNS, idx % STATE_COLUMNS)
        layout.addLayout(grid)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all(self, checked):
        for cb in self.checkboxes.values():
            cb.setChecked(checked)

    def selected_states(self):
        return {code for code, cb in self.checkboxes.items() if cb.isChecked()}


class LocalsFetchWorker(QThread):
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, raw_category_names):
        super().__init__()
        self.raw_category_names = raw_category_names

    def run(self):
        try:
            client = XtreamClient.from_config()
            grouped = fetch_locals(client, self.raw_category_names)
            self.succeeded.emit(grouped)
        except ConfigError as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


class LocalsTab(QWidget):
    def __init__(self, store, log_fn, selection_store=None, on_change=None):
        super().__init__()
        self.store = store
        self.log = log_fn
        self.selection_store = selection_store if selection_store is not None else LocalsSelectionStore().load()
        # Called whenever the fetched data or the selection changes, so the
        # Live TV tab's "Will Export" preview can show an up-to-date
        # per-state breakdown of what Locals will contribute.
        self.on_change = on_change
        self.grouped = {}  # state -> [{'name', 'stream_id', 'category_name'}, ...]
        self._worker = None

        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Locals")
        refresh_btn.setProperty('role', 'primary')
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        toolbar.addWidget(select_all_btn)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        toolbar.addWidget(deselect_all_btn)
        self.defaults_btn = QPushButton()
        self.defaults_btn.clicked.connect(self._select_defaults)
        toolbar.addWidget(self.defaults_btn)
        set_defaults_btn = QPushButton("Set Defaults...")
        set_defaults_btn.clicked.connect(self._open_set_defaults_dialog)
        toolbar.addWidget(set_defaults_btn)
        save_btn = QPushButton("Save Selection")
        save_btn.clicked.connect(self._save_selection)
        toolbar.addWidget(save_btn)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(_section_label("States"))
        self.state_list = QListWidget()
        self.state_list.currentItemChanged.connect(self._on_state_changed)
        left_layout.addWidget(self.state_list)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        header_row = QHBoxLayout()
        self.channel_header = _section_label("Channels")
        header_row.addWidget(self.channel_header)
        header_row.addStretch(1)
        state_select_all_btn = QPushButton("Select all in state")
        state_select_all_btn.clicked.connect(lambda: self._set_all_in_current_state(True))
        header_row.addWidget(state_select_all_btn)
        state_deselect_all_btn = QPushButton("Deselect all in state")
        state_deselect_all_btn.clicked.connect(lambda: self._set_all_in_current_state(False))
        header_row.addWidget(state_deselect_all_btn)
        right_layout.addLayout(header_row)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter channels...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        right_layout.addWidget(self.filter_edit)

        self.channel_list = QListWidget()
        self.channel_list.itemChanged.connect(self._on_channel_item_changed)
        right_layout.addWidget(self.channel_list)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, stretch=1)

        self.status_label = QLabel("Click \"Refresh Locals\" to fetch channels.")
        root.addWidget(self.status_label)

        self._refresh_defaults_button_label()

    # ------------------------------------------------------------------
    def _refresh_defaults_button_label(self):
        states = sorted(self.selection_store.default_states)
        label = ", ".join(states) if states else "none set"
        self.defaults_btn.setText(f"Defaults ({label})")

    def _open_set_defaults_dialog(self):
        dialog = SetDefaultsDialog(self.selection_store.default_states, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_defaults = dialog.selected_states()
            self.selection_store.set_default_states(new_defaults)
            self._refresh_defaults_button_label()
            self.log(f"Default states set to: {', '.join(sorted(new_defaults)) or '(none)'}")

    # ------------------------------------------------------------------
    def refresh(self):
        raw_names = find_locals_raw_categories(self.store)
        if not raw_names:
            QMessageBox.information(
                self, "No locals configured",
                "No Live subcategory named \"Locals\" was found in the taxonomy. "
                "Assign local-affiliate raw categories to a subcategory named "
                "\"Locals\" on the Live TV tab first."
            )
            return
        self.log(f"Fetching {len(raw_names)} local-affiliate categories...")
        self._worker = LocalsFetchWorker(raw_names)
        self._worker.succeeded.connect(self._on_fetch_succeeded)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_failed(self, message):
        self.log(f"Locals fetch failed: {message.splitlines()[-1] if message else message}")
        QMessageBox.critical(self, "Fetch failed", message)

    def _on_fetch_succeeded(self, grouped):
        self.grouped = grouped
        total = sum(len(v) for v in grouped.values())
        self.log(f"Locals: {total} channels across {len(grouped)} states/regions")
        self._rebuild_state_list()
        self._notify_change()

    def _notify_change(self):
        if self.on_change:
            self.on_change()

    def _rebuild_state_list(self):
        self.state_list.clear()
        # Sort states alphabetically, but always put OTHER last.
        states = sorted(k for k in self.grouped if k != OTHER_BUCKET)
        if OTHER_BUCKET in self.grouped:
            states.append(OTHER_BUCKET)
        for state in states:
            item = QListWidgetItem(self._state_label(state))
            item.setData(STREAM_ID_ROLE, state)
            self.state_list.addItem(item)
        if self.state_list.count():
            self.state_list.setCurrentRow(0)

    def _state_label(self, state):
        channels = self.grouped.get(state, [])
        selected = sum(1 for ch in channels if self.selection_store.is_selected(ch['stream_id']))
        label = "Other / Unrecognized" if state == OTHER_BUCKET else state
        return f"{label}  ({selected}/{len(channels)})"

    def _refresh_state_label(self, state):
        for row in range(self.state_list.count()):
            item = self.state_list.item(row)
            if item.data(STREAM_ID_ROLE) == state:
                item.setText(self._state_label(state))
                return

    # ------------------------------------------------------------------
    def _on_state_changed(self, current, previous):
        if current is None:
            self.channel_list.clear()
            return
        state = current.data(STREAM_ID_ROLE)
        label = "Other / Unrecognized" if state == OTHER_BUCKET else state
        self.channel_header.setText(f"Channels — {label}")
        self._populate_channel_list(state)

    def _populate_channel_list(self, state):
        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        for ch in sorted(self.grouped.get(state, []), key=lambda c: c['name']):
            item = QListWidgetItem(ch['name'])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if self.selection_store.is_selected(ch['stream_id'])
                else Qt.CheckState.Unchecked
            )
            item.setData(STREAM_ID_ROLE, ch['stream_id'])
            self.channel_list.addItem(item)
        self.channel_list.blockSignals(False)
        self._apply_filter(self.filter_edit.text())

    def _apply_filter(self, text):
        text = text.strip().lower()
        for row in range(self.channel_list.count()):
            item = self.channel_list.item(row)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _current_state(self):
        current = self.state_list.currentItem()
        return current.data(STREAM_ID_ROLE) if current else None

    def _on_channel_item_changed(self, item):
        stream_id = item.data(STREAM_ID_ROLE)
        self.selection_store.set_selected(stream_id, item.checkState() == Qt.CheckState.Checked)
        state = self._current_state()
        if state:
            self._refresh_state_label(state)
        self._notify_change()

    def _set_all_in_current_state(self, selected):
        state = self._current_state()
        if not state:
            return
        for ch in self.grouped.get(state, []):
            self.selection_store.set_selected(ch['stream_id'], selected)
        self._populate_channel_list(state)
        self._refresh_state_label(state)
        self._notify_change()

    # ------------------------------------------------------------------
    def _select_all(self):
        for channels in self.grouped.values():
            for ch in channels:
                self.selection_store.set_selected(ch['stream_id'], True)
        self._rebuild_state_list()
        state = self._current_state()
        if state:
            self._populate_channel_list(state)
        self.log("Selected all local channels")
        self._notify_change()

    def _deselect_all(self):
        for channels in self.grouped.values():
            for ch in channels:
                self.selection_store.set_selected(ch['stream_id'], False)
        self._rebuild_state_list()
        state = self._current_state()
        if state:
            self._populate_channel_list(state)
        self.log("Deselected all local channels")
        self._notify_change()

    def _select_defaults(self):
        defaults = self.selection_store.default_states
        for state, channels in self.grouped.items():
            include = state in defaults
            for ch in channels:
                self.selection_store.set_selected(ch['stream_id'], include)
        self._rebuild_state_list()
        state = self._current_state()
        if state:
            self._populate_channel_list(state)
        self._notify_change()
        self.log(f"Selected defaults: {', '.join(sorted(defaults)) or '(none)'}")

    def _save_selection(self):
        self.selection_store.save()
        total = len(self.selection_store.selected_ids)
        self.log(f"Saved {total} selected local channels to {self.selection_store.path}")
