"""Main window: banner, sidebar, Live TV / On Demand taxonomy tabs."""

import traceback

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem, QListWidget,
    QListWidgetItem, QComboBox, QSplitter, QPlainTextEdit, QStatusBar,
    QMessageBox, QFileDialog, QLineEdit,
)

from . import export as export_module
from .category_store import CategoryStore
from .export_selection import ExportSelectionStore
from .locals_data import (
    LocalsSelectionStore, find_locals_parent_category_name,
    is_locals_subcategory, OTHER_BUCKET, LOCALS_OWN_CATEGORY_NAME,
)
from .locals_tab import LocalsTab
from .logger import get_logger
from .settings_tab import SettingsTab
from .xtream_client import XtreamClient, ConfigError, NetworkError, load_config_or_blank, save_config

APP_VERSION = "0.6.1"

# Same Ko-fi page already used by the sibling apps (Echo Audio Converter,
# TorBox Manager EchoStorm Edition) -- see their donate buttons.
KOFI_URL = "https://ko-fi.com/xechostormx/tip"

RAW_NAME_ROLE = Qt.ItemDataRole.UserRole


def _configured_blank_buffer():
    """Read the Settings-tab blank-event-slot buffer for export/count calls.
    Stored as -1 for "off" (see SettingsTab); export.py's build_m3u/
    count_channels expect None for that same meaning."""
    value = load_config_or_blank().get('blank_buffer', 20)
    return None if value < 0 else value


class FetchCategoriesWorker(QThread):
    """Fetches live + VOD + series category lists off the UI thread."""
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            client = XtreamClient.from_config()
            live_cats = [c['category_name'] for c in client.get_live_categories()]
            vod_cats = [c['category_name'] for c in client.get_vod_categories()]
            series_cats = [c['category_name'] for c in client.get_series_categories()]
            self.succeeded.emit({
                'live': live_cats,
                'on_demand': sorted(set(vod_cats) | set(series_cats)),
            })
        except ConfigError as e:
            self.failed.emit(str(e))
        except NetworkError as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


class ExportWorker(QThread):
    """Builds the M3U (which means one API call per included raw category
    plus the Locals fetch if needed) and writes it to disk, off the UI
    thread since this can take a while."""
    succeeded = pyqtSignal(str, int, int)  # path, channel_count, locals_channel_count
    failed = pyqtSignal(str)

    def __init__(self, store, export_store, locals_store, path):
        super().__init__()
        self.store = store
        self.export_store = export_store
        self.locals_store = locals_store
        self.path = path

    def run(self):
        try:
            client = XtreamClient.from_config()
            content, count, locals_count = export_module.build_m3u(
                self.store, self.export_store, self.locals_store, client,
                blank_buffer=_configured_blank_buffer(),
            )
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.succeeded.emit(self.path, count, locals_count)
        except ConfigError as e:
            self.failed.emit(str(e))
        except NetworkError as e:
            self.failed.emit(str(e))
        except OSError as e:
            self.failed.emit(f"Could not write {self.path}: {e}")
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


class CountWorker(QThread):
    """Same fetch cost as an export (one API call per included raw category)
    but doesn't write anything -- for previewing scale before committing."""
    succeeded = pyqtSignal(int, int)  # channel_count, locals_channel_count
    failed = pyqtSignal(str)

    def __init__(self, store, export_store, locals_store):
        super().__init__()
        self.store = store
        self.export_store = export_store
        self.locals_store = locals_store

    def run(self):
        try:
            client = XtreamClient.from_config()
            count, locals_count = export_module.count_channels(
                self.store, self.export_store, self.locals_store, client,
                blank_buffer=_configured_blank_buffer(),
            )
            self.succeeded.emit(count, locals_count)
        except ConfigError as e:
            self.failed.emit(str(e))
        except NetworkError as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


def _banner_line():
    line = QFrame()
    line.setProperty('role', 'banner-line')
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def _banner_separator():
    """Vertical '|' glyph flanking the banner title -- matches the sibling
    apps' header treatment (TorBox_Manager's _build_header())."""
    sep = QLabel("|")
    sep.setProperty('role', 'banner-sep')
    return sep


def _section_label(text):
    lbl = QLabel(text)
    lbl.setProperty('role', 'section')
    return lbl


class CategoryTab(QWidget):
    """One tab (Live TV or On Demand): checkable taxonomy tree, an export
    preview showing exactly what's currently included, and the
    unassigned/stale triage panel."""

    def __init__(self, content_type, store: CategoryStore, export_store: ExportSelectionStore, log_fn,
                 locals_tab=None):
        super().__init__()
        self.content_type = content_type
        self.store = store
        self.export_store = export_store
        self.log = log_fn
        # Only meaningful for content_type == 'live' -- gives the export
        # preview access to the Locals tab's fetched channel data and
        # selection, so it can show a real per-state channel count instead
        # of treating Locals raw category names like any other.
        self.locals_tab = locals_tab
        self.last_fetched_names = []

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Left: taxonomy tree ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        tree_header_row = QHBoxLayout()
        tree_header_row.addWidget(_section_label("Taxonomy (checked = included in export)"))
        tree_header_row.addStretch(1)
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        tree_header_row.addWidget(select_all_btn)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        tree_header_row.addWidget(deselect_all_btn)
        left_layout.addLayout(tree_header_row)
        self.tree_filter_edit = QLineEdit()
        self.tree_filter_edit.setPlaceholderText("Filter taxonomy...")
        self.tree_filter_edit.textChanged.connect(self._apply_tree_filter)
        left_layout.addWidget(self.tree_filter_edit)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Category / Subcategory / Raw name"])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        left_layout.addWidget(self.tree)

        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("Select raw names above, pick a destination on the right, then:"))
        move_row.addStretch(1)
        move_selected_btn = QPushButton("Move Selected →")
        move_selected_btn.setProperty('role', 'primary')
        move_selected_btn.clicked.connect(self._move_selected_tree_items)
        move_row.addWidget(move_selected_btn)
        left_layout.addLayout(move_row)

        splitter.addWidget(left)

        # ---- Right: export preview + unassigned + stale ----
        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(_section_label("Unassigned (from latest fetch)"))
        self.unassigned_list = QListWidget()
        self.unassigned_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self.unassigned_list, stretch=1)

        assign_row = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setPlaceholderText("Category")
        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(True)
        self.subcategory_combo.setPlaceholderText("Subcategory")
        assign_btn = QPushButton("Assign →")
        assign_btn.setProperty('role', 'primary')
        assign_btn.clicked.connect(self._assign_selected)
        assign_row.addWidget(self.category_combo)
        assign_row.addWidget(self.subcategory_combo)
        assign_row.addWidget(assign_btn)
        right_layout.addLayout(assign_row)

        self.export_preview_label = _section_label("Will Export")
        right_layout.addWidget(self.export_preview_label)
        self.export_preview_list = QListWidget()
        right_layout.addWidget(self.export_preview_list, stretch=3)

        right_layout.addWidget(_section_label("Stale (in taxonomy, missing from latest fetch)"))
        self.stale_list = QListWidget()
        self.stale_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self.stale_list, stretch=1)

        unassign_btn = QPushButton("Remove from taxonomy")
        unassign_btn.clicked.connect(self._unassign_selected_stale)
        right_layout.addWidget(unassign_btn)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self.refresh_tree()
        self.category_combo.currentTextChanged.connect(self._refresh_subcategory_options)
        self._refresh_category_options()

    # ------------------------------------------------------------------
    def refresh_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        for cat in self.store.categories(self.content_type):
            cat_item = QTreeWidgetItem([cat['name']])
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            cat_included_flags = []
            for sub in cat.get('subcategories', []):
                sub_item = QTreeWidgetItem([f"{sub['name']}  ({len(sub.get('raw_categories', []))})"])
                sub_item.setFlags(sub_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                sub_included_flags = []
                for raw in sub.get('raw_categories', []):
                    leaf_item = QTreeWidgetItem([raw])
                    leaf_item.setFlags(leaf_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    leaf_item.setData(0, RAW_NAME_ROLE, raw)
                    included = self.export_store.is_included(self.content_type, raw)
                    leaf_item.setCheckState(0, Qt.CheckState.Checked if included else Qt.CheckState.Unchecked)
                    sub_item.addChild(leaf_item)
                    sub_included_flags.append(included)
                sub_item.setCheckState(0, self._aggregate_state(sub_included_flags))
                cat_item.addChild(sub_item)
                cat_included_flags.extend(sub_included_flags)
            cat_item.setCheckState(0, self._aggregate_state(cat_included_flags))
            self.tree.addTopLevelItem(cat_item)
        self.tree.expandToDepth(0)
        self.tree.blockSignals(False)
        self._apply_tree_filter(self.tree_filter_edit.text())
        self._refresh_export_preview()

    def _apply_tree_filter(self, text):
        """
        Hide any category/subcategory/raw-name row that doesn't match, but
        keep every ancestor of a match visible (and expanded) so the match
        is actually reachable -- and once a row itself matches, show its
        whole subtree unconditionally rather than filtering further down
        (searching "USA LIVE" should show everything under it, not just
        raw names that happen to also contain "USA LIVE").
        """
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            self._filter_tree_item(self.tree.topLevelItem(i), text)

    def _filter_tree_item(self, item, text):
        if not text or text in item.text(0).lower():
            item.setHidden(False)
            self._show_all_descendants(item)
            return True
        child_match = False
        for i in range(item.childCount()):
            if self._filter_tree_item(item.child(i), text):
                child_match = True
        item.setHidden(not child_match)
        if child_match:
            item.setExpanded(True)
        return child_match

    def _show_all_descendants(self, item):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setHidden(False)
            self._show_all_descendants(child)

    @staticmethod
    def _aggregate_state(included_flags):
        if not included_flags or all(included_flags):
            return Qt.CheckState.Checked
        if not any(included_flags):
            return Qt.CheckState.Unchecked
        return Qt.CheckState.PartiallyChecked

    # ------------------------------------------------------------------
    # Checkbox handling — a raw-name leaf is the ground truth (persisted via
    # export_store); category/subcategory checkboxes are a derived tri-state
    # display, and toggling one directly cascades to every descendant leaf.
    # ------------------------------------------------------------------
    def _on_tree_item_changed(self, item, column):
        self.tree.blockSignals(True)
        try:
            raw_name = item.data(0, RAW_NAME_ROLE)
            if raw_name is not None:
                included = item.checkState(0) == Qt.CheckState.Checked
                self.export_store.set_included(self.content_type, raw_name, included)
            else:
                # Category/subcategory clicked directly: Qt only lets a user
                # click land on Checked or Unchecked (never PartiallyChecked),
                # so this cascades that state to every descendant leaf.
                included = item.checkState(0) == Qt.CheckState.Checked
                self._set_descendants_checked(item, included)
            self._update_ancestors(item)
        finally:
            self.tree.blockSignals(False)
        self._refresh_export_preview()

    def _set_descendants_checked(self, item, included):
        state = Qt.CheckState.Checked if included else Qt.CheckState.Unchecked
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            raw_name = child.data(0, RAW_NAME_ROLE)
            if raw_name is not None:
                self.export_store.set_included(self.content_type, raw_name, included)
            else:
                self._set_descendants_checked(child, included)

    def _update_ancestors(self, item):
        parent = item.parent()
        while parent is not None:
            states = [parent.child(i).checkState(0) for i in range(parent.childCount())]
            if all(s == Qt.CheckState.Checked for s in states):
                new_state = Qt.CheckState.Checked
            elif all(s == Qt.CheckState.Unchecked for s in states):
                new_state = Qt.CheckState.Unchecked
            else:
                new_state = Qt.CheckState.PartiallyChecked
            parent.setCheckState(0, new_state)
            parent = parent.parent()

    def _set_all_checked(self, included):
        self.tree.blockSignals(True)
        try:
            for i in range(self.tree.topLevelItemCount()):
                top = self.tree.topLevelItem(i)
                top.setCheckState(0, Qt.CheckState.Checked if included else Qt.CheckState.Unchecked)
                self._set_descendants_checked(top, included)
        finally:
            self.tree.blockSignals(False)
        self._refresh_export_preview()
        self.log(f"{'Selected' if included else 'Deselected'} all {self.content_type} categories for export")

    def _refresh_export_preview(self):
        self.export_preview_list.clear()

        # The "Locals" special-case (raw categories that don't get listed
        # individually because their real export set is the per-channel
        # selection from the Locals tab) only applies to the Live TV tab.
        # On Demand has no Locals concept -- even if a subcategory there
        # happened to be named "Locals", treat it as an ordinary subcategory
        # rather than silently dropping its raw categories from the preview.
        treat_locals_specially = self.content_type == 'live'

        locals_raw_upper = set()
        if treat_locals_specially:
            for cat in self.store.categories(self.content_type):
                for sub in cat.get('subcategories', []):
                    if is_locals_subcategory(sub['name']):
                        locals_raw_upper.update(r.strip().upper() for r in sub.get('raw_categories', []))

        included_names = []
        checked_locals_raw = set()
        for cat in self.store.categories(self.content_type):
            for sub in cat.get('subcategories', []):
                for raw in sub.get('raw_categories', []):
                    if not self.export_store.is_included(self.content_type, raw):
                        continue
                    if raw.strip().upper() in locals_raw_upper:
                        checked_locals_raw.add(raw.strip().upper())
                    else:
                        included_names.append(raw)
        total = sum(
            len(sub.get('raw_categories', []))
            for cat in self.store.categories(self.content_type)
            for sub in cat.get('subcategories', [])
            if not (treat_locals_specially and is_locals_subcategory(sub['name']))
        )
        self.export_preview_label.setText(f"Will Export  ({len(included_names)} of {total} categories)")

        if checked_locals_raw and self.locals_tab is not None:
            self._add_locals_preview_rows(checked_locals_raw)

        for name in sorted(included_names, key=str.upper):
            self.export_preview_list.addItem(QListWidgetItem(name))

    def _add_locals_preview_rows(self, checked_locals_raw_upper):
        """Prepend a Locals summary (per-state channel counts) to the export
        preview list, using whatever the Locals tab currently has -- live
        data from its last fetch/selection if available, else just the
        saved total selection count."""
        selection_store = self.locals_tab.selection_store
        grouped = self.locals_tab.grouped
        dest = (find_locals_parent_category_name(self.store) or "its parent category") \
            if selection_store.merge_into_parent else LOCALS_OWN_CATEGORY_NAME

        if not grouped:
            # This total isn't filtered by which raw categories are
            # currently checked (that mapping only exists in the per-state
            # data from a Locals fetch) -- it's every channel ever selected,
            # so it can overstate what actually exports if a raw category
            # got unchecked since the last Locals fetch. The real export
            # (export.py) always re-fetches and filters correctly regardless.
            total_selected = len(selection_store.selected_ids)
            header = QListWidgetItem(
                f'LOCALS — ~{total_selected} channels selected → exports under "{dest}" '
                f'(unfiltered estimate; refresh Locals tab for an exact, per-state count)'
            )
            header.setForeground(Qt.GlobalColor.yellow)
            self.export_preview_list.addItem(header)
            return

        per_state_selected = {}
        total_selected = 0
        for state, channels in grouped.items():
            for ch in channels:
                if ch['category_name'].strip().upper() not in checked_locals_raw_upper:
                    continue
                if selection_store.is_selected(ch['stream_id']):
                    per_state_selected[state] = per_state_selected.get(state, 0) + 1
                    total_selected += 1

        header = QListWidgetItem(f'LOCALS — {total_selected} channels selected → exports under "{dest}"')
        header.setForeground(Qt.GlobalColor.yellow)
        self.export_preview_list.addItem(header)
        for state in sorted(k for k in per_state_selected if k != OTHER_BUCKET):
            self.export_preview_list.addItem(QListWidgetItem(f"    {state}: {per_state_selected[state]}"))
        if OTHER_BUCKET in per_state_selected:
            self.export_preview_list.addItem(
                QListWidgetItem(f"    Other/Unrecognized: {per_state_selected[OTHER_BUCKET]}")
            )

    def _refresh_category_options(self):
        current = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems([c['name'] for c in self.store.categories(self.content_type)])
        self.category_combo.setCurrentText(current)
        self.category_combo.blockSignals(False)
        self._refresh_subcategory_options()

    def _refresh_subcategory_options(self):
        self.subcategory_combo.clear()
        target = self.category_combo.currentText().strip().upper()
        for cat in self.store.categories(self.content_type):
            if cat['name'].strip().upper() == target:
                self.subcategory_combo.addItems([s['name'] for s in cat.get('subcategories', [])])
                return

    def apply_fetch(self, raw_names):
        self.last_fetched_names = raw_names
        diff = self.store.diff(self.content_type, raw_names)
        self.unassigned_list.clear()
        for name in diff['unassigned']:
            self.unassigned_list.addItem(QListWidgetItem(name))
        self.stale_list.clear()
        for name in diff['stale']:
            self.stale_list.addItem(QListWidgetItem(name))
        self.log(f"{self.content_type}: {len(raw_names)} fetched, "
                  f"{len(diff['unassigned'])} unassigned, {len(diff['stale'])} stale")

    def _assign_selected(self):
        category_name = self.category_combo.currentText().strip()
        subcategory_name = self.subcategory_combo.currentText().strip()
        if not category_name or not subcategory_name:
            QMessageBox.warning(self, "Assign", "Pick (or type) both a category and a subcategory first.")
            return
        selected = self.unassigned_list.selectedItems()
        if not selected:
            QMessageBox.information(self, "Assign", "Select one or more unassigned categories first.")
            return
        for item in selected:
            self.store.assign(self.content_type, item.text(), category_name, subcategory_name)
        for item in selected:
            self.unassigned_list.takeItem(self.unassigned_list.row(item))
        self.refresh_tree()
        self._refresh_category_options()
        self.log(f"Assigned {len(selected)} {self.content_type} categories to "
                 f"{category_name} → {subcategory_name}")

    def _move_selected_tree_items(self):
        """
        Reassign already-assigned raw categories to a different
        category/subcategory, selected directly in the tree -- the only
        way to reorganize the taxonomy before this was editing
        data/taxonomy.seed.json by hand and relying on the auto-sync to
        carry the move into taxonomy.json. Category/subcategory rows in
        the selection are ignored (only raw-name leaves have anything to
        move); reuses the same destination combos as the Unassigned
        "Assign" flow just below.
        """
        category_name = self.category_combo.currentText().strip()
        subcategory_name = self.subcategory_combo.currentText().strip()
        if not category_name or not subcategory_name:
            QMessageBox.warning(self, "Move", "Pick (or type) both a destination category and subcategory first.")
            return
        raw_names = [
            item.data(0, RAW_NAME_ROLE) for item in self.tree.selectedItems()
            if item.data(0, RAW_NAME_ROLE) is not None
        ]
        if not raw_names:
            QMessageBox.information(
                self, "Move", "Select one or more raw names in the tree first "
                "(category/subcategory rows don't have anything to move)."
            )
            return
        for raw in raw_names:
            self.store.assign(self.content_type, raw, category_name, subcategory_name)
        self.refresh_tree()
        self._refresh_category_options()
        self.log(f"Moved {len(raw_names)} {self.content_type} raw categories to "
                 f"{category_name} → {subcategory_name}")

    def _unassign_selected_stale(self):
        selected = self.stale_list.selectedItems()
        if not selected:
            return
        for item in selected:
            self.store.unassign(self.content_type, item.text())
        for item in selected:
            self.stale_list.takeItem(self.stale_list.row(item))
        self.refresh_tree()
        self._refresh_category_options()
        self.log(f"Removed {len(selected)} stale {self.content_type} categories from taxonomy")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S1 IPTV Helper")
        self.resize(1200, 800)

        self.store = CategoryStore().load()
        self.export_store = ExportSelectionStore().load()
        self.locals_selection_store = LocalsSelectionStore().load()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_banner())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.addWidget(self._build_sidebar())

        self.tabs = QTabWidget()
        self.locals_tab = LocalsTab(self.store, self._log, selection_store=self.locals_selection_store)
        self.live_tab = CategoryTab('live', self.store, self.export_store, self._log, locals_tab=self.locals_tab)
        self.vod_tab = CategoryTab('on_demand', self.store, self.export_store, self._log)
        self.settings_tab = SettingsTab(self._log)
        # Locals selection changes should refresh the Live TV export preview.
        self.locals_tab.on_change = self.live_tab._refresh_export_preview
        self.tabs.addTab(self.live_tab, "Live TV")
        self.tabs.addTab(self.vod_tab, "On Demand")
        self.tabs.addTab(self.locals_tab, "Locals")
        self.tabs.addTab(self.settings_tab, "Settings")
        body_layout.addWidget(self.tabs, stretch=1)
        root.addWidget(body, stretch=1)

        self.log_view = QPlainTextEdit()
        self.log_view.setProperty('role', 'log')
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        root.addWidget(self.log_view)

        self.setStatusBar(QStatusBar())

        # Ko-fi donate link -- permanent widget, far right of the status bar.
        # Same pattern and same page as the sibling apps' own donate buttons.
        donate_btn = QPushButton("donate  ♥  ko-fi")
        donate_btn.setObjectName("donateBtn")
        donate_btn.setFlat(True)
        donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_btn.setToolTip("Support development on Ko-fi")
        donate_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(KOFI_URL)))
        self.statusBar().addPermanentWidget(donate_btn)

        self._log("Ready. Taxonomy loaded from " + self.store.path)
        if self.store.last_sync_notes:
            self._log(f"Auto-synced {len(self.store.last_sync_notes)} raw categories to match updated taxonomy seed:")
            for note in self.store.last_sync_notes:
                self._log(f"  {note}")

        # Auto-fetch Locals channels on startup instead of making it a manual
        # "Refresh Locals" click every session -- silent=True so a fresh
        # install (no credentials yet) or a momentary network hiccup logs
        # quietly instead of throwing a dialog before the window is even
        # shown. Must come after self.log_view exists above: refresh() logs
        # immediately via self._log(), which writes to self.log_view.
        self.locals_tab.refresh(silent=True)

    # ------------------------------------------------------------------
    def _build_banner(self):
        """Fixed-height header bar: [v0.6.0] ———|  S1 IPTV HELPER  |——— [ECHOSTORM EDITION]
        Matches the sibling apps' actual header treatment (see
        TorBox_Manager's _build_header()) -- panel-colored bar, bright
        accent top/bottom border, vertical separator glyphs flanking a
        large bold title, thin accent lines running out to the edges."""
        banner = QWidget()
        banner.setProperty('role', 'banner')
        banner.setFixedHeight(64)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setProperty('role', 'banner-tag')
        version_lbl.setFixedWidth(48)
        layout.addWidget(version_lbl)

        layout.addWidget(_banner_line(), stretch=1)
        layout.addWidget(_banner_separator())

        title_lbl = QLabel("S1 IPTV HELPER")
        title_lbl.setProperty('role', 'banner-title')
        layout.addWidget(title_lbl)

        layout.addWidget(_banner_separator())
        layout.addWidget(_banner_line(), stretch=1)

        edition_lbl = QLabel("ECHOSTORM EDITION")
        edition_lbl.setProperty('role', 'banner-tag')
        edition_lbl.setFixedWidth(150)
        edition_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(edition_lbl)

        return banner

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setProperty('role', 'sidebar')
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        layout.addWidget(_section_label("Connection"))
        self.refresh_categories_btn = QPushButton("⟳  Refresh Categories")
        self.refresh_categories_btn.setProperty('role', 'primary')
        self.refresh_categories_btn.setMinimumHeight(30)
        self.refresh_categories_btn.clicked.connect(self._refresh_categories)
        layout.addWidget(self.refresh_categories_btn)

        layout.addWidget(_section_label("Taxonomy"))
        save_btn = QPushButton("\U0001f4be  Save Taxonomy")
        save_btn.setMinimumHeight(30)
        save_btn.clicked.connect(self._save_taxonomy)
        layout.addWidget(save_btn)

        layout.addWidget(_section_label("Export"))
        self.count_btn = QPushButton("\U0001f522  Count Channels")
        self.count_btn.setMinimumHeight(30)
        self.count_btn.clicked.connect(self._count_channels)
        layout.addWidget(self.count_btn)
        self.export_btn = QPushButton("↑  Export Live M3U...")
        self.export_btn.setProperty('role', 'primary')
        self.export_btn.setMinimumHeight(30)
        self.export_btn.clicked.connect(self._export_m3u)
        layout.addWidget(self.export_btn)

        layout.addStretch(1)
        return sidebar

    # ------------------------------------------------------------------
    def _log(self, message):
        self.log_view.appendPlainText(message)
        self.statusBar().showMessage(message, 5000)
        get_logger().info(message)

    def _refresh_categories(self):
        self.refresh_categories_btn.setEnabled(False)
        self._log("Fetching categories from provider...")
        self._worker = FetchCategoriesWorker()
        self._worker.succeeded.connect(self._on_fetch_succeeded)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_succeeded(self, result):
        self.refresh_categories_btn.setEnabled(True)
        self.live_tab.apply_fetch(result['live'])
        self.vod_tab.apply_fetch(result['on_demand'])

    def _on_fetch_failed(self, message):
        self.refresh_categories_btn.setEnabled(True)
        self._log(f"Fetch failed: {message.splitlines()[-1] if message else message}")
        QMessageBox.critical(self, "Fetch failed", message)

    def _count_channels(self):
        self.count_btn.setEnabled(False)
        self._log("Counting channels for the current selection...")
        self._count_worker = CountWorker(self.store, self.export_store, self.locals_selection_store)
        self._count_worker.succeeded.connect(self._on_count_succeeded)
        self._count_worker.failed.connect(self._on_count_failed)
        self._count_worker.start()

    def _on_count_succeeded(self, count, locals_count):
        self.count_btn.setEnabled(True)
        message = f"Current selection totals {count} channels ({locals_count} from Locals)"
        self._log(message)
        QMessageBox.information(self, "Channel Count", message)

    def _on_count_failed(self, message):
        self.count_btn.setEnabled(True)
        self._log(f"Count failed: {message.splitlines()[-1] if message else message}")
        QMessageBox.critical(self, "Count failed", message)

    def _export_m3u(self):
        cfg = load_config_or_blank()
        default_path = cfg.get('export_path') or export_module.default_export_path()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Live M3U", default_path, "M3U Playlist (*.m3u8 *.m3u);;All Files (*)"
        )
        if not path:
            return
        self.export_btn.setEnabled(False)
        self._log(f"Exporting to {path} ...")
        self._export_worker = ExportWorker(self.store, self.export_store, self.locals_selection_store, path)
        self._export_worker.succeeded.connect(self._on_export_succeeded)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_worker.start()

    def _on_export_succeeded(self, path, count, locals_count):
        self.export_btn.setEnabled(True)
        self._log(f"Exported {count} channels ({locals_count} from Locals) to {path}")
        # Remember this as the default for next time.
        cfg = load_config_or_blank()
        if cfg.get('server'):
            save_config(cfg['server'], cfg['username'], cfg['password'], export_path=path)
        self.settings_tab.refresh_export_path_field(path)

    def _on_export_failed(self, message):
        self.export_btn.setEnabled(True)
        self._log(f"Export failed: {message.splitlines()[-1] if message else message}")
        QMessageBox.critical(self, "Export failed", message)

    def _save_taxonomy(self):
        self.store.save()
        self._log(f"Taxonomy saved to {self.store.path}")
