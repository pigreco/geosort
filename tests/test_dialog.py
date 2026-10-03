# -*- coding: utf-8 -*-
"""
Test sulla finestra di dialogo GeoSortDialog.

Richiedono QGIS installato e avviabile tramite qgis.testing.
Eseguibili con: python -m pytest tests/test_dialog.py
oppure dalla console QGIS: exec(open('tests/test_dialog.py').read())

Se QGIS non è disponibile nel PATH, i test vengono saltati automaticamente.
"""

import sys
import os
import unittest


def _qgis_available():
    try:
        import qgis  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_qgis_available(), "QGIS non disponibile in questo ambiente di test")
class TestGeoSortDialog(unittest.TestCase):
    """Test sulla UI costruita programmaticamente."""

    @classmethod
    def setUpClass(cls):
        """Avvia l'applicazione QGIS minima necessaria per i widget Qt."""
        from qgis.testing import start_app
        cls.qgis_app = start_app()

    def setUp(self):
        """Istanzia il dialog senza iface (modalità test, senza QGIS canvas)."""
        # Aggiunge il plugin al path se necessario
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(plugin_root)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from geosort.geosort_dialog import GeoSortDialog
        self.dialog = GeoSortDialog(iface=None)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()

    # ── Istanziazione ─────────────────────────────────────────────────────────

    def test_dialog_instantiation(self):
        """Il dialog deve essere istanziabile senza errori."""
        self.assertIsNotNone(self.dialog)

    def test_dialog_has_title(self):
        """Il dialog deve avere un titolo non vuoto."""
        self.assertTrue(len(self.dialog.windowTitle()) > 0)

    # ── Valori di default ─────────────────────────────────────────────────────

    def test_default_criterion_is_attribute(self):
        """Il criterio di default deve essere 'attribute'."""
        self.assertEqual(self.dialog.get_criterion(), "attribute")

    def test_default_direction_is_ascending(self):
        """La direzione di default deve essere ascendente."""
        self.assertEqual(self.dialog.get_direction(), "ascending")

    def test_default_output_is_update_layer(self):
        """L'output di default deve essere 'Aggiorna layer corrente'."""
        self.assertEqual(self.dialog.get_output_mode(), "update")

    def test_default_nulls_last_checked(self):
        """La checkbox 'NULL in fondo' deve essere spuntata per default."""
        self.assertTrue(self.dialog.chk_nulls_last.isChecked())

    def test_default_numbering_widgets(self):
        """Nome campo/inizio/passo devono avere i default retrocompatibili."""
        self.assertEqual(self.dialog.edit_order_field.text(), "sort_order")
        self.assertEqual(self.dialog.spin_start.value(), 1)
        self.assertEqual(self.dialog.spin_step.value(), 1)

    def test_step_minimum_is_one(self):
        """Il passo non può scendere sotto 1."""
        self.dialog.spin_step.setValue(0)
        self.assertEqual(self.dialog.spin_step.value(), 1)

    # ── Cambio criterio → stato widget ───────────────────────────────────────

    def test_attribute_criterion_enables_field_combo(self):
        """Con criterio 'Attributo', la combo dei campi deve essere abilitata."""
        self.dialog.rb_attribute.setChecked(True)
        self.assertTrue(self.dialog.combo_field.isEnabled())

    def test_geometry_criterion_disables_field_combo(self):
        """Con criterio 'Geometria', la combo dei campi deve essere disabilitata."""
        self.dialog.rb_geometry.setChecked(True)
        self.assertFalse(self.dialog.combo_field.isEnabled())

    def test_centroid_criterion_disables_field_combo(self):
        """Con criterio 'Centroide', la combo dei campi deve essere disabilitata."""
        self.dialog.rb_centroid.setChecked(True)
        self.assertFalse(self.dialog.combo_field.isEnabled())

    def test_spatial_criterion_disables_field_combo(self):
        """Con criterio 'Spaziale', la combo dei campi deve essere disabilitata."""
        self.dialog.rb_spatial.setChecked(True)
        self.assertFalse(self.dialog.combo_field.isEnabled())

    def test_hilbert_criterion_disables_field_combo(self):
        """Con criterio 'Curva di Hilbert', la combo dei campi deve essere disabilitata."""
        self.dialog.rb_hilbert.setChecked(True)
        self.assertFalse(self.dialog.combo_field.isEnabled())

    def test_hilbert_criterion_disables_secondary_criterion(self):
        """Il criterio secondario (multi-criterio) non è disponibile con Hilbert."""
        self.dialog.rb_hilbert.setChecked(True)
        self.assertFalse(self.dialog.combo_secondary.isEnabled())

    def test_serpentine_criterion_disables_field_combo(self):
        """Con criterio 'Serpentina', la combo dei campi deve essere disabilitata."""
        self.dialog.rb_serpentine.setChecked(True)
        self.assertFalse(self.dialog.combo_field.isEnabled())

    def test_serpentine_criterion_disables_secondary_criterion(self):
        """Il criterio secondario (multi-criterio) non è disponibile con la serpentina."""
        self.dialog.rb_serpentine.setChecked(True)
        self.assertFalse(self.dialog.combo_secondary.isEnabled())

    def test_serpentine_criterion_enables_band_size_spinbox(self):
        """Con criterio 'Serpentina', il campo dimensione banda deve essere abilitato."""
        self.dialog.rb_serpentine.setChecked(True)
        self.assertTrue(self.dialog.spin_band_size.isEnabled())

    def test_serpentine_criterion_enables_band_axis_combo(self):
        """Con criterio 'Serpentina', la combo orientamento bande deve essere abilitata."""
        self.dialog.rb_serpentine.setChecked(True)
        self.assertTrue(self.dialog.combo_band_axis.isEnabled())

    def test_other_criterion_disables_band_size_spinbox(self):
        """Con un criterio diverso da 'Serpentina', il campo dimensione banda è disabilitato."""
        self.dialog.rb_attribute.setChecked(True)
        self.assertFalse(self.dialog.spin_band_size.isEnabled())

    def test_other_criterion_disables_band_axis_combo(self):
        """Con un criterio diverso da 'Serpentina', la combo orientamento bande è disabilitata."""
        self.dialog.rb_attribute.setChecked(True)
        self.assertFalse(self.dialog.combo_band_axis.isEnabled())

    def test_band_axis_default_is_horizontal(self):
        """Di default l'orientamento bande deve essere 'horizontal'."""
        self.assertEqual(self.dialog.combo_band_axis.currentData(), "horizontal")

    def test_serpentine_criterion_enables_cross_ascending_checkbox(self):
        """Con criterio 'Serpentina', il checkbox 'prima banda crescente' deve essere abilitato."""
        self.dialog.rb_serpentine.setChecked(True)
        self.assertTrue(self.dialog.chk_cross_ascending.isEnabled())

    def test_other_criterion_disables_cross_ascending_checkbox(self):
        """Con un criterio diverso da 'Serpentina', il checkbox è disabilitato."""
        self.dialog.rb_attribute.setChecked(True)
        self.assertFalse(self.dialog.chk_cross_ascending.isEnabled())

    def test_cross_ascending_default_is_checked(self):
        """Di default 'prima banda in verso crescente' deve essere spuntato
        (comportamento retrocompatibile, angolo di partenza invariato)."""
        self.assertTrue(self.dialog.chk_cross_ascending.isChecked())

    # ── Selettore layer di riferimento ────────────────────────────────────────

    def test_ref_layer_enabled_for_spatial(self):
        """Il selettore layer di riferimento deve essere attivo solo per criterio spaziale."""
        self.dialog.rb_spatial.setChecked(True)
        self.assertTrue(self.dialog.combo_ref_layer.isEnabled())

    def test_ref_layer_disabled_for_attribute(self):
        self.dialog.rb_attribute.setChecked(True)
        self.assertFalse(self.dialog.combo_ref_layer.isEnabled())

    def test_ref_layer_disabled_for_centroid(self):
        self.dialog.rb_centroid.setChecked(True)
        self.assertFalse(self.dialog.combo_ref_layer.isEnabled())

    def test_ref_layer_disabled_for_geometry(self):
        self.dialog.rb_geometry.setChecked(True)
        self.assertFalse(self.dialog.combo_ref_layer.isEnabled())

    # ── Solo feature selezionate ──────────────────────────────────────────────

    def test_selected_only_unchecked_by_default(self):
        """La checkbox 'solo selezionate' deve essere spenta per default."""
        self.assertFalse(self.dialog.chk_selected_only.isChecked())

    def _memory_layer_with_selection(self):
        from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "t", "memory")
        prov = layer.dataProvider()
        feats = []
        for i in range(4):
            f = QgsFeature(layer.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(i, 0)))
            f["id"] = i
            feats.append(f)
        prov.addFeatures(feats)
        return layer

    def test_load_features_all_when_unchecked(self):
        layer = self._memory_layer_with_selection()
        self.dialog.chk_selected_only.setChecked(False)
        self.assertEqual(len(self.dialog._load_features(layer)), 4)

    def test_load_features_selected_only(self):
        layer = self._memory_layer_with_selection()
        ids = [f.id() for f in layer.getFeatures()][:2]
        layer.selectByIds(ids)
        self.dialog.chk_selected_only.setChecked(True)
        self.assertEqual(len(self.dialog._load_features(layer)), 2)

    def test_load_features_selected_only_empty_selection_raises(self):
        layer = self._memory_layer_with_selection()
        self.dialog.chk_selected_only.setChecked(True)
        with self.assertRaises(ValueError):
            self.dialog._load_features(layer)

    # ── Punto di riferimento (solo per distanza) ──────────────────────────────

    def test_ref_point_group_visible_for_distance(self):
        """Il gruppo punto di riferimento deve essere visibile solo per 'Distanza'.

        isVisibleTo: isVisible() è sempre False se il dialog non è mai stato
        mostrato (esecuzione headless).
        """
        self.dialog.rb_centroid.setChecked(True)
        self.dialog.combo_centroid.setCurrentIndex(2)  # Distanza
        self.assertTrue(self.dialog.ref_point_group.isVisibleTo(self.dialog))

    def test_ref_point_group_hidden_for_x(self):
        self.dialog.rb_centroid.setChecked(True)
        self.dialog.combo_centroid.setCurrentIndex(0)  # X
        self.assertFalse(self.dialog.ref_point_group.isVisible())

    def test_ref_point_group_hidden_for_y(self):
        self.dialog.rb_centroid.setChecked(True)
        self.dialog.combo_centroid.setCurrentIndex(1)  # Y
        self.assertFalse(self.dialog.ref_point_group.isVisible())

    # ── Direzione ─────────────────────────────────────────────────────────────

    def test_direction_toggle_to_descending(self):
        self.dialog.rb_desc.setChecked(True)
        self.assertEqual(self.dialog.get_direction(), "descending")

    def test_direction_toggle_back_to_ascending(self):
        self.dialog.rb_desc.setChecked(True)
        self.dialog.rb_asc.setChecked(True)
        self.assertEqual(self.dialog.get_direction(), "ascending")

    # ── Output mode ───────────────────────────────────────────────────────────

    def test_output_mode_toggle_to_new_layer(self):
        self.dialog.rb_new_layer.setChecked(True)
        self.assertEqual(self.dialog.get_output_mode(), "new_layer")

    def test_output_mode_toggle_back_to_update(self):
        self.dialog.rb_new_layer.setChecked(True)
        self.dialog.rb_update.setChecked(True)
        self.assertEqual(self.dialog.get_output_mode(), "update")

    # ── Metodi pubblici ───────────────────────────────────────────────────────

    def test_get_criterion_returns_string(self):
        for rb, expected in [
            (self.dialog.rb_attribute, "attribute"),
            (self.dialog.rb_centroid,  "centroid"),
            (self.dialog.rb_geometry,  "geometry"),
            (self.dialog.rb_spatial,   "spatial"),
            (self.dialog.rb_hilbert,   "hilbert"),
            (self.dialog.rb_serpentine, "serpentine"),
        ]:
            rb.setChecked(True)
            self.assertEqual(self.dialog.get_criterion(), expected)

    def test_get_selected_layer_returns_none_when_no_layers(self):
        """Senza layer caricati, get_selected_layer() deve restituire None."""
        layer = self.dialog.get_selected_layer()
        # Può essere None o un layer vuoto – non deve sollevare eccezioni
        self.assertTrue(layer is None or hasattr(layer, "id"))


@unittest.skipUnless(_qgis_available(), "QGIS non disponibile in questo ambiente di test")
class TestGeoSortRegressions(unittest.TestCase):
    """Regressioni su CRS (linea/punto di riferimento) e scrittura sul layer."""

    @classmethod
    def setUpClass(cls):
        from qgis.testing import start_app
        cls.qgis_app = start_app()
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(plugin_root)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

    def _point_layer(self, crs="EPSG:4326", extra_fields=""):
        """Layer di 3 punti (lon 10, 11, 12 – lat 45) con campo testuale 'name'."""
        from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
        layer = QgsVectorLayer(
            f"Point?crs={crs}&field=name:string(20){extra_fields}", "pts", "memory"
        )
        feats = []
        for name, x in (("c", 12.0), ("a", 10.0), ("b", 11.0)):
            f = QgsFeature(layer.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, 45.0)))
            f["name"] = name
            feats.append(f)
        layer.dataProvider().addFeatures(feats)
        return layer

    # ── apply_sort_order: sessione di editing dell'utente ─────────────────────

    def test_apply_keeps_user_edit_session(self):
        """Layer già in editing: niente commit, le modifiche restano nel buffer."""
        from geosort.geosort_core import apply_sort_order, sort_by_attribute
        layer = self._point_layer()
        layer.startEditing()
        first = next(layer.getFeatures())
        layer.changeAttributeValue(first.id(), layer.fields().indexOf("name"), "zzz")

        feats = sort_by_attribute(list(layer.getFeatures()), "name")
        self.assertTrue(apply_sort_order(layer, feats))

        self.assertTrue(layer.isEditable())
        # Né la modifica dell'utente né sort_order sono arrivate al provider
        self.assertEqual(layer.dataProvider().fields().indexOf("sort_order"), -1)
        stored = [f["name"] for f in layer.dataProvider().getFeatures()]
        self.assertNotIn("zzz", stored)
        # ...ma sono entrambe presenti nel buffer di editing
        buffered = {f["name"]: f["sort_order"] for f in layer.getFeatures()}
        self.assertEqual(buffered, {"a": 1, "b": 2, "zzz": 3})
        layer.rollBack()

    def test_apply_commits_when_not_editing(self):
        """Layer non in editing: commit automatico come prima."""
        from geosort.geosort_core import apply_sort_order, sort_by_attribute
        layer = self._point_layer()
        feats = sort_by_attribute(list(layer.getFeatures()), "name")
        self.assertTrue(apply_sort_order(layer, feats))
        self.assertFalse(layer.isEditable())
        stored = {f["name"]: f["sort_order"] for f in layer.dataProvider().getFeatures()}
        self.assertEqual(stored, {"a": 1, "b": 2, "c": 3})

    # ── apply_sort_order: campo criterio già esistente ────────────────────────

    def test_existing_text_criterion_field_keeps_values(self):
        """Seconda esecuzione: il campo criterio testuale non diventa NULL."""
        from geosort.geosort_core import apply_sort_order, sort_by_attribute
        layer = self._point_layer()
        for _ in range(2):
            feats = sort_by_attribute(list(layer.getFeatures()), "name")
            values = [f["name"] for f in feats]
            self.assertTrue(apply_sort_order(layer, feats, True, values, "sort_name"))
        stored = {f["name"]: f["sort_name"] for f in layer.getFeatures()}
        self.assertEqual(stored, {"a": "a", "b": "b", "c": "c"})

    def test_existing_integer_criterion_field(self):
        """Campo criterio intero già presente: valori convertiti a intero."""
        from geosort.geosort_core import apply_sort_order
        layer = self._point_layer(extra_fields="&field=sort_value:integer")
        feats = list(layer.getFeatures())
        self.assertTrue(apply_sort_order(layer, feats, True, [1.0, 2.0, 3.0], "sort_value"))
        self.assertEqual(sorted(f["sort_value"] for f in layer.getFeatures()), [1, 2, 3])

    # ── Dialogo: riproiezione della linea di riferimento ──────────────────────

    def test_ref_line_reprojected_to_layer_crs(self):
        """Linea in EPSG:3857, layer in EPSG:4326: la linea torna in gradi."""
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject,
        )
        from geosort.geosort_dialog import GeoSortDialog
        from geosort.geosort_core import sort_by_line_position

        layer = self._point_layer("EPSG:4326")
        to_3857 = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsCoordinateReferenceSystem("EPSG:3857"), QgsProject.instance(),
        )
        # Linea da est (lon 13) a ovest (lon 9), espressa in EPSG:3857
        line = QgsGeometry.fromPolylineXY([QgsPointXY(13.0, 45.0), QgsPointXY(9.0, 45.0)])
        line.transform(to_3857)
        ref = QgsVectorLayer("LineString?crs=EPSG:3857", "ref", "memory")
        f = QgsFeature()
        f.setGeometry(line)
        ref.dataProvider().addFeatures([f])

        dialog = GeoSortDialog(iface=None)
        try:
            geom = dialog._ref_line_geom(ref, layer)
        finally:
            dialog.close()
            dialog.deleteLater()

        bbox = geom.boundingBox()
        self.assertAlmostEqual(bbox.xMinimum(), 9.0, places=5)
        self.assertAlmostEqual(bbox.xMaximum(), 13.0, places=5)
        sorted_feats, _values, _excl = sort_by_line_position(
            list(layer.getFeatures()), geom
        )
        self.assertEqual([f["name"] for f in sorted_feats], ["c", "b", "a"])

    def test_ref_line_empty_layer_raises(self):
        from qgis.core import QgsVectorLayer
        from geosort.geosort_dialog import GeoSortDialog
        dialog = GeoSortDialog(iface=None)
        try:
            ref = QgsVectorLayer("LineString?crs=EPSG:4326", "ref", "memory")
            with self.assertRaises(ValueError):
                dialog._ref_line_geom(ref, self._point_layer())
            with self.assertRaises(ValueError):
                dialog._ref_line_geom(None, self._point_layer())
        finally:
            dialog.close()
            dialog.deleteLater()

    # ── Dialogo: punto scelto sulla mappa ─────────────────────────────────────

    def test_picked_point_reprojected_to_layer_crs(self):
        """Click nel CRS del canvas (EPSG:3857) → coordinate nel CRS del layer."""
        from unittest import mock
        from qgis.core import (
            QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsPointXY,
        )
        from geosort.geosort_dialog import GeoSortDialog

        layer = self._point_layer("EPSG:4326")
        canvas_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        clicked = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:4326"), canvas_crs, QgsProject.instance()
        ).transform(QgsPointXY(11.5, 45.5))

        iface = mock.MagicMock()
        iface.mapCanvas.return_value.mapSettings.return_value.destinationCrs.return_value = canvas_crs
        dialog = GeoSortDialog(iface=None)
        try:
            dialog.iface = iface
            dialog._pick_completed = False
            with mock.patch.object(dialog.layer_combo, "currentLayer", return_value=layer), \
                    mock.patch.object(dialog, "_restore_map_tool"), \
                    mock.patch.object(dialog, "_restore_dialog"):
                dialog._on_point_picked(clicked, None)
            self.assertAlmostEqual(dialog.spin_ref_x.value(), 11.5, places=5)
            self.assertAlmostEqual(dialog.spin_ref_y.value(), 45.5, places=5)
        finally:
            dialog.close()
            dialog.deleteLater()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
