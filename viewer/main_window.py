import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QLabel,
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QSettings, Slot

from viewer.constants import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, DEFAULT_METADATA_PANEL_WIDTH,
    APP_NAME,
)
from viewer.image_store import ImageStore
from viewer.image_view import ImageView
from viewer.image_loader import ImageLoader
from viewer.gif_player import GifPlayer
from viewer.top_bar import TopBar
from viewer.metadata_panel import MetadataPanel
from viewer.keyboard_handler import KeyboardHandler


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)

        self._store = ImageStore(self)
        self._loader = ImageLoader(self)
        self._gif_player = GifPlayer(self)
        self._current_index = -1
        self._settings = QSettings()

        self._init_ui()
        self._init_keyboard()
        self._connect_signals()
        self._restore_settings()
        self.statusBar().showMessage("Ready — Ctrl+O to open a folder")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        self._top_bar = TopBar()
        main_layout.addWidget(self._top_bar)

        # Splitter: image view + metadata panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._image_view = ImageView()
        self._splitter.addWidget(self._image_view)

        self._metadata_panel = MetadataPanel()
        self._splitter.addWidget(self._metadata_panel)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([
            DEFAULT_WINDOW_WIDTH - DEFAULT_METADATA_PANEL_WIDTH,
            DEFAULT_METADATA_PANEL_WIDTH,
        ])

        main_layout.addWidget(self._splitter)

        # Empty message label (hidden by default)
        self._empty_label = QLabel("No images found.\nUse Ctrl+O or the Open Folder button to open a folder.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("font-size: 14pt; color: #888; padding: 40px;")
        self._empty_label.setVisible(False)
        main_layout.addWidget(self._empty_label)

        # Keyboard controls info bar
        controls_text = (
            "\u2190\u2192 Navigate  |  \u2191\u2193 Zoom  |  "
            "PgUp/PgDn Groups  |  Home/End First/Last  |  "
            "F Fit  |  M Metadata  |  Ctrl+O Open  |  Ctrl+Q Quit"
        )
        self._controls_bar = QLabel(controls_text)
        self._controls_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._controls_bar.setStyleSheet(
            "background-color: #252525; color: #888; font-size: 9pt; padding: 3px 8px;"
        )
        main_layout.addWidget(self._controls_bar)

    def _init_keyboard(self):
        KeyboardHandler(self, {
            "prev_image": self._prev_image,
            "next_image": self._next_image,
            "zoom_in": self._image_view.zoom_in,
            "zoom_out": self._image_view.zoom_out,
            "prev_group": self._prev_group,
            "next_group": self._next_group,
            "first_image": self._first_image,
            "last_image": self._last_image,
            "fit_view": self._image_view.fit_to_view,
            "toggle_metadata": self._toggle_metadata,
            "open_folder": self._open_folder,
            "quit_app": self.close,
        })

    def _connect_signals(self):
        self._top_bar.open_folder_clicked.connect(self._open_folder)
        self._store.scan_finished.connect(self._on_scan_finished)
        self._loader.image_loaded.connect(self._on_image_loaded)
        self._loader.load_error.connect(self._on_load_error)
        self._loader.loading_started.connect(lambda: self.statusBar().showMessage("Loading..."))
        self._image_view.zoom_changed.connect(self._on_zoom_changed)
        self._gif_player.frame_ready.connect(self._image_view.update_pixmap_frame)

    def _restore_settings(self):
        geom = self._settings.value("window/geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        splitter_state = self._settings.value("window/splitter")
        if splitter_state:
            self._splitter.restoreState(splitter_state)

        meta_visible = self._settings.value("window/metadata_visible", True, type=bool)
        self._metadata_panel.setVisible(meta_visible)

    def _save_settings(self):
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/splitter", self._splitter.saveState())
        self._settings.setValue("window/metadata_visible", self._metadata_panel.isVisible())

    def closeEvent(self, event):
        self._save_settings()
        self._gif_player.stop()
        super().closeEvent(event)

    # --- Folder opening ---

    @Slot()
    def _open_folder(self):
        last_dir = self._settings.value("last_folder", "")
        folder = QFileDialog.getExistingDirectory(self, "Open Image Folder", last_dir)
        if not folder:
            return
        self._settings.setValue("last_folder", folder)
        self.statusBar().showMessage(f"Scanning {folder}...")
        self._gif_player.stop()
        self._current_index = -1
        self._store.scan_folder(folder)

    @Slot()
    def _on_scan_finished(self):
        total = self._store.total_count
        if total == 0:
            self._image_view.clear_display()
            self._top_bar.clear()
            self._metadata_panel.clear()
            self._empty_label.setVisible(True)
            self._splitter.setVisible(False)
            self.statusBar().showMessage("No images found in folder")
            return

        self._empty_label.setVisible(False)
        self._splitter.setVisible(True)
        self._navigate_to(0)
        self.statusBar().showMessage(f"Found {total} images in {len(self._store.groups)} directories")

    # --- Navigation ---

    def _navigate_to(self, index: int):
        if index < 0 or index >= self._store.total_count:
            return
        self._current_index = index
        self._gif_player.stop()

        entry = self._store.get_entry(index)
        if entry is None:
            return

        # Update top bar
        idx_in_group, group_size = self._store.position_in_group(index)
        self._top_bar.update_info(
            entry.directory_display, entry.filename,
            idx_in_group, group_size,
            index, self._store.total_count,
        )

        # Update metadata
        self._metadata_panel.update_metadata(entry.file_path)

        # Load image
        self._loader.load(entry.file_path)

    @Slot(QImage, bool)
    def _on_image_loaded(self, qimage: QImage, is_animated: bool):
        if is_animated:
            # Use GIF player instead
            entry = self._store.get_entry(self._current_index)
            if entry:
                pixmap = QPixmap.fromImage(qimage)
                self._image_view.display_image(pixmap)
                self._gif_player.start(entry.file_path)
        else:
            pixmap = QPixmap.fromImage(qimage)
            self._image_view.display_image(pixmap)
        self.statusBar().showMessage("Ready")

    @Slot(str)
    def _on_load_error(self, error_message: str):
        self._image_view.display_placeholder(f"Error loading image:\n{error_message}")
        self.statusBar().showMessage(f"Error: {error_message}")

    @Slot(float)
    def _on_zoom_changed(self, zoom: float):
        pct = zoom * 100
        self.statusBar().showMessage(f"Zoom: {pct:.0f}%")

    @Slot()
    def _prev_image(self):
        if self._current_index > 0:
            self._navigate_to(self._current_index - 1)

    @Slot()
    def _next_image(self):
        if self._current_index < self._store.total_count - 1:
            self._navigate_to(self._current_index + 1)

    @Slot()
    def _prev_group(self):
        if self._current_index < 0:
            return
        target = self._store.first_of_prev_group(self._current_index)
        if target is not None:
            self._navigate_to(target)

    @Slot()
    def _next_group(self):
        if self._current_index < 0:
            return
        target = self._store.first_of_next_group(self._current_index)
        if target is not None:
            self._navigate_to(target)

    @Slot()
    def _first_image(self):
        if self._store.total_count > 0:
            self._navigate_to(0)

    @Slot()
    def _last_image(self):
        if self._store.total_count > 0:
            self._navigate_to(self._store.total_count - 1)

    @Slot()
    def _toggle_metadata(self):
        visible = self._metadata_panel.isVisible()
        self._metadata_panel.setVisible(not visible)
