"""Sidebar component with drag-and-drop folder receiving, balanced '+ New' button, and nested subfolders."""

import os
from pathlib import Path
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
from PySide6.QtCore import Qt, Signal, QSize, QPointF
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QDragEnterEvent, QDragMoveEvent, QDropEvent


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
    """Generate a clean vector plus icon."""
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
    """Custom TreeWidget accepting file drops directly into virtual folders."""

    file_dropped = Signal(int, str)  # (file_id, folder_path)

    def __init__(self, sidebar, parent=None):
        super().__init__(parent)
        self.sidebar = sidebar
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            item = self.itemAt(event.position().toPoint())
            if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole)[0] == "folder":
                self.setCurrentItem(item)
                event.acceptProposedAction()
                return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasFormat("application/x-telecup-file"):
            item = self.itemAt(event.position().toPoint())
            if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole)[0] == "folder":
                file_id = int(event.mimeData().data("application/x-telecup-file").data().decode("utf-8"))
                target_path = self.sidebar._get_item_full_path(item)
                self.file_dropped.emit(file_id, target_path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class SidebarWidget(QWidget):
    """Sidebar with nested virtual folders, drag-and-drop receiving, and prominent '+ New' button."""

    category_selected = Signal(str)
    folder_selected = Signal(str)
    file_dropped_on_folder = Signal(int, str)
    sync_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(290)
        self.assets_path = ensure_branch_icons()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(14)

        # ── 1. App Title ──
        title_label = QLabel("TeleCup")
        title_font = QFont("Segoe UI", 13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #e4e4e7; padding: 2px 4px;")
        layout.addWidget(title_label)

        # ── 2. Prominent '+ New' Action Button ──
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

        # ── 3. Navigation Tree with Drop Receiving & Persistent Chevrons ──
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
                padding: 2px 4px;
                color: #d4d4d8;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover, QTreeWidget::branch:hover {{
                background-color: #27272a;
                color: #ffffff;
            }}
            QTreeWidget::item:selected, QTreeWidget::branch:selected {{
                background-color: #1e293b;
                color: #60a5fa;
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

        self._build_tree()

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

        root_folder_action = self.new_menu.addAction("New Root Folder")
        root_folder_action.triggered.connect(lambda: self._create_folder(parent_item=None))

        sub_folder_action = self.new_menu.addAction("New Subfolder in Selected")
        sub_folder_action.triggered.connect(self._create_subfolder_for_current)

        self.new_menu.addSeparator()

        sync_action = self.new_menu.addAction("Sync Telegram Messages")
        sync_action.triggered.connect(self.sync_requested.emit)

        self.new_btn.setMenu(self.new_menu)

    def _build_tree(self):
        self.tree.clear()

        # ── 1. Library Categories ──
        cat_header = QTreeWidgetItem(self.tree, ["CATEGORIES"])
        cat_header.setFlags(Qt.NoItemFlags)
        cat_font = QFont("Segoe UI", 9, QFont.Bold)
        cat_header.setFont(0, cat_font)
        cat_header.setForeground(0, QColor("#71717a"))

        self.item_all = self._add_item(self.tree, "All Files", "category", "all")
        self._add_item(self.tree, "Documents", "category", "documents")
        self._add_item(self.tree, "Images & Photos", "category", "images")
        self._add_item(self.tree, "Media & Audio", "category", "media")
        self._add_item(self.tree, "Archives", "category", "archives")
        self._add_item(self.tree, "Favorites", "category", "favorites")

        # Spacer
        spacer = QTreeWidgetItem(self.tree, [""])
        spacer.setFlags(Qt.NoItemFlags)

        # ── 2. Virtual Folders ──
        folders_header = QTreeWidgetItem(self.tree, ["VIRTUAL FOLDERS"])
        folders_header.setFlags(Qt.NoItemFlags)
        folders_header.setFont(0, cat_font)
        folders_header.setForeground(0, QColor("#71717a"))

        work = self._add_item(self.tree, "Work Projects", "folder", "Work Projects")
        sub_2026 = self._add_item(work, "2026", "folder", "Work Projects / 2026")
        self._add_item(sub_2026, "Q4 Deliverables", "folder", "Work Projects / 2026 / Q4 Deliverables")
        self._add_item(work, "Client Reviews", "folder", "Work Projects / Client Reviews")
        work.setExpanded(True)
        sub_2026.setExpanded(True)

        finance = self._add_item(self.tree, "Receipts & Finance", "folder", "Receipts & Finance")
        self._add_item(finance, "Tax 2026", "folder", "Receipts & Finance / Tax 2026")
        finance.setExpanded(True)

        self._add_item(self.tree, "Learning & E-books", "folder", "Learning & E-books")

        self.tree.setCurrentItem(self.item_all)

    def _add_item(self, parent, title: str, item_type: str, path_val: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [title])
        item.setData(0, Qt.UserRole, (item_type, path_val))
        return item

    def _get_item_full_path(self, item: QTreeWidgetItem) -> str:
        data = item.data(0, Qt.UserRole)
        if not data:
            return ""
        item_type, val = data
        if item_type != "folder":
            return val

        parts = [item.text(0)]
        curr = item.parent()
        while curr:
            curr_data = curr.data(0, Qt.UserRole)
            if curr_data and curr_data[0] == "folder":
                parts.insert(0, curr.text(0))
            curr = curr.parent()

        return " / ".join(parts)

    def select_by_path(self, target_path: str):
        def search(item):
            data = item.data(0, Qt.UserRole)
            if data and (data[1] == target_path or self._get_item_full_path(item) == target_path):
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if search(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if search(self.tree.topLevelItem(i)):
                break

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        item_type, val = data
        if item_type == "category":
            self.category_selected.emit(val)
        elif item_type == "folder":
            full_path = self._get_item_full_path(item)
            self.folder_selected.emit(full_path)

    def _create_folder(self, parent_item=None):
        prompt_target = parent_item.text(0) if parent_item else "root"
        folder_name, ok = QInputDialog.getText(
            self, "New Folder", f"Enter folder name (inside {prompt_target}):"
        )
        if ok and folder_name.strip():
            target_parent = parent_item if parent_item else self.tree
            parent_path = self._get_item_full_path(parent_item) if parent_item else ""
            full_path = f"{parent_path} / {folder_name.strip()}" if parent_path else folder_name.strip()

            new_item = self._add_item(target_parent, folder_name.strip(), "folder", full_path)
            if parent_item:
                parent_item.setExpanded(True)
            self.tree.setCurrentItem(new_item)
            self.folder_selected.emit(full_path)

    def _create_subfolder_for_current(self):
        curr = self.tree.currentItem()
        if curr and curr.data(0, Qt.UserRole) and curr.data(0, Qt.UserRole)[0] == "folder":
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
        if not data or data[0] != "folder":
            return

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

        subfolder_action = menu.addAction("New Subfolder...")
        rename_action = menu.addAction("Rename Folder...")
        menu.addSeparator()
        delete_action = menu.addAction("Delete Folder")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == subfolder_action:
            self._create_folder(item)
        elif action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, "Rename Folder", "Enter new folder name:", text=item.text(0)
            )
            if ok and new_name.strip():
                item.setText(0, new_name.strip())
                full_path = self._get_item_full_path(item)
                self.folder_selected.emit(full_path)
        elif action == delete_action:
            confirm = QMessageBox.question(
                self,
                "Delete Folder",
                f"Delete folder '{item.text(0)}' and its contents?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm == QMessageBox.Yes:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    idx = self.tree.indexOfTopLevelItem(item)
                    if idx >= 0:
                        self.tree.takeTopLevelItem(idx)
                self.tree.setCurrentItem(self.item_all)
                self.category_selected.emit("all")
