from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, Signal

from viewer.constants import ZOOM_IN_FACTOR, ZOOM_OUT_FACTOR, ZOOM_MIN, ZOOM_MAX


class ImageView(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._current_zoom = 1.0
        self._fit_mode = True

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.black)

    def display_image(self, pixmap: QPixmap):
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(pixmap.rect().toRectF())
        self._fit_mode = True
        self._fit_in_view()

    def display_placeholder(self, message: str):
        self._scene.clear()
        self._pixmap_item = None
        text_item = self._scene.addText(message)
        text_item.setDefaultTextColor(Qt.GlobalColor.gray)
        self._scene.setSceneRect(self._scene.itemsBoundingRect())
        self.resetTransform()
        self._current_zoom = 1.0
        self.zoom_changed.emit(self._current_zoom)

    def clear_display(self):
        self._scene.clear()
        self._pixmap_item = None

    def zoom_in(self):
        self._apply_zoom(ZOOM_IN_FACTOR)

    def zoom_out(self):
        self._apply_zoom(ZOOM_OUT_FACTOR)

    def fit_to_view(self):
        self._fit_mode = True
        self._fit_in_view()

    def _apply_zoom(self, factor: float):
        new_zoom = self._current_zoom * factor
        if new_zoom < ZOOM_MIN or new_zoom > ZOOM_MAX:
            return
        self._fit_mode = False
        self.scale(factor, factor)
        self._current_zoom = new_zoom
        self.zoom_changed.emit(self._current_zoom)

    def _fit_in_view(self):
        if self._pixmap_item is None:
            return
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        # Calculate effective zoom after fit
        if self._pixmap_item.pixmap().width() > 0:
            view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            pix_w = self._pixmap_item.pixmap().width()
            self._current_zoom = view_rect.width() / pix_w
        else:
            self._current_zoom = 1.0
        self.zoom_changed.emit(self._current_zoom)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode:
            self._fit_in_view()

    def keyPressEvent(self, event):
        # Don't consume arrow keys — let MainWindow handle navigation
        event.ignore()

    def update_pixmap_frame(self, pixmap: QPixmap):
        """Update the pixmap for animated GIF frames without resetting view."""
        if self._pixmap_item is not None:
            self._pixmap_item.setPixmap(pixmap)
        else:
            self.display_image(pixmap)
