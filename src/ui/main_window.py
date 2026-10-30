"""Main application window for TeleCup with unified dark styling, breadcrumbs, and drag & drop support."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QStatusBar,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt

from .sidebar import SidebarWidget
from .toolbar import ToolbarWidget
from .file_grid import FileGridWidget


class MainWindow(QMainWindow):
    """Main window coordinating sidebar, toolbar, file grid, and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeleCup - Saved Messages Vault")
        self.resize(1160, 720)
        self.setMinimumSize(900, 560)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #18181b;
            }
            QWidget {
                color: #e4e4e7;
            }
            """
        )

        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: #18181b;")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Top Toolbar ──
        self.toolbar = ToolbarWidget(self)
        root_layout.addWidget(self.toolbar)

        # Divider line
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #27272a;")
        root_layout.addWidget(divider)

        # ── 2. Splitter (Sidebar + Content View) ──
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #27272a;
            }
            """
        )

        self.sidebar = SidebarWidget(self)
        self.sidebar.setStyleSheet("background-color: #141416; border-right: 1px solid #27272a;")
        self.file_grid = FileGridWidget(self)

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.file_grid)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([230, 930])

        root_layout.addWidget(self.splitter, stretch=1)

        # ── 3. Status Bar ──
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            """
            QStatusBar {
                background-color: #141416;
                color: #a1a1aa;
                border-top: 1px solid #27272a;
                font-size: 11px;
                padding: 4px 10px;
            }
            """
        )
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready | 6 files in local vault")
        self.status_label.setStyleSheet("color: #a1a1aa;")
        self.status_bar.addWidget(self.status_label)

        self.sync_status_label = QLabel("Telegram: Configured (ready to link)")
        self.sync_status_label.setStyleSheet("color: #3b82f6; font-weight: 500; margin-right: 12px;")
        self.status_bar.addPermanentWidget(self.sync_status_label)

    def _connect_signals(self):
        # Sidebar to File Grid
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.sidebar.folder_selected.connect(self._on_folder_selected)
        self.sidebar.sync_requested.connect(self._on_sync_requested)
        self.sidebar.file_dropped_on_folder.connect(self.file_grid.move_file_to_folder)

        # File Grid events
        self.file_grid.breadcrumb_navigated.connect(self._on_breadcrumb_navigated)
        self.file_grid.file_relocated.connect(self._on_file_relocated)

        # Toolbar controls
        self.toolbar.search_changed.connect(self.file_grid.filter_by_search)
        self.toolbar.view_mode_changed.connect(self.file_grid.set_view_mode)
        self.toolbar.sort_changed.connect(self.file_grid.sort_files)
        self.toolbar.sync_requested.connect(self._on_sync_requested)

    def _on_category_selected(self, category: str):
        self.file_grid.filter_by_category(category)
        count = len(self.file_grid.displayed_files)
        self.status_label.setText(f"Category: {category.capitalize()} | {count} file(s)")

    def _on_folder_selected(self, folder_name: str):
        self.file_grid.filter_by_folder(folder_name)
        count = len(self.file_grid.displayed_files)
        self.status_label.setText(f"Folder: {folder_name} | {count} file(s)")

    def _on_breadcrumb_navigated(self, item_type: str, path_val: str):
        self.sidebar.select_by_path(path_val)
        if item_type == "category":
            self._on_category_selected(path_val)
        else:
            self._on_folder_selected(path_val)

    def _on_file_relocated(self, file_data: dict, target_folder: str):
        self.status_label.setText(f"Moved '{file_data['name']}' to '{target_folder}'")

    def _on_sync_requested(self):
        QMessageBox.information(
            self,
            "Sync Telegram",
            "Telegram sync requested.\n\n"
            "Kredensial Telegram sudah terdeteksi di config/settings.json.\n"
            "Di Langkah 4, tombol ini akan menghubungkan sesi Telethon Anda dan mengunduh pesan terbaru dari Saved Messages.",
        )
