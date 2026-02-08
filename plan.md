# ImageViewer.html - Build Plan

Single-file offline image viewer with crop & resize capability. One HTML file with embedded CSS and JS. No dependencies. No build step.

## Output

Create `ImageViewer.html` in the project root.

## Layout

Full-viewport dark-themed app. Vertical flex layout:

```
+---------------------------------------------------------------+
| Top Bar: [Open Folder] [View/Select] | dir-name | filename    |
|   WxH | pos-label | Selection: | Scale | [RESIZE] [Undo (N)] |
+----------+-------------------------------+--------------------+
| Tree     | Image Viewport               | Metadata Panel     |
| Panel    | (center, black bg)           | (right)            |
| (left,   | [selection overlay canvas]   |                    |
|  hierarc |                               | Description        |
|  hical)  |                               | [Edit] button      |
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
- RESIZE button enabled: `#2a8a2a` bg, hover `#33a333`
- RESIZE button disabled: `#444` bg, `#666` text
- Selection overlay: `rgba(42,130,218,0.2)` fill, `rgba(0,0,0,0.4)` dim, white dashed border
- Font: system sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`)

## Supported Image Formats

**Viewable**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`, `.svg`, `.avif`

**Saveable** (crop+resize): `.jpg`, `.jpeg`, `.png`, `.webp`

## Features

### 1. Folder Opening (two methods)

**File System Access API** (Chrome/Edge) - preferred:
- Use `window.showDirectoryPicker()` when available
- Recursively scan with `dirHandle.values()`, collecting `FileSystemFileHandle` objects
- Grants write access (needed for metadata editing and resize)

**Fallback** (Firefox, others):
- Hidden `<input type="file" webkitdirectory multiple>`
- Parse `file.webkitRelativePath` to extract directory structure
- Read-only (no metadata editing, no resize)

Trigger: "Open Folder" button or Ctrl+O.

### 2. Directory Grouping

Images are grouped by their relative directory path. Each group is sorted case-insensitively by filename. Groups themselves are sorted case-insensitively by directory name.

Data structures:
- `groups[]` - array of `{dir, images[]}`
- `flat[]` - flattened array of all image entries with `{file/handle, name, dir, groupIdx, fullPath}`
- `groupBounds[]` - starting flat index of each group (for binary search)

### 3. Hierarchical Tree Panel (Left)

- 250px default width, resizable 120-500px via splitter
- Hidden until folder is opened (toggled via `.visible` class)
- `.treeDir`: container for each directory node
- `.treeDirHeader`: flex row with arrow + name (indented by `depth * 16 + 4` px)
- `.treeDirArrow`: 12px wide, shows `▶` (collapsed) or `▼` (expanded)
- `.treeDirChildren`: hidden by default, `.expanded` class to show
- `.treeFile`: individual file entry, indented by `(depth+1) * 16 + 4` px
- `.treeFile.active`: blue left border (`#2a82da`), white text, `#353535` bg

**Building** (`buildTree()`):
- From flat entries, build a nested tree structure: `{ name, children: Map<string, node>, files: [] }`
- Root node uses `rootDirName` as name

**Rendering** (`renderTreeNode(node, container, depth, startExpanded)`):
- Sub-directories sorted case-insensitively, rendered recursively at `depth+1`
- Files rendered as `.treeFile` entries at `depth+1` indentation
- Click on directory header toggles expand/collapse
- Click on file calls `navigate(flatIndex)`

**Active tracking** (`updateTreeActive(entry)`):
- Toggle `.active` on `.treeFile` matching `entry.fullPath`
- Auto-expand all parent `.treeDirChildren` up to root
- Scroll active entry into view

### 4. Image Display (Center Viewport)

- Display image using `<img>` with CSS transforms for position and scale
- `transform-origin: 0 0`, apply `translate(panX, panY) scale(zoom)`
- Set `width`/`height` to natural dimensions so scale works correctly
- Black background
- View mode: `cursor: grab` (changes to `grabbing` while dragging)
- Select mode: `cursor: crosshair`

**Fit-to-view**: Calculate `min(viewportW/naturalW, viewportH/naturalH)`, center the image. This is the default on load, resize, and double-click.

**Zoom**: Factor 1.25x per step. Min 0.02, max 40. Zoom toward mouse cursor position (anchor under mouse). Show zoom % indicator (bottom-right, fades after 1.2s).

**Pan**: View mode: mouse drag. Select mode: Space+drag. Track `dragStart` and `panStart`, update `panX/panY` on mousemove.

**Mouse wheel**: Zoom in/out anchored at cursor position. Use `{ passive: false }` and `preventDefault()`.

### 5. View/Select Mode Toggle

Toggle button `#btnMode` in top bar. Keyboard shortcut: `S`.

**View mode** (default):
- Viewport cursor: `grab` / `grabbing`
- Mouse drag pans image
- Selection overlay: `pointer-events: none`
- Resize controls visually muted

**Select mode**:
- Viewport cursor: `crosshair`
- Mouse drag draws selection on overlay canvas
- Space+drag pans image
- Selection overlay: `pointer-events: auto`
- Resize controls active

Mode persists across image navigation; selection clears on navigate. Escape in Select mode: clear selection (if any) or switch to View mode (if no selection).

### 6. Selection System

**State variables**: `selActive` (boolean), `selDragging` (boolean), `selImgX1/Y1/X2/Y2` (image pixel coordinates).

**Drawing selection** (mousedown → mousemove → mouseup on overlay canvas):
1. On `mousedown`: if Space is held, start panning instead. Otherwise, convert screen coords to image coords, store as start point, set `selDragging = true`
2. On `mousemove`: update end point, redraw overlay
3. On `mouseup`: finalize — if selection is >= 1px in both dimensions, set `selActive = true`

**Coordinate conversion**:
- `screenToImage(sx, sy)`: `{ x: (sx - panX) / zoom, y: (sy - panY) / zoom }`
- `imageToScreen(ix, iy)`: `{ x: ix * zoom + panX, y: iy * zoom + panY }`

**Selection rect normalization** (`getSelRect()`):
- Normalize min/max of start/end coords
- Clamp to image bounds (0..naturalW, 0..naturalH)
- Round to integers
- Return `{x, y, w, h}`

**Overlay rendering** (`drawSelection()`):
- Clear canvas
- If no active or dragging selection, return
- Convert image rect to screen coords
- Draw dimmed overlay (4 rectangles around selection): `rgba(0,0,0,0.4)`
- Draw selection fill: `rgba(42,130,218,0.2)`
- Draw selection border: white, 1px, dashed `[6, 3]`
- Draw dimension label centered above selection (or below if too close to top)

**Overlay canvas sizing**: `resizeOverlay()` sets canvas width/height to viewport dimensions. Called on window resize and after splitter drag.

### 7. Resize & Save Pipeline

When user clicks RESIZE:
1. Compute output dimensions → show confirmation dialog
2. Dialog shows: "Crop to WxH and scale to outW×outH" + warning "This will permanently modify the image file."
3. Cancel → close dialog. Confirm → run resize pipeline

**Before writing:** save current file content as Blob into undo history for that file.

**Pipeline:**
1. Load original image as `ImageBitmap` from file handle
2. Create offscreen `<canvas>` with `outW × outH`
3. `ctx.drawImage(imgBitmap, selX, selY, selW, selH, 0, 0, outW, outH)`
4. Determine MIME type: `.jpg`/`.jpeg` → `image/jpeg` (quality 0.92), `.png` → `image/png`, `.webp` → `image/webp` (quality 0.92)
5. `canvas.toBlob()` → write via FSAPI → reload image
6. After save: revoke/recreate URL, fitToView, clearSelection, reload metadata, show status, update undo button

### 8. Undo History System

- `undoHistory` — a `Map<fullPath, Blob[]>` storing up to 10 previous file states per image
- Before each resize, read the current file into a Blob and push to that file's history stack
- If stack exceeds 10 entries, drop the oldest (shift)
- **Undo button** (`#btnUndo`) in top bar next to RESIZE button, labeled "Undo (N)" where N is the current undo history count for the active file
- Examples: "Undo (0)" when no history (disabled/grayed), "Undo (2)" after two resizes (enabled)
- Enabled (clickable, styled like active button) when N > 0; disabled/grayed when N = 0
- On click: pop last Blob from history → write it back to file via FSAPI → reload image → refresh metadata
- `Ctrl+Z` keyboard shortcut also triggers undo (when not in modal/input)
- Undo history for a file is cleared when navigating to a different folder (new `openFolder()`)
- Undo history persists across image navigation within the same folder

### 9. RESIZE Button State

`updateResizeButton()`:
- Enabled (green) when: selection active with w>0 & h>0 AND useFSAPI AND file extension is in SAVE_EXTS
- Disabled (gray) otherwise with contextual tooltip:
  - No selection: "Select an area first"
  - No FSAPI: "Requires Chrome/Edge with File System Access API"
  - Unsupported format: "Saving not supported for this format"

### 10. Metadata Panel (Right)

Width: 300px default. Resizable via splitter (min 150px, max 600px). Toggle with M key.

Contents:
- **Description header row** with "Edit" button (grayed out when no write access)
- **Description text** - shows `(No description)` in muted color when empty
- Horizontal separator
- **File info**: size (B/KB/MB), format, dimensions (W x H), last modified date
- **"Show All Metadata" toggle button**
- **Tags table**: two columns (Tag, Value), sorted alphabetically

### 11. EXIF/Metadata Reader (pure JS, no dependencies)

Read first 256KB of file into ArrayBuffer. Support:

**JPEG**: Find APP1 marker (0xFFE1). Check for "Exif\0\0" prefix, then parse TIFF structure. Also check for XMP APP1.

**TIFF structure parsing**: Read byte order, verify magic 0x002A, parse IFD entries.

**PNG**: Parse chunks sequentially. Read `tEXt` and `iTXt` chunks.

**WebP**: Parse RIFF container, find "EXIF" chunk, parse as TIFF.

**Description priority**: ImageDescription > XMP description > PNG text "Description" > UserComment.

### 12. Description Editing

**Edit button**: Enabled only when opened via File System Access API AND file is writable format (.jpg, .jpeg, .png).

**Modal dialog**: Dark themed overlay with textarea, Cancel and Save buttons.

**JPEG writer**: Patch or create APP1 EXIF segment with tag 270 (ImageDescription).

**PNG writer**: Replace/insert tEXt chunk with "Description" key.

### 13. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Left/Right arrow | Previous/next image |
| Up/Down arrow | Zoom in/out (center) |
| Mouse wheel | Zoom at cursor |
| PgUp/PgDn | Previous/next directory (first image of that dir) |
| Home/End | First/last image overall |
| F | Fit to view |
| M | Toggle metadata panel |
| S | Toggle View/Select mode |
| Escape | Clear selection (Select mode) or switch to View mode |
| Delete | Clear selection (Select mode) |
| Ctrl+Z | Undo last resize |
| Ctrl+O | Open folder |
| Double-click | Fit to view |

All shortcuts suppressed when edit modal or confirmation dialog is open (except Escape).

### 14. Top Bar

`[Open Folder]` `[View/Select]` | separator | directory name (bold) | separator | filename | dimensions (muted) | position label (right-aligned) | spacer | "Selection:" + info | separator | "Scale:" + number input + "%" | separator | `[RESIZE]` `[Undo (N)]`

Top bar has `flex-wrap: wrap` for narrow windows.

### 15. Controls Bar

Bottom bar with dark bg (`#252525`), muted text (`#888`), 9pt:
```
← → Navigate | Up/Down / Scroll Zoom | PgUp/PgDn Directory | Home/End First/Last | F Fit | M Metadata | S Select | Esc Clear | Ctrl+Z Undo | Ctrl+O Open
```

### 16. Status Bar

Below controls bar. Shows: "Ready", "Loading...", "Zoom: X%", error messages, "Description saved", "Saved: WxH (mime)", scan results.

### 17. Splitter Panels

Both left (tree) and right (metadata) splitters:
- 4px wide, `#444` background, `col-resize` cursor
- Hover: `#2a82da`
- Mouse drag: track startX and panel startWidth, clamp to min/max
- Re-fit image on drag if in fit mode
- Resize overlay on drag end

### 18. Confirmation Dialog

Shown before resize. Dark overlay with dialog box:
- Text: "Crop to WxH and scale to outW×outH"
- Warning: "This will permanently modify the image file."
- Cancel and Confirm buttons
- While open, suppress all keyboard shortcuts

### 19. Empty State

Centered message in viewport: "No images loaded. Use Ctrl+O or the Open Folder button to open a folder." `pointer-events: none`, `z-index: 5`.

### 20. Object URL Management

- Cache object URLs in a Map keyed by file handle or File object
- Revoke old URL before creating new one
- Clean up all URLs when opening a new folder
