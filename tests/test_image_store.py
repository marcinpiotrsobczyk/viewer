import os
import tempfile

import pytest

from viewer.image_store import ImageStore, ImageEntry, DirectoryGroup, _ScanWorker


@pytest.fixture
def sample_tree(tmp_path):
    """Create a temp folder tree with dummy image files."""
    # Root images
    (tmp_path / "alpha.jpg").write_bytes(b"fake")
    (tmp_path / "beta.png").write_bytes(b"fake")

    # Subdir A
    sub_a = tmp_path / "Animals"
    sub_a.mkdir()
    (sub_a / "cat.jpg").write_bytes(b"fake")
    (sub_a / "Dog.png").write_bytes(b"fake")
    (sub_a / "bird.gif").write_bytes(b"fake")

    # Subdir B (nested)
    sub_b = tmp_path / "Beach" / "Summer"
    sub_b.mkdir(parents=True)
    (sub_b / "wave.webp").write_bytes(b"fake")
    (sub_b / "sand.tiff").write_bytes(b"fake")

    # Non-image files (should be skipped)
    (tmp_path / "readme.txt").write_text("not an image")
    (sub_a / "notes.pdf").write_bytes(b"fake")

    return tmp_path


class TestScanWorker:
    def test_basic_scan(self, sample_tree):
        worker = _ScanWorker(str(sample_tree))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()

        assert len(results) == 1
        groups = results[0]

        # Should have 3 groups: root dir, Animals, Beach/Summer
        assert len(groups) == 3

    def test_groups_sorted_alphabetically(self, sample_tree):
        worker = _ScanWorker(str(sample_tree))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()
        groups = results[0]

        displays = [g.directory_display for g in groups]
        assert displays == sorted(displays, key=str.casefold)

    def test_images_sorted_within_group(self, sample_tree):
        worker = _ScanWorker(str(sample_tree))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()
        groups = results[0]

        for group in groups:
            filenames = [e.filename for e in group.images]
            assert filenames == sorted(filenames, key=str.casefold)

    def test_non_image_files_skipped(self, sample_tree):
        worker = _ScanWorker(str(sample_tree))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()
        groups = results[0]

        all_files = [e.filename for g in groups for e in g.images]
        assert "readme.txt" not in all_files
        assert "notes.pdf" not in all_files

    def test_total_image_count(self, sample_tree):
        worker = _ScanWorker(str(sample_tree))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()
        groups = results[0]

        total = sum(len(g.images) for g in groups)
        assert total == 7  # 2 root + 3 Animals + 2 Beach/Summer

    def test_empty_folder(self, tmp_path):
        worker = _ScanWorker(str(tmp_path))
        results = []
        worker.finished.connect(lambda groups: results.append(groups))
        worker.run()
        groups = results[0]

        assert len(groups) == 0


class TestImageStore:
    def _make_store_with_groups(self) -> ImageStore:
        """Manually populate a store for testing navigation."""
        store = ImageStore()
        groups = [
            DirectoryGroup(
                directory_display="Adir",
                images=[
                    ImageEntry("/a/img1.jpg", "img1.jpg", "/a", "Adir"),
                    ImageEntry("/a/img2.jpg", "img2.jpg", "/a", "Adir"),
                    ImageEntry("/a/img3.jpg", "img3.jpg", "/a", "Adir"),
                ],
            ),
            DirectoryGroup(
                directory_display="Bdir",
                images=[
                    ImageEntry("/b/pic1.png", "pic1.png", "/b", "Bdir"),
                    ImageEntry("/b/pic2.png", "pic2.png", "/b", "Bdir"),
                ],
            ),
            DirectoryGroup(
                directory_display="Cdir",
                images=[
                    ImageEntry("/c/photo.gif", "photo.gif", "/c", "Cdir"),
                ],
            ),
        ]
        store._on_scan_finished(groups)
        return store

    def test_total_count(self):
        store = self._make_store_with_groups()
        assert store.total_count == 6

    def test_get_entry(self):
        store = self._make_store_with_groups()
        assert store.get_entry(0).filename == "img1.jpg"
        assert store.get_entry(3).filename == "pic1.png"
        assert store.get_entry(5).filename == "photo.gif"
        assert store.get_entry(-1) is None
        assert store.get_entry(6) is None

    def test_group_index_for(self):
        store = self._make_store_with_groups()
        # Adir: indices 0,1,2
        assert store.group_index_for(0) == 0
        assert store.group_index_for(2) == 0
        # Bdir: indices 3,4
        assert store.group_index_for(3) == 1
        assert store.group_index_for(4) == 1
        # Cdir: index 5
        assert store.group_index_for(5) == 2

    def test_position_in_group(self):
        store = self._make_store_with_groups()
        assert store.position_in_group(0) == (0, 3)
        assert store.position_in_group(2) == (2, 3)
        assert store.position_in_group(3) == (0, 2)
        assert store.position_in_group(5) == (0, 1)

    def test_first_of_next_group(self):
        store = self._make_store_with_groups()
        assert store.first_of_next_group(0) == 3  # Adir → Bdir
        assert store.first_of_next_group(2) == 3  # Still Adir → Bdir
        assert store.first_of_next_group(3) == 5  # Bdir → Cdir
        assert store.first_of_next_group(5) is None  # Cdir → nothing

    def test_first_of_prev_group(self):
        store = self._make_store_with_groups()
        assert store.first_of_prev_group(0) is None  # Adir → nothing
        assert store.first_of_prev_group(3) == 0  # Bdir → Adir
        assert store.first_of_prev_group(5) == 3  # Cdir → Bdir

    def test_first_of_current_group(self):
        store = self._make_store_with_groups()
        assert store.first_of_current_group(0) == 0
        assert store.first_of_current_group(2) == 0
        assert store.first_of_current_group(4) == 3
        assert store.first_of_current_group(5) == 5
