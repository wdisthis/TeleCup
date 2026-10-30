"""Responsive file grid with flexible-width cards, drag-and-drop to folders, transparent text labels, and breadcrumbs."""

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QApplication,
)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QRect, QMimeData
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QDrag


def create_file_badge_icon(ext: str, bg_hex: str = "#475569") -> QIcon:
    """Generate a crisp file badge icon."""
    width = 42
    height = 42
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor(bg_hex))
    painter.setPen(QColor("#52525b"))
    painter.drawRoundedRect(1, 1, width - 2, height - 2, 6, 6)

    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 9, QFont.Bold)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, width, height), Qt.AlignCenter, ext.upper()[:4])
    painter.end()

    return QIcon(pixmap)


BADGE_COLORS = {
    "pdf": "#991b1b",
    "png": "#0369a1",
    "jpg": "#0369a1",
    "jpeg": "#0369a1",
    "zip": "#b45309",
    "rar": "#b45309",
    "mp3": "#6d28d9",
    "mp4": "#4338ca",
    "docx": "#1d4ed8",
    "doc": "#1d4ed8",
    "txt": "#475569",
}


class FileCardWidget(QFrame):
    """Flexible card with drag support (drag to sidebar folders) and 100% transparent label backgrounds."""

    card_clicked = Signal(dict)
    card_double_clicked = Signal(dict)
    card_context_menu = Signal(dict, QPoint)

    def __init__(self, file_data: dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.is_selected = False
        self.drag_start_pos = None

        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(200)
        self.setMaximumWidth(360)
        self.setFixedHeight(126)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._init_ui()
        self._update_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Badge Icon
        ext = self.file_data.get("ext", "file").lower()
        badge_color = BADGE_COLORS.get(ext, "#475569")
        icon = create_file_badge_icon(ext, badge_color)

        icon_label = QLabel()
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_label.setPixmap(icon.pixmap(40, 40))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # 2. File Name (100% Transparent background, no dark patches)
        fav_tag = "[Fav] " if self.file_data.get("is_fav") else ""
        name_text = f"{fav_tag}{self.file_data['name']}"
        self.name_label = QLabel(name_text)
        self.name_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            "background: transparent; background-color: transparent; border: none; color: #f4f4f5; font-size: 11px; font-weight: 500;"
        )
        layout.addWidget(self.name_label)

        # 3. Meta (Size | Date)
        date_short = self.file_data["date"].split()[0]
        meta_text = f"{self.file_data['size_str']}  |  {date_short}"
        meta_label = QLabel(meta_text)
        meta_label.setAttribute(Qt.WA_TranslucentBackground, True)
        meta_label.setAlignment(Qt.AlignCenter)
        meta_label.setStyleSheet(
            "background: transparent; background-color: transparent; border: none; color: #a1a1aa; font-size: 10px;"
        )
        layout.addWidget(meta_label)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet(
                """
                FileCardWidget {
                    background-color: #1a2c42;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                }
                FileCardWidget QLabel {
                    background: transparent;
                    background-color: transparent;
                    border: none;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                FileCardWidget {
                    background-color: #222226;
                    border: 1px solid #333338;
                    border-radius: 8px;
                }
                FileCardWidget:hover {
                    background-color: #2a2a30;
                    border-color: #4b4b54;
                }
                FileCardWidget QLabel {
                    background: transparent;
                    background-color: transparent;
                    border: none;
                }
                """
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            self.card_clicked.emit(self.file_data)
        elif event.button() == Qt.RightButton:
            self.card_context_menu.emit(self.file_data, event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Controlled drag-and-drop: can drag to move into folders, but stays aligned in grid
        if event.buttons() & Qt.LeftButton and self.drag_start_pos:
            distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData("application/x-telecup-file", str(self.file_data["id"]).encode("utf-8"))
                mime.setText(self.file_data["name"])
                drag.setMimeData(mime)

                # Semi-transparent ghost preview following the cursor
                ghost = self.grab()
                drag.setPixmap(ghost)
                drag.setHotSpot(self.drag_start_pos)
                drag.exec(Qt.MoveAction)
                self.drag_start_pos = None
                return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_double_clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)


class FileGridWidget(QWidget):
    """Main file view with flexible-width responsive cards, breadcrumbs, and folder drop handling."""

    file_opened = Signal(dict)
    breadcrumb_navigated = Signal(str, str)
    file_relocated = Signal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_files = []
        self.displayed_files = []
        self.current_location = ("category", "all")
        self.card_widgets = []
        self.selected_card = None

        self._init_ui()
        self._load_dummy_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        # ── 1. Breadcrumb Path Bar ──
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(6)
        layout.addWidget(self.breadcrumb_container)

        # ── 2. View Container (Grid / List) ──
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # ── Responsive Grid with Flexible-Width Cards ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: 1px solid #27272a;
                border-radius: 8px;
                background-color: #18181b;
            }
            """
        )

        self.grid_content = QWidget()
        self.grid_content.setStyleSheet("background-color: #18181b;")
        self.grid_layout = QGridLayout(self.grid_content)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_content)
        self.stack.addWidget(self.scroll_area)  # index 0

        # ── List View ──
        self.list_view = QTableWidget()
        self.list_view.setColumnCount(5)
        self.list_view.setHorizontalHeaderLabels([
            "Name", "Category", "Size", "Date Added", "Telegram Source"
        ])
        self.list_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.list_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.list_view.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.list_view.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_view.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_view.verticalHeader().setVisible(False)
        self.list_view.verticalHeader().setDefaultSectionSize(40)
        self.list_view.setShowGrid(False)
        self.list_view.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #27272a;
                border-radius: 8px;
                background-color: #18181b;
                color: #e4e4e7;
                font-size: 12px;
                outline: none;
            }
            QTableWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid #222226;
            }
            QTableWidget::item:selected {
                background-color: #1a2c42;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1f1f23;
                color: #a1a1aa;
                padding: 10px 14px;
                border: none;
                border-bottom: 1px solid #333338;
                font-weight: 600;
                font-size: 12px;
            }
            """
        )
        self.list_view.cellDoubleClicked.connect(self._on_table_double_click)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._open_table_context_menu)

        self.stack.addWidget(self.list_view)  # index 1

        self.update_breadcrumb("category", "all")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalculate_grid_columns()

    def _recalculate_grid_columns(self):
        """Auto-calculate columns and stretch cards flexibly to fill the entire row width."""
        if not self.card_widgets:
            return

        viewport_w = self.scroll_area.viewport().width()
        min_card_w = 210
        gap = 16
        padding = 32

        available = max(min_card_w, viewport_w - padding)
        cols = max(1, available // (min_card_w + gap))

        # Clear existing column stretches
        for c in range(12):
            self.grid_layout.setColumnStretch(c, 0)

        # Distribute cards in grid and set column stretch so they fill the width evenly
        for idx, card in enumerate(self.card_widgets):
            self.grid_layout.removeWidget(card)
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

    def refresh_display(self):
        for card in self.card_widgets:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.card_widgets.clear()
        self.selected_card = None

        for f in self.displayed_files:
            card = FileCardWidget(f)
            card.card_clicked.connect(self._on_card_clicked)
            card.card_double_clicked.connect(self._on_card_double_click)
            card.card_context_menu.connect(self._on_card_context_menu)
            self.card_widgets.append(card)

        self._recalculate_grid_columns()

        # Update List View
        self.list_view.setRowCount(len(self.displayed_files))
        for row, f in enumerate(self.displayed_files):
            fav_tag = "[Fav] " if f.get("is_fav") else ""
            name_item = QTableWidgetItem(f"{fav_tag}{f['name']}")
            name_item.setData(Qt.UserRole, f)

            cat_item = QTableWidgetItem(f["category"].capitalize())
            size_item = QTableWidgetItem(f["size_str"])
            date_item = QTableWidgetItem(f["date"])
            msg_item = QTableWidgetItem(f["message"])

            for col, item in enumerate([name_item, cat_item, size_item, date_item, msg_item]):
                self.list_view.setItem(row, col, item)

    def move_file_to_folder(self, file_id: int, target_folder: str):
        """Handle moving a file to a new virtual folder (from drag & drop)."""
        target_file = None
        for f in self.all_files:
            if f["id"] == file_id:
                f["folder"] = target_folder
                target_file = f
                break

        if target_file:
            # Re-filter and refresh
            item_type, val = self.current_location
            if item_type == "category":
                self.filter_by_category(val)
            else:
                self.filter_by_folder(val)
            self.file_relocated.emit(target_file, target_folder)

    def _on_card_clicked(self, file_data: dict):
        for card in self.card_widgets:
            card.set_selected(card.file_data["id"] == file_data["id"])
        self.selected_card = file_data

    def _on_card_double_click(self, file_data: dict):
        self.file_opened.emit(file_data)
        self._show_info(file_data)

    def _on_card_context_menu(self, file_data: dict, global_pos: QPoint):
        self._on_card_clicked(file_data)
        self._show_context_menu(file_data, global_pos)

    def _on_table_double_click(self, row: int, col: int):
        item = self.list_view.item(row, 0)
        if item:
            file_data = item.data(Qt.UserRole)
            if file_data:
                self.file_opened.emit(file_data)
                self._show_info(file_data)

    def _open_table_context_menu(self, pos):
        item = self.list_view.item(self.list_view.currentRow(), 0)
        if item:
            file_data = item.data(Qt.UserRole)
            if file_data:
                self._show_context_menu(file_data, self.list_view.viewport().mapToGlobal(pos))

    def _show_context_menu(self, file_data: dict, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #222226;
                color: #e4e4e7;
                border: 1px solid #333338;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #60a5fa;
            }
            QMenu::separator {
                height: 1px;
                background-color: #333338;
                margin: 4px 0px;
            }
            """
        )
        open_action = menu.addAction("Open / Preview")
        show_action = menu.addAction("Show in Explorer")
        fav_action = menu.addAction("Toggle Favorite")
        menu.addSeparator()
        delete_action = menu.addAction("Remove from Vault")

        action = menu.exec(global_pos)
        if action == open_action:
            self._show_info(file_data)

    def _show_info(self, file_data: dict):
        QMessageBox.information(
            self,
            "File Details",
            f"File: {file_data['name']}\nSize: {file_data['size_str']}\nTelegram Ref: {file_data['message']}\nFolder: {file_data.get('folder', '-')}\n\n(Local file preview & open will be connected in Step 3)",
        )

    def update_breadcrumb(self, item_type: str, val: str, extra_label: str = None):
        self.current_location = (item_type, val)

        while self.breadcrumb_layout.count():
            w = self.breadcrumb_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        root_btn = QPushButton("Vault")
        root_btn.setCursor(Qt.PointingHandCursor)
        root_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 13px;
                font-weight: 500;
                padding: 2px 4px;
            }
            QPushButton:hover {
                color: #60a5fa;
                text-decoration: underline;
            }
            """
        )
        root_btn.clicked.connect(lambda: self.breadcrumb_navigated.emit("category", "all"))
        self.breadcrumb_layout.addWidget(root_btn)

        if extra_label:
            self._add_separator()
            label = QLabel(extra_label)
            label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
            self.breadcrumb_layout.addWidget(label)
        elif item_type == "category":
            self._add_separator()
            cat_display = "All Files" if val == "all" else val.capitalize()
            label = QLabel(cat_display)
            label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
            self.breadcrumb_layout.addWidget(label)
        elif item_type == "folder":
            parts = val.split(" / ")
            accum = []
            for i, part in enumerate(parts):
                self._add_separator()
                accum.append(part)
                curr_path = " / ".join(accum)
                is_last = (i == len(parts) - 1)

                if is_last:
                    leaf_label = QLabel(part)
                    leaf_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
                    self.breadcrumb_layout.addWidget(leaf_label)
                else:
                    crumb_btn = QPushButton(part)
                    crumb_btn.setCursor(Qt.PointingHandCursor)
                    crumb_btn.setStyleSheet(
                        """
                        QPushButton {
                            background: transparent;
                            border: none;
                            color: #94a3b8;
                            font-size: 13px;
                            font-weight: 500;
                            padding: 2px 4px;
                        }
                        QPushButton:hover {
                            color: #60a5fa;
                            text-decoration: underline;
                        }
                        """
                    )
                    crumb_btn.clicked.connect(lambda _, p=curr_path: self.breadcrumb_navigated.emit("folder", p))
                    self.breadcrumb_layout.addWidget(crumb_btn)

        self.breadcrumb_layout.addStretch(1)
        count_label = QLabel(f"{len(self.displayed_files)} item(s)")
        count_label.setStyleSheet("color: #71717a; font-size: 12px; padding-right: 4px;")
        self.breadcrumb_layout.addWidget(count_label)

    def _add_separator(self):
        sep = QLabel("›")
        sep.setStyleSheet("color: #52525b; font-size: 14px; font-weight: bold;")
        self.breadcrumb_layout.addWidget(sep)

    def set_view_mode(self, mode: str):
        if mode == "grid":
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)

    def _load_dummy_data(self):
        self.all_files = [
            {
                "id": 1,
                "name": "Python_CheatSheet_v2.pdf",
                "ext": "pdf",
                "category": "documents",
                "size_str": "2.4 MB",
                "size_bytes": 2516582,
                "date": "2026-10-28 14:20",
                "message": "#1042 - Quick Python Guide",
                "folder": "Learning & E-books",
                "is_fav": True,
            },
            {
                "id": 2,
                "name": "Server_Architecture_Diagram.png",
                "ext": "png",
                "category": "images",
                "size_str": "1.8 MB",
                "size_bytes": 1887436,
                "date": "2026-10-27 09:12",
                "message": "#1039 - Diagram final",
                "folder": "Work Projects / 2026 / Q4 Deliverables",
                "is_fav": False,
            },
            {
                "id": 3,
                "name": "Backup_Database_Postgres.zip",
                "ext": "zip",
                "category": "archives",
                "size_str": "14.5 MB",
                "size_bytes": 15204352,
                "date": "2026-10-25 18:00",
                "message": "#1025 - DB Dump",
                "folder": "Work Projects / 2026",
                "is_fav": False,
            },
            {
                "id": 4,
                "name": "Meeting_Audio_Transcript.mp3",
                "ext": "mp3",
                "category": "media",
                "size_str": "8.2 MB",
                "size_bytes": 8598323,
                "date": "2026-10-24 11:30",
                "message": "#1010 - Voice note recording",
                "folder": "Work Projects / Client Reviews",
                "is_fav": True,
            },
            {
                "id": 5,
                "name": "Receipt_Hosting_AWS_Oct26.pdf",
                "ext": "pdf",
                "category": "documents",
                "size_str": "420 KB",
                "size_bytes": 430080,
                "date": "2026-10-20 08:45",
                "message": "#980 - Server invoice",
                "folder": "Receipts & Finance / Tax 2026",
                "is_fav": False,
            },
            {
                "id": 6,
                "name": "App_Demo_Walkthrough.mp4",
                "ext": "mp4",
                "category": "media",
                "size_str": "35.1 MB",
                "size_bytes": 36805017,
                "date": "2026-10-18 20:15",
                "message": "#964 - Demo testing video",
                "folder": "Learning & E-books",
                "is_fav": False,
            },
        ]
        self.displayed_files = list(self.all_files)
        self.refresh_display()

    def filter_by_category(self, category: str):
        if category == "all":
            self.displayed_files = list(self.all_files)
        elif category == "favorites":
            self.displayed_files = [f for f in self.all_files if f.get("is_fav")]
        else:
            self.displayed_files = [f for f in self.all_files if f.get("category") == category]
        self.update_breadcrumb("category", category)
        self.refresh_display()

    def filter_by_folder(self, folder_path: str):
        self.displayed_files = [
            f for f in self.all_files
            if f.get("folder", "") == folder_path or f.get("folder", "").startswith(f"{folder_path} /")
        ]
        self.update_breadcrumb("folder", folder_path)
        self.refresh_display()

    def filter_by_search(self, query: str):
        query = query.strip().lower()
        if not query:
            item_type, val = self.current_location
            if item_type == "category":
                self.filter_by_category(val)
            else:
                self.filter_by_folder(val)
        else:
            self.displayed_files = [
                f for f in self.all_files
                if query in f["name"].lower() or query in f["message"].lower()
            ]
            self.update_breadcrumb("search", query, extra_label=f'Search: "{query}"')
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
