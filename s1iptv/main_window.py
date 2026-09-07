"""Main window: banner, sidebar, Live TV / On Demand taxonomy tabs."""

import traceback

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem, QListWidget,
    QListWidgetItem, QComboBox, QSplitter, QPlainTextEdit, QStatusBar,
    QMessageBox,
)

from .category_store import CategoryStore
from .xtream_client import XtreamClient, ConfigError

APP_VERSION = "0.1.0"


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
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


def _banner_line():
    line = QFrame()
    line.setProperty('role', 'banner-line')
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def _section_label(text):
    lbl = QLabel(text)
    lbl.setProperty('role', 'section')
    return lbl


class CategoryTab(QWidget):
    """One tab (Live TV or On Demand): taxonomy tree + unassigned/stale panel."""

    def __init__(self, content_type, store: CategoryStore, log_fn):
        super().__init__()
        self.content_type = content_type
        self.store = store
        self.log = log_fn
        self.last_fetched_names = []

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Left: taxonomy tree ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(_section_label("Taxonomy"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Category / Subcategory / Raw name"])
        left_layout.addWidget(self.tree)
        splitter.addWidget(left)

        # ---- Right: unassigned + stale ----
        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(_section_label("Unassigned (from latest fetch)"))
        self.unassigned_list = QListWidget()
        self.unassigned_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self.unassigned_list)

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

        right_layout.addWidget(_section_label("Stale (in taxonomy, missing from latest fetch)"))
        self.stale_list = QListWidget()
        self.stale_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self.stale_list)

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
        self.tree.clear()
        for cat in self.store.categories(self.content_type):
            cat_item = QTreeWidgetItem([cat['name']])
            for sub in cat.get('subcategories', []):
                sub_item = QTreeWidgetItem([f"{sub['name']}  ({len(sub.get('raw_categories', []))})"])
                for raw in sub.get('raw_categories', []):
                    sub_item.addChild(QTreeWidgetItem([raw]))
                cat_item.addChild(sub_item)
            self.tree.addTopLevelItem(cat_item)
        self.tree.expandToDepth(0)

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
        self.live_tab = CategoryTab('live', self.store, self._log)
        self.vod_tab = CategoryTab('on_demand', self.store, self._log)
        self.tabs.addTab(self.live_tab, "Live TV")
        self.tabs.addTab(self.vod_tab, "On Demand")
        body_layout.addWidget(self.tabs, stretch=1)
        root.addWidget(body, stretch=1)

        self.log_view = QPlainTextEdit()
        self.log_view.setProperty('role', 'log')
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        root.addWidget(self.log_view)

        self.setStatusBar(QStatusBar())
        self._log("Ready. Taxonomy loaded from " + self.store.path)

    # ------------------------------------------------------------------
    def _build_banner(self):
        banner = QWidget()
        banner.setProperty('role', 'banner')
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 10, 16, 10)

        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setProperty('role', 'banner-tag')
        layout.addWidget(version_lbl)

        layout.addWidget(_banner_line(), stretch=1)

        title_lbl = QLabel("S1 IPTV HELPER")
        title_lbl.setProperty('role', 'banner-title')
        layout.addWidget(title_lbl)

        layout.addWidget(_banner_line(), stretch=1)

        edition_lbl = QLabel("ECHOSTORM EDITION")
        edition_lbl.setProperty('role', 'banner-tag')
        layout.addWidget(edition_lbl)

        return banner

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)

        layout.addWidget(_section_label("Connection"))
        refresh_btn = QPushButton("Refresh Categories")
        refresh_btn.setProperty('role', 'primary')
        refresh_btn.clicked.connect(self._refresh_categories)
        layout.addWidget(refresh_btn)

        layout.addWidget(_section_label("Taxonomy"))
        save_btn = QPushButton("Save Taxonomy")
        save_btn.clicked.connect(self._save_taxonomy)
        layout.addWidget(save_btn)

        layout.addWidget(_section_label("Export"))
        export_btn = QPushButton("Export Live M3U...")
        export_btn.setEnabled(False)
        export_btn.setToolTip("Coming soon — see docs/ROADMAP.md")
        layout.addWidget(export_btn)

        layout.addStretch(1)
        return sidebar

    # ------------------------------------------------------------------
    def _log(self, message):
        self.log_view.appendPlainText(message)
        self.statusBar().showMessage(message, 5000)

    def _refresh_categories(self):
        self._log("Fetching categories from provider...")
        self._worker = FetchCategoriesWorker()
        self._worker.succeeded.connect(self._on_fetch_succeeded)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_succeeded(self, result):
        self.live_tab.apply_fetch(result['live'])
        self.vod_tab.apply_fetch(result['on_demand'])

    def _on_fetch_failed(self, message):
        self._log(f"Fetch failed: {message.splitlines()[-1] if message else message}")
        QMessageBox.critical(self, "Fetch failed", message)

    def _save_taxonomy(self):
        self.store.save()
        self._log(f"Taxonomy saved to {self.store.path}")
