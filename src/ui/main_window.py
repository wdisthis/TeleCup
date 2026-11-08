"""Main application window connecting SQLite Database to PySide6 UI."""

from typing import Optional
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

from ..database import DatabaseManager
from .sidebar import SidebarWidget
from .toolbar import ToolbarWidget
from .file_grid import FileGridWidget


class MainWindow(QMainWindow):
    """Main window coordinating SQLite database with UI widgets."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeleCup - Saved Messages Vault")
        self.resize(1160, 720)
        self.setMinimumSize(900, 560)

        # 1. Initialize SQLite Database
        self.db = DatabaseManager()

        # 2. State Tracking
        self.current_category: Optional[str] = "all"
        self.current_folder_id: Optional[int] = None
        self.current_folder_path: str = ""
        self.current_search: str = ""
        self.current_sort: str = "date_desc"

        # 3. Build UI & Wire Signals
        self._init_ui()
        self._connect_signals()

        # 4. Initial Load from SQLite
        self._refresh_vault()

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

        self.sidebar = SidebarWidget(self.db, self)
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

        self.status_label = QLabel("Loading vault...")
        self.status_label.setStyleSheet("color: #a1a1aa;")
        self.status_bar.addWidget(self.status_label)

        self.sync_status_label = QLabel("Database: SQLite Connected")
        self.sync_status_label.setStyleSheet("color: #3b82f6; font-weight: 500; margin-right: 12px;")
        self.status_bar.addPermanentWidget(self.sync_status_label)

    def _connect_signals(self):
        # Sidebar Events
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.sidebar.folder_selected.connect(self._on_folder_selected)
        self.sidebar.sync_requested.connect(self._on_sync_requested)
        self.sidebar.file_dropped_on_folder.connect(self._on_file_dropped_on_folder)

        # File & Folder Grid Events
        self.file_grid.folder_navigated.connect(self._on_folder_navigated_from_grid)
        self.file_grid.file_dropped_on_folder.connect(self._on_file_dropped_on_folder)
        self.file_grid.breadcrumb_navigated.connect(self._on_breadcrumb_navigated)
        self.file_grid.toggle_favorite_requested.connect(self._on_toggle_favorite)
        self.file_grid.delete_file_requested.connect(self._on_delete_file)

        # Toolbar Events
        self.toolbar.search_changed.connect(self._on_search_changed)
        self.toolbar.view_mode_changed.connect(self.file_grid.set_view_mode)
        self.toolbar.sort_changed.connect(self._on_sort_changed)
        self.toolbar.sync_requested.connect(self._on_sync_requested)

    def _refresh_vault(self):
        """Query SQLite database for child folders AND files, then refresh display."""
        # Query child folders if currently viewing a folder
        subfolders = []
        if not self.current_search:
            if self.current_folder_id is not None:
                subfolders = self.db.get_subfolders(self.current_folder_id)

        # Query files
        files = self.db.get_files(
            category=self.current_category,
            folder_id=self.current_folder_id,
            search_query=self.current_search,
            sort_key=self.current_sort,
        )

        self.file_grid.set_data(subfolders, files)

        # Update Status Bar Text
        summary = []
        if subfolders:
            summary.append(f"{len(subfolders)} folder(s)")
        if files:
            summary.append(f"{len(files)} file(s)")
        count_str = ", ".join(summary) if summary else "0 items"

        if self.current_search:
            self.status_label.setText(f'Search: "{self.current_search}" | {len(files)} file(s) found')
        elif self.current_folder_id is not None:
            self.status_label.setText(f"Folder: {self.current_folder_path} | {count_str}")
        else:
            cat_name = "All Files" if self.current_category == "all" else (self.current_category or "").capitalize()
            self.status_label.setText(f"Category: {cat_name} | {count_str}")

    def _on_category_selected(self, category_key: str):
        self.current_category = category_key
        self.current_folder_id = None
        self.current_folder_path = ""
        self.file_grid.update_breadcrumb("category", category_key)
        self._refresh_vault()

    def _on_folder_selected(self, folder_id: int, full_path: str):
        self.current_category = None
        self.current_folder_id = folder_id
        self.current_folder_path = full_path
        self.file_grid.update_breadcrumb("folder", full_path)
        self._refresh_vault()

    def _on_folder_navigated_from_grid(self, folder_id: int, full_path: str):
        """User double clicked a child folder card in the main view."""
        self.sidebar.select_folder_by_id(folder_id)
        self._on_folder_selected(folder_id, full_path)

    def _on_file_dropped_on_folder(self, file_id: int, target_folder_id: int):
        self.db.move_file_to_folder(file_id, target_folder_id)
        folder_path = self.db.get_folder_path(target_folder_id)
        self.status_label.setText(f"Moved file ID {file_id} to folder '{folder_path}' (Saved in SQLite)")
        self._refresh_vault()

    def _on_search_changed(self, query: str):
        self.current_search = query.strip()
        if self.current_search:
            self.file_grid.update_breadcrumb("search", self.current_search, extra_label=f'Search: "{self.current_search}"')
        else:
            if self.current_folder_id is not None:
                self.file_grid.update_breadcrumb("folder", self.current_folder_path)
            else:
                self.file_grid.update_breadcrumb("category", self.current_category or "all")
        self._refresh_vault()

    def _on_sort_changed(self, sort_key: str):
        self.current_sort = sort_key
        self._refresh_vault()

    def _on_toggle_favorite(self, file_id: int):
        new_state = self.db.toggle_favorite(file_id)
        state_str = "added to" if new_state else "removed from"
        self.status_label.setText(f"File {state_str} Favorites (Saved in SQLite)")
        self._refresh_vault()

    def _on_delete_file(self, file_id: int):
        self.db.delete_file(file_id)
        self.status_label.setText(f"File ID {file_id} removed from vault.")
        self._refresh_vault()

    def _on_breadcrumb_navigated(self, item_type: str, path_val: str):
        if item_type == "category":
            self.sidebar.select_category_by_key(path_val)
            self._on_category_selected(path_val)
        elif item_type == "folder":
            for f in self.db.get_all_folders():
                if self.db.get_folder_path(f["id"]) == path_val:
                    self.sidebar.select_folder_by_id(f["id"])
                    self._on_folder_selected(f["id"], path_val)
                    break

    def _on_sync_requested(self):
        QMessageBox.information(
            self,
            "Sync Telegram",
            "Telegram sync requested.\n\n"
            "Database SQLite (storage/vault.db) sudah aktif dan siap menampung data.\n"
            "Di Langkah 4, modul telethon akan dihubungkan untuk menyinkronkan Saved Messages secara riil.",
        )
