# -*- coding: utf-8 -*-
"""
GeoSort – Processing Algorithm.
Compatibile con il Processing Toolbox, il modellatore grafico e PyQGIS headless.
"""

import os

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterMapLayer,
    QgsProcessingOutputNumber,
    QgsFeatureSink,
    QgsWkbTypes,
    QgsProcessing,
    QgsProcessingException,
    QgsField,
    QgsFeature,
    QgsFields,
    QgsGeometry,
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


class GeoSortAlgorithm(QgsProcessingAlgorithm):
    """Algoritmo Processing per ordinare le feature di un layer vettoriale."""

    # Parametri
    INPUT = "INPUT"
    CRITERION = "CRITERION"
    ATTRIBUTE_FIELD = "ATTRIBUTE_FIELD"
    DIRECTION = "DIRECTION"
    NULLS_LAST = "NULLS_LAST"
    REF_LAYER = "REF_LAYER"
    ADD_VALUE_FIELD = "ADD_VALUE_FIELD"
    OUTPUT = "OUTPUT"

    # Indici criterio → chiave interna
    _CRITERIA_KEYS = [
        "attribute",
        "centroid_x",
        "centroid_y",
        "centroid_dist",
        "area",
        "perimeter",
        "length",
        "n_vertices",
        "bbox_width",
        "bbox_height",
        "bbox_area",
        "bbox_xmin",
        "bbox_ymin",
        "line_position",
        "expression",
    ]

    _CRITERIA_LABELS = [
        "Attributo tabellare",
        "Centroide – coordinata X",
        "Centroide – coordinata Y",
        "Centroide – distanza da origine (0,0)",
        "Area (poligoni)",
        "Perimetro (poligoni)",
        "Lunghezza (linee)",
        "Numero di vertici",
        "Larghezza Bounding Box",
        "Altezza Bounding Box",
        "Area Bounding Box",
        "Xmin Bounding Box",
        "Ymin Bounding Box",
        "Posizione lungo linea di riferimento",
        "Espressione QGIS",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # Metadati algoritmo
    # ──────────────────────────────────────────────────────────────────────────

    def name(self):
        return "geosort_sort"

    def displayName(self):
        return "Ordina feature (GeoSort)"

    def group(self):
        return "GeoSort"

    def groupId(self):
        return "geosort"

    def shortHelpString(self):
        return (
            "Ordina le feature di un layer vettoriale per criteri geometrici o attributivi "
            "e aggiunge il campo <b>sort_order</b> (numero progressivo, 1 = prima feature).\n\n"
            "Criteri disponibili: attributo tabellare, coordinate del centroide, "
            "area, lunghezza, perimetro, numero di vertici, bounding box, "
            "posizione lungo una linea di riferimento.\n\n"
            "Compatibile con il Processing Toolbox, il modellatore grafico e PyQGIS headless."
        )

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def createInstance(self):
        return GeoSortAlgorithm()

    # ──────────────────────────────────────────────────────────────────────────
    # Parametri
    # ──────────────────────────────────────────────────────────────────────────

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                "Layer di input",
                types=[QgsProcessing.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CRITERION,
                "Criterio di ordinamento",
                options=self._CRITERIA_LABELS,
                defaultValue=0,
            )
        )
        param_field = QgsProcessingParameterField(
            self.ATTRIBUTE_FIELD,
            "Campo attributo (solo per criterio 'Attributo tabellare')",
            parentLayerParameterName=self.INPUT,
            optional=True,
        )
        self.addParameter(param_field)

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DIRECTION, "Ordine ascendente", defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NULLS_LAST,
                "Valori NULL in fondo (solo per criterio attributo)",
                defaultValue=True,
            )
        )
        param_ref = QgsProcessingParameterMapLayer(
            self.REF_LAYER,
            "Layer linea di riferimento (solo per criterio 'Posizione lungo linea')",
            optional=True,
        )
        self.addParameter(param_ref)

        from qgis.core import QgsProcessingParameterExpression
        self.addParameter(
            QgsProcessingParameterExpression(
                "EXPRESSION",
                "Espressione QGIS (solo per criterio 'Espressione QGIS')",
                defaultValue="",
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_VALUE_FIELD,
                "Aggiungi campo con il valore del criterio (sort_value)",
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Layer ordinato")
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Esecuzione
    # ──────────────────────────────────────────────────────────────────────────

    def processAlgorithm(self, parameters, context, feedback):
        from .geosort_core import (
            sort_by_attribute,
            sort_by_centroid,
            sort_by_geometry_property,
            sort_by_line_position,
        )

        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException("Layer di input non trovato.")

        crit_idx = self.parameterAsEnum(parameters, self.CRITERION, context)
        criterion = self._CRITERIA_KEYS[crit_idx]
        ascending = self.parameterAsBoolean(parameters, self.DIRECTION, context)
        nulls_last = self.parameterAsBoolean(parameters, self.NULLS_LAST, context)
        add_value = self.parameterAsBoolean(parameters, self.ADD_VALUE_FIELD, context)

        feedback.setProgressText("Caricamento feature...")
        features = list(layer.getFeatures())
        if not features:
            raise QgsProcessingException("Il layer non contiene feature.")

        feedback.setProgress(10)
        if feedback.isCanceled():
            return {}

        # ── Ordinamento ──────────────────────────────────────────────────────
        feedback.setProgressText("Ordinamento in corso...")
        values = []

        if criterion == "attribute":
            field = self.parameterAsString(parameters, self.ATTRIBUTE_FIELD, context)
            if not field:
                raise QgsProcessingException(
                    "Specificare un campo attributo per il criterio 'Attributo tabellare'."
                )
            sorted_feats = sort_by_attribute(features, field, ascending, nulls_last)
            values = [f[field] for f in sorted_feats]
            excluded = []

        elif criterion in ("centroid_x", "centroid_y", "centroid_dist"):
            axis_map = {
                "centroid_x": "x",
                "centroid_y": "y",
                "centroid_dist": "dist",
            }
            axis = axis_map[criterion]
            sorted_feats, values = sort_by_centroid(
                features, axis=axis, ascending=ascending
            )
            excluded = []

        elif criterion == "line_position":
            ref_layer = self.parameterAsLayer(parameters, self.REF_LAYER, context)
            if not ref_layer:
                raise QgsProcessingException(
                    "Specificare un layer di riferimento per il criterio 'Posizione lungo linea'."
                )
            ref_feats = list(ref_layer.getFeatures())
            if not ref_feats:
                raise QgsProcessingException("Il layer di riferimento non contiene feature.")
            line_geom = QgsGeometry.unaryUnion([f.geometry() for f in ref_feats])
            line_mode_keys = ["centroid_projection", "intersecting_projection", "intersecting_first_pt"]
            line_mode_idx = self.parameterAsEnum(parameters, "LINE_MODE", context)
            line_mode = line_mode_keys[line_mode_idx]
            sorted_feats, values, excluded = sort_by_line_position(
                features, line_geom, ascending, mode=line_mode
            )
            if excluded:
                feedback.pushWarning(
                    f"GeoSort: {len(excluded)} feature escluse perché non intersecano la linea."
                )

        elif criterion == "expression":
            from .geosort_core import sort_by_expression
            expr_text = self.parameterAsExpression(parameters, "EXPRESSION", context)
            if not expr_text or not expr_text.strip():
                raise QgsProcessingException(
                    "Specificare un'espressione per il criterio 'Espressione QGIS'."
                )
            try:
                sorted_feats, values, warnings = sort_by_expression(
                    features, layer, expr_text, ascending, nulls_last
                )
            except ValueError as exc:
                raise QgsProcessingException(str(exc))
            if warnings:
                for w in warnings:
                    feedback.pushWarning(f"GeoSort espressione: {w}")
            excluded = []

        else:
            # Tutti i criteri geometrici
            try:
                sorted_feats, values = sort_by_geometry_property(
                    features, criterion, ascending
                )
            except ValueError as exc:
                raise QgsProcessingException(str(exc))
            excluded = []

        feedback.setProgress(60)
        if feedback.isCanceled():
            return {}

        # ── Costruzione layer output ─────────────────────────────────────────
        feedback.setProgressText("Scrittura output...")

        out_fields = QgsFields()
        for field in layer.fields():
            out_fields.append(field)
        out_fields.append(QgsField("sort_order", QVariant.Int))
        if add_value:
            out_fields.append(QgsField("sort_value", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            out_fields,
            layer.wkbType(),
            layer.crs(),
        )
        if sink is None:
            raise QgsProcessingException("Impossibile creare il layer di output.")

        total = len(sorted_feats)
        for i, feat in enumerate(sorted_feats):
            if feedback.isCanceled():
                break
            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            for field in layer.fields():
                new_feat[field.name()] = feat[field.name()]
            new_feat["sort_order"] = i + 1
            if add_value and i < len(values):
                try:
                    new_feat["sort_value"] = float(values[i])
                except (TypeError, ValueError):
                    pass
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            if i % 100 == 0:
                feedback.setProgress(60 + int(40 * i / total))

        feedback.setProgress(100)
        return {self.OUTPUT: dest_id}
