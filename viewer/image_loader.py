import time

from PIL import Image, ImageOps
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage


class WorkerSignals(QObject):
    result = Signal(int, QImage, bool)  # task_id, image, is_animated
    error = Signal(int, str)  # task_id, error_message


class _LoadTask(QRunnable):
    def __init__(self, task_id: int, file_path: str, signals: WorkerSignals):
        super().__init__()
        self.task_id = task_id
        self.file_path = file_path
        self.signals = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            pil_img = Image.open(self.file_path)
            is_animated = getattr(pil_img, "is_animated", False)

            pil_img = ImageOps.exif_transpose(pil_img)

            if pil_img.mode != "RGBA":
                pil_img = pil_img.convert("RGBA")

            data = pil_img.tobytes("raw", "RGBA")
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            # Detach from Python bytes buffer
            qimg = qimg.copy()

            self.signals.result.emit(self.task_id, qimg, is_animated)
        except Exception as e:
            self.signals.error.emit(self.task_id, str(e))


class ImageLoader(QObject):
    image_loaded = Signal(QImage, bool)  # qimage, is_animated
    load_error = Signal(str)  # error_message
    loading_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._task_counter = 0
        self._current_task_id = 0
        self._signals = WorkerSignals()
        self._signals.result.connect(self._on_result)
        self._signals.error.connect(self._on_error)

    def load(self, file_path: str):
        self._task_counter += 1
        self._current_task_id = self._task_counter
        self.loading_started.emit()
        task = _LoadTask(self._current_task_id, file_path, self._signals)
        self._pool.start(task)

    @Slot(int, QImage, bool)
    def _on_result(self, task_id: int, qimage: QImage, is_animated: bool):
        if task_id != self._current_task_id:
            return  # stale result, discard
        self.image_loaded.emit(qimage, is_animated)

    @Slot(int, str)
    def _on_error(self, task_id: int, error_message: str):
        if task_id != self._current_task_id:
            return
        self.load_error.emit(error_message)
