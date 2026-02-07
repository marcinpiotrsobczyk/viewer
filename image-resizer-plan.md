# ImageResizer.html - Build Plan

Single-file offline image crop & resize tool. One HTML file with embedded CSS and JS. No dependencies. No build step. Same dark theme as ImageViewer.html.

## Output

Create `ImageResizer.html` in the project root.

## Reference

Reuse patterns from `ImageViewer.html` for: folder opening, directory scanning, splitter, URL management, helpers, dark theme CSS.

## Layout

Full-viewport dark-themed app. Vertical flex layout:

```
+---------------------------------------------------------------+
| Top Bar: [Open Folder] | filename | WxH | Selection: | Scale  |
|          ... | [RESIZE] | [Reset Selection]                   |
+----------+------------------------------------------------+---+
| Tree     | Image Viewport                                     |
| Panel    | (center, black bg, crosshair cursor)               |
| (left)   |                                                    |
|          | [selection overlay canvas on top]                   |
+----------+----------------------------------------------------+
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

## HTML Structure

```html
<div id="app">
  <div id="topBar">
    <button class="topBtn" id="btnOpen">Open Folder</button>
    <div class="topSep"></div>
    <span id="topFileName"></span>          <!-- current file path -->
    <span id="topDimensions"></span>        <!-- e.g. "1920×1080" -->
    <div class="topSpacer"></div>           <!-- margin-left:auto pushes rest right -->
    <span class="topLabel">Selection:</span>
    <span id="selectionInfo">None</span>    <!-- e.g. "200×150 at 340,120" -->
    <div class="topSep"></div>
    <span class="topLabel">Scale:</span>
    <input type="number" id="scaleInput" value="100" min="1" max="1000">
    <span class="topLabel">%</span>
    <div class="topSep"></div>
    <button id="btnResize">RESIZE</button>
    <button class="topBtn" id="btnReset">Reset Selection</button>
  </div>
  <div id="mainArea">
    <div id="treePanel"></div>
    <div class="splitter" id="leftSplitter"></div>
    <div id="viewport">
      <img id="viewportImg">
      <canvas id="selectionOverlay"></canvas>
      <div id="emptyState">...</div>
      <div id="zoomIndicator"></div>
    </div>
  </div>
  <div id="controlsBar">...</div>
  <div id="statusBar"><span id="statusText">Ready</span></div>
</div>
<input type="file" id="folderInput" webkitdirectory multiple>
```

## CSS Details

### Top Bar
- Flex row with `gap: 8px`, `flex-wrap: wrap` for narrow windows
- `.topBtn`: standard dark buttons, `.topSep`: 1px vertical separator
- `#scaleInput`: 55px wide, dark bg, right-aligned text
- `#btnResize`: bold, has `.enabled` class toggle (green when active, gray when disabled)
- `.topSpacer`: `margin-left: auto` to push selection/scale/resize controls to the right

### Tree Panel
- 250px default width, resizable 120-500px via splitter
- Hidden until folder is opened (toggled via `.visible` class)
- `.treeDir`: container for each directory node
- `.treeDirHeader`: flex row with arrow + name, bold, `padding-left` = `depth * 16 + 4` px
- `.treeDirArrow`: 12px wide, shows `▶` (collapsed) or `▼` (expanded)
- `.treeDirChildren`: hidden by default, `.expanded` class to show
- `.treeFile`: individual file entry, `padding-left` = `(depth+1) * 16 + 4` px
- `.treeFile.active`: blue left border (`#2a82da`), white text, `#353535` bg
- Hover on both: `#353535` bg

### Viewport
- `cursor: crosshair` default (for selection drawing)
- `.panning` class changes cursor to `grabbing`
- `#selectionOverlay`: canvas, `position:absolute; inset:0; z-index:10; pointer-events:auto`
- `#emptyState`: centered text, `pointer-events:none`, `z-index:5`
- `#zoomIndicator`: bottom-right corner, `z-index:20`, fades via opacity transition

## Features

### 1. Folder Opening (two methods)

**File System Access API** (Chrome/Edge) - preferred:
- Use `window.showDirectoryPicker({ mode: 'readwrite' })` when available
- Recursively scan with `dirHandle.values()`, collecting `FileSystemFileHandle` objects
- Each entry gets `{handle, name, dir, fullPath}` where `dir` is relative directory path and `fullPath` is `dir + '/' + name`
- Grants write access (needed for saving)

**Fallback** (Firefox, others):
- Hidden `<input type="file" webkitdirectory multiple>`
- Parse `file.webkitRelativePath` to extract directory structure
- Each entry gets `{file, name, dir, fullPath}`
- Read-only (RESIZE button disabled)

Trigger: "Open Folder" button or Ctrl+O.

### 2. Entry Processing

After scanning, `processEntries()`:
- Revoke all old object URLs
- Sort entries by `fullPath` case-insensitively into `flat[]` array
- Build hierarchical tree
- Auto-select first image

### 3. Hierarchical Tree Panel (Left)

**Building** (`buildTree()`):
- From flat entries, build a nested tree structure: `{ name, children: Map<string, node>, files: [] }`
- Root node uses `rootDirName` as name
- Split each entry's `dir` by `/` to walk into nested nodes

**Rendering** (`renderTreeNode(node, container, depth, startExpanded)`):
- For each node, create:
  - `.treeDir` container
  - `.treeDirHeader` with arrow + name (indented by depth)
  - `.treeDirChildren` container (expanded only for root)
- Sub-directories sorted case-insensitively, rendered recursively at `depth+1`
- Files rendered as `.treeFile` entries at `depth+1` indentation
- Click on directory header toggles `.expanded` class and arrow character
- Click on file calls `selectFile(entry)`

**Active tracking** (`updateTreeActive(entry)`):
- Toggle `.active` on `.treeFile` matching `entry.fullPath`
- Auto-expand all parent `.treeDirChildren` up to root
- Scroll active entry into view

### 4. Image Display (Center Viewport)

- Display image using `<img>` with CSS transforms for position and scale
- `transform-origin: 0 0`, apply `translate(panX, panY) scale(zoom)`
- Set `width`/`height` to natural dimensions so scale works correctly
- Black background

**Fit-to-view**: Calculate `min(viewportW/naturalW, viewportH/naturalH)`, center the image. Default on load, resize, and double-click.

**Zoom**: Factor 1.25x per step. Min 0.02, max 40. Zoom toward mouse cursor position. Show zoom % indicator (bottom-right, fades after 1.2s).

**Pan**: Hold Space + left-drag. Track start positions, update `panX/panY` on mousemove.

**Mouse wheel**: Zoom in/out on overlay canvas. Use `{ passive: false }` and `preventDefault()`.

### 5. Selection System

**State variables**: `selActive` (boolean), `selDragging` (boolean), `selImgX1/Y1/X2/Y2` (image pixel coordinates).

**Drawing selection** (mousedown → mousemove → mouseup on overlay canvas):
1. On `mousedown`: if Space is held, start panning instead. Otherwise, convert screen coords to image coords via `(screenX - panX) / zoom`, store as start point, set `selDragging = true`
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
- Draw dimension label (e.g. "200×150") centered above selection (or below if too close to top), with dark background pill

**Overlay canvas sizing**: `resizeOverlay()` sets canvas width/height to viewport dimensions. Called on window resize and after splitter drag.

**Selection info**: Updated in top bar showing "WxH at X,Y" or "None".

### 6. Resize & Save Pipeline

When user clicks RESIZE (`doResize()`):
1. Validate: selection exists, button is enabled
2. Read scale from input, clamp 1-1000, calculate output dimensions: `outW = round(selW * scale/100)`, `outH = round(selH * scale/100)`
3. Load original image as `ImageBitmap` from file handle via `createImageBitmap(file)`
4. Create offscreen `<canvas>` with `outW × outH`
5. `ctx.drawImage(imgBitmap, selX, selY, selW, selH, 0, 0, outW, outH)` — crops and scales in one call
6. Close ImageBitmap
7. Determine MIME type from extension:
   - `.jpg`/`.jpeg` → `image/jpeg`, quality `0.92`
   - `.png` → `image/png`, no quality parameter
   - `.webp` → `image/webp`, quality `0.92`
8. `canvas.toBlob()` wrapped in Promise
9. Write blob to file: `fileHandle.createWritable()` → `writable.write(blob)` → `writable.close()`
10. Reload image display: revoke old URL, create new, set as img src
11. On load: update natural dimensions, fit to view, resize overlay, clear selection, update top bar
12. Show status: "Saved: WxH (mime)"

### 7. RESIZE Button State

`updateResizeButton()`:
- Enabled (green) when: selection active with w>0 & h>0 AND useFSAPI AND file extension is in SAVE_EXTS
- Disabled (gray) otherwise with contextual tooltip:
  - No selection: "Select an area first"
  - No FSAPI: "Requires Chrome/Edge with File System Access API"
  - Unsupported format: "Saving not supported for this format"

### 8. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+O | Open folder (works even when input focused) |
| Escape | Clear selection |
| Delete | Clear selection |
| F | Fit to view |
| Space+drag | Pan image |
| Mouse wheel | Zoom at cursor |
| Double-click | Fit to view |
| Up arrow | Previous file in tree |
| Down arrow | Next file in tree |

When focus is on `INPUT` or `TEXTAREA`, only Ctrl+O is intercepted; all other shortcuts are suppressed.

Space key handling: separate keydown/keyup listeners set `spaceDown` flag. Keydown changes cursor to `grab`, keyup restores to `crosshair`. Prevents default to avoid page scroll.

### 9. Top Bar

`[Open Folder]` | separator | filename (bold, full relative path) | dimensions (muted) | spacer | "Selection:" label + info | separator | "Scale:" + number input + "%" | separator | `[RESIZE]` | `[Reset Selection]`

### 10. Controls Bar

Bottom bar with dark bg (`#252525`), muted text (`#888`), 9pt:
```
Drag to select | Space+Drag Pan | Scroll Zoom | DblClick Fit | F Fit | Esc Clear | ↑↓ Prev/Next | Ctrl+O Open
```

### 11. Status Bar

Below controls bar. Shows: "Ready", "Loading...", "Scanning...", "Zoom: X%", error messages, "Saved: WxH (mime)", "Found N images."

### 12. Splitter Panel

Left splitter only (no right panel):
- 4px wide, `#444` background, `col-resize` cursor
- Hover/dragging: `#2a82da`
- `initSplitter(splitter, panel, side, min, max)` — tracks startX and panel startWidth on mousedown, clamps to min/max on mousemove
- On mouseup: resize overlay, re-fit image if in fit mode, else just redraw selection
- Hidden via CSS until tree panel is visible: `#treePanel.visible ~ #leftSplitter { display: block; }`

### 13. Empty State

Centered message in viewport: "No images loaded. Use Ctrl+O or the Open Folder button to open a folder." Shown by default and when scan finds nothing. `pointer-events: none` so it doesn't block selection.

### 14. Object URL Management

- Cache object URLs in a Map keyed by entry object
- `createObjectURL(entry)`: revoke old, get File from handle or entry.file, create blob URL, cache and return
- `revokeObjectURL(entry)`: revoke and remove from cache if exists
- `revokeAllURLs()`: revoke all cached URLs on new folder open
- After resize+save, revoke old URL and create new one to reflect updated file content

## Edge Cases

- No selection → RESIZE button grayed out with tooltip
- No FSAPI (Firefox fallback) → RESIZE button disabled with tooltip "Requires Chrome/Edge"
- Selection outside image bounds → clamped to image dimensions in `getSelRect()`
- Scale < 1 or > 1000 → clamped via `Math.max(1, Math.min(1000, ...))`
- Output dimensions < 1px → status message "Output dimensions too small"
- After save, image dimensions change → display updated, old selection cleared
- Window resize → overlay canvas resized, fit-to-view recalculated if in fit mode
- Space held during mousedown → pans instead of selecting
