"""Main application window for TeleCup."""

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
from PySide6.QtGui import QIcon

from .sidebar import SidebarWidget
from .toolbar import ToolbarWidget
from .file_grid import FileGridWidget


class MainWindow(QMainWindow):
    """Main window coordinating sidebar, toolbar, file grid, and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeleCup - Saved Messages Vault")
        self.resize(1120, 720)
        self.setMinimumSize(850, 550)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        central_widget = QWidget(self)
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
        divider.setStyleSheet("background-color: #e0e0e0;")
        root_layout.addWidget(divider)

        # ── 2. Splitter (Sidebar + Content View) ──
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            """
        )

        self.sidebar = SidebarWidget(self)
        self.file_grid = FileGridWidget(self)

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.file_grid)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        root_layout.addWidget(self.splitter, stretch=1)

        # ── 3. Status Bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready • 6 files in local vault")
        self.status_bar.addWidget(self.status_label)

        self.sync_status_label = QLabel("Telegram: Configured (ready to link)")
        self.sync_status_label.setStyleSheet("color: #1a73e8; font-weight: 500; margin-right: 12px;")
        self.status_bar.addPermanentWidget(self.sync_status_label)

    def _connect_signals(self):
        # Navigation
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.sidebar.folder_selected.connect(self._on_folder_selected)

        # Toolbar controls
        self.toolbar.search_changed.connect(self.file_grid.filter_by_search)
        self.toolbar.view_mode_changed.connect(self.file_grid.set_view_mode)
        self.toolbar.sort_changed.connect(self.file_grid.sort_files)
        self.toolbar.sync_requested.connect(self._on_sync_requested)

    def _on_category_selected(self, category: str):
        self.file_grid.filter_by_category(category)
        count = len(self.file_grid.displayed_files)
        self.status_label.setText(f"Category: {category.capitalize()} • {count} file(s)")

    def _on_folder_selected(self, folder_name: str):
        self.file_grid.filter_by_folder(folder_name)
        count = len(self.file_grid.displayed_files)
        self.status_label.setText(f"Folder: {folder_name} • {count} file(s)")

    def _on_sync_requested(self):
        QMessageBox.information(
            self,
            "Sync Telegram",
            "Telegram sync requested!\n\n"
            "Kredensial Telegram sudah terdeteksi di config/settings.json.\n"
            "Di Langkah 4, tombol ini akan menghubungkan sesi Telethon Anda dan mengunduh pesan terbaru dari Saved Messages.",
        )

