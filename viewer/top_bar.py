from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt


class TopBar(QWidget):
    open_folder_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        self._open_btn = QPushButton("Open Folder")
        self._open_btn.clicked.connect(self.open_folder_clicked)
        layout.addWidget(self._open_btn)

        sep = QLabel("|")
        sep.setStyleSheet("color: #666;")
        layout.addWidget(sep)

        self._dir_label = QLabel("")
        self._dir_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._dir_label)

        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #666;")
        layout.addWidget(sep2)

        self._file_label = QLabel("")
        layout.addWidget(self._file_label)

        layout.addStretch()

        self._position_label = QLabel("")
        self._position_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._position_label)

    def update_info(self, directory: str, filename: str,
                    index_in_group: int, group_size: int,
                    global_index: int, total: int):
        self._dir_label.setText(directory)
        self._file_label.setText(filename)
        self._position_label.setText(
            f"{index_in_group + 1}/{group_size} in group  |  {global_index + 1}/{total} total"
        )

    def clear(self):
        self._dir_label.setText("")
        self._file_label.setText("")
        self._position_label.setText("")
