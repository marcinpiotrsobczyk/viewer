from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
)
from PySide6.QtCore import Qt

from viewer.exif_reader import read_metadata


class MetadataPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Description label
        desc_header = QLabel("Description")
        desc_header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 2px;")
        layout.addWidget(desc_header)

        self._desc_label = QLabel("(No description)")
        self._desc_label.setWordWrap(True)
        self._desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._desc_label.setStyleSheet("font-size: 11pt; padding: 4px;")
        layout.addWidget(self._desc_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #555;")
        layout.addWidget(sep)

        # File info section
        self._file_info_label = QLabel("")
        self._file_info_label.setWordWrap(True)
        self._file_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._file_info_label.setStyleSheet("font-size: 10pt; padding: 4px; color: #bbb;")
        layout.addWidget(self._file_info_label)

        # Toggle button
        self._toggle_btn = QPushButton("Show All Metadata")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.toggled.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        # EXIF table in scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setVisible(False)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Tag", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._scroll.setWidget(self._table)

        layout.addWidget(self._scroll)
        layout.addStretch()

    def update_metadata(self, file_path: str):
        meta = read_metadata(file_path)

        # Description
        desc = meta.get("description")
        if desc:
            self._desc_label.setText(desc)
            self._desc_label.setStyleSheet("font-size: 11pt; padding: 4px; color: #ddd;")
        else:
            self._desc_label.setText("(No description)")
            self._desc_label.setStyleSheet("font-size: 11pt; padding: 4px; color: #888;")

        # File info
        file_info = meta.get("file_info", {})
        info_lines = [f"{k}: {v}" for k, v in file_info.items()]
        self._file_info_label.setText("\n".join(info_lines))

        # All tags table
        all_tags = meta.get("all_tags", {})
        # Merge file_info into display
        combined = {**file_info, **all_tags}
        self._table.setRowCount(len(combined))
        for row, (tag, value) in enumerate(sorted(combined.items())):
            self._table.setItem(row, 0, QTableWidgetItem(tag))
            self._table.setItem(row, 1, QTableWidgetItem(str(value)))

    def clear(self):
        self._desc_label.setText("(No description)")
        self._desc_label.setStyleSheet("font-size: 11pt; padding: 4px; color: #888;")
        self._file_info_label.setText("")
        self._table.setRowCount(0)

    def _on_toggle(self, checked: bool):
        self._scroll.setVisible(checked)
        self._toggle_btn.setText("Hide All Metadata" if checked else "Show All Metadata")
