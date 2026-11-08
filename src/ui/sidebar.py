"""Sidebar component with high-visibility drag-and-drop folder target highlighting and auto-expansion."""

from pathlib import Path
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QInputDialog,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QSize, QPointF, QTimer
from PySide6.QtGui import (
    QFont,
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)

from ..database import DatabaseManager


def ensure_branch_icons() -> str:
    """Generate crisp branch chevrons to guarantee arrows never disappear on hover."""
    assets_dir = Path(__file__).resolve().parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    def draw_chevron(points, color_hex, filename):
        size = 14
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(points)
        painter.end()
        pixmap.save(str(assets_dir / filename))

    right_points = [QPointF(4.5, 3.5), QPointF(9.5, 7.0), QPointF(4.5, 10.5)]
    down_points = [QPointF(3.5, 4.5), QPointF(10.5, 4.5), QPointF(7.0, 9.5)]

    draw_chevron(right_points, "#a1a1aa", "branch_closed.png")
    draw_chevron(right_points, "#ffffff", "branch_closed_hover.png")
    draw_chevron(down_points, "#a1a1aa", "branch_open.png")
    draw_chevron(down_points, "#ffffff", "branch_open_hover.png")

    return str(assets_dir).replace("\\", "/")


def create_plus_icon(size: int = 15, color_hex: str = "#3b82f6") -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color_hex), 2.2, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    mid = size / 2.0
    pad = 2.0
    painter.drawLine(pad, mid, size - pad, mid)
    painter.drawLine(mid, pad, mid, size - pad)
    painter.end()
    return QIcon(pixmap)


class NavTreeWidget(QTreeWidget):
    """Custom TreeWidget with pinpoint accurate drag-hover tracking and auto-expand."""

    file_dropped = Signal(int, int)  # (file_id, target_folder_id)

    def __init__(self, sidebar, parent=None):
        super().__init__(parent)
        self.sidebar = sidebar
        self.setAcceptDrops(True)
        self.saved_selected_item: Optional[QTreeWidgetItem] = None
        self.drag_hover_item: Optional[QTreeWidgetItem] = None

        self.expand_timer = QTimer(self)
        self.expand_timer.setSingleShot(True)
        self.expand_timer.timeout.connect(self._auto_expand_hovered)

    def _auto_expand_hovered(self):
        if self.drag_hover_item and not self.drag_hover_item.isExpanded():
            self.drag_hover_item.setExpanded(True)

    def _get_target_item_at(self, pos) -> Optional[QTreeWidgetItem]:
        """Resolve item under cursor accurately with fallback to global cursor."""
        item = self.itemAt(pos)
        if not item:
            item = self.itemAt(self.viewport().mapFromGlobal(QCursor.pos()))
        return item

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            self.saved_selected_item = self.currentItem()
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            item = self._get_target_item_at(event.position().toPoint())

            if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole).get("type") == "folder":
                if self.drag_hover_item != item:
                    self.drag_hover_item = item
                    self.setCurrentItem(item)
                    self.expand_timer.start(500)
                event.acceptProposedAction()
                return
            else:
                self.drag_hover_item = None
                self.expand_timer.stop()
                if self.saved_selected_item:
                    self.setCurrentItem(self.saved_selected_item)

        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.expand_timer.stop()
        self.drag_hover_item = None
        if self.saved_selected_item:
            self.setCurrentItem(self.saved_selected_item)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.expand_timer.stop()
        target_item = self._get_target_item_at(event.position().toPoint())
        if not target_item:
            target_item = self.drag_hover_item

        self.drag_hover_item = None

        if event.mimeData().hasFormat("application/x-telecup-file"):
            if target_item and target_item.data(0, Qt.UserRole) and target_item.data(0, Qt.UserRole).get("type") == "folder":
                file_id = int(event.mimeData().data("application/x-telecup-file").data().decode("utf-8"))
                folder_id = target_item.data(0, Qt.UserRole).get("id")
                self.file_dropped.emit(file_id, folder_id)
                event.acceptProposedAction()
                return

        if self.saved_selected_item:
            self.setCurrentItem(self.saved_selected_item)
        super().dropEvent(event)


class SidebarWidget(QWidget):
    """Sidebar reading and persisting virtual folders directly in SQLite."""

    category_selected = Signal(str)
    folder_selected = Signal(int, str)
    file_dropped_on_folder = Signal(int, int)
    sync_requested = Signal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setMinimumWidth(220)
        self.setMaximumWidth(290)
        self.assets_path = ensure_branch_icons()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(14)

        # 1. App Title
        title_label = QLabel("TeleCup")
        title_font = QFont("Segoe UI", 13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #e4e4e7; padding: 2px 4px;")
        layout.addWidget(title_label)

        # 2. '+ New' Button
        btn_container = QHBoxLayout()
        btn_container.setContentsMargins(4, 0, 0, 0)

        self.new_btn = QPushButton("  New")
        self.new_btn.setIcon(create_plus_icon(15, "#3b82f6"))
        self.new_btn.setIconSize(QSize(15, 15))
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.setFixedHeight(38)
        self.new_btn.setMinimumWidth(118)
        self.new_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27272a;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #323238;
                border-color: #52525b;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #1f1f23;
            }
            QPushButton::menu-indicator {
                image: none;
                width: 0px;
            }
            """
        )
        self._setup_new_menu()
        btn_container.addWidget(self.new_btn)
        btn_container.addStretch(1)
        layout.addLayout(btn_container)

        # 3. Tree Widget with High-Contrast Vivid Selection & Drop Target
        self.tree = NavTreeWidget(self, self)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_tree_context_menu)
        self.tree.file_dropped.connect(self.file_dropped_on_folder.emit)

        p = self.assets_path
        self.tree.setStyleSheet(
            f"""
            QTreeWidget {{
                border: none;
                background-color: transparent;
                font-size: 13px;
                color: #d4d4d8;
                outline: none;
                show-decoration-selected: 1;
            }}
            QTreeWidget::item {{
                height: 28px;
                padding: 2px 6px;
                color: #d4d4d8;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover, QTreeWidget::branch:hover {{
                background-color: #27272a;
                color: #ffffff;
            }}
            /* High-visibility active selection & drop target indicator */
            QTreeWidget::item:selected, QTreeWidget::branch:selected {{
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: url("{p}/branch_closed.png");
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed:hover,
            QTreeWidget::branch:closed:has-children:has-siblings:hover {{
                image: url("{p}/branch_closed_hover.png");
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                image: url("{p}/branch_open.png");
            }}
            QTreeWidget::branch:open:has-children:!has-siblings:hover,
            QTreeWidget::branch:open:has-children:has-siblings:hover {{
                image: url("{p}/branch_open_hover.png");
            }}
            """
        )
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        self.reload_tree()

    def _setup_new_menu(self):
        self.new_menu = QMenu(self)
        self.new_menu.setStyleSheet(
            """
            QMenu {
                background-color: #222226;
                color: #e4e4e7;
                border: 1px solid #333338;
                padding: 6px;
                border-radius: 6px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 7px 16px;
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

        root_folder_action = self.new_menu.addAction("New Root Folder")
        root_folder_action.triggered.connect(lambda: self._create_folder(parent_item=None))

        sub_folder_action = self.new_menu.addAction("New Subfolder in Selected")
        sub_folder_action.triggered.connect(self._create_subfolder_for_current)

        self.new_menu.addSeparator()

        sync_action = self.new_menu.addAction("Sync Telegram Messages")
        sync_action.triggered.connect(self.sync_requested.emit)

        self.new_btn.setMenu(self.new_menu)

    def reload_tree(self, select_folder_id: Optional[int] = None):
        self.tree.clear()

        cat_header = QTreeWidgetItem(self.tree, ["CATEGORIES"])
        cat_header.setFlags(Qt.NoItemFlags)
        cat_font = QFont("Segoe UI", 9, QFont.Bold)
        cat_header.setFont(0, cat_font)
        cat_header.setForeground(0, QColor("#71717a"))

        self.item_all = self._add_category_item("All Files", "all")
        self._add_category_item("Documents", "documents")
        self._add_category_item("Images & Photos", "images")
        self._add_category_item("Media & Audio", "media")
        self._add_category_item("Archives", "archives")
        self._add_category_item("Favorites", "favorites")

        spacer = QTreeWidgetItem(self.tree, [""])
        spacer.setFlags(Qt.NoItemFlags)

        folders_header = QTreeWidgetItem(self.tree, ["VIRTUAL FOLDERS"])
        folders_header.setFlags(Qt.NoItemFlags)
        folders_header.setFont(0, cat_font)
        folders_header.setForeground(0, QColor("#71717a"))

        db_folders = self.db.get_all_folders()
        folder_items_map: Dict[int, QTreeWidgetItem] = {}

        for f in db_folders:
            if f["parent_id"] is None:
                item = QTreeWidgetItem(self.tree, [f["name"]])
                item.setData(0, Qt.UserRole, {"type": "folder", "id": f["id"], "name": f["name"]})
                item.setExpanded(True)
                folder_items_map[f["id"]] = item

        remaining = [f for f in db_folders if f["parent_id"] is not None]
        while remaining:
            placed = False
            for f in list(remaining):
                parent_id = f["parent_id"]
                if parent_id in folder_items_map:
                    parent_item = folder_items_map[parent_id]
                    item = QTreeWidgetItem(parent_item, [f["name"]])
                    item.setData(0, Qt.UserRole, {"type": "folder", "id": f["id"], "name": f["name"]})
                    item.setExpanded(True)
                    folder_items_map[f["id"]] = item
                    remaining.remove(f)
                    placed = True
            if not placed:
                break

        if select_folder_id and select_folder_id in folder_items_map:
            self.tree.setCurrentItem(folder_items_map[select_folder_id])
        else:
            self.tree.setCurrentItem(self.item_all)

    def _add_category_item(self, title: str, category_key: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(self.tree, [title])
        item.setData(0, Qt.UserRole, {"type": "category", "key": category_key})
        return item

    def _get_item_full_path(self, item: QTreeWidgetItem) -> str:
        data = item.data(0, Qt.UserRole)
        if not data or data.get("type") != "folder":
            return ""

        parts = [item.text(0)]
        curr = item.parent()
        while curr:
            curr_data = curr.data(0, Qt.UserRole)
            if curr_data and curr_data.get("type") == "folder":
                parts.insert(0, curr.text(0))
            curr = curr.parent()

        return " / ".join(parts)

    def select_folder_by_id(self, folder_id: int):
        def search(item):
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "folder" and data.get("id") == folder_id:
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if search(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if search(self.tree.topLevelItem(i)):
                break

    def select_category_by_key(self, cat_key: str):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "category" and data.get("key") == cat_key:
                self.tree.setCurrentItem(item)
                break

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if data["type"] == "category":
            self.category_selected.emit(data["key"])
        elif data["type"] == "folder":
            full_path = self._get_item_full_path(item)
            self.folder_selected.emit(data["id"], full_path)

    def _create_folder(self, parent_item: Optional[QTreeWidgetItem] = None):
        parent_id = None
        prompt_target = "root"
        if parent_item:
            parent_data = parent_item.data(0, Qt.UserRole)
            parent_id = parent_data.get("id")
            prompt_target = parent_item.text(0)

        folder_name, ok = QInputDialog.getText(
            self, "New Folder", f"Enter folder name (inside {prompt_target}):"
        )
        if ok and folder_name.strip():
            new_id = self.db.add_folder(folder_name.strip(), parent_id)
            self.reload_tree(select_folder_id=new_id)
            full_path = self.db.get_folder_path(new_id)
            self.folder_selected.emit(new_id, full_path)

    def _create_subfolder_for_current(self):
        curr = self.tree.currentItem()
        if curr and curr.data(0, Qt.UserRole) and curr.data(0, Qt.UserRole).get("type") == "folder":
            self._create_folder(curr)
        else:
            QMessageBox.information(
                self, "Select Folder", "Please select a folder first to create a subfolder inside it."
            )

    def _open_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data or data.get("type") != "folder":
            return

        folder_id = data["id"]
        folder_name = item.text(0)

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #222226;
                color: #e4e4e7;
                border: 1px solid #333338;
                padding: 6px;
                border-radius: 6px;
                font-size: 12px;
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

        subfolder_action = menu.addAction("New Subfolder...")
        rename_action = menu.addAction("Rename Folder...")
        menu.addSeparator()
        delete_action = menu.addAction("Delete Folder")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == subfolder_action:
            self._create_folder(item)
        elif action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, "Rename Folder", "Enter new folder name:", text=folder_name
            )
            if ok and new_name.strip():
                self.db.rename_folder(folder_id, new_name.strip())
                self.reload_tree(select_folder_id=folder_id)
                full_path = self.db.get_folder_path(folder_id)
                self.folder_selected.emit(folder_id, full_path)
        elif action == delete_action:
            confirm = QMessageBox.question(
                self,
                "Delete Folder",
                f"Delete folder '{folder_name}' and all subfolders? Files will remain in vault.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm == QMessageBox.Yes:
                self.db.delete_folder(folder_id)
                self.reload_tree()
                self.category_selected.emit("all")
