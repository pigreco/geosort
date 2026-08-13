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
import math
import unittest


def _qgis_available():
    try:
        import qgis  # noqa: F401
        return True
    except ImportError:
        return False


def _processing_available():
    try:
        import processing  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_qgis_available(), "QGIS non disponibile in questo ambiente di test")
@unittest.skipUnless(_processing_available(), "Processing module non disponibile in questo ambiente di test")
class TestGeoSortAlgorithm(unittest.TestCase):
    """Test sul GeoSortAlgorithm (Processing Toolbox)."""

    @classmethod
    def setUpClass(cls):
        """Avvia l'applicazione QGIS e registra il provider GeoSort."""
        from qgis.testing import start_app
        cls.qgis_app = start_app()

        # Registra il provider una sola volta: serve al test end-to-end
        # che invoca l'algoritmo tramite processing.run().
        from qgis.core import QgsApplication
        from processing.core.Processing import Processing
        Processing.initialize()
        registry = QgsApplication.processingRegistry()
        if registry.providerById("geosort") is None:
            from geosort.geosort_provider import GeoSortProvider
            cls._provider = GeoSortProvider()
            registry.addProvider(cls._provider)

    def setUp(self):
        """Istanzia l'algoritmo e crea layer di test."""
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsFields, QgsField, QgsProject
        )
        from qgis.PyQt.QtCore import QMetaType
        from geosort.geosort_algorithm import GeoSortAlgorithm

        self.algo = GeoSortAlgorithm()
        # In QGIS è il framework Processing a chiamare initAlgorithm alla
        # registrazione: qui va invocato esplicitamente per creare i parametri.
        self.algo.initAlgorithm()

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

    def test_algorithm_has_ref_point_parameter(self):
        """L'algoritmo deve avere il parametro REF_POINT (opzionale)."""
        param = self.algo.parameterDefinition("REF_POINT")
        self.assertIsNotNone(param)

    def test_algorithm_has_numbering_parameters(self):
        """L'algoritmo deve avere i parametri START, STEP e ORDER_FIELD."""
        param_names = [p.name() for p in self.algo.parameterDefinitions()]
        self.assertIn("START", param_names)
        self.assertIn("STEP", param_names)
        self.assertIn("ORDER_FIELD", param_names)

    # ── Criteri ───────────────────────────────────────────────────────────────

    def test_algorithm_criteria_keys_count(self):
        """Deve avere 18 criteri (17 + 1 nuovo serpentine)."""
        self.assertEqual(len(self.algo._CRITERIA_KEYS), 18)

    def test_algorithm_criteria_keys_include_line_distance(self):
        """Deve includere 'line_distance' nei criteri."""
        self.assertIn("line_distance", self.algo._CRITERIA_KEYS)

    def test_algorithm_criteria_keys_include_hilbert(self):
        """Deve includere 'hilbert' nei criteri."""
        self.assertIn("hilbert", self.algo._CRITERIA_KEYS)

    def test_algorithm_criteria_keys_include_serpentine(self):
        """Deve includere 'serpentine' nei criteri."""
        self.assertIn("serpentine", self.algo._CRITERIA_KEYS)

    def test_algorithm_criteria_labels_count(self):
        """Deve avere 18 etichette (una per criterio)."""
        self.assertEqual(len(self.algo._CRITERIA_LABELS), 18)

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

    def test_hilbert_index_position(self):
        """'hilbert' deve essere al corretto indice (15), subito prima di 'expression'."""
        self.assertEqual(self.algo._CRITERIA_KEYS[15], "hilbert")

    def test_algorithm_has_hilbert_order_parameter(self):
        """L'algoritmo deve esporre il parametro avanzato HILBERT_ORDER."""
        param_names = [p.name() for p in self.algo.parameterDefinitions()]
        self.assertIn("HILBERT_ORDER", param_names)

    def test_expression_index_position(self):
        """'expression' deve essere al corretto indice (16)."""
        self.assertEqual(self.algo._CRITERIA_KEYS[16], "expression")

    def test_serpentine_is_last_criterion(self):
        """'serpentine' deve essere l'ultimo criterio (aggiunto in coda, non
        rompe gli indici dei criteri esistenti)."""
        self.assertEqual(self.algo._CRITERIA_KEYS[-1], "serpentine")
        self.assertEqual(self.algo._CRITERIA_KEYS[17], "serpentine")

    def test_algorithm_has_band_height_parameter(self):
        """L'algoritmo deve esporre il parametro avanzato BAND_HEIGHT."""
        param_names = [p.name() for p in self.algo.parameterDefinitions()]
        self.assertIn("BAND_HEIGHT", param_names)

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

    def test_multi_primary_keys_excludes_hilbert(self):
        """'hilbert' richiede l'extent globale: non ammesso come primario in multi-criterio."""
        self.assertNotIn("hilbert", self.algo._MULTI_PRIMARY_KEYS)
        self.assertNotIn("hilbert", self.algo._SECONDARY_KEYS)

    def test_multi_primary_keys_excludes_serpentine(self):
        """'serpentine' richiede le bande calcolate globalmente: non ammesso
        come primario in multi-criterio."""
        self.assertNotIn("serpentine", self.algo._MULTI_PRIMARY_KEYS)
        self.assertNotIn("serpentine", self.algo._SECONDARY_KEYS)

    def test_end_to_end_selected_features_only(self):
        """Con QgsProcessingFeatureSourceDefinition vengono ordinate solo le selezionate."""
        import processing
        from qgis.core import QgsProcessingFeatureSourceDefinition
        selected_ids = [f.id() for f in self.layer.getFeatures()][:2]
        self.layer.selectByIds(selected_ids)
        try:
            result = processing.run("geosort:geosort_sort", {
                "INPUT": QgsProcessingFeatureSourceDefinition(
                    self.layer.id(), selectedFeaturesOnly=True
                ),
                "CRITERION": 1,             # centroide X
                "DIRECTION": True,
                "OUTPUT": "memory:",
            })
        finally:
            self.layer.removeSelection()
        out = result["OUTPUT"]
        self.assertEqual(out.featureCount(), 2)
        orders = sorted(f["sort_order"] for f in out.getFeatures())
        self.assertEqual(orders, [1, 2])

    def test_end_to_end_ref_point(self):
        """Con REF_POINT la distanza del centroide è calcolata dal punto indicato."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 3,                 # centroide – distanza da punto
            "DIRECTION": True,
            "REF_POINT": "2,2 [EPSG:4326]",
            "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        # Le feature sono in (0,0), (1,1), (2,2): dal punto (2,2) l'ordine
        # ascendente è id 2, 1, 0 (dall'origine sarebbe l'inverso).
        order_by_id = {f["id"]: f["sort_order"] for f in out.getFeatures()}
        self.assertEqual(order_by_id, {2: 1, 1: 2, 0: 3})

    def test_end_to_end_without_ref_point_uses_origin(self):
        """Senza REF_POINT la distanza resta calcolata dall'origine (0,0)."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 3,                 # centroide – distanza da punto
            "DIRECTION": True,
            "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        order_by_id = {f["id"]: f["sort_order"] for f in out.getFeatures()}
        self.assertEqual(order_by_id, {0: 1, 1: 2, 2: 3})

    def test_end_to_end_ref_point_multi_criteria(self):
        """REF_POINT è rispettato anche con un criterio secondario attivo."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 3,                 # centroide – distanza da punto
            "DIRECTION": True,
            "REF_POINT": "2,2 [EPSG:4326]",
            "SECONDARY_CRITERION": 1,       # attributo
            "SECONDARY_FIELD": "name",
            "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        order_by_id = {f["id"]: f["sort_order"] for f in out.getFeatures()}
        self.assertEqual(order_by_id, {2: 1, 1: 2, 0: 3})

    def test_end_to_end_start_step_field_name(self):
        """START, STEP e ORDER_FIELD personalizzano la numerazione."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 1,                 # centroide X
            "DIRECTION": True,
            "START": 0,
            "STEP": 10,
            "ORDER_FIELD": "rank",
            "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        field_names = [f.name() for f in out.fields()]
        self.assertIn("rank", field_names)
        self.assertNotIn("sort_order", field_names)
        orders = sorted(f["rank"] for f in out.getFeatures())
        self.assertEqual(orders, [0, 10, 20])

    def test_end_to_end_existing_order_field_reused(self):
        """Se il campo progressivo esiste già nell'input non viene duplicato."""
        import processing
        first = processing.run("geosort:geosort_sort", {
            "INPUT": self.layer,
            "CRITERION": 1,                 # centroide X
            "DIRECTION": True,
            "OUTPUT": "memory:",
        })["OUTPUT"]
        second = processing.run("geosort:geosort_sort", {
            "INPUT": first,
            "CRITERION": 1,                 # centroide X
            "DIRECTION": False,             # inverte l'ordine
            "OUTPUT": "memory:",
        })["OUTPUT"]
        field_names = [f.name() for f in second.fields()]
        self.assertEqual(field_names.count("sort_order"), 1)
        order_by_id = {f["id"]: f["sort_order"] for f in second.getFeatures()}
        self.assertEqual(order_by_id, {2: 1, 1: 2, 0: 3})

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
# Copertura end-to-end di TUTTI i 17 criteri via processing.run()
# ──────────────────────────────────────────────────────────────────────────────
# TestGeoSortAlgorithm sopra esercita solo gli indici 0 (attribute), 1
# (centroid_x) e 3 (centroid_dist) attraverso l'algoritmo Processing reale.
# Questa classe copre i restanti: centroid_y, i criteri geometrici (area,
# perimeter, length, n_vertices, i 5 bbox_*), line_position, line_distance,
# hilbert ed expression — con geometrie scelte apposta perché ogni
# sotto-criterio dia un ordine diverso dagli altri, in modo da smascherare
# eventuali scambi (es. area/perimeter o xmin/ymin invertiti) invece di
# limitarsi a verificare che l'algoritmo non vada in crash.

@unittest.skipUnless(_qgis_available(), "QGIS non disponibile in questo ambiente di test")
@unittest.skipUnless(_processing_available(), "Processing module non disponibile in questo ambiente di test")
class TestGeoSortAlgorithmAllCriteria(unittest.TestCase):
    """Copertura end-to-end (processing.run) dei criteri non testati altrove."""

    @classmethod
    def setUpClass(cls):
        from qgis.testing import start_app
        cls.qgis_app = start_app()
        from qgis.core import QgsApplication
        from processing.core.Processing import Processing
        Processing.initialize()
        registry = QgsApplication.processingRegistry()
        if registry.providerById("geosort") is None:
            from geosort.geosort_provider import GeoSortProvider
            cls._provider = GeoSortProvider()
            registry.addProvider(cls._provider)

    def _make_layer(self, uri, name, features):
        """Crea un layer in memoria con le feature (geometria, attributi) date."""
        from qgis.core import QgsVectorLayer, QgsFeature, QgsProject
        layer = QgsVectorLayer(uri, name, "memory")
        layer.startEditing()
        for geom, attrs in features:
            feat = QgsFeature()
            feat.setGeometry(geom)
            if attrs:
                feat.setAttributes(attrs)
            layer.addFeature(feat)
        layer.commitChanges()
        QgsProject.instance().addMapLayer(layer)
        self._layers.append(layer)
        return layer

    def setUp(self):
        self._layers = []  # rimossi in tearDown

    def tearDown(self):
        from qgis.core import QgsProject
        for layer in self._layers:
            QgsProject.instance().removeMapLayer(layer.id())

    def _order_by_id(self, out_layer, id_field="id", order_field="sort_order"):
        return {f[id_field]: f[order_field] for f in out_layer.getFeatures()}

    # ── centroid_y (indice 2) ───────────────────────────────────────────────

    def test_centroid_y(self):
        """CRITERION=2: ordina per la coordinata Y del centroide, non per X."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY, QgsFields, QgsField
        from qgis.PyQt.QtCore import QMetaType
        fields = QgsFields()
        fields.append(QgsField("id", QMetaType.Type.Int))
        # Punti con X e Y "scambiati" rispetto all'id: se il codice usasse per
        # errore la X invece della Y, l'ordine risultante sarebbe diverso.
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "xy_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(0, 5)), [0]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 3)), [1]),
                (QgsGeometry.fromPointXY(QgsPointXY(2, 8)), [2]),
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 2, "DIRECTION": True, "OUTPUT": "memory:",
        })
        order_by_id = self._order_by_id(result["OUTPUT"])
        # Ascendente per Y: id1 (y=3) < id0 (y=5) < id2 (y=8)
        self.assertEqual(order_by_id, {1: 1, 0: 2, 2: 3})

    # ── area / perimeter (indici 4 / 5) ─────────────────────────────────────

    def _poly_layer(self):
        from qgis.core import QgsGeometry, QgsPointXY, QgsFields, QgsField
        from qgis.PyQt.QtCore import QMetaType
        # E: rettangolo molto sottile e lungo → area piccola, perimetro grande.
        # F: quadrato compatto → area grande, perimetro piccolo.
        # L'ordine di area e perimetro è quindi OPPOSTO: un eventuale scambio
        # fra i due criteri nel codice produrrebbe l'ordine sbagliato.
        e = QgsGeometry.fromPolygonXY([[
            QgsPointXY(0, 0), QgsPointXY(100, 0), QgsPointXY(100, 0.01),
            QgsPointXY(0, 0.01), QgsPointXY(0, 0),
        ]])  # area = 1, perimetro ≈ 200.02
        f = QgsGeometry.fromPolygonXY([[
            QgsPointXY(0, 0), QgsPointXY(5, 0), QgsPointXY(5, 5),
            QgsPointXY(0, 5), QgsPointXY(0, 0),
        ]])  # area = 25, perimetro = 20
        return self._make_layer(
            "Polygon?crs=EPSG:32633&field=id:integer", "poly_layer",
            [(e, [0]), (f, [1])],
        )

    def test_area(self):
        """CRITERION=4: area ascendente → rettangolo sottile (E) prima del quadrato (F)."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self._poly_layer(), "CRITERION": 4, "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {0: 1, 1: 2})

    def test_perimeter(self):
        """CRITERION=5: perimetro ascendente → ordine OPPOSTO a quello dell'area."""
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self._poly_layer(), "CRITERION": 5, "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {1: 1, 0: 2})

    # ── length (indice 6) ────────────────────────────────────────────────────

    def test_length(self):
        """CRITERION=6: ordina le linee per lunghezza."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        # CRS proiettato (metri): "length" è in GEODESIC_CRITERIA, un CRS
        # geografico userebbe la misura ellissoidica invece dei metri piani
        # calcolati a mano qui sotto.
        short = QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(3, 0)])   # lunghezza 3
        long_ = QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(0, 7)])   # lunghezza 7
        layer = self._make_layer(
            "LineString?crs=EPSG:32633&field=id:integer", "lines_layer",
            [(short, [0]), (long_, [1])],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 6, "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {0: 1, 1: 2})

    # ── n_vertices (indice 7) ────────────────────────────────────────────────

    def test_n_vertices(self):
        """CRITERION=7: ordina per numero di vertici, non per lunghezza."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        # 'straight' è più corta ma ha meno vertici; 'zigzag' è più lunga con
        # più vertici: se il criterio usasse la lunghezza invece del conteggio
        # vertici, l'ordine risultante sarebbe l'opposto.
        straight = QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(1, 0)])
        zigzag = QgsGeometry.fromPolylineXY([
            QgsPointXY(0, 0), QgsPointXY(1, 1), QgsPointXY(2, 0), QgsPointXY(3, 1),
        ])
        layer = self._make_layer(
            "LineString?crs=EPSG:4326&field=id:integer", "vertices_layer",
            [(straight, [0]), (zigzag, [1])],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 7, "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {0: 1, 1: 2})

    # ── bounding box: width, height, area, xmin, ymin (indici 8-12) ─────────

    def _bbox_layer(self):
        from qgis.core import QgsGeometry, QgsPointXY
        # P: bbox largo e basso, xmin piccolo, ymin grande.
        # Q: bbox stretto e alto, xmin grande, ymin piccolo.
        # Ogni sotto-criterio bbox_* dà quindi un ordine diverso dagli altri.
        p = QgsGeometry.fromPolygonXY([[
            QgsPointXY(0, 5), QgsPointXY(3, 5), QgsPointXY(3, 7),
            QgsPointXY(0, 7), QgsPointXY(0, 5),
        ]])  # width=3, height=2, area=6, xmin=0, ymin=5
        q = QgsGeometry.fromPolygonXY([[
            QgsPointXY(10, 1), QgsPointXY(15, 1), QgsPointXY(15, 2),
            QgsPointXY(10, 2), QgsPointXY(10, 1),
        ]])  # width=5, height=1, area=5, xmin=10, ymin=1
        return self._make_layer(
            "Polygon?crs=EPSG:32633&field=id:integer", "bbox_layer",
            [(p, [0]), (q, [1])],
        )

    def _run_bbox(self, criterion_idx):
        import processing
        result = processing.run("geosort:geosort_sort", {
            "INPUT": self._bbox_layer(), "CRITERION": criterion_idx,
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        return self._order_by_id(result["OUTPUT"])

    def test_bbox_width(self):
        """CRITERION=8: bbox_width ascendente → P (3) prima di Q (5)."""
        self.assertEqual(self._run_bbox(8), {0: 1, 1: 2})

    def test_bbox_height(self):
        """CRITERION=9: bbox_height ascendente → ordine opposto a bbox_width."""
        self.assertEqual(self._run_bbox(9), {1: 1, 0: 2})

    def test_bbox_area(self):
        """CRITERION=10: bbox_area ascendente → Q (5) prima di P (6)."""
        self.assertEqual(self._run_bbox(10), {1: 1, 0: 2})

    def test_bbox_xmin(self):
        """CRITERION=11: bbox_xmin ascendente → P (0) prima di Q (10)."""
        self.assertEqual(self._run_bbox(11), {0: 1, 1: 2})

    def test_bbox_ymin(self):
        """CRITERION=12: bbox_ymin ascendente → ordine opposto a bbox_xmin."""
        self.assertEqual(self._run_bbox(12), {1: 1, 0: 2})

    # ── line_position / line_distance (indici 13 / 14) ──────────────────────

    def _line_ref_and_points(self):
        from qgis.core import QgsGeometry, QgsPointXY
        # CRS proiettato (metri): line_distance è in GEODESIC_CRITERIA, quindi
        # su un CRS geografico userebbe la misura ellissoidica e i valori
        # calcolati a mano qui sotto non coinciderebbero più esattamente.
        # Linea di riferimento orizzontale (0,0)-(10,0).
        ref_line = self._make_layer(
            "LineString?crs=EPSG:32633", "ref_line",
            [(QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(10, 0)]), [])],
        )
        # Punti fuori dalla linea: proiezione e distanza perpendicolare danno
        # ordini diversi, così i due criteri non si confondono a vicenda.
        # id0: proiezione=2, distanza=3   id1: proiezione=5, distanza=1   id2: proiezione=8, distanza=5
        pts_layer = self._make_layer(
            "Point?crs=EPSG:32633&field=id:integer", "offset_points",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(2, 3)), [0]),
                (QgsGeometry.fromPointXY(QgsPointXY(5, 1)), [1]),
                (QgsGeometry.fromPointXY(QgsPointXY(8, 5)), [2]),
            ],
        )
        return ref_line, pts_layer

    def test_line_position(self):
        """CRITERION=13: posizione (proiezione) lungo la linea di riferimento."""
        import processing
        ref_line, pts_layer = self._line_ref_and_points()
        result = processing.run("geosort:geosort_sort", {
            "INPUT": pts_layer, "CRITERION": 13, "REF_LAYER": ref_line,
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        # Proiezione crescente: id0 (2) < id1 (5) < id2 (8)
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {0: 1, 1: 2, 2: 3})

    def test_line_distance(self):
        """CRITERION=14: distanza perpendicolare dalla linea — ordine diverso da line_position."""
        import processing
        ref_line, pts_layer = self._line_ref_and_points()
        result = processing.run("geosort:geosort_sort", {
            "INPUT": pts_layer, "CRITERION": 14, "REF_LAYER": ref_line,
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        # Distanza crescente: id1 (1) < id0 (3) < id2 (5)
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {1: 1, 0: 2, 2: 3})

    # ── REF_LAYER con CRS diverso dall'input (regressione) ──────────────────
    # Bug reale trovato ispezionando un GeoPackage catastale empirico con
    # INPUT e REF_LAYER in due CRS diversi: geosort_algorithm.py univa le
    # geometrie del REF_LAYER senza mai riproiettarle nel CRS dell'input.
    # Con CRS numericamente vicini (es. due datum geografici europei) l'errore
    # è invisibile; con CRS nettamente diversi (gradi vs UTM in metri) il
    # risultato diventava silenziosamente NaN in sort_value, senza errori
    # né avvisi.

    def test_ref_layer_reprojected_when_crs_differs(self):
        """line_distance con REF_LAYER in un CRS diverso dall'INPUT deve dare
        lo stesso ordine e gli stessi valori (a meno di arrotondamento) di
        un'esecuzione con CRS già allineati — mai NaN."""
        import processing
        ref_line_utm, pts_utm = self._line_ref_and_points()  # entrambi EPSG:32633
        # Stesso layer di riferimento, riproiettato in un CRS nettamente
        # diverso (gradi anziché metri UTM): stesse geometrie reali, CRS diverso.
        ref_line_4326 = processing.run("native:reprojectlayer", {
            "INPUT": ref_line_utm, "TARGET_CRS": "EPSG:4326", "OUTPUT": "memory:",
        })["OUTPUT"]

        def _run(ref_layer):
            result = processing.run("geosort:geosort_sort", {
                "INPUT": pts_utm, "CRITERION": 14, "REF_LAYER": ref_layer,
                "ADD_VALUE_FIELD": True, "DIRECTION": True, "OUTPUT": "memory:",
            })["OUTPUT"]
            return {f["id"]: (f["sort_order"], f["sort_value"]) for f in result.getFeatures()}

        same_crs = _run(ref_line_utm)
        mismatched_crs = _run(ref_line_4326)

        for fid in same_crs:
            order_a, value_a = same_crs[fid]
            order_b, value_b = mismatched_crs[fid]
            self.assertEqual(order_a, order_b)
            # Nessun NaN: prima del fix un CRS nettamente diverso produceva
            # sort_value = nan su tutte le feature invece di questi valori.
            self.assertFalse(math.isnan(value_b))
            self.assertAlmostEqual(value_a, value_b, delta=0.5)  # metri, tolleranza riproiezione

    # ── hilbert (indice 15) ──────────────────────────────────────────────────

    def test_hilbert(self):
        """CRITERION=15: ordina lungo la curva di Hilbert calcolata sui centroidi.

        I quattro punti formano un quadrato percorso in senso orario
        (0,0)→(1,0)→(1,1)→(0,1): l'ordine di Hilbert atteso è invece
        (0,0)→(0,1)→(1,1)→(1,0) — diverso sia da una scansione per sola X
        sia per sola Y, così un'implementazione sbagliata (es. che ordinasse
        per X o Y anziché per indice di Hilbert) verrebbe smascherata.
        """
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "hilbert_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(0, 0)), [0]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 0)), [1]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 1)), [2]),
                (QgsGeometry.fromPointXY(QgsPointXY(0, 1)), [3]),
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 15, "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {0: 1, 3: 2, 2: 3, 1: 4})

    def test_hilbert_order_parameter_changes_precision(self):
        """HILBERT_ORDER più basso non deve far crashare l'algoritmo (griglia più grezza)."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "hilbert_order_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(0, 0)), [0]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 0)), [1]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 1)), [2]),
                (QgsGeometry.fromPointXY(QgsPointXY(0, 1)), [3]),
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 15, "HILBERT_ORDER": 2,
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        self.assertEqual(out.featureCount(), 4)
        orders = sorted(f["sort_order"] for f in out.getFeatures())
        self.assertEqual(orders, [1, 2, 3, 4])

    # ── expression (indice 16) ──────────────────────────────────────────────

    def test_expression(self):
        """CRITERION=16: ordina per il risultato di un'espressione QGIS."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "expr_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(0, 0)), [0]),
                (QgsGeometry.fromPointXY(QgsPointXY(1, 1)), [1]),
                (QgsGeometry.fromPointXY(QgsPointXY(2, 2)), [2]),
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 16,
            "EXPRESSION": "10 - \"id\"",  # inverte l'ordine naturale degli id
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        # 10-id ascendente → id decrescente: id2 (8) < id1 (9) < id0 (10)
        self.assertEqual(self._order_by_id(result["OUTPUT"]), {2: 1, 1: 2, 0: 3})

    # ── serpentine (indice 17) ────────────────────────────────────────────────

    def test_serpentine(self):
        """CRITERION=17: bande orizzontali per Y, X alternato pari/dispari.

        Griglia 4×2 (x=0..3, y=0,1) con BAND_HEIGHT=1 esplicito: banda 0
        (y=0, in basso) percorsa a X crescente, banda 1 (y=1) a X
        decrescente — un ordinamento a righe semplice (solo Y poi X)
        produrrebbe invece id 0,1,2,3,4,5,6,7, smascherando un'implementazione
        che ignori l'alternanza.
        """
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "serpentine_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(x, y)), [y * 4 + x])
                for y in range(2) for x in range(4)
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 17, "BAND_HEIGHT": 1,
            "DIRECTION": True, "OUTPUT": "memory:",
        })
        self.assertEqual(
            self._order_by_id(result["OUTPUT"]),
            {0: 1, 1: 2, 2: 3, 3: 4, 7: 5, 6: 6, 5: 7, 4: 8},
        )

    def test_serpentine_auto_band_height(self):
        """BAND_HEIGHT non impostato (0/default) non deve far crashare l'algoritmo
        e deve comunque produrre un ordinamento completo (fallback automatico)."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "serpentine_auto_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(x, y)), [y * 4 + x])
                for y in range(2) for x in range(4)
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 17, "DIRECTION": True, "OUTPUT": "memory:",
        })
        out = result["OUTPUT"]
        self.assertEqual(out.featureCount(), 8)
        orders = sorted(f["sort_order"] for f in out.getFeatures())
        self.assertEqual(orders, list(range(1, 9)))

    def test_serpentine_not_available_as_multi_primary(self):
        """Il criterio secondario deve essere ignorato quando il primario è 'serpentine'."""
        import processing
        from qgis.core import QgsGeometry, QgsPointXY
        layer = self._make_layer(
            "Point?crs=EPSG:4326&field=id:integer", "serpentine_multi_layer",
            [
                (QgsGeometry.fromPointXY(QgsPointXY(x, y)), [y * 4 + x])
                for y in range(2) for x in range(4)
            ],
        )
        result = processing.run("geosort:geosort_sort", {
            "INPUT": layer, "CRITERION": 17, "BAND_HEIGHT": 1, "DIRECTION": True,
            "SECONDARY_CRITERION": 1, "OUTPUT": "memory:",
        })
        # Deve comunque completare (criterio secondario ignorato, non un errore)
        # e produrre lo stesso ordine del test 'serpentine' senza secondario.
        self.assertEqual(
            self._order_by_id(result["OUTPUT"]),
            {0: 1, 1: 2, 2: 3, 3: 4, 7: 5, 6: 6, 5: 7, 4: 8},
        )


# ──────────────────────────────────────────────────────────────────────────────
# Entry point

if __name__ == "__main__":
    unittest.main(verbosity=2)
