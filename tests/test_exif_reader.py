import os
import struct
import tempfile

import pytest
from PIL import Image

from viewer.exif_reader import read_metadata, _decode_user_comment, _extract_xmp_description


class TestDecodeUserComment:
    def test_ascii_comment(self):
        raw = b"ASCII\x00\x00\x00Hello World"
        assert _decode_user_comment(raw) == "Hello World"

    def test_unicode_comment(self):
        text = "Hello"
        encoded = text.encode("utf-16-le")
        raw = b"UNICODE\x00" + encoded
        result = _decode_user_comment(raw)
        assert result is not None
        assert "Hello" in result

    def test_string_passthrough(self):
        assert _decode_user_comment("just a string") == "just a string"

    def test_too_short(self):
        assert _decode_user_comment(b"short") is None

    def test_none_for_non_bytes(self):
        assert _decode_user_comment(12345) is None


class TestExtractXmpDescription:
    def test_basic_xmp(self):
        xmp = b"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">A beautiful sunset</rdf:li>
        </rdf:Alt>
      </dc:description>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""
        result = _extract_xmp_description(xmp)
        assert result == "A beautiful sunset"

    def test_no_description(self):
        xmp = b"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description/>
  </rdf:RDF>
</x:xmpmeta>"""
        result = _extract_xmp_description(xmp)
        assert result is None

    def test_invalid_xml(self):
        result = _extract_xmp_description(b"not xml at all")
        assert result is None


class TestReadMetadata:
    def test_basic_jpg(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        img = Image.new("RGB", (100, 50), color="red")
        img.save(img_path, "JPEG")

        meta = read_metadata(img_path)
        assert meta["file_info"]["Dimensions"] == "100 × 50"
        assert meta["file_info"]["Format"] == "JPEG"
        assert "File Size" in meta["file_info"]

    def test_png_no_exif(self, tmp_path):
        img_path = str(tmp_path / "test.png")
        img = Image.new("RGBA", (200, 100), color="blue")
        img.save(img_path, "PNG")

        meta = read_metadata(img_path)
        assert meta["description"] is None
        assert meta["file_info"]["Format"] == "PNG"
        assert meta["file_info"]["Dimensions"] == "200 × 100"

    def test_nonexistent_file(self):
        meta = read_metadata("/nonexistent/path/image.jpg")
        assert meta["description"] is None
        assert meta["all_tags"] == {}

    def test_file_size_formatting(self, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        img = Image.new("RGB", (10, 10), color="green")
        img.save(img_path, "JPEG")

        meta = read_metadata(img_path)
        size_str = meta["file_info"]["File Size"]
        # Small file, should be in B or KB
        assert "B" in size_str or "KB" in size_str

    def test_jpg_with_image_description(self, tmp_path):
        """Test that ImageDescription EXIF tag is extracted using raw EXIF bytes."""
        img_path = str(tmp_path / "described.jpg")
        img = Image.new("RGB", (100, 100), color="white")

        # Build minimal EXIF with ImageDescription (tag 270)
        # Using Pillow's built-in EXIF support
        from PIL.ExifTags import Base as ExifBase
        import io

        img.save(img_path, "JPEG")

        # Re-open and set EXIF via Pillow
        img2 = Image.open(img_path)
        exif = img2.getexif()
        exif[270] = "A test description"  # ImageDescription
        buf = io.BytesIO()
        img2.save(buf, "JPEG", exif=exif.tobytes())
        (tmp_path / "described.jpg").write_bytes(buf.getvalue())

        meta = read_metadata(img_path)
        assert meta["description"] == "A test description"
