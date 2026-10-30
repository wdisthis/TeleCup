"""TeleCup - Main Application Entry Point."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TeleCup")
    app.setOrganizationName("TeleCup")

    # Set modern clean style
    app.setStyle("Fusion")

    # Set clean system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

