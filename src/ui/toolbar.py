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
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # ── 1. Sync Button ──
        self.sync_btn = QPushButton("🔄  Sync Telegram")
        self.sync_btn.setCursor(Qt.PointingHandCursor)
        self.sync_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            """
        )
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

        # ── 2. Search Box ──
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search files, captions, tags...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #dadce0;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
                background-color: #f1f3f4;
            }
            QLineEdit:focus {
                background-color: #ffffff;
                border: 2px solid #1a73e8;
            }
            """
        )
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, stretch=1)

        # ── 3. Sort Options ──
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Sort by: Date (Newest)",
            "Sort by: Date (Oldest)",
            "Sort by: Name (A-Z)",
            "Sort by: Size (Largest)",
        ])
        self.sort_combo.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 5px 10px;
                background: #ffffff;
                font-size: 12px;
                min-width: 150px;
            }
            """
        )
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        layout.addWidget(self.sort_combo)

        # ── 4. View Mode (Grid vs List) ──
        self.grid_btn = QPushButton("⊞ Grid")
        self.list_btn = QPushButton("☰ List")

        for btn in (self.grid_btn, self.list_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #dadce0;
                    background: #ffffff;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background: #e8f0fe;
                    color: #1a73e8;
                    border-color: #1a73e8;
                    font-weight: bold;
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

