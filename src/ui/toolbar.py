"""Top toolbar widget containing search, sync, view toggles, and sorting."""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QComboBox,
    QButtonGroup,
)
from PySide6.QtCore import Qt, Signal


class ToolbarWidget(QWidget):
    """Toolbar with Sync button, search box, sort options, and view mode toggles."""

    sync_requested = Signal()
    search_changed = Signal(str)
    view_mode_changed = Signal(str)  # "grid" or "list"
    sort_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # ── 1. Sync Button ──
        self.sync_btn = QPushButton("Sync Telegram")
        self.sync_btn.setCursor(Qt.PointingHandCursor)
        self.sync_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            """
        )
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

        # ── 2. Search Box ──
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files, captions, tags...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                background-color: #27272a;
                color: #f4f4f5;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #27272a;
            }
            """
        )
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, stretch=1)

        # ── 3. Sort Options ──
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Sort: Date (Newest)",
            "Sort: Date (Oldest)",
            "Sort: Name (A-Z)",
            "Sort: Size (Largest)",
        ])
        self.sort_combo.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: #27272a;
                color: #e4e4e7;
                font-size: 12px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #52525b;
            }
            QComboBox QAbstractItemView {
                background-color: #18181b;
                color: #e4e4e7;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                border: 1px solid #3f3f46;
                outline: none;
            }
            """
        )
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        layout.addWidget(self.sort_combo)

        # ── 4. View Mode (Grid vs List) ──
        self.grid_btn = QPushButton("Grid")
        self.list_btn = QPushButton("List")

        for btn in (self.grid_btn, self.list_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #3f3f46;
                    background-color: #27272a;
                    color: #a1a1aa;
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: #3f3f46;
                }
                QPushButton:checked {
                    background-color: #3b82f6;
                    color: #ffffff;
                    border-color: #3b82f6;
                    font-weight: 600;
                }
                """
            )

        self.view_group = QButtonGroup(self)
        self.view_group.addButton(self.grid_btn, 1)
        self.view_group.addButton(self.list_btn, 2)
        self.grid_btn.setChecked(True)

        self.grid_btn.clicked.connect(lambda: self.view_mode_changed.emit("grid"))
        self.list_btn.clicked.connect(lambda: self.view_mode_changed.emit("list"))

        layout.addWidget(self.grid_btn)
        layout.addWidget(self.list_btn)

    def _on_sort_changed(self, index: int):
        sort_map = {
            0: "date_desc",
            1: "date_asc",
            2: "name_asc",
            3: "size_desc",
        }
        self.sort_changed.emit(sort_map.get(index, "date_desc"))
