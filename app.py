"""TeleCup - Main Application Entry Point."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QColor, QPalette

from src.ui.main_window import MainWindow


def configure_dark_palette(app: QApplication):
    """Ensure standard dialogs and menus adhere to modern dark palette."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#18181b"))
    palette.setColor(QPalette.WindowText, QColor("#e4e4e7"))
    palette.setColor(QPalette.Base, QColor("#18181b"))
    palette.setColor(QPalette.AlternateBase, QColor("#27272a"))
    palette.setColor(QPalette.ToolTipBase, QColor("#27272a"))
    palette.setColor(QPalette.ToolTipText, QColor("#f4f4f5"))
    palette.setColor(QPalette.Text, QColor("#e4e4e7"))
    palette.setColor(QPalette.Button, QColor("#27272a"))
    palette.setColor(QPalette.ButtonText, QColor("#e4e4e7"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#3b82f6"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TeleCup")
    app.setOrganizationName("TeleCup")

    # Set modern clean style
    app.setStyle("Fusion")
    configure_dark_palette(app)

    # Set clean system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
