"""File display area with Grid and List views."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QFont, QColor


class FileGridWidget(QWidget):
    """Main file view supporting switching between Grid and List views."""

    file_opened = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_files = []
        self.displayed_files = []
        self._init_ui()
        self._load_dummy_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # ── 1. Grid View ──
        self.grid_view = QListWidget()
        self.grid_view.setViewMode(QListWidget.IconMode)
        self.grid_view.setIconSize(QSize(64, 64))
        self.grid_view.setGridSize(QSize(130, 120))
        self.grid_view.setSpacing(12)
        self.grid_view.setResizeMode(QListWidget.Adjust)
        self.grid_view.setWordWrap(True)
        self.grid_view.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
                padding: 10px;
            }
            QListWidget::item {
                background-color: #ffffff;
                border: 1px solid #e8eaed;
                border-radius: 8px;
                padding: 8px;
                text-align: center;
            }
            QListWidget::item:hover {
                border: 1px solid #1a73e8;
                background-color: #f8fafd;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                border: 1.5px solid #1a73e8;
                color: #1967d2;
                font-weight: bold;
            }
            """
        )
        self.grid_view.itemDoubleClicked.connect(self._on_grid_double_click)
        self.grid_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid_view.customContextMenuRequested.connect(self._open_context_menu)

        # ── 2. List View ──
        self.list_view = QTableWidget()
        self.list_view.setColumnCount(5)
        self.list_view.setHorizontalHeaderLabels([
            "Name", "Category", "Size", "Date Added", "Telegram Message"
        ])
        self.list_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.list_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.list_view.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_view.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_view.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                gridline-color: #f1f3f4;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #dadce0;
                font-weight: bold;
                color: #5f6368;
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;
                color: #1967d2;
            }
            """
        )
        self.list_view.cellDoubleClicked.connect(self._on_table_double_click)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._open_context_menu)

        self.stack.addWidget(self.grid_view)  # index 0
        self.stack.addWidget(self.list_view)  # index 1

    def set_view_mode(self, mode: str):
        if mode == "grid":
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)

    def _load_dummy_data(self):
        """Initial dummy data mimicking saved messages files."""
        self.all_files = [
            {
                "id": 1,
                "name": "Python_CheatSheet_v2.pdf",
                "category": "documents",
                "size_str": "2.4 MB",
                "size_bytes": 2516582,
                "date": "2026-10-28 14:20",
                "message": "#1042 - Quick Python Guide",
                "folder": "Learning & E-books",
                "is_fav": True,
                "icon": "📄",
            },
            {
                "id": 2,
                "name": "Server_Architecture_Diagram.png",
                "category": "images",
                "size_str": "1.8 MB",
                "size_bytes": 1887436,
                "date": "2026-10-27 09:12",
                "message": "#1039 - Diagram final",
                "folder": "Work Projects",
                "is_fav": False,
                "icon": "🖼️",
            },
            {
                "id": 3,
                "name": "Backup_Database_Postgres.zip",
                "category": "archives",
                "size_str": "14.5 MB",
                "size_bytes": 15204352,
                "date": "2026-10-25 18:00",
                "message": "#1025 - DB Dump",
                "folder": "Work Projects",
                "is_fav": False,
                "icon": "🗜️",
            },
            {
                "id": 4,
                "name": "Meeting_Audio_Transcript.mp3",
                "category": "media",
                "size_str": "8.2 MB",
                "size_bytes": 8598323,
                "date": "2026-10-24 11:30",
                "message": "#1010 - Voice note rekaman",
                "folder": "Work Projects",
                "is_fav": True,
                "icon": "🎵",
            },
            {
                "id": 5,
                "name": "Receipt_Hosting_AWS_Oct26.pdf",
                "category": "documents",
                "size_str": "420 KB",
                "size_bytes": 430080,
                "date": "2026-10-20 08:45",
                "message": "#980 - Tagihan server",
                "folder": "Receipts & Finance",
                "is_fav": False,
                "icon": "📄",
            },
            {
                "id": 6,
                "name": "App_Demo_Walkthrough.mp4",
                "category": "media",
                "size_str": "35.1 MB",
                "size_bytes": 36805017,
                "date": "2026-10-18 20:15",
                "message": "#964 - Video testing",
                "folder": "Learning & E-books",
                "is_fav": False,
                "icon": "🎬",
            },
        ]
        self.displayed_files = list(self.all_files)
        self.refresh_display()

    def refresh_display(self):
        # 1. Populate Grid
        self.grid_view.clear()
        for f in self.displayed_files:
            star = "⭐ " if f.get("is_fav") else ""
            display_text = f"{star}{f['icon']} {f['name']}\n{f['size_str']}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, f)
            item.setTextAlignment(Qt.AlignCenter)
            self.grid_view.addItem(item)

        # 2. Populate List Table
        self.list_view.setRowCount(len(self.displayed_files))
        for row, f in enumerate(self.displayed_files):
            star = "⭐ " if f.get("is_fav") else ""
            name_item = QTableWidgetItem(f"{star}{f['icon']}  {f['name']}")
            name_item.setData(Qt.UserRole, f)

            cat_item = QTableWidgetItem(f["category"].capitalize())
            size_item = QTableWidgetItem(f["size_str"])
            date_item = QTableWidgetItem(f["date"])
            msg_item = QTableWidgetItem(f["message"])

            for col, item in enumerate([name_item, cat_item, size_item, date_item, msg_item]):
                self.list_view.setItem(row, col, item)

    def filter_by_category(self, category: str):
        if category == "all":
            self.displayed_files = list(self.all_files)
        elif category == "favorites":
            self.displayed_files = [f for f in self.all_files if f.get("is_fav")]
        else:
            self.displayed_files = [f for f in self.all_files if f.get("category") == category]
        self.refresh_display()

    def filter_by_folder(self, folder_name: str):
        self.displayed_files = [f for f in self.all_files if f.get("folder") == folder_name]
        self.refresh_display()

    def filter_by_search(self, query: str):
        query = query.strip().lower()
        if not query:
            self.displayed_files = list(self.all_files)
        else:
            self.displayed_files = [
                f for f in self.all_files
                if query in f["name"].lower() or query in f["message"].lower()
            ]
        self.refresh_display()

    def sort_files(self, sort_key: str):
        if sort_key == "name_asc":
            self.displayed_files.sort(key=lambda x: x["name"].lower())
        elif sort_key == "date_desc":
            self.displayed_files.sort(key=lambda x: x["date"], reverse=True)
        elif sort_key == "date_asc":
            self.displayed_files.sort(key=lambda x: x["date"])
        elif sort_key == "size_desc":
            self.displayed_files.sort(key=lambda x: x["size_bytes"], reverse=True)
        self.refresh_display()

    def _on_grid_double_click(self, item: QListWidgetItem):
        file_data = item.data(Qt.UserRole)
        if file_data:
            self.file_opened.emit(file_data)
            self._show_info(file_data)

    def _on_table_double_click(self, row: int, col: int):
        item = self.list_view.item(row, 0)
        if item:
            file_data = item.data(Qt.UserRole)
            if file_data:
                self.file_opened.emit(file_data)
                self._show_info(file_data)

    def _show_info(self, file_data: dict):
        QMessageBox.information(
            self,
            "File Preview",
            f"Opening: {file_data['name']}\nSize: {file_data['size_str']}\nTelegram Ref: {file_data['message']}\n\n(Local file opener will be connected in Step 3)",
        )

    def _open_context_menu(self, pos):
        menu = QMenu(self)
        open_action = menu.addAction("👁️ Open / Preview")
        show_action = menu.addAction("📂 Open in Explorer")
        fav_action = menu.addAction("⭐ Toggle Favorite")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Remove from Vault")

        action = menu.exec(self.sender().mapToGlobal(pos))
        if action == open_action:
            item = self.grid_view.currentItem() if self.stack.currentIndex() == 0 else self.list_view.item(self.list_view.currentRow(), 0)
            if item:
                self._show_info(item.data(Qt.UserRole))

