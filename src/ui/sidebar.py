"""Sidebar component for navigation, categories, and virtual folders."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class SidebarWidget(QWidget):
    """Sidebar navigation panel for categories and virtual folders."""

    category_selected = Signal(str)
    folder_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(10)

        # Header Title
        title_label = QLabel("TeleCup Vault")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1a73e8; margin-bottom: 4px;")
        layout.addWidget(title_label)

        # Navigation Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet(
            """
            QTreeWidget {
                border: none;
                background: transparent;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 6px;
                margin: 1px 0px;
            }
            QTreeWidget::item:hover {
                background: #f1f3f4;
            }
            QTreeWidget::item:selected {
                background: #e8f0fe;
                color: #1967d2;
                font-weight: bold;
            }
            """
        )
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        # Populate Sections
        self._build_tree()

        # Add Folder Button
        self.add_folder_btn = QPushButton("+ New Virtual Folder")
        self.add_folder_btn.setCursor(Qt.PointingHandCursor)
        self.add_folder_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f1f3f4;
                color: #3c4043;
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
                border-color: #bdc1c6;
            }
            QPushButton:pressed {
                background-color: #dadce0;
            }
            """
        )
        self.add_folder_btn.clicked.connect(self._create_new_folder)
        layout.addWidget(self.add_folder_btn)

    def _build_tree(self):
        self.tree.clear()

        # ── 1. Library Categories ──
        cat_group = QTreeWidgetItem(self.tree, ["CATEGORIES"])
        cat_group.setFlags(Qt.ItemIsEnabled)
        cat_font = QFont()
        cat_font.setBold(True)
        cat_font.setPointSize(9)
        cat_group.setFont(0, cat_font)
        cat_group.setForeground(0, Qt.gray)

        self.item_all = QTreeWidgetItem(cat_group, ["📦  All Files"])
        self.item_all.setData(0, Qt.UserRole, ("category", "all"))

        self.item_docs = QTreeWidgetItem(cat_group, ["📄  Documents"])
        self.item_docs.setData(0, Qt.UserRole, ("category", "documents"))

        self.item_images = QTreeWidgetItem(cat_group, ["🖼️  Images & Photos"])
        self.item_images.setData(0, Qt.UserRole, ("category", "images"))

        self.item_media = QTreeWidgetItem(cat_group, ["🎬  Media & Audio"])
        self.item_media.setData(0, Qt.UserRole, ("category", "media"))

        self.item_archives = QTreeWidgetItem(cat_group, ["🗜️  Archives"])
        self.item_archives.setData(0, Qt.UserRole, ("category", "archives"))

        self.item_favorites = QTreeWidgetItem(cat_group, ["⭐  Favorites"])
        self.item_favorites.setData(0, Qt.UserRole, ("category", "favorites"))

        cat_group.setExpanded(True)

        # ── 2. Virtual Folders ──
        self.folders_group = QTreeWidgetItem(self.tree, ["FOLDERS"])
        self.folders_group.setFlags(Qt.ItemIsEnabled)
        self.folders_group.setFont(0, cat_font)
        self.folders_group.setForeground(0, Qt.gray)

        # Dummy folders
        dummy_folders = ["Work Projects", "Receipts & Finance", "Learning & E-books"]
        for f in dummy_folders:
            self._add_folder_node(f)

        self.folders_group.setExpanded(True)

        # Default selection: All Files
        self.tree.setCurrentItem(self.item_all)

    def _add_folder_node(self, folder_name: str):
        item = QTreeWidgetItem(self.folders_group, [f"📁  {folder_name}"])
        item.setData(0, Qt.UserRole, ("folder", folder_name))
        return item

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        item_type, val = data
        if item_type == "category":
            self.category_selected.emit(val)
        elif item_type == "folder":
            self.folder_selected.emit(val)

    def _create_new_folder(self):
        folder_name, ok = QInputDialog.getText(
            self, "New Virtual Folder", "Enter folder name:"
        )
        if ok and folder_name.strip():
            item = self._add_folder_node(folder_name.strip())
            self.tree.setCurrentItem(item)
            self.folder_selected.emit(folder_name.strip())

