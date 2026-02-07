from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDialog, QPlainTextEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal

from viewer.exif_reader import read_metadata, can_write_description


class MetadataPanel(QWidget):
    description_edit_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self._file_path: str | None = None
        self._current_description: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Description header row with Edit button
        desc_header_layout = QHBoxLayout()
        desc_header = QLabel("Description")
        desc_header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 2px;")
        desc_header_layout.addWidget(desc_header)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setEnabled(False)
        self._edit_btn.setFixedWidth(50)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        desc_header_layout.addWidget(self._edit_btn)

        layout.addLayout(desc_header_layout)

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
        self._file_path = file_path
        meta = read_metadata(file_path)

        # Enable/disable edit button
        self._edit_btn.setEnabled(can_write_description(file_path))

        # Description
        desc = meta.get("description")
        self._current_description = desc or ""
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
        self._file_path = None
        self._current_description = ""
        self._edit_btn.setEnabled(False)
        self._desc_label.setText("(No description)")
        self._desc_label.setStyleSheet("font-size: 11pt; padding: 4px; color: #888;")
        self._file_info_label.setText("")
        self._table.setRowCount(0)

    def _on_toggle(self, checked: bool):
        self._scroll.setVisible(checked)
        self._toggle_btn.setText("Hide All Metadata" if checked else "Show All Metadata")

    def _on_edit_clicked(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Description")
        dialog.setMinimumWidth(400)
        dialog_layout = QVBoxLayout(dialog)

        text_edit = QPlainTextEdit()
        text_edit.setPlainText(self._current_description)
        dialog_layout.addWidget(text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_text = text_edit.toPlainText()
            self.description_edit_requested.emit(new_text)
