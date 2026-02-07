import os
import xml.etree.ElementTree as ET
from PIL import Image, PngImagePlugin
from PIL.ExifTags import TAGS, GPSTAGS


def _decode_user_comment(raw) -> str | None:
    """Decode UserComment field which has an 8-byte encoding prefix."""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, bytes) or len(raw) <= 8:
        return None
    prefix = raw[:8]
    payload = raw[8:]
    if prefix.startswith(b"UNICODE\x00"):
        try:
            return payload.decode("utf-16-le").strip("\x00 ")
        except Exception:
            try:
                return payload.decode("utf-16-be").strip("\x00 ")
            except Exception:
                return None
    if prefix.startswith(b"ASCII\x00"):
        try:
            return payload.decode("ascii", errors="replace").strip("\x00 ")
        except Exception:
            return None
    # Unknown encoding, try UTF-8
    try:
        return payload.decode("utf-8", errors="replace").strip("\x00 ")
    except Exception:
        return None


def _extract_xmp_description(xmp_data: bytes | str) -> str | None:
    """Extract dc:description from XMP data."""
    try:
        if isinstance(xmp_data, bytes):
            xmp_data = xmp_data.decode("utf-8", errors="replace")
        root = ET.fromstring(xmp_data)
        ns = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "dc": "http://purl.org/dc/elements/1.1/",
        }
        for desc in root.iter("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description"):
            # Check dc:description as child element
            dc_desc = desc.find("dc:description", ns)
            if dc_desc is not None:
                alt = dc_desc.find("rdf:Alt", ns)
                if alt is not None:
                    li = alt.find("rdf:li", ns)
                    if li is not None and li.text:
                        return li.text.strip()
            # Check dc:description as attribute
            for attr_name, attr_val in desc.attrib.items():
                if "description" in attr_name.lower() and attr_val.strip():
                    return attr_val.strip()
    except Exception:
        pass
    return None


def _safe_tag_value(value) -> str:
    """Convert a tag value to a display string."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    if isinstance(value, tuple):
        return ", ".join(str(v) for v in value)
    return str(value)


def _resolve_ifd(exif_data, tag_id: int, tag_map: dict) -> dict[str, str]:
    """Resolve an IFD (sub-IFD or GPS IFD) from EXIF data."""
    result = {}
    try:
        ifd = exif_data.get_ifd(tag_id)
        for k, v in ifd.items():
            name = tag_map.get(k, f"Tag 0x{k:04X}")
            result[name] = _safe_tag_value(v)
    except Exception:
        pass
    return result


def read_metadata(file_path: str) -> dict:
    """Read metadata from an image file.

    Returns dict with keys:
        description: str | None
        all_tags: dict[str, str]
        file_info: dict[str, str]
    """
    result = {
        "description": None,
        "all_tags": {},
        "file_info": {},
    }

    # File info
    try:
        stat = os.stat(file_path)
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        result["file_info"]["File Size"] = size_str
    except Exception:
        pass

    try:
        pil_img = Image.open(file_path)
    except Exception:
        return result

    result["file_info"]["Format"] = pil_img.format or "Unknown"
    result["file_info"]["Dimensions"] = f"{pil_img.width} × {pil_img.height}"
    result["file_info"]["Mode"] = pil_img.mode

    # EXIF
    all_tags: dict[str, str] = {}
    description: str | None = None
    image_description: str | None = None
    user_comment: str | None = None
    xp_comment: str | None = None

    try:
        exif_data = pil_img.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f"Tag 0x{tag_id:04X}")
                if tag_id == 0x8769:  # ExifIFD pointer, resolve sub-IFD
                    continue
                if tag_id == 0x8825:  # GPSIFD pointer, resolve separately
                    continue
                all_tags[tag_name] = _safe_tag_value(value)

                if tag_id == 270:  # ImageDescription
                    image_description = _safe_tag_value(value).strip()

            # Resolve EXIF sub-IFD (0x8769)
            exif_sub = _resolve_ifd(exif_data, 0x8769, TAGS)
            for k, v in exif_sub.items():
                all_tags[k] = v
            if "UserComment" in exif_sub:
                raw_uc = exif_data.get_ifd(0x8769).get(37510)
                if raw_uc is not None:
                    user_comment = _decode_user_comment(raw_uc)

            # Resolve GPS IFD (0x8825)
            gps_tags = _resolve_ifd(exif_data, 0x8825, GPSTAGS)
            for k, v in gps_tags.items():
                all_tags[f"GPS {k}"] = v

    except Exception:
        pass

    # XMP
    xmp_description: str | None = None
    try:
        xmp = pil_img.info.get("xmp") or pil_img.info.get("XML:com.adobe.xmp")
        if xmp:
            xmp_description = _extract_xmp_description(xmp)
            if xmp_description:
                all_tags["XMP Description"] = xmp_description
    except Exception:
        pass

    # Also check for XPComment (tag 40092) in main EXIF
    try:
        exif_data = pil_img.getexif()
        raw_xpc = exif_data.get(40092)
        if raw_xpc is not None:
            if isinstance(raw_xpc, bytes):
                xp_comment = raw_xpc.decode("utf-16-le", errors="replace").strip("\x00 ")
            else:
                xp_comment = str(raw_xpc).strip()
    except Exception:
        pass

    # PNG text chunks
    png_description: str | None = None
    try:
        if pil_img.format == "PNG" and hasattr(pil_img, "info"):
            for key, value in pil_img.info.items():
                if isinstance(value, str):
                    all_tags[key] = value
                    if key.lower() == "description" and value.strip():
                        png_description = value.strip()
    except Exception:
        pass

    # Description priority: ImageDescription → XMP → PNG text → UserComment → XPComment
    for candidate in [image_description, xmp_description, png_description, user_comment, xp_comment]:
        if candidate:
            description = candidate
            break

    result["description"] = description
    result["all_tags"] = all_tags
    return result


_WRITABLE_EXTENSIONS = {".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".png"}


def can_write_description(file_path: str) -> bool:
    """Check if description metadata can be written to this file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _WRITABLE_EXTENSIONS:
        return False
    return os.access(file_path, os.W_OK)


def write_description(file_path: str, description: str) -> None:
    """Write a description to the image file's metadata.

    Supports JPEG, TIFF, WebP (via EXIF tag 270) and PNG (via text chunk).
    Raises ValueError for unsupported formats.
    Raises OSError on write failures.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in {".jpg", ".jpeg"}:
        img = Image.open(file_path)
        exif = img.getexif()
        exif[270] = description
        img.save(file_path, exif=exif.tobytes(), quality="keep", subsampling=0)

    elif ext in {".tiff", ".tif"}:
        img = Image.open(file_path)
        exif = img.getexif()
        exif[270] = description
        img.save(file_path, exif=exif.tobytes(), compression="tiff_deflate")

    elif ext == ".webp":
        img = Image.open(file_path)
        exif = img.getexif()
        exif[270] = description
        img.save(file_path, exif=exif.tobytes(), quality=90)

    elif ext == ".png":
        img = Image.open(file_path)
        # Preserve existing text chunks
        pnginfo = PngImagePlugin.PngInfo()
        existing = img.info or {}
        for key, value in existing.items():
            if isinstance(value, str):
                pnginfo.add_text(key, value)
        pnginfo.add_text("Description", description)
        img.save(file_path, pnginfo=pnginfo)

    else:
        raise ValueError(f"Writing description is not supported for {ext} files")
