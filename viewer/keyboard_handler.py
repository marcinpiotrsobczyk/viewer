from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt


class KeyboardHandler:
    """Sets up keyboard shortcuts on the main window."""

    def __init__(self, window: QMainWindow, actions: dict):
        """
        actions: dict mapping action names to callables:
            prev_image, next_image, zoom_in, zoom_out,
            prev_group, next_group, first_image, last_image,
            fit_view, toggle_metadata, open_folder, quit_app
        """
        shortcuts = {
            Qt.Key.Key_Left: "prev_image",
            Qt.Key.Key_Right: "next_image",
            Qt.Key.Key_Up: "zoom_in",
            Qt.Key.Key_Down: "zoom_out",
            Qt.Key.Key_PageUp: "prev_group",
            Qt.Key.Key_PageDown: "next_group",
            Qt.Key.Key_Home: "first_image",
            Qt.Key.Key_End: "last_image",
            Qt.Key.Key_F: "fit_view",
            Qt.Key.Key_M: "toggle_metadata",
        }

        for key, action_name in shortcuts.items():
            if action_name in actions:
                shortcut = QShortcut(QKeySequence(key), window)
                shortcut.activated.connect(actions[action_name])

        # Ctrl+O
        if "open_folder" in actions:
            sc = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_O), window)
            sc.activated.connect(actions["open_folder"])

        # Ctrl+Q
        if "quit_app" in actions:
            sc = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Q), window)
            sc.activated.connect(actions["quit_app"])
