# -*- coding: utf-8 -*-
"""
Test sul GeoSortAlgorithm (Processing).

Richiedono QGIS installato e avviabile tramite qgis.testing.
Eseguibili con: python -m pytest tests/test_algorithm.py
oppure dalla console QGIS: exec(open('tests/test_algorithm.py').read())

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
class TestGeoSortAlgorithm(unittest.TestCase):
    """Test sul GeoSortAlgorithm (Processing Toolbox)."""

    @classmethod
    def setUpClass(cls):
        """Avvia l'applicazione QGIS."""
        from qgis.testing import start_app
        cls.qgis_app = start_app()

    def setUp(self):
        """Istanzia l'algoritmo e crea layer di test."""
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsFields, QgsField, QgsProject
        )
        from qgis.PyQt.QtCore import QMetaType
        from geosort.geosort_algorithm import GeoSortAlgorithm

        self.algo = GeoSortAlgorithm()

        # Crea un layer di test semplice (punti)
        fields = QgsFields()
        fields.append(QgsField("id", QMetaType.Type.Int))
        fields.append(QgsField("name", QMetaType.Type.QString))

        self.layer = QgsVectorLayer(
            f"Point?crs=EPSG:4326&field=id:integer&field=name:string",
            "test_layer",
            "memory"
        )
        self.layer.startEditing()

        # Aggiungi 3 feature di test
        for i in range(3):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(i, i)))
            feat.setAttributes([i, f"feat_{i}"])
            self.layer.addFeature(feat)

        self.layer.commitChanges()
        QgsProject.instance().addMapLayer(self.layer)

        # Crea un layer linea di test
        self.line_layer = QgsVectorLayer(
            f"LineString?crs=EPSG:4326",
            "line_layer",
            "memory"
        )
        self.line_layer.startEditing()

        feat_line = QgsFeature()
        feat_line.setGeometry(
            QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(2, 2)])
        )
        self.line_layer.addFeature(feat_line)
        self.line_layer.commitChanges()
        QgsProject.instance().addMapLayer(self.line_layer)

    def tearDown(self):
        """Rimuove i layer di test."""
        from qgis.core import QgsProject
        QgsProject.instance().removeMapLayer(self.layer.id())
        QgsProject.instance().removeMapLayer(self.line_layer.id())

    # ── Istanziazione ─────────────────────────────────────────────────────────

    def test_algorithm_instantiation(self):
        """L'algoritmo deve essere istanziabile."""
        self.assertIsNotNone(self.algo)

    def test_algorithm_name(self):
        """L'algoritmo deve avere un nome."""
        self.assertEqual(self.algo.name(), "geosort_sort")

    def test_algorithm_display_name(self):
        """L'algoritmo deve avere un nome visibile."""
        self.assertIn("Ordina", self.algo.displayName())

    def test_algorithm_group(self):
        """L'algoritmo deve appartenere al gruppo GeoSort."""
        self.assertEqual(self.algo.group(), "GeoSort")

    # ── Parametri ─────────────────────────────────────────────────────────────

    def test_algorithm_has_input_parameter(self):
        """L'algoritmo deve avere un parametro INPUT."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("INPUT", param_names)

    def test_algorithm_has_criterion_parameter(self):
        """L'algoritmo deve avere un parametro CRITERION."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("CRITERION", param_names)

    def test_algorithm_has_direction_parameter(self):
        """L'algoritmo deve avere un parametro DIRECTION."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("DIRECTION", param_names)

    def test_algorithm_has_ref_layer_parameter(self):
        """L'algoritmo deve avere un parametro REF_LAYER."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("REF_LAYER", param_names)

    def test_algorithm_has_line_mode_parameter(self):
        """L'algoritmo deve avere il parametro LINE_MODE."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("LINE_MODE", param_names)

    def test_algorithm_has_line_distance_mode_parameter(self):
        """L'algoritmo deve avere il parametro LINE_DISTANCE_MODE."""
        params = self.algo.parameterDefinitions()
        param_names = [p.name() for p in params]
        self.assertIn("LINE_DISTANCE_MODE", param_names)

    # ── Criteri ───────────────────────────────────────────────────────────────

    def test_algorithm_criteria_keys_count(self):
        """Deve avere 16 criteri (15 originali + 1 nuovo line_distance)."""
        self.assertEqual(len(self.algo._CRITERIA_KEYS), 16)

    def test_algorithm_criteria_keys_include_line_distance(self):
        """Deve includere 'line_distance' nei criteri."""
        self.assertIn("line_distance", self.algo._CRITERIA_KEYS)

    def test_algorithm_criteria_labels_count(self):
        """Deve avere 16 etichette (una per criterio)."""
        self.assertEqual(len(self.algo._CRITERIA_LABELS), 16)

    def test_algorithm_criteria_keys_and_labels_match(self):
        """Numero di chiavi e etichette deve coincidere."""
        self.assertEqual(
            len(self.algo._CRITERIA_KEYS),
            len(self.algo._CRITERIA_LABELS)
        )

    def test_algorithm_line_distance_in_labels(self):
        """L'etichetta 'Distanza dalla linea' deve essere presente."""
        labels_str = " ".join(self.algo._CRITERIA_LABELS)
        self.assertIn("Distanza dalla linea", labels_str)

    # ── Posizione e ordine criteri ────────────────────────────────────────────

    def test_line_position_index(self):
        """'line_position' deve essere al corretto indice."""
        self.assertEqual(self.algo._CRITERIA_KEYS[13], "line_position")

    def test_line_distance_index(self):
        """'line_distance' deve essere al corretto indice (14)."""
        self.assertEqual(self.algo._CRITERIA_KEYS[14], "line_distance")

    def test_expression_is_last_criterion(self):
        """'expression' deve essere l'ultimo criterio."""
        self.assertEqual(self.algo._CRITERIA_KEYS[-1], "expression")

    # ── Criterio secondario (multi-criterio) ──────────────────────────────────

    def test_algorithm_has_secondary_criterion_parameter(self):
        """L'algoritmo deve esporre il parametro SECONDARY_CRITERION."""
        param_names = [p.name() for p in self.algo.parameterDefinitions()]
        self.assertIn("SECONDARY_CRITERION", param_names)

    def test_algorithm_has_secondary_field_and_direction(self):
        """Devono esserci i parametri di supporto al criterio secondario."""
        param_names = [p.name() for p in self.algo.parameterDefinitions()]
        self.assertIn("SECONDARY_FIELD", param_names)
        self.assertIn("SECONDARY_EXPRESSION", param_names)
        self.assertIn("SECONDARY_DIRECTION", param_names)

    def test_secondary_keys_first_is_none(self):
        """L'indice 0 del criterio secondario significa 'nessuno'."""
        self.assertIsNone(self.algo._SECONDARY_KEYS[0])

    def test_secondary_keys_and_labels_match(self):
        """Numero di chiavi ed etichette del secondario deve coincidere."""
        self.assertEqual(
            len(self.algo._SECONDARY_KEYS),
            len(self.algo._SECONDARY_LABELS),
        )

    def test_multi_primary_keys_excludes_line_criteria(self):
        """I criteri basati su linea non sono ammessi come primario in multi-criterio."""
        self.assertNotIn("line_position", self.algo._MULTI_PRIMARY_KEYS)
        self.assertNotIn("line_distance", self.algo._MULTI_PRIMARY_KEYS)

    def test_end_to_end_multi_criteria(self):
        """Esecuzione completa con criterio primario + secondario."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 0,                 # attributo
            "ATTRIBUTE_FIELD": "name",
            "DIRECTION": True,
            "SECONDARY_CRITERION": 3,       # centroide X
            "SECONDARY_DIRECTION": False,
            "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        self.assertEqual(out.featureCount(), 3)
        self.assertIn("sort_order", [f.name() for f in out.fields()])
        orders = sorted(f["sort_order"] for f in out.getFeatures())
        self.assertEqual(orders, [1, 2, 3])


# ──────────────────────────────────────────────────────────────────────────────
# Entry point

if __name__ == "__main__":
    unittest.main(verbosity=2)
