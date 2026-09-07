# Design system — "Echo/S1" house style

Pulled directly from the two sibling desktop apps (`E:\Echo Audio
Converter`, `E:\TorBox_Manager`) so this app looks like it belongs next to
them. Both use **PyQt6**, not PySide6 or tkinter — match that here.

## Palette

Source of truth: `TorBox_Manager/tbm/constants.py`. Echo Audio Converter
uses the same accent green and near-black background with slightly
different exact shades; TorBox's is the more fleshed-out palette and is
what this app should start from.

| Token | Hex | Use |
|---|---|---|
| `COLOR_BG` | `#181818` | main window background |
| `COLOR_PANEL` | `#1f1f1f` | side panel / strip backgrounds |
| `COLOR_PANEL_ALT` | `#232323` | alternate row / subtle contrast surface |
| `COLOR_HEADER_BAR` | `#2d1f00` | header bar background (amber-dark) |
| `COLOR_ACCENT` | `#7cb342` | primary accent — section labels, progress, active state |
| `COLOR_ACCENT_DIM` | `#4a6b28` | dimmed accent for subtle highlights / separator lines |
| `COLOR_TEXT` | `#e8e8e8` | primary text |
| `COLOR_TEXT_MUTED` | `#666666` | secondary / placeholder text |
| `COLOR_BUTTON_BG` | `#282828` | normal button background |
| `COLOR_BUTTON_HOVER` | `#323232` | button hover state |
| `COLOR_BORDER` | `#2a2a2a` | subtle dividers |
| `COLOR_BORDER_BRIGHT` | `#3a3a3a` | brighter border for focused elements |
| `COLOR_ROW_HOVER` | `#252f1a` | row hover — very subtle green tint |

Additional shades seen in Echo Audio Converter worth keeping available for
state colors (error/disabled), same family:
- Error/destructive: bg `#4a2020`, border `#a04040`, text `#d08080` (hover bg `#5a2828`)
- Disabled: bg `#252525`, border `#353535`/`#404040`, text `#505050`/`#606060`
- Success/active toggle: bg `#2e4a1e`, border `#7cb342`, text `#7cb342` (hover bg `#3e5a2e`)

## Typography

- UI font: **Segoe UI**, 9pt.
- Log/monospace strip: **Consolas**, 8pt.
- Section labels and the app title are uppercase, letter-spaced, in the
  accent green or a muted variant.

## Layout conventions

- **Top banner**: centered uppercase app title, flanked by thin horizontal
  accent-colored divider lines running to the window edges (see TorBox
  Manager's `TORBOX MANAGER` header — small chevron/arrow glyphs sit right
  before the divider lines start). A version tag sits at the far left of the
  banner row, an edition/branding tag at the far right.
- **Left sidebar**: grouped action buttons under uppercase section headers
  (e.g. `ADD`, `QUEUE`, `ACCOUNT`). Buttons are full-width, flat, subtle
  border, left-aligned icon glyph + label.
- **Main content**: a table/tree view with a header row in the accent color
  and thin bottom border; status values render as small pill/badge widgets
  (colored background matching state — green for good/ready, muted grey for
  idle).
- **Bottom strip**: a monospace log panel above a final status bar (left:
  plain-text status/count, right: primary action button).
- Borders are 1px, flat, no heavy shadows or gradients — keep it flat and
  utilitarian, consistent with both sibling apps.

## What to reuse vs. rebuild

Both sibling apps hand-roll their QSS as an f-string built from the color
constants above (see `TorBox_Manager/tbm/ui.py` `MAIN_STYLE`). Follow the
same pattern here in `s1iptv/theme.py`: a module of color constants plus a
function that returns the full QSS string, applied once via
`window.setStyleSheet(...)`. Don't reach for a separate .qss resource file
or a theming library — it isn't what the sibling apps do and would be
inconsistent with them for no benefit.
