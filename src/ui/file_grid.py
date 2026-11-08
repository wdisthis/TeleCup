"""Responsive file and folder grid with compact drag preview, Google Drive folder cards, and drop highlight."""

from typing import List, Dict, Any, Optional
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
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QFont,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QPen,
)


def create_file_badge_icon(ext: str, bg_hex: str = "#475569") -> QIcon:
    """Generate crisp file badge without external image assets."""
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


def create_folder_badge_icon() -> QIcon:
    """Generate clean folder icon for child folder cards."""
    width = 42
    height = 42
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor("#2563eb"))
    painter.setPen(QColor("#3b82f6"))
    painter.drawRoundedRect(2, 6, width - 4, height - 10, 6, 6)
    painter.drawRoundedRect(2, 2, 18, 10, 3, 3)

    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 8, QFont.Bold)
    painter.setFont(font)
    painter.drawText(QRect(0, 4, width, height - 4), Qt.AlignCenter, "DIR")
    painter.end()

    return QIcon(pixmap)


def create_compact_drag_pill(file_data: dict) -> QPixmap:
    """Create a sleek, compact floating pill for dragging so it never blocks what's underneath."""
    w, h = 160, 32
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Pill Background
    painter.setBrush(QColor(30, 41, 59, 235))
    painter.setPen(QPen(QColor("#3b82f6"), 1.5))
    painter.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

    # Mini Badge
    ext = file_data.get("ext", "file").upper()[:4]
    badge_bg = BADGE_COLORS.get(file_data.get("ext", "").lower(), "#475569")
    painter.setBrush(QColor(badge_bg))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(5, 5, 26, 22, 4, 4)

    painter.setPen(QColor("#ffffff"))
    badge_font = QFont("Segoe UI", 7, QFont.Bold)
    painter.setFont(badge_font)
    painter.drawText(QRect(5, 5, 26, 22), Qt.AlignCenter, ext)

    # Truncated File Name
    name = file_data.get("name", "")
    painter.setPen(QColor("#f4f4f5"))
    name_font = QFont("Segoe UI", 9, QFont.Medium)
    painter.setFont(name_font)
    text_rect = QRect(36, 0, w - 42, h)
    metrics = painter.fontMetrics()
    elided = metrics.elidedText(name, Qt.ElideMiddle, text_rect.width())
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

    painter.end()
    return pixmap


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


class FolderCardWidget(QFrame):
    """Google Drive style child folder card with vivid dashed highlight on drag-hover."""

    folder_clicked = Signal(dict)
    folder_double_clicked = Signal(dict)
    file_dropped_here = Signal(int, int)

    def __init__(self, folder_data: dict, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.is_selected = False
        self.is_drop_target = False
        self.setAcceptDrops(True)

        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(200)
        self.setMaximumWidth(360)
        self.setFixedHeight(82)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._init_ui()
        self._update_style()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignVCenter)

        icon_label = QLabel()
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_label.setPixmap(create_folder_badge_icon().pixmap(38, 38))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignVCenter)

        safe_name = self.folder_data["name"].replace("&", "&&")
        self.name_label = QLabel(safe_name)
        self.name_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.name_label.setStyleSheet(
            "background: transparent; border: none; color: #f4f4f5; font-size: 13px; font-weight: 600;"
        )
        text_layout.addWidget(self.name_label)

        direct_files = self.folder_data.get("direct_files", 0)
        sub_count = self.folder_data.get("subfolders_count", 0)
        meta_parts = []
        if sub_count > 0:
            meta_parts.append(f"{sub_count} subfolder(s)")
        if direct_files > 0:
            meta_parts.append(f"{direct_files} file(s)")
        meta_str = " • ".join(meta_parts) if meta_parts else "Empty folder"

        self.meta_label = QLabel(meta_str)
        self.meta_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.meta_label.setStyleSheet(
            "background: transparent; border: none; color: #a1a1aa; font-size: 11px;"
        )
        text_layout.addWidget(self.meta_label)

        layout.addLayout(text_layout, stretch=1)

        chevron = QLabel("›")
        chevron.setStyleSheet("color: #71717a; font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(chevron)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()

    def set_drop_target(self, is_target: bool):
        self.is_drop_target = is_target
        self._update_style()

    def _update_style(self):
        if self.is_drop_target:
            self.setStyleSheet(
                """
                FolderCardWidget {
                    background-color: #1e3a5f;
                    border: 2px dashed #60a5fa;
                    border-radius: 8px;
                }
                """
            )
        elif self.is_selected:
            self.setStyleSheet(
                """
                FolderCardWidget {
                    background-color: #1a2c42;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                FolderCardWidget {
                    background-color: #202024;
                    border: 1px solid #333338;
                    border-radius: 8px;
                }
                FolderCardWidget:hover {
                    background-color: #27272e;
                    border-color: #4b4b54;
                }
                """
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.folder_clicked.emit(self.folder_data)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.folder_double_clicked.emit(self.folder_data)
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            self.set_drop_target(True)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            if not self.is_drop_target:
                self.set_drop_target(True)
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.set_drop_target(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.set_drop_target(False)
        if event.mimeData().hasFormat("application/x-telecup-file"):
            file_id = int(event.mimeData().data("application/x-telecup-file").data().decode("utf-8"))
            self.file_dropped_here.emit(file_id, self.folder_data["id"])
            event.acceptProposedAction()


class FileCardWidget(QFrame):
    """Flexible card with compact drag preview and 100% transparent label backgrounds."""

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

        ext = self.file_data.get("ext", "file").lower()
        badge_color = BADGE_COLORS.get(ext, "#475569")
        icon = create_file_badge_icon(ext, badge_color)

        icon_label = QLabel()
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_label.setPixmap(icon.pixmap(40, 40))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        fav_tag = "[Fav] " if self.file_data.get("is_fav") else ""
        safe_name = f"{fav_tag}{self.file_data['name']}".replace("&", "&&")
        self.name_label = QLabel(safe_name)
        self.name_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            "background: transparent; border: none; color: #f4f4f5; font-size: 11px; font-weight: 500;"
        )
        layout.addWidget(self.name_label)

        date_short = self.file_data.get("date_added", self.file_data.get("date", "")).split()[0]
        meta_text = f"{self.file_data['size_str']}  |  {date_short}"
        meta_label = QLabel(meta_text)
        meta_label.setAttribute(Qt.WA_TranslucentBackground, True)
        meta_label.setAlignment(Qt.AlignCenter)
        meta_label.setStyleSheet(
            "background: transparent; border: none; color: #a1a1aa; font-size: 10px;"
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
        if event.buttons() & Qt.LeftButton and self.drag_start_pos:
            distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData("application/x-telecup-file", str(self.file_data["id"]).encode("utf-8"))
                mime.setText(self.file_data["name"])
                drag.setMimeData(mime)

                # Use compact floating pill (160x32px) so cursor and target folders remain 100% visible
                preview = create_compact_drag_pill(self.file_data)
                drag.setPixmap(preview)
                drag.setHotSpot(QPoint(12, 16))
                drag.exec(Qt.MoveAction)
                self.drag_start_pos = None
                return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_double_clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)


class FileGridWidget(QWidget):
    """File & Folder display area rendering child folder cards, file cards, and breadcrumb bar."""

    file_opened = Signal(dict)
    folder_navigated = Signal(int, str)
    file_dropped_on_folder = Signal(int, int)
    breadcrumb_navigated = Signal(str, str)
    toggle_favorite_requested = Signal(int)
    delete_file_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.displayed_folders: List[Dict[str, Any]] = []
        self.displayed_files: List[Dict[str, Any]] = []
        self.current_location = ("category", "all")
        self.folder_widgets: List[FolderCardWidget] = []
        self.card_widgets: List[FileCardWidget] = []
        self.header_widgets: List[QWidget] = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(6)
        layout.addWidget(self.breadcrumb_container)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

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
        self.stack.addWidget(self.scroll_area)

        self.list_view = QTableWidget()
        self.list_view.setColumnCount(5)
        self.list_view.setHorizontalHeaderLabels([
            "Name", "Category / Type", "Size", "Date Added", "Telegram Source"
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

        self.stack.addWidget(self.list_view)

        self.update_breadcrumb("category", "all")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalculate_grid_columns()

    def _recalculate_grid_columns(self):
        if not self.folder_widgets and not self.card_widgets:
            return

        viewport_w = self.scroll_area.viewport().width()
        min_card_w = 210
        gap = 16
        padding = 32

        available = max(min_card_w, viewport_w - padding)
        cols = max(1, available // (min_card_w + gap))

        for c in range(12):
            self.grid_layout.setColumnStretch(c, 0)

        curr_row = 0

        if self.folder_widgets:
            if self.card_widgets:
                sec_label = QLabel("FOLDERS")
                sec_label.setStyleSheet("color: #71717a; font-weight: 700; font-size: 11px; padding: 4px 0px;")
                self.grid_layout.addWidget(sec_label, curr_row, 0, 1, cols)
                self.header_widgets.append(sec_label)
                curr_row += 1

            for idx, f_card in enumerate(self.folder_widgets):
                self.grid_layout.removeWidget(f_card)
                r = curr_row + (idx // cols)
                c = idx % cols
                self.grid_layout.addWidget(f_card, r, c)

            curr_row += (len(self.folder_widgets) + cols - 1) // cols

        if self.card_widgets:
            if self.folder_widgets:
                sec_label = QLabel("FILES")
                sec_label.setStyleSheet("color: #71717a; font-weight: 700; font-size: 11px; padding: 12px 0px 4px 0px;")
                self.grid_layout.addWidget(sec_label, curr_row, 0, 1, cols)
                self.header_widgets.append(sec_label)
                curr_row += 1

            for idx, card in enumerate(self.card_widgets):
                self.grid_layout.removeWidget(card)
                r = curr_row + (idx // cols)
                c = idx % cols
                self.grid_layout.addWidget(card, r, c)

        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

    def set_data(self, subfolders: List[Dict[str, Any]], files: List[Dict[str, Any]]):
        self.displayed_folders = subfolders
        self.displayed_files = files

        for w in self.header_widgets:
            self.grid_layout.removeWidget(w)
            w.deleteLater()
        self.header_widgets.clear()

        for f_card in self.folder_widgets:
            self.grid_layout.removeWidget(f_card)
            f_card.deleteLater()
        self.folder_widgets.clear()

        for card in self.card_widgets:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.card_widgets.clear()

        for f in self.displayed_folders:
            f_card = FolderCardWidget(f)
            f_card.folder_clicked.connect(self._on_folder_clicked)
            f_card.folder_double_clicked.connect(self._on_folder_double_clicked)
            f_card.file_dropped_here.connect(self.file_dropped_on_folder.emit)
            self.folder_widgets.append(f_card)

        for f in self.displayed_files:
            card = FileCardWidget(f)
            card.card_clicked.connect(self._on_card_clicked)
            card.card_double_clicked.connect(self._on_card_double_click)
            card.card_context_menu.connect(self._on_card_context_menu)
            self.card_widgets.append(card)

        self._recalculate_grid_columns()

        total_rows = len(self.displayed_folders) + len(self.displayed_files)
        self.list_view.setRowCount(total_rows)

        row_idx = 0
        for f in self.displayed_folders:
            safe_name = f["name"].replace("&", "&&")
            name_item = QTableWidgetItem(f"[Folder]  {safe_name}")
            name_item.setData(Qt.UserRole, {"type": "folder", "data": f})
            type_item = QTableWidgetItem("Folder")
            size_item = QTableWidgetItem("-")
            date_item = QTableWidgetItem("-")
            source_item = QTableWidgetItem(f["path"])
            for col, item in enumerate([name_item, type_item, size_item, date_item, source_item]):
                self.list_view.setItem(row_idx, col, item)
            row_idx += 1

        for f in self.displayed_files:
            fav_tag = "[Fav] " if f.get("is_fav") else ""
            safe_name = f"{fav_tag}{f['name']}".replace("&", "&&")
            name_item = QTableWidgetItem(safe_name)
            name_item.setData(Qt.UserRole, {"type": "file", "data": f})
            cat_item = QTableWidgetItem(f["category"].capitalize())
            size_item = QTableWidgetItem(f["size_str"])
            date_item = QTableWidgetItem(f.get("date_added", f.get("date", "")))
            msg_item = QTableWidgetItem(f.get("message", ""))
            for col, item in enumerate([name_item, cat_item, size_item, date_item, msg_item]):
                self.list_view.setItem(row_idx, col, item)
            row_idx += 1

        item_type, val = self.current_location
        self.update_breadcrumb(item_type, val)

    def set_view_mode(self, mode: str):
        if mode == "grid":
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)

    def _on_folder_clicked(self, folder_data: dict):
        for f_card in self.folder_widgets:
            f_card.set_selected(f_card.folder_data["id"] == folder_data["id"])
        for card in self.card_widgets:
            card.set_selected(False)

    def _on_folder_double_clicked(self, folder_data: dict):
        self.folder_navigated.emit(folder_data["id"], folder_data["path"])

    def _on_card_clicked(self, file_data: dict):
        for card in self.card_widgets:
            card.set_selected(card.file_data["id"] == file_data["id"])
        for f_card in self.folder_widgets:
            f_card.set_selected(False)

    def _on_card_double_click(self, file_data: dict):
        self.file_opened.emit(file_data)
        self._show_info(file_data)

    def _on_card_context_menu(self, file_data: dict, global_pos: QPoint):
        self._on_card_clicked(file_data)
        self._show_context_menu(file_data, global_pos)

    def _on_table_double_click(self, row: int, col: int):
        item = self.list_view.item(row, 0)
        if not item:
            return
        u_data = item.data(Qt.UserRole)
        if not u_data:
            return

        if u_data["type"] == "folder":
            self.folder_navigated.emit(u_data["data"]["id"], u_data["data"]["path"])
        else:
            file_data = u_data["data"]
            self.file_opened.emit(file_data)
            self._show_info(file_data)

    def _open_table_context_menu(self, pos):
        item = self.list_view.item(self.list_view.currentRow(), 0)
        if item:
            u_data = item.data(Qt.UserRole)
            if u_data and u_data["type"] == "file":
                self._show_context_menu(u_data["data"], self.list_view.viewport().mapToGlobal(pos))

    def _show_context_menu(self, file_data: dict, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #222226;
                color: #e4e4e7;
                border: 1px solid #333338;
                padding: 6px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 7px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
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
        
        fav_label = "Remove from Favorites" if file_data.get("is_fav") else "Add to Favorites"
        fav_action = menu.addAction(fav_label)
        
        menu.addSeparator()
        delete_action = menu.addAction("Delete from Vault")

        action = menu.exec(global_pos)
        if action == open_action:
            self._show_info(file_data)
        elif action == fav_action:
            self.toggle_favorite_requested.emit(file_data["id"])
        elif action == delete_action:
            confirm = QMessageBox.question(
                self,
                "Delete File",
                f"Remove '{file_data['name']}' from TeleCup Vault?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm == QMessageBox.Yes:
                self.delete_file_requested.emit(file_data["id"])

    def _show_info(self, file_data: dict):
        folder_display = file_data.get("folder") or "Unassigned"
        QMessageBox.information(
            self,
            "File Details",
            f"File: {file_data['name']}\nSize: {file_data['size_str']}\nTelegram Ref: {file_data.get('message', '-')}\nFolder: {folder_display}\n\n(Local file preview & open will be connected in Step 4)",
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
            label = QLabel(extra_label.replace("&", "&&"))
            label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
            self.breadcrumb_layout.addWidget(label)
        elif item_type == "category":
            self._add_separator()
            cat_display = "All Files" if val == "all" else val.capitalize()
            label = QLabel(cat_display.replace("&", "&&"))
            label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
            self.breadcrumb_layout.addWidget(label)
        elif item_type == "folder":
            parts = val.split(" / ") if val else []
            accum = []
            for i, part in enumerate(parts):
                self._add_separator()
                accum.append(part)
                curr_path = " / ".join(accum)
                is_last = (i == len(parts) - 1)

                safe_part = part.replace("&", "&&")
                if is_last:
                    leaf_label = QLabel(safe_part)
                    leaf_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
                    self.breadcrumb_layout.addWidget(leaf_label)
                else:
                    crumb_btn = QPushButton(safe_part)
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

        counts = []
        if self.displayed_folders:
            counts.append(f"{len(self.displayed_folders)} folder(s)")
        if self.displayed_files:
            counts.append(f"{len(self.displayed_files)} file(s)")
        count_str = ", ".join(counts) if counts else "0 items"

        count_label = QLabel(count_str)
        count_label.setStyleSheet("color: #71717a; font-size: 12px; padding-right: 4px;")
        self.breadcrumb_layout.addWidget(count_label)

    def _add_separator(self):
        sep = QLabel("›")
        sep.setStyleSheet("color: #52525b; font-size: 14px; font-weight: bold;")
        self.breadcrumb_layout.addWidget(sep)
