from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from viewer.constants import APP_NAME, ORG_NAME


class ViewerApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName(ORG_NAME)
        self.setStyle("Fusion")
        self._apply_dark_palette()

    def _apply_dark_palette(self):
        palette = QPalette()
        dark = QColor(45, 45, 45)
        darker = QColor(30, 30, 30)
        text = QColor(208, 208, 208)
        highlight = QColor(42, 130, 218)
        disabled_text = QColor(127, 127, 127)
        bright_text = QColor(255, 255, 255)

        palette.setColor(QPalette.ColorRole.Window, dark)
        palette.setColor(QPalette.ColorRole.WindowText, text)
        palette.setColor(QPalette.ColorRole.Base, darker)
        palette.setColor(QPalette.ColorRole.AlternateBase, dark)
        palette.setColor(QPalette.ColorRole.ToolTipBase, dark)
        palette.setColor(QPalette.ColorRole.ToolTipText, text)
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.Button, dark)
        palette.setColor(QPalette.ColorRole.ButtonText, text)
        palette.setColor(QPalette.ColorRole.BrightText, bright_text)
        palette.setColor(QPalette.ColorRole.Link, highlight)
        palette.setColor(QPalette.ColorRole.Highlight, highlight)
        palette.setColor(QPalette.ColorRole.HighlightedText, bright_text)

        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text)

        self.setPalette(palette)
