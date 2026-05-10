# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

GeoSort is a QGIS plugin (≥ 3.16) that sorts vector layer features by geometric and attribute criteria, writing a progressive `sort_order` field. It requires no external Python dependencies beyond PyQGIS.

## Running tests

The core sorting logic tests run without QGIS (they use lightweight mocks):

```bash
cd /home/pigreco/git/geosort
python -m pytest tests/test_sorting.py -v
# or
python -m unittest tests.test_sorting -v
```

The dialog tests require QGIS in PATH:

```bash
python -m pytest tests/test_dialog.py -v
```

## Architecture

The plugin is split into four modules with a deliberate dependency boundary:

- **`geosort_core.py`** — pure sorting logic with no UI dependency. Contains all sort functions (`sort_by_attribute`, `sort_by_centroid`, `sort_by_geometry_property`, `sort_by_line_position`, `sort_by_expression`) plus `apply_sort_order` and `create_memory_layer`. This is the only module with unit tests.

- **`geosort_algorithm.py`** — `GeoSortAlgorithm(QgsProcessingAlgorithm)` that wraps `geosort_core` for use in the Processing Toolbox, the graphical modeler, and headless PyQGIS. Defines the 15 sort criteria as an enum (`_CRITERIA_KEYS` / `_CRITERIA_LABELS`).

- **`geosort_dialog.py`** — `GeoSortDialog(QDialog)` for the interactive UI. Built programmatically (no `.ui` file). The dialog is opened non-modally via `show()` (not `exec()`) so the QGIS canvas stays interactive for map-point picking. Contains `_PointPickerTool(QgsMapToolEmitPoint)` for reference-point selection.

- **`geosort.py`** — `GeoSort` plugin class, handles `initGui` / `unload`, registers the Processing provider, and manages the non-modal dialog lifecycle.

## Key design decisions

- The dialog uses `show()` not `exec()` — changing this to modal would break the map-point picker tool.
- `geosort_core.py` intentionally avoids any UI imports so it can be tested without QGIS.
- `test_sorting.py` duplicates the sort logic as standalone functions (rather than importing from `geosort_core`) because importing the module requires PyQGIS to be available.
- `sort_by_line_position` returns a 3-tuple `(sorted_feats, values, excluded)` — the `excluded` list contains features that don't intersect the reference line (relevant only for `intersecting_*` modes).
- `apply_sort_order` starts an edit session if the layer isn't already editable, commits on success, and rolls back on failure.

## Processing Toolbox usage

```python
import processing
result = processing.run("geosort:geosort_sort", {
    'INPUT': layer,
    'CRITERION': 0,          # index into _CRITERIA_KEYS
    'ATTRIBUTE_FIELD': 'fieldname',
    'DIRECTION': True,        # True = ascending
    'NULLS_LAST': True,
    'ADD_VALUE_FIELD': False,
    'OUTPUT': 'memory:'
})
output_layer = result['OUTPUT']
```
