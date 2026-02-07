from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QMovie, QPixmap


class GifPlayer(QObject):
    frame_ready = Signal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._movie: QMovie | None = None

    def start(self, file_path: str):
        self.stop()
        self._movie = QMovie(file_path)
        self._movie.frameChanged.connect(self._on_frame)
        self._movie.start()

    def stop(self):
        if self._movie is not None:
            self._movie.stop()
            self._movie.frameChanged.disconnect(self._on_frame)
            self._movie.deleteLater()
            self._movie = None

    @property
    def is_playing(self) -> bool:
        return self._movie is not None

    @Slot()
    def _on_frame(self):
        if self._movie is not None:
            pixmap = self._movie.currentPixmap()
            if not pixmap.isNull():
                self.frame_ready.emit(pixmap)
