import os
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QThread, Signal

from viewer.constants import SUPPORTED_EXTENSIONS


@dataclass
class ImageEntry:
    file_path: str
    filename: str
    directory: str
    directory_display: str


@dataclass
class DirectoryGroup:
    directory_display: str
    images: list[ImageEntry] = field(default_factory=list)


class _ScanWorker(QObject):
    finished = Signal(list)  # list[DirectoryGroup]

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = root_path

    def run(self):
        groups_map: dict[str, list[ImageEntry]] = {}
        root = self.root_path

        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                full_path = os.path.join(dirpath, fname)
                rel_dir = os.path.relpath(dirpath, root)
                if rel_dir == ".":
                    rel_dir = os.path.basename(root)
                display = rel_dir

                entry = ImageEntry(
                    file_path=full_path,
                    filename=fname,
                    directory=dirpath,
                    directory_display=display,
                )
                groups_map.setdefault(display, []).append(entry)

        groups: list[DirectoryGroup] = []
        for display in sorted(groups_map.keys(), key=str.casefold):
            images = sorted(groups_map[display], key=lambda e: e.filename.casefold())
            groups.append(DirectoryGroup(directory_display=display, images=images))

        self.finished.emit(groups)


class ImageStore(QObject):
    scan_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: list[DirectoryGroup] = []
        self._flat: list[ImageEntry] = []
        self._group_boundaries: list[int] = []  # start index of each group
        self._root_path: str = ""
        self._scan_thread: QThread | None = None
        self._scan_worker: _ScanWorker | None = None

    @property
    def root_path(self) -> str:
        return self._root_path

    @property
    def total_count(self) -> int:
        return len(self._flat)

    @property
    def groups(self) -> list[DirectoryGroup]:
        return self._groups

    def scan_folder(self, root_path: str):
        self._root_path = root_path
        if self._scan_thread is not None:
            self._scan_thread.quit()
            self._scan_thread.wait()

        self._scan_thread = QThread()
        self._scan_worker = _ScanWorker(root_path)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.start()

    def _on_scan_finished(self, groups: list[DirectoryGroup]):
        self._groups = groups
        self._flat = []
        self._group_boundaries = []
        for group in groups:
            self._group_boundaries.append(len(self._flat))
            self._flat.extend(group.images)
        self._scan_worker = None
        self.scan_finished.emit()

    def get_entry(self, index: int) -> ImageEntry | None:
        if 0 <= index < len(self._flat):
            return self._flat[index]
        return None

    def group_index_for(self, flat_index: int) -> int:
        """Return the group index that contains the given flat index."""
        if not self._group_boundaries:
            return 0
        gi = bisect_right(self._group_boundaries, flat_index) - 1
        return max(0, gi)

    def position_in_group(self, flat_index: int) -> tuple[int, int]:
        """Return (index_within_group, group_size) for given flat index."""
        gi = self.group_index_for(flat_index)
        group = self._groups[gi]
        start = self._group_boundaries[gi]
        return flat_index - start, len(group.images)

    def first_of_next_group(self, flat_index: int) -> int | None:
        """Return flat index of first image in the next group, or None."""
        gi = self.group_index_for(flat_index)
        if gi + 1 < len(self._group_boundaries):
            return self._group_boundaries[gi + 1]
        return None

    def first_of_prev_group(self, flat_index: int) -> int | None:
        """Return flat index of first image in the previous group, or None."""
        gi = self.group_index_for(flat_index)
        if gi > 0:
            return self._group_boundaries[gi - 1]
        return None

    def first_of_current_group(self, flat_index: int) -> int:
        """Return flat index of first image in the current group."""
        gi = self.group_index_for(flat_index)
        return self._group_boundaries[gi]
