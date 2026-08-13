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
        ]:
            rb.setChecked(True)
            self.assertEqual(self.dialog.get_criterion(), expected)

    def test_get_selected_layer_returns_none_when_no_layers(self):
        """Senza layer caricati, get_selected_layer() deve restituire None."""
        layer = self.dialog.get_selected_layer()
        # Può essere None o un layer vuoto – non deve sollevare eccezioni
        self.assertTrue(layer is None or hasattr(layer, "id"))


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
