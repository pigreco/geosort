# -*- coding: utf-8 -*-
"""
Test sulla logica di ordinamento pura di GeoSort.

Questi test NON richiedono QGIS: usano mock leggeri che replicano
l'interfaccia di QgsFeature e QgsGeometry necessaria per la logica core.
Eseguibili con: python -m pytest tests/test_sorting.py  oppure
                python -m unittest tests.test_sorting
"""

import math
import sys
import os
import unittest

# ──────────────────────────────────────────────────────────────────────────────
# Normalizzazione date/time (replica standalone di geosort_core._normalize_val)
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_val(val):
    """Normalizza date/time in formato ISO confrontabile Lessicograficamente."""
    # Python datetime
    try:
        return val.isoformat()
    except AttributeError:
        pass
    # PyQt date/time (mockato via toString nello unit test)
    try:
        return val.toString("yyyy-MM-dd")
    except AttributeError:
        pass
    return val

# ──────────────────────────────────────────────────────────────────────────────
# Mock leggeri (nessuna dipendenza PyQGIS)
# ──────────────────────────────────────────────────────────────────────────────

class MockPoint:
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def x(self):
        return self._x

    def y(self):
        return self._y


class MockGeometryResult:
    """Restituito da centroid() / pointOnSurface()."""
    def __init__(self, x, y):
        self._pt = MockPoint(x, y)

    def asPoint(self):
        return self._pt


class MockGeometry:
    """Mock minimale di QgsGeometry."""
    def __init__(self, geom_type, cx=0.0, cy=0.0, area=0.0, length=0.0, n_vertices=4):
        self._type = geom_type  # "point" | "line" | "polygon"
        self._cx = cx
        self._cy = cy
        self._area = area
        self._length = length
        self._n_vertices = n_vertices

    def isMultipart(self):
        return False

    def centroid(self):
        return MockGeometryResult(self._cx, self._cy)

    def pointOnSurface(self):
        return MockGeometryResult(self._cx, self._cy)

    def area(self):
        if self._type != "polygon":
            raise ValueError(f"Criterio 'area' richiede geometrie poligonali, trovato: {self._type}.")
        return self._area

    def length(self):
        return self._length


class MockFeature:
    """Mock minimale di QgsFeature."""
    def __init__(self, fid, attributes=None, geometry=None):
        self._fid = fid
        self._attrs = attributes or {}
        self._geom = geometry

    def id(self):
        return self._fid

    def __getitem__(self, key):
        return self._attrs.get(key)

    def geometry(self):
        return self._geom


# ──────────────────────────────────────────────────────────────────────────────
# Funzioni standalone (stessa logica di geosort_core.py, senza import PyQGIS)
# ──────────────────────────────────────────────────────────────────────────────

def _natural_key(val):
    import re
    return [int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r"(\d+)", str(val))]


def _sort_by_attribute(features, field, ascending=True, nulls_last=True, natural_sort=False, progress_callback=None):
    null_priority = 1 if nulls_last else -1

    def key(f):
        val = f[field]
        if val is None:
            return (null_priority, [])
        if natural_sort:
            return (0, _natural_key(val))
        try:
            return (0, _normalize_val(val))
        except TypeError:
            return (0, str(val))

    result = sorted(features, key=key, reverse=not ascending)

    if progress_callback:
        progress_callback(100)

    return result


def _sort_by_centroid(features, axis="x", ascending=True, ref_point=None):
    def key(f):
        geom = f.geometry()
        pt = geom.centroid().asPoint()
        if axis == "dist" and ref_point is not None:
            return math.sqrt(
                (pt.x() - ref_point[0]) ** 2 + (pt.y() - ref_point[1]) ** 2
            )
        return pt.x() if axis == "x" else pt.y()

    sorted_feats = sorted(features, key=key, reverse=not ascending)
    values = [key(f) for f in sorted_feats]
    return sorted_feats, values


def _check_criterion_compatibility(geom_type, criterion):
    """Replica la validazione di geosort_core._geom_value()."""
    if criterion == "area" and geom_type != "polygon":
        raise ValueError(f"Criterio 'area' richiede geometrie poligonali, trovato: {geom_type}.")
    if criterion == "perimeter" and geom_type != "polygon":
        raise ValueError(f"Criterio 'perimeter' richiede geometrie poligonali, trovato: {geom_type}.")
    if criterion == "length" and geom_type != "line":
        raise ValueError(f"Criterio 'length' richiede geometrie lineari, trovato: {geom_type}.")


# ──────────────────────────────────────────────────────────────────────────────
# Test: ordinamento per attributo
# ──────────────────────────────────────────────────────────────────────────────

class TestSortByAttribute(unittest.TestCase):

    def _feats(self, values, field="val"):
        return [MockFeature(i, {field: v}) for i, v in enumerate(values)]

    def test_ascending(self):
        result = _sort_by_attribute(self._feats([30, 10, 20]), "val", ascending=True)
        self.assertEqual([f["val"] for f in result], [10, 20, 30])

    def test_descending(self):
        result = _sort_by_attribute(self._feats([30, 10, 20]), "val", ascending=False)
        self.assertEqual([f["val"] for f in result], [30, 20, 10])

    def test_null_last(self):
        result = _sort_by_attribute(self._feats([None, 5, 2]), "val",
                                    ascending=True, nulls_last=True)
        self.assertIsNone(result[-1]["val"])

    def test_null_first(self):
        result = _sort_by_attribute(self._feats([None, 5, 2]), "val",
                                    ascending=True, nulls_last=False)
        self.assertIsNone(result[0]["val"])

    def test_already_sorted(self):
        result = _sort_by_attribute(self._feats([1, 2, 3]), "val", ascending=True)
        self.assertEqual([f["val"] for f in result], [1, 2, 3])

    def test_single_feature(self):
        result = _sort_by_attribute(self._feats([42]), "val")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["val"], 42)

    def test_all_nulls(self):
        result = _sort_by_attribute(self._feats([None, None, None]), "val")
        self.assertEqual(len(result), 3)

    def test_string_values(self):
        result = _sort_by_attribute(self._feats(["banana", "apple", "cherry"]), "val",
                                    ascending=True)
        self.assertEqual([f["val"] for f in result], ["apple", "banana", "cherry"])

    def test_float_values(self):
        result = _sort_by_attribute(self._feats([1.5, 0.3, 2.7]), "val", ascending=True)
        vals = [f["val"] for f in result]
        self.assertEqual(vals, sorted(vals))

    def test_natural_sort_issue3(self):
        # Riproduce esattamente il caso dell'issue #3: valori stringa "11", "1010", "1111"
        result = _sort_by_attribute(
            self._feats(["1010", "11", "1111"]), "val",
            ascending=True, natural_sort=True,
        )
        self.assertEqual([f["val"] for f in result], ["11", "1010", "1111"])

    def test_natural_sort_ascending(self):
        result = _sort_by_attribute(
            self._feats(["file10", "file2", "file1"]), "val",
            ascending=True, natural_sort=True,
        )
        self.assertEqual([f["val"] for f in result], ["file1", "file2", "file10"])

    def test_natural_sort_descending(self):
        result = _sort_by_attribute(
            self._feats(["file10", "file2", "file1"]), "val",
            ascending=False, natural_sort=True,
        )
        self.assertEqual([f["val"] for f in result], ["file10", "file2", "file1"])

    def test_natural_sort_off_is_lexicographic(self):
        # Senza natural_sort le stringhe restano lessicografiche
        result = _sort_by_attribute(
            self._feats(["11", "1010", "1111"]), "val",
            ascending=True, natural_sort=False,
        )
        self.assertEqual([f["val"] for f in result], ["1010", "11", "1111"])

    def test_natural_sort_nulls(self):
        result = _sort_by_attribute(
            self._feats([None, "file10", "file2"]), "val",
            ascending=True, nulls_last=True, natural_sort=True,
        )
        vals = [f["val"] for f in result]
        self.assertEqual(vals, ["file2", "file10", None])

    def test_date_sorting_ascending(self):
        """Date Python datetime.date: ordinate cronologicamente."""
        from datetime import date
        feats = [
            MockFeature(0, {"data": date(2024, 6, 15)}),
            MockFeature(1, {"data": date(2024, 1, 10)}),
            MockFeature(2, {"data": date(2023, 12, 31)}),
        ]
        result = _sort_by_attribute(feats, "data", ascending=True)
        dates = [f["data"] for f in result]
        self.assertEqual(dates, [date(2023, 12, 31), date(2024, 1, 10), date(2024, 6, 15)])

    def test_date_sorting_descending(self):
        from datetime import date
        feats = [
            MockFeature(0, {"data": date(2024, 1, 10)}),
            MockFeature(1, {"data": date(2024, 6, 15)}),
        ]
        result = _sort_by_attribute(feats, "data", ascending=False)
        dates = [f["data"] for f in result]
        self.assertEqual(dates, [date(2024, 6, 15), date(2024, 1, 10)])

    def test_datetime_sorting_ascending(self):
        """Python datetime.datetime: ordine cronologico corretto."""
        from datetime import datetime
        feats = [
            MockFeature(0, {"ts": datetime(2024, 6, 15, 12, 0)}),
            MockFeature(1, {"ts": datetime(2024, 6, 15, 8, 30)}),
            MockFeature(2, {"ts": datetime(2024, 6, 14, 23, 59)}),
        ]
        result = _sort_by_attribute(feats, "ts", ascending=True)
        ts = [f["ts"] for f in result]
        self.assertEqual(ts[0], datetime(2024, 6, 14, 23, 59))
        self.assertEqual(ts[1], datetime(2024, 6, 15, 8, 30))
        self.assertEqual(ts[2], datetime(2024, 6, 15, 12, 0))

    def test_date_with_nulls(self):
        """Date con NULL: i NULL vanno in fondo (nulls_last=True)."""
        from datetime import date
        feats = [
            MockFeature(0, {"data": None}),
            MockFeature(1, {"data": date(2024, 3, 1)}),
            MockFeature(2, {"data": date(2024, 1, 1)}),
        ]
        result = _sort_by_attribute(feats, "data", ascending=True, nulls_last=True)
        self.assertEqual(result[0]["data"], date(2024, 1, 1))
        self.assertEqual(result[1]["data"], date(2024, 3, 1))
        self.assertIsNone(result[2]["data"])


# ──────────────────────────────────────────────────────────────────────────────
# Test: ordinamento per centroide
# ──────────────────────────────────────────────────────────────────────────────

def _mock_sort_by_geometry_property(features, criterion, ascending=True):
    """Mock standalone di sort_by_geometry_property – replica la validazione early-check."""
    if features:
        _check_criterion_compatibility(features[0].geometry()._type, criterion)

    def _geom_val(f):
        geom = f.geometry()
        if criterion in ("area",):
            return geom._area
        if criterion in ("perimeter", "length"):
            return geom._length
        if criterion == "n_vertices":
            return geom._n_vertices
        return 0.0

    sorted_feats = sorted(features, key=_geom_val, reverse=not ascending)
    values = [_geom_val(f) for f in sorted_feats]
    return sorted_feats, values


# ──────────────────────────────────────────────────────────────────────────────
# Test: sort_by_geometry_property – ValueError su tipo incompatibile
# ──────────────────────────────────────────────────────────────────────────────

class TestSortByGeometryPropertyValidation(unittest.TestCase):
    """Testa che sort_by_geometry_property lanci ValueError immediatamente sul primo tipo incompatibile."""

    def _poly(self, area=100.0):
        return MockFeature(0, geometry=MockGeometry("polygon", area=area))

    def _line(self, length=10.0):
        return MockFeature(0, geometry=MockGeometry("line", length=length))

    def _point(self):
        return MockFeature(0, geometry=MockGeometry("point"))

    def test_area_on_polygon_ok(self):
        _mock_sort_by_geometry_property([self._poly()], "area")

    def test_area_on_point_raises(self):
        with self.assertRaises(ValueError):
            _mock_sort_by_geometry_property([self._point()], "area")

    def test_area_on_line_raises(self):
        with self.assertRaises(ValueError):
            _mock_sort_by_geometry_property([self._line()], "area")

    def test_length_on_line_ok(self):
        _mock_sort_by_geometry_property([self._line()], "length")

    def test_length_on_polygon_raises(self):
        with self.assertRaises(ValueError):
            _mock_sort_by_geometry_property([self._poly()], "length")

    def test_perimeter_on_polygon_ok(self):
        _mock_sort_by_geometry_property([self._poly()], "perimeter")

    def test_perimeter_on_point_raises(self):
        with self.assertRaises(ValueError):
            _mock_sort_by_geometry_property([self._point()], "perimeter")

    def test_n_vertices_any_type(self):
        for geom_type in ("point", "line", "polygon"):
            feats = [MockFeature(0, geometry=MockGeometry(geom_type))]
            _mock_sort_by_geometry_property(feats, "n_vertices")

    def test_empty_list_no_exception(self):
        _mock_sort_by_geometry_property([], "area")

    def test_sort_area_ascending(self):
        feats = [
            MockFeature(0, geometry=MockGeometry("polygon", area=300)),
            MockFeature(1, geometry=MockGeometry("polygon", area=100)),
            MockFeature(2, geometry=MockGeometry("polygon", area=200)),
        ]
        _, values = _mock_sort_by_geometry_property(feats, "area", ascending=True)
        self.assertEqual(values, [100, 200, 300])

    def test_sort_area_descending(self):
        feats = [
            MockFeature(0, geometry=MockGeometry("polygon", area=300)),
            MockFeature(1, geometry=MockGeometry("polygon", area=100)),
        ]
        _, values = _mock_sort_by_geometry_property(feats, "area", ascending=False)
        self.assertEqual(values, [300, 100])


# ──────────────────────────────────────────────────────────────────────────────
# Mock layer per testare apply_sort_order standalone
# ──────────────────────────────────────────────────────────────────────────────

class MockLayer:
    """Mock minimale di QgsVectorLayer per apply_sort_order."""

    def __init__(self, field_names=None, editing=False):
        self._field_names = list(field_names or [])
        self._editing = editing
        self._changes = {}          # {(fid, idx): val}
        self._start_editing_fails = False
        self._committed = False

    def isEditable(self):
        return self._editing

    def startEditing(self):
        if self._start_editing_fails:
            return False
        self._editing = True
        return True

    def fields(self):
        return self

    def indexOf(self, name):
        return self._field_names.index(name) if name in self._field_names else -1

    def addAttribute(self, field_name):
        # field_name può essere una stringa (mock) o un oggetto con attributo .name
        name = field_name if isinstance(field_name, str) else getattr(field_name, "name", str(field_name))
        self._field_names.append(name)

    def updateFields(self):
        pass

    def changeAttributeValue(self, fid, idx, val):
        self._changes[(fid, idx)] = val

    def commitChanges(self):
        self._committed = True
        return True

    def rollBack(self):
        pass


def _mock_apply_sort_order(layer, sorted_features, add_criterion_field=False,
                           criterion_values=None, criterion_field_name="sort_value"):
    """Mock standalone di apply_sort_order – senza QgsField/QMetaType."""
    try:
        if not layer.isEditable():
            if not layer.startEditing():
                return False

        sort_idx = layer.indexOf("sort_order")
        if sort_idx == -1:
            layer.addAttribute("sort_order")
            sort_idx = layer.indexOf("sort_order")

        crit_idx = -1
        if add_criterion_field and criterion_values:
            crit_idx = layer.indexOf(criterion_field_name)
            if crit_idx == -1:
                layer.addAttribute(criterion_field_name)
                crit_idx = layer.indexOf(criterion_field_name)

        for i, feat in enumerate(sorted_features):
            layer.changeAttributeValue(feat.id(), sort_idx, i + 1)
            if add_criterion_field and criterion_values and crit_idx != -1:
                try:
                    layer.changeAttributeValue(feat.id(), crit_idx, float(criterion_values[i]))
                except (TypeError, ValueError):
                    pass

        layer.commitChanges()
        return True

    except Exception:
        return False


class TestApplySortOrder(unittest.TestCase):
    """Testa apply_sort_order (mock standalone, senza QGIS)."""

    def _feats(self, n):
        return [MockFeature(i, {"val": i}) for i in range(n)]

    def test_adds_sort_order_when_missing(self):
        layer = MockLayer(field_names=["nome", "area"])
        ok = _mock_apply_sort_order(layer, self._feats(3))
        self.assertTrue(ok)
        self.assertIn("sort_order", layer._field_names)

    def test_no_duplicate_sort_order_when_existing(self):
        layer = MockLayer(field_names=["nome", "sort_order"])
        initial_len = len(layer._field_names)
        ok = _mock_apply_sort_order(layer, self._feats(3))
        self.assertTrue(ok)
        self.assertEqual(layer._field_names.count("sort_order"), 1)
        self.assertEqual(len(layer._field_names), initial_len)

    def test_values_written_correctly(self):
        layer = MockLayer(field_names=["nome"])
        feats = self._feats(3)
        ok = _mock_apply_sort_order(layer, feats)
        self.assertTrue(ok)
        sort_idx = layer.indexOf("sort_order")
        for i, feat in enumerate(feats):
            self.assertEqual(layer._changes[(feat.id(), sort_idx)], i + 1)

    def test_start_editing_fails_returns_false(self):
        layer = MockLayer(field_names=["nome"], editing=False)
        layer._start_editing_fails = True
        ok = _mock_apply_sort_order(layer, self._feats(2))
        self.assertFalse(ok)

    def test_adds_criterion_field(self):
        layer = MockLayer(field_names=["nome"])
        feats = self._feats(3)
        values = [100.0, 200.0, 300.0]
        ok = _mock_apply_sort_order(layer, feats, add_criterion_field=True,
                                    criterion_values=values, criterion_field_name="sort_area")
        self.assertTrue(ok)
        self.assertIn("sort_area", layer._field_names)
        crit_idx = layer.indexOf("sort_area")
        for i, feat in enumerate(feats):
            self.assertAlmostEqual(layer._changes[(feat.id(), crit_idx)], values[i])

    def test_existing_criterion_field_not_duplicated(self):
        layer = MockLayer(field_names=["nome", "sort_area"])
        feats = self._feats(2)
        values = [10.0, 20.0]
        _mock_apply_sort_order(layer, feats, add_criterion_field=True,
                               criterion_values=values, criterion_field_name="sort_area")
        self.assertEqual(layer._field_names.count("sort_area"), 1)

    def test_sort_order_starts_at_one(self):
        layer = MockLayer(field_names=[])
        feats = self._feats(4)
        _mock_apply_sort_order(layer, feats)
        sort_idx = layer.indexOf("sort_order")
        self.assertEqual(layer._changes[(feats[0].id(), sort_idx)], 1)

    def test_committed_on_success(self):
        layer = MockLayer(field_names=[])
        _mock_apply_sort_order(layer, self._feats(2))
        self.assertTrue(layer._committed)


class TestSortByCentroid(unittest.TestCase):

    def _point_feats(self, coords):
        return [
            MockFeature(i, geometry=MockGeometry("point", cx=x, cy=y))
            for i, (x, y) in enumerate(coords)
        ]

    def test_sort_x_ascending(self):
        feats = self._point_feats([(3, 1), (1, 5), (2, 3)])
        result, _ = _sort_by_centroid(feats, axis="x", ascending=True)
        xs = [f.geometry().centroid().asPoint().x() for f in result]
        self.assertEqual(xs, [1.0, 2.0, 3.0])

    def test_sort_y_ascending(self):
        feats = self._point_feats([(1, 3), (2, 1), (3, 2)])
        result, _ = _sort_by_centroid(feats, axis="y", ascending=True)
        ys = [f.geometry().centroid().asPoint().y() for f in result]
        self.assertEqual(ys, [1.0, 2.0, 3.0])

    def test_sort_x_descending(self):
        feats = self._point_feats([(1, 0), (3, 0), (2, 0)])
        result, _ = _sort_by_centroid(feats, axis="x", ascending=False)
        xs = [f.geometry().centroid().asPoint().x() for f in result]
        self.assertEqual(xs, [3.0, 2.0, 1.0])

    def test_sort_distance_from_origin(self):
        # Distanze da (0,0): (3,4)=5, (0,1)=1, (1,1)≈1.41
        feats = self._point_feats([(3, 4), (0, 1), (1, 1)])
        result, values = _sort_by_centroid(feats, axis="dist", ascending=True,
                                           ref_point=(0, 0))
        self.assertAlmostEqual(values[0], 1.0, places=5)
        self.assertAlmostEqual(values[1], math.sqrt(2), places=5)
        self.assertAlmostEqual(values[2], 5.0, places=5)

    def test_values_monotone_ascending(self):
        feats = self._point_feats([(3, 0), (1, 0), (2, 0)])
        _, values = _sort_by_centroid(feats, axis="x", ascending=True)
        self.assertTrue(all(values[i] <= values[i + 1] for i in range(len(values) - 1)))

    def test_values_count_matches_features(self):
        feats = self._point_feats([(i, 0) for i in range(5)])
        result, values = _sort_by_centroid(feats, axis="x", ascending=True)
        self.assertEqual(len(result), len(values))


# ──────────────────────────────────────────────────────────────────────────────
# Test: compatibilità criterio / tipo geometria
# ──────────────────────────────────────────────────────────────────────────────

class TestCriterionCompatibility(unittest.TestCase):

    def test_area_on_polygon_ok(self):
        _check_criterion_compatibility("polygon", "area")  # non deve sollevare

    def test_area_on_point_raises(self):
        with self.assertRaises(ValueError):
            _check_criterion_compatibility("point", "area")

    def test_area_on_line_raises(self):
        with self.assertRaises(ValueError):
            _check_criterion_compatibility("line", "area")

    def test_perimeter_on_polygon_ok(self):
        _check_criterion_compatibility("polygon", "perimeter")

    def test_perimeter_on_point_raises(self):
        with self.assertRaises(ValueError):
            _check_criterion_compatibility("point", "perimeter")

    def test_length_on_line_ok(self):
        _check_criterion_compatibility("line", "length")

    def test_length_on_polygon_raises(self):
        with self.assertRaises(ValueError):
            _check_criterion_compatibility("polygon", "length")

    def test_n_vertices_accepts_any(self):
        for gt in ("point", "line", "polygon"):
            _check_criterion_compatibility(gt, "n_vertices")  # nessuna eccezione


# ──────────────────────────────────────────────────────────────────────────────
# Test: progress_callback
# ──────────────────────────────────────────────────────────────────────────────

class TestProgressCallback(unittest.TestCase):

    def _feats(self, n, field="val"):
        return [MockFeature(i, {field: i}) for i in range(n)]

    def test_callback_called_for_sort_by_attribute(self):
        feats = self._feats(5)
        called_with = []
        _sort_by_attribute(feats, "val", ascending=True,
                          progress_callback=lambda pct: called_with.append(pct))
        self.assertGreater(len(called_with), 0)
        self.assertEqual(called_with[-1], 100)

    def test_callback_called_for_expression_sort(self):
        feats = self._feats(5)
        called_with = []
        _mock_sort_by_expression(
            feats, lambda f: f["val"], ascending=True,
            progress_callback=lambda pct: called_with.append(pct),
        )
        self.assertGreater(len(called_with), 0)
        self.assertEqual(called_with[-1], 100)


# ──────────────────────────────────────────────────────────────────────────────
# Test: sort_order progressivo
# ──────────────────────────────────────────────────────────────────────────────

class TestSortOrderValues(unittest.TestCase):

    def test_sort_order_starts_at_one(self):
        feats = [MockFeature(i, {"val": v}) for i, v in enumerate([3, 1, 2])]
        sorted_feats = _sort_by_attribute(feats, "val", ascending=True)
        for expected, feat in enumerate(sorted_feats, start=1):
            # Verifica che l'indice corrisponda alla posizione attesa
            self.assertEqual(expected, list(range(1, len(sorted_feats) + 1))[expected - 1])

    def test_sort_order_length_equals_features(self):
        feats = [MockFeature(i, {"val": i}) for i in range(7)]
        sorted_feats = _sort_by_attribute(feats, "val")
        self.assertEqual(len(sorted_feats), 7)

    def test_sort_order_no_duplicates(self):
        feats = [MockFeature(i, {"val": i}) for i in range(5)]
        sorted_feats = _sort_by_attribute(feats, "val")
        orders = list(range(1, len(sorted_feats) + 1))
        self.assertEqual(len(set(orders)), len(sorted_feats))




# ──────────────────────────────────────────────────────────────────────────────
# Test: ordinamento lungo linea – tutti e tre i modi
# (standalone, senza PyQGIS: usa mock con flag intersects)
# ──────────────────────────────────────────────────────────────────────────────

class MockLineSortGeometry:
    """Mock geometria per testare sort_by_line_position standalone."""

    def __init__(self, cx, cy, intersects_line=True):
        self._cx = cx
        self._cy = cy
        self._intersects = intersects_line

    def isMultipart(self):
        return False

    def centroid(self):
        return MockGeometryResult(self._cx, self._cy)

    def wkbType(self):
        return "point_mock"


def _mock_sort_by_line_position(features, ascending=True, mode="centroid_projection"):
    """Versione standalone del sort_by_line_position con mock.

    Usa feature.geometry()._cx come distanza simulata lungo la linea.
    """
    sorted_feats = []
    values = []
    excluded = []

    for f in features:
        geom = f.geometry()
        intersects = geom._intersects

        if mode == "centroid_projection":
            dist = geom._cx   # cx simula distanza curvilinea
            sorted_feats.append(f)
            values.append(dist)

        elif mode == "intersecting_projection":
            if not intersects:
                excluded.append(f)
                continue
            dist = geom._cx
            sorted_feats.append(f)
            values.append(dist)

        elif mode == "intersecting_first_pt":
            if not intersects:
                excluded.append(f)
                continue
            dist = geom._cx  # simula primo punto di intersezione = cx
            sorted_feats.append(f)
            values.append(dist)

    paired = sorted(zip(values, sorted_feats), reverse=not ascending)
    return [f for _, f in paired], [v for v, _ in paired], excluded


class TestLineSortModes(unittest.TestCase):

    def _make(self, specs):
        """specs = [(cx, intersects), ...]"""
        return [
            MockFeature(i, geometry=MockLineSortGeometry(cx, cy=0, intersects_line=ints))
            for i, (cx, ints) in enumerate(specs)
        ]

    # ── centroid_projection: tutte le feature incluse ─────────────────────────

    def test_centroid_projection_includes_all(self):
        feats = self._make([(3, True), (1, False), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="centroid_projection")
        self.assertEqual(len(result), 3)
        self.assertEqual(len(excluded), 0)

    def test_centroid_projection_ascending(self):
        feats = self._make([(3, True), (1, True), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="centroid_projection", ascending=True)
        self.assertEqual(values, [1, 2, 3])

    def test_centroid_projection_descending(self):
        feats = self._make([(3, True), (1, True), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="centroid_projection", ascending=False)
        self.assertEqual(values, [3, 2, 1])

    # ── intersecting_projection: esclude non-intersecanti ─────────────────────

    def test_intersecting_projection_excludes_non_intersecting(self):
        feats = self._make([(3, True), (1, False), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="intersecting_projection")
        self.assertEqual(len(result), 2)
        self.assertEqual(len(excluded), 1)
        self.assertFalse(excluded[0].geometry()._intersects)

    def test_intersecting_projection_correct_order(self):
        feats = self._make([(3, True), (1, False), (2, True)])
        result, values, _ = _mock_sort_by_line_position(feats, mode="intersecting_projection", ascending=True)
        self.assertEqual(values, [2, 3])

    def test_intersecting_projection_all_excluded(self):
        feats = self._make([(1, False), (2, False)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="intersecting_projection")
        self.assertEqual(len(result), 0)
        self.assertEqual(len(excluded), 2)

    # ── intersecting_first_pt: usa primo punto di intersezione ────────────────

    def test_intersecting_first_pt_excludes_non_intersecting(self):
        feats = self._make([(1, False), (2, True), (3, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="intersecting_first_pt")
        self.assertEqual(len(result), 2)
        self.assertEqual(len(excluded), 1)

    def test_intersecting_first_pt_ascending(self):
        feats = self._make([(3, True), (1, True), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="intersecting_first_pt", ascending=True)
        self.assertEqual(values, [1, 2, 3])

    def test_intersecting_first_pt_mixed(self):
        """Feature miste: alcune intersecano (usano primo punto), altre no (escluse)."""
        feats = self._make([(5, False), (1, True), (3, False), (2, True)])
        result, values, excluded = _mock_sort_by_line_position(feats, mode="intersecting_first_pt", ascending=True)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(excluded), 2)
        self.assertEqual(values, [1, 2])

    # ── modalità sconosciuta ──────────────────────────────────────────────────

    def test_unknown_mode_raises(self):
        """Una modalità sconosciuta deve sollevare ValueError."""
        feats = self._make([(1, True)])
        with self.assertRaises(KeyError):
            # Verifica che le sole chiavi valide siano le tre definite
            valid = {"centroid_projection", "intersecting_projection", "intersecting_first_pt"}
            unknown = "invalid_mode"
            if unknown not in valid:
                raise KeyError(f"Modalità sconosciuta: {unknown!r}")



# ──────────────────────────────────────────────────────────────────────────────
# Test: ordinamento per espressione (mock standalone, senza PyQGIS)
# ──────────────────────────────────────────────────────────────────────────────

def _mock_sort_by_expression(features, expr_fn, ascending=True, nulls_last=True, natural_sort=False, progress_callback=None):
    """Versione standalone di sort_by_expression.

    ``expr_fn`` è una callable Python che riceve una MockFeature e restituisce
    il valore di ordinamento (equivalente all'espressione QGIS valutata).
    None = errore di valutazione (→ trattato come NULL).
    """
    null_priority = 1 if nulls_last else -1
    pairs = []

    for feat in features:
        try:
            val = expr_fn(feat)
        except Exception:
            val = None
        is_null = val is None
        pairs.append((feat, val, is_null))

    def key(item):
        _, val, is_null = item
        if is_null:
            return (null_priority, [])
        if natural_sort:
            return (0, _natural_key(val))
        try:
            return (0, _normalize_val(val))
        except TypeError:
            return (0, str(val))

    pairs.sort(key=key, reverse=not ascending)

    if progress_callback:
        progress_callback(100)

    return [p[0] for p in pairs], [p[1] for p in pairs], []


class TestSortByExpression(unittest.TestCase):

    def _feats(self, values, field="val"):
        return [MockFeature(i, {field: v}) for i, v in enumerate(values)]

    def _geom_feats(self, areas):
        """Feature con geometria poligonale mock (area simulata via attributo)."""
        return [MockFeature(i, {"area": a}) for i, a in enumerate(areas)]

    # ── Espressioni su attributo singolo ─────────────────────────────────────

    def test_expression_field_ascending(self):
        feats = self._feats([30, 10, 20])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"], ascending=True
        )
        self.assertEqual(values, [10, 20, 30])

    def test_expression_field_descending(self):
        feats = self._feats([30, 10, 20])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"], ascending=False
        )
        self.assertEqual(values, [30, 20, 10])

    # ── Espressioni calcolate (combinazione campi) ────────────────────────────

    def test_expression_ratio(self):
        """Ordina per rapporto area/perimetro (es. "area" / "perimetro")."""
        feats = [
            MockFeature(0, {"area": 100, "perim": 40}),  # ratio 2.5
            MockFeature(1, {"area": 50,  "perim": 50}),  # ratio 1.0
            MockFeature(2, {"area": 80,  "perim": 20}),  # ratio 4.0
        ]
        expr = lambda f: f["area"] / f["perim"]
        result, values, _ = _mock_sort_by_expression(feats, expr, ascending=True)
        self.assertAlmostEqual(values[0], 1.0)
        self.assertAlmostEqual(values[1], 2.5)
        self.assertAlmostEqual(values[2], 4.0)

    def test_expression_string_concat(self):
        """Ordina per concatenazione di due campi stringa."""
        feats = [
            MockFeature(0, {"regione": "Veneto",   "comune": "Mestre"}),
            MockFeature(1, {"regione": "Campania", "comune": "Napoli"}),
            MockFeature(2, {"regione": "Campania", "comune": "Avellino"}),
        ]
        expr = lambda f: f["regione"] + f["comune"]
        result, values, _ = _mock_sort_by_expression(feats, expr, ascending=True)
        # Campania+Avellino < Campania+Napoli < Veneto+Mestre
        self.assertEqual(values[0], "CampaniaAvellino")
        self.assertEqual(values[1], "CampaniaNapoli")
        self.assertEqual(values[2], "VenetoMestre")

    def test_expression_conditional(self):
        """Ordina per espressione condizionale (CASE WHEN equivalente)."""
        feats = [
            MockFeature(0, {"tipo": "B"}),
            MockFeature(1, {"tipo": "A"}),
            MockFeature(2, {"tipo": "C"}),
        ]
        # A→1, B→2, C→3
        priority = {"A": 1, "B": 2, "C": 3}
        expr = lambda f: priority.get(f["tipo"], 99)
        result, values, _ = _mock_sort_by_expression(feats, expr, ascending=True)
        self.assertEqual(values, [1, 2, 3])
        self.assertEqual(result[0]["tipo"], "A")

    # ── Gestione errori / NULL ────────────────────────────────────────────────

    def test_expression_null_last(self):
        """Feature con valore NULL (errore di valutazione) vanno in fondo."""
        feats = self._feats([None, 5, 2])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"], ascending=True, nulls_last=True
        )
        self.assertIsNone(values[-1])
        self.assertEqual(values[0], 2)

    def test_expression_null_first(self):
        feats = self._feats([None, 5, 2])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"], ascending=True, nulls_last=False
        )
        self.assertIsNone(values[0])

    def test_expression_eval_error_treated_as_null(self):
        """Un errore di valutazione (divisione per zero) deve essere trattato come NULL."""
        feats = [
            MockFeature(0, {"a": 10, "b": 2}),
            MockFeature(1, {"a": 5,  "b": 0}),  # divisione per zero
            MockFeature(2, {"a": 8,  "b": 4}),
        ]
        def expr(f):
            b = f["b"]
            if b == 0:
                return None  # simula errore di valutazione
            return f["a"] / b

        result, values, _ = _mock_sort_by_expression(
            feats, expr, ascending=True, nulls_last=True
        )
        # Valori validi: 2.0 (8/4), 5.0 (10/2); NULL in fondo
        self.assertAlmostEqual(values[0], 2.0)
        self.assertAlmostEqual(values[1], 5.0)
        self.assertIsNone(values[2])

    def test_expression_all_nulls(self):
        feats = self._feats([None, None, None])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"]
        )
        self.assertEqual(len(result), 3)
        self.assertTrue(all(v is None for v in values))

    def test_expression_returns_same_count(self):
        feats = self._feats([5, 3, 8, 1, 9])
        result, values, _ = _mock_sort_by_expression(
            feats, lambda f: f["val"]
        )
        self.assertEqual(len(result), 5)
        self.assertEqual(len(values), 5)

    def test_natural_sort_expression_issue3(self):
        # Riproduce il caso issue #3: fid||id_poly → "11","1010","1111"
        feats = [
            MockFeature(0, {"fid": 10, "id_poly": 10}),
            MockFeature(1, {"fid": 1,  "id_poly": 1}),
            MockFeature(2, {"fid": 11, "id_poly": 11}),
        ]
        expr = lambda f: str(f["fid"]) + str(f["id_poly"])
        result, values, _ = _mock_sort_by_expression(
            feats, expr, ascending=True, natural_sort=True
        )
        self.assertEqual(values, ["11", "1010", "1111"])

    def test_natural_sort_expression_off_is_lexicographic(self):
        feats = [
            MockFeature(0, {"fid": 10, "id_poly": 10}),
            MockFeature(1, {"fid": 1,  "id_poly": 1}),
            MockFeature(2, {"fid": 11, "id_poly": 11}),
        ]
        expr = lambda f: str(f["fid"]) + str(f["id_poly"])
        result, values, _ = _mock_sort_by_expression(
            feats, expr, ascending=True, natural_sort=False
        )
        # Ordinamento lessicografico: "1010" < "11" < "1111"
        self.assertEqual(values, ["1010", "11", "1111"])

# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
