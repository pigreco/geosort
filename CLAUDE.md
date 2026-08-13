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

### Test empirici (manuali, non in CI)

`test_empirici/` (gitignored, non tracciato) può contenere GeoPackage reali —
punti, linee, poligoni con casi limite scomodi da costruire a mano in un test
(multipart, buchi, geometrie NULL, geometrie topologicamente invalide) — per
esplorazione manuale con la skill `qgis-headless`, non come parte della suite
automatica. Rigenerabile con:

```bash
MAMBA_ROOT_PREFIX=$HOME/micromamba QT_QPA_PLATFORM=offscreen \
  micromamba run -n qgis python scripts/gen_test_empirici.py
```

Se un caso scoperto lì rivela un bug, va poi incapsulato come geometria
sintetica minimale in `tests/test_algorithm.py` (o `test_sorting.py`) così da
restare protetto in CI — `test_empirici/` è dove si *scopre* un problema, non
dove resta l'unica prova che sia stato risolto.

## Architecture

The plugin is split into four modules with a deliberate dependency boundary:

- **`geosort_core.py`** — pure sorting logic with no UI dependency. Contains all sort functions (`sort_by_attribute`, `sort_by_centroid`, `sort_by_geometry_property`, `sort_by_line_position`, `sort_by_expression`) plus `apply_sort_order` and `create_memory_layer`. This is the only module with unit tests.

- **`geosort_algorithm.py`** — `GeoSortAlgorithm(QgsProcessingAlgorithm)` that wraps `geosort_core` for use in the Processing Toolbox, the graphical modeler, and headless PyQGIS. Defines the 17 sort criteria as an enum (`_CRITERIA_KEYS` / `_CRITERIA_LABELS`).

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

## README & Documentation Best Practices

### Required Badges (all QGIS plugins should have these)

Every README must include **version**, **QGIS compatibility**, and **license** badges early on:

```markdown
[![Version](https://img.shields.io/badge/version-X.Y.Z-blue.svg)](https://github.com/user/repo/releases)
[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B%20%7C%204.x-orange.svg)](#requirements)
[![License](https://img.shields.io/badge/license-GPLv2-red.svg)](LICENSE)
```

Add a **language selector** if the plugin supports multiple languages:

```markdown
[![Languages](https://img.shields.io/badge/languages-IT%20%7C%20EN-green.svg)](#languages)
```

### Bilingual README Structure (when applicable)

For multilingual plugins, create:
- `README.md` (primary language, e.g., Italian)
- `README.en.md` (English)

Add language selector links at the top of each:

```markdown
🇮🇹 **Italiano** | [🇬🇧 English](README.en.md)
```

### README Sections (standard order)

1. Title + Language selectors + Badges
2. One-line description
3. Screenshot (if available)
4. Features (table format recommended)
5. Installation
6. Usage
7. Processing Toolbox (if applicable)
8. Requirements
9. Compatibility notes (Qt5/Qt6, QGIS versions, etc.)
10. Testing (for developers)
11. Contributing guidelines
12. License
13. Acknowledgments

### Translation/i18n Documentation

If adding translations, document:
- How to generate/update `.ts` files
- How to add new language translations
- Whether `.qm` compilation is required or optional
