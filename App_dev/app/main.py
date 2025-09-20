from PySide6.QtWidgets import QApplication
import sys
from loguru import logger

from app.ui.main_window import MainWindow
from app.controllers.controller import AppController

def main() -> int:
    logger.info("Starting UI (Step 2: skeleton only; no camera yet)")
    app = QApplication(sys.argv)

    window = MainWindow()
    controller = AppController(window)

    window.show()
    code = app.exec()
    logger.info("Exiting UI with code {}", code)
    return code
