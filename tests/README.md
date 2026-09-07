# Tests

Offscreen PyQt6 unit tests — stdlib `unittest`, no extra dependency, same
pattern as `TorBox_Manager/tbm/tests/`. They build real objects (a
`CategoryStore`, a `CategoryTab`, etc.) against fake data/a fake Xtream
client and exercise the logic directly (no real network calls, no visible
window), so they run headless in CI or a plain terminal.

## Running

From the repo root:

```bash
venv\Scripts\python -m unittest discover -s tests -v
```

Or run a single file directly:

```bash
venv\Scripts\python tests\test_category_store.py
```

## What's covered

| File | Covers |
|---|---|
| `test_category_store.py` | assign/unassign with automatic empty subcategory/category pruning, diff (unassigned/stale), load/save round-trip, the auto-sync-from-seed reconciliation (seed-moved item follows automatically, user-reassigned item is left alone, repeated loads don't duplicate, a pre-existing file with no snapshot adopts one without changing data), rotating backups on save |
| `test_export_selection.py` | Everything included by default, exclude/include round-trip, case-insensitive matching, persistence across reload, content types don't leak into each other |
| `test_locals_data.py` | State parsing from channel names (`parse_state`), `is_locals_subcategory` matching, `find_locals_raw_categories`/`find_locals_parent_category_name`, `LocalsSelectionStore` persistence (selection, default states, merge-into-parent flag) |
| `test_export.py` | `build_m3u()`: normal categories export under their top-level group-title with full `tvg-id`/`tvg-name`/`tvg-logo`, Locals channels are excluded unless individually selected, the merged-vs-standalone-category toggle, excluded raw categories are skipped entirely, `count_channels()` matches `build_m3u()`'s counts, `default_export_path()` fallback |
| `test_category_tab.py` | Tri-state checkbox cascading (leaf → ancestors, category → descendants, Select/Deselect All), the "Will Export" preview never lists a Locals raw category by name, the taxonomy tree search filter (ancestor-chain visibility, whole-subtree-visible-on-parent-match), bulk move/reassignment of already-assigned raw categories (single and multi-select) |

## Gotcha: QMessageBox in tests

A few code paths show a real `QMessageBox` (e.g. "select something first").
Under `QT_QPA_PLATFORM=offscreen`, `.exec()` on one of these would block
forever waiting for a click that can never come. Where a test's code path
would trigger one, patch it out first — see
`test_category_tab.py::test_move_with_no_selection_does_not_raise` for the
pattern (same as `TorBox_Manager/tbm/tests/_helpers.py::always_yes`).
