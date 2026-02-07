# ImageViewer.html - Build Plan

Single-file offline image viewer. One HTML file with embedded CSS and JS. No dependencies. No build step.

## Output

Create `ImageViewer.html` in the project root.

## Layout

Full-viewport dark-themed app. Vertical flex layout:

```
+---------------------------------------------------------------+
| Top Bar: [Open Folder] | dir-name | filename | pos-label      |
+----------+-------------------------------+--------------------+
| Dir Tree | Image Viewport               | Metadata Panel     |
| (left)   | (center, black bg)           | (right)            |
|          |                               |                    |
|          |                               | Description        |
|          |                               | [Edit] button      |
|          |                               | File Info          |
|          |                               | [Show All Metadata]|
|          |                               | Tags table         |
+----------+-------------------------------+--------------------+
| Controls bar: keyboard shortcuts reference                    |
+---------------------------------------------------------------+
| Status bar: zoom %, loading state, messages                   |
+---------------------------------------------------------------+
```

## Dark Theme Colors

- Background: `#1e1e1e`, panels: `#2d2d2d`, darker: `#252525`
- Text: `#d0d0d0`, muted: `#888`, disabled: `#666`
- Highlight/accent: `#2a82da`
- Viewport bg: `#000` (pure black)
- Buttons: `#3a3a3a` bg, `#555` border, hover `#4a4a4a`
- Font: system sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`)

## Supported Image Formats

`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`, `.svg`, `.avif`

## Features

### 1. Folder Opening (two methods)

**File System Access API** (Chrome/Edge) - preferred:
- Use `window.showDirectoryPicker()` when available
- Recursively scan with `dirHandle.values()`, collecting `FileSystemFileHandle` objects
- Grants write access (needed for metadata editing)

**Fallback** (Firefox, others):
- Hidden `<input type="file" webkitdirectory multiple>`
- Parse `file.webkitRelativePath` to extract directory structure
- Read-only (no metadata editing)

Trigger: "Open Folder" button or Ctrl+O.

### 2. Directory Grouping

Images are grouped by their relative directory path. Each group is sorted case-insensitively by filename. Groups themselves are sorted case-insensitively by directory name.

Data structures:
- `groups[]` - array of `{dir, images[]}`
- `flat[]` - flattened array of all image entries with `{file/handle, name, dir, groupIdx}`
- `groupBounds[]` - starting flat index of each group (for binary search)

### 3. Directory Tree Panel (Left)

- Shows all directories with image counts, e.g. `photos/vacation (23)`
- Active directory highlighted with blue left border (`#2a82da`) and lighter text
- Click a directory to navigate to its first image
- Auto-scrolls active entry into view on navigation
- Resizable via draggable splitter (min 120px, max 500px)
- Initially hidden, appears after folder scan
- Default width: 220px

### 4. Image Display (Center Viewport)

- Display image using `<img>` with CSS transforms for position and scale
- `transform-origin: 0 0`, apply `translate(panX, panY) scale(zoom)`
- Set `width`/`height` to natural dimensions so scale works correctly
- Black background, `cursor: grab` (changes to `grabbing` while dragging)

**Fit-to-view**: Calculate `min(viewportW/naturalW, viewportH/naturalH)`, center the image. This is the default on load, resize, and double-click.

**Zoom**: Factor 1.25x per step. Min 0.02, max 40. Zoom toward mouse cursor position (anchor under mouse). Show zoom % indicator (bottom-right, fades after 1.2s).

**Pan**: Mouse drag. Track `dragStart` and `panStart`, update `panX/panY` on mousemove.

**Mouse wheel**: Zoom in/out anchored at cursor position. Use `{ passive: false }` and `preventDefault()`.

### 5. Metadata Panel (Right)

Width: 300px default. Resizable via splitter (min 150px, max 600px). Toggle with M key. Has class `hidden` when toggled off (+ hide its splitter).

Contents:
- **Description header row** with "Edit" button (right-aligned, grayed out when no write access with explanatory tooltip)
- **Description text** - shows `(No description)` in muted color when empty
- Horizontal separator
- **File info**: size (B/KB/MB), format, dimensions (W x H), last modified date
- **"Show All Metadata" toggle button** - expands/collapses the tags table
- **Tags table**: two columns (Tag, Value), sorted alphabetically, alternating row colors, sticky header

### 6. EXIF/Metadata Reader (pure JS, no dependencies)

Read first 256KB of file into ArrayBuffer. Support:

**JPEG**: Find APP1 marker (0xFFE1). Check for "Exif\0\0" prefix, then parse TIFF structure. Also check for XMP APP1 (`http://ns.adobe.com/xap/1.0/\0` prefix).

**TIFF structure parsing**: Read byte order (II=little-endian, MM=big-endian), verify magic 0x002A, read IFD0 offset. Parse IFD entries (12 bytes each): tag ID, type, count, value/offset. Support types: BYTE(1), ASCII(2), SHORT(3), LONG(4), RATIONAL(5), UNDEFINED(7), SLONG(9), SRATIONAL(10). Values >4 bytes are stored at an offset from TIFF start.

**Important EXIF tags to name**: ImageDescription(0x010E), Make(0x010F), Model(0x0110), Orientation(0x0112), XResolution(0x011A), YResolution(0x011B), ResolutionUnit(0x0128), Software(0x0131), DateTime(0x0132), Artist(0x013B), Copyright(0x8298), ExifIFD(0x8769), GPSIFD(0x8825), ExposureTime(0x829A), FNumber(0x829D), ISOSpeedRatings(0x8827), ExifVersion(0x9000), DateTimeOriginal(0x9003), UserComment(0x9286), FocalLength(0x920A), LensMake(0xA433), LensModel(0xA434), plus others.

**Sub-IFD reading**: Follow ExifIFD pointer (tag 0x8769) to read exposure/camera tags.

**UserComment decoding**: 8-byte prefix indicates encoding (ASCII\0, UNICODE\0, or unknown). Decode payload accordingly.

**XMP**: Extract `dc:description` via regex from XMP XML data.

**PNG**: Parse chunks sequentially from offset 8. Read `tEXt` chunks (key\0value, Latin-1) and `iTXt` chunks (key\0compressionflag\0method\0lang\0translatedkey\0text, UTF-8). Stop at IDAT/IEND. Look for "Description" key.

**WebP**: Parse RIFF container, find "EXIF" chunk, parse as TIFF.

**Description priority**: ImageDescription > XMP description > PNG text "Description" > UserComment.

### 7. Description Editing

**Edit button**: Enabled only when opened via File System Access API AND file is writable format (.jpg, .jpeg, .png). When disabled (no write permission or unsupported format), the button is visually grayed out (dimmed colors, no hover effect) with a tooltip explaining why editing is unavailable.

**Modal dialog**: Dark themed overlay with textarea, Cancel and Save buttons. Pre-filled with current description.

**Keyboard handling**: While modal is open, ALL keyboard shortcuts are suppressed (check modal open state at top of keydown handler). Escape closes modal.

**JPEG writer** (`writeJpegDescription`):
- Find existing APP1 EXIF marker
- If exists: extract TIFF data, call `patchExifDescription` to rebuild IFD0 with new tag 270 (ImageDescription), preserving all other tags. Rebuild APP1 segment in place.
- If not exists: create minimal TIFF (big-endian, single IFD0 entry for tag 270), wrap in APP1 segment, insert after SOI marker.
- Write back via `fileHandle.createWritable()`.

**`patchExifDescription`**: Parse existing IFD0, collect all entries except tag 270, add new 270 entry, sort entries by tag ID (TIFF requirement), rebuild TIFF: header + IFD0 + external data. Handle both little-endian and big-endian.

**PNG writer** (`writePngDescription`):
- Parse all chunks, remove existing "Description" tEXt chunks
- Build new tEXt chunk: "Description\0" + text
- Compute CRC32 over type+data for the chunk
- Insert before first IDAT chunk
- Reassemble entire PNG

**CRC32**: Precompute 256-entry table using polynomial 0xEDB88320. Apply to chunk type+data bytes.

### 8. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Left/Right arrow | Previous/next image |
| Up/Down arrow | Zoom in/out (center) |
| Mouse wheel | Zoom at cursor |
| PgUp/PgDn | Previous/next directory (first image of that dir) |
| Home/End | First/last image overall |
| F | Fit to view |
| M | Toggle metadata panel |
| Ctrl+O | Open folder |
| Escape | Close edit modal |
| Double-click | Fit to view |

All shortcuts suppressed when edit modal is open (except Escape).

### 9. Top Bar

`Open Folder` button | separator | directory name (bold, max-width 300px, ellipsis) | separator | filename (ellipsis) | position label (right-aligned, e.g. `3/12 in dir  |  45/200 total`).

### 10. Controls Bar

Bottom bar with dark bg (#252525), muted text (#888), 9pt:
```
<- -> Navigate | Up/Down / Scroll Zoom | PgUp/PgDn Directory | Home/End First/Last | F Fit | M Metadata | Ctrl+O Open
```

### 11. Status Bar

Below controls bar. Shows: "Ready", "Loading...", "Zoom: X%", error messages, "Description saved", scan results.

### 12. Splitter Panels

Both left (dir tree) and right (metadata) splitters:
- 4px wide, `#444` background, `col-resize` cursor
- Hover: `#2a82da`
- Mouse drag: track startX and panel startWidth, clamp to min/max
- Re-fit image on drag if in fit mode

### 13. Empty State

Centered message in viewport: "No images found. Use Ctrl+O or the Open Folder button to open a folder." Shown by default and when scan finds nothing.

### 14. Object URL Management

- Cache object URLs in a Map keyed by file handle or File object
- Revoke old URL before creating new one (important after description edit changes the file)
- Clean up all URLs when opening a new folder
