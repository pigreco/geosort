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
    QgsPointXY,
    QgsMessageLog,
    Qgis,
    NULL,
)
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QIcon


def _spec_from(key, field, expression, ascending, nulls_last, natural_sort):
    """Costruisce un descrittore di criterio per ``geosort_core.sort_multi``.

    Supporta solo i criteri "semplici" (senza geometria di riferimento esterna):
    attributo, espressione, centroide X/Y/distanza-da-origine, proprietà geometriche.
    """
    spec = {
        "key": key,
        "ascending": ascending,
        "nulls_last": nulls_last,
        "natural_sort": natural_sort,
    }
    if key == "attribute":
        spec["field"] = field
    elif key == "expression":
        spec["expression"] = expression
    elif key == "centroid_dist":
        spec["ref_point"] = QgsPointXY(0, 0)  # distanza dall'origine (0,0)
    return spec


class GeoSortAlgorithm(QgsProcessingAlgorithm):
    """Algoritmo Processing per ordinare le feature di un layer vettoriale."""

    # Parametri
    INPUT = "INPUT"
    CRITERION = "CRITERION"
    ATTRIBUTE_FIELD = "ATTRIBUTE_FIELD"
    DIRECTION = "DIRECTION"
    NULLS_LAST = "NULLS_LAST"
    NATURAL_SORT = "NATURAL_SORT"
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
        "line_distance",
        "expression",
    ]

    # ── Criterio secondario (tie-break) per l'ordinamento multi-criterio ──
    SECONDARY_CRITERION = "SECONDARY_CRITERION"
    SECONDARY_FIELD = "SECONDARY_FIELD"
    SECONDARY_EXPRESSION = "SECONDARY_EXPRESSION"
    SECONDARY_DIRECTION = "SECONDARY_DIRECTION"

    # Criteri ammessi come primario in modalità multi-criterio (no linea: niente
    # geometria di riferimento esterna né semantica di esclusione).
    _MULTI_PRIMARY_KEYS = frozenset({
        "attribute", "expression",
        "centroid_x", "centroid_y", "centroid_dist",
        "area", "perimeter", "length", "n_vertices",
        "bbox_width", "bbox_height", "bbox_area", "bbox_xmin", "bbox_ymin",
    })

    # 0 = nessuno; gli altri indici → chiave di criterio secondario
    _SECONDARY_KEYS = [
        None,
        "attribute", "expression",
        "centroid_x", "centroid_y",
        "area", "perimeter", "length", "n_vertices",
        "bbox_width", "bbox_height", "bbox_area", "bbox_xmin", "bbox_ymin",
    ]
    _SECONDARY_LABELS = [
        "(nessuno)",
        "Attributo tabellare", "Espressione QGIS",
        "Centroide – coordinata X", "Centroide – coordinata Y",
        "Area (poligoni)", "Perimetro (poligoni)", "Lunghezza (linee)",
        "Numero di vertici", "Larghezza Bounding Box", "Altezza Bounding Box",
        "Area Bounding Box", "Xmin Bounding Box", "Ymin Bounding Box",
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
        "Distanza dalla linea di riferimento",
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
            "posizione lungo una linea di riferimento, distanza dalla linea di riferimento, espressione QGIS.\n\n"
            "<b>Modalità di ordinamento testuale (attributo/espressione):</b>\n"
            "• <b>Lessicografico</b> (default): confronto carattere per carattere. "
            "Esempio: «1010» &lt; «11» &lt; «1111».\n"
            "• <b>Natural Sort</b>: le sequenze di cifre sono confrontate come numeri. "
            "Esempio: «11» &lt; «1010» &lt; «1111». "
            "Utile con campi alfanumerici (FILE1, FILE2, FILE10) o espressioni "
            "di concatenazione come <code>\"fid\" || \"id_poly\"</code>.\n\n"
            "<b>Ordinamento multi-criterio:</b> imposta un <b>criterio secondario</b> "
            "per spezzare i pareggi del criterio primario (es. primario = regione, "
            "secondario = area decrescente). Disponibile per i criteri non basati su linea.\n\n"
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
                types=[QgsProcessing.SourceType.TypeVectorAnyGeometry],
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
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NATURAL_SORT,
                "Ordinamento naturale – Natural Sort (solo per criterio attributo/espressione)",
                defaultValue=False,
            )
        )
        param_ref = QgsProcessingParameterMapLayer(
            self.REF_LAYER,
            "Layer linea di riferimento (solo per criteri 'Posizione/Distanza dalla linea')",
            optional=True,
        )
        self.addParameter(param_ref)
        # Modalità di calcolo per il criterio "Posizione lungo linea"
        self.addParameter(
            QgsProcessingParameterEnum(
                "LINE_MODE",
                "Modalità di calcolo – Posizione lungo linea",
                options=[
                    "Proiezione centroide  –  tutte le feature",
                    "Solo intersecanti –  proiezione centroide",
                    "Solo intersecanti –  primo punto di intersezione",
                ],
                defaultValue=0,
            )
        )
        # Modalità di calcolo per il criterio "Distanza dalla linea"
        self.addParameter(
            QgsProcessingParameterEnum(
                "LINE_DISTANCE_MODE",
                "Modalità di calcolo – Distanza dalla linea",
                options=[
                    "Distanza dal centroide",
                    "Distanza dall'elemento",
                ],
                defaultValue=1,
            )
        )
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

        # ── Criterio secondario (tie-break) – ordinamento multi-criterio ──
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SECONDARY_CRITERION,
                "Criterio secondario per i pareggi (opzionale)",
                options=self._SECONDARY_LABELS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.SECONDARY_FIELD,
                "Campo del criterio secondario (solo se 'Attributo tabellare')",
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )
        from qgis.core import QgsProcessingParameterExpression
        self.addParameter(
            QgsProcessingParameterExpression(
                self.SECONDARY_EXPRESSION,
                "Espressione del criterio secondario (solo se 'Espressione QGIS')",
                defaultValue="",
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SECONDARY_DIRECTION,
                "Criterio secondario: ordine ascendente",
                defaultValue=True,
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

    def _run_multi(self, parameters, context, feedback, layer, features,
                   primary_key, sec_key, ascending, nulls_last, natural_sort):
        """Esegue l'ordinamento gerarchico (primario + secondario) via sort_multi.

        Returns:
            tuple[list, list, list]: (feature ordinate, valori primario, escluse=[]).
        """
        from .geosort_core import sort_multi

        primary_field = self.parameterAsString(parameters, self.ATTRIBUTE_FIELD, context)
        primary_expr = self.parameterAsExpression(parameters, "EXPRESSION", context)
        if primary_key == "attribute" and not primary_field:
            raise QgsProcessingException(
                "Specificare un campo attributo per il criterio primario."
            )
        if primary_key == "expression" and not (primary_expr and primary_expr.strip()):
            raise QgsProcessingException(
                "Specificare un'espressione per il criterio primario."
            )
        primary_spec = _spec_from(
            primary_key, primary_field, primary_expr, ascending, nulls_last, natural_sort
        )

        sec_field = self.parameterAsString(parameters, self.SECONDARY_FIELD, context)
        sec_expr = self.parameterAsExpression(parameters, self.SECONDARY_EXPRESSION, context)
        sec_asc = self.parameterAsBoolean(parameters, self.SECONDARY_DIRECTION, context)
        if sec_key == "attribute" and not sec_field:
            raise QgsProcessingException(
                "Specificare un campo per il criterio secondario."
            )
        if sec_key == "expression" and not (sec_expr and sec_expr.strip()):
            raise QgsProcessingException(
                "Specificare un'espressione per il criterio secondario."
            )
        secondary_spec = _spec_from(
            sec_key, sec_field, sec_expr, sec_asc, nulls_last, natural_sort
        )

        feedback.pushInfo("GeoSort: ordinamento multi-criterio (primario + secondario).")
        try:
            sorted_feats, values = sort_multi(
                features, [primary_spec, secondary_spec], layer
            )
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        return sorted_feats, values, []

    def processAlgorithm(self, parameters, context, feedback):
        from .geosort_core import (
            sort_by_attribute,
            sort_by_centroid,
            sort_by_geometry_property,
            sort_by_line_position,
            sort_by_line_distance,
            _infer_field_type,
        )

        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException("Layer di input non trovato.")

        crit_idx = self.parameterAsEnum(parameters, self.CRITERION, context)
        criterion = self._CRITERIA_KEYS[crit_idx]
        ascending = self.parameterAsBoolean(parameters, self.DIRECTION, context)
        nulls_last = self.parameterAsBoolean(parameters, self.NULLS_LAST, context)
        natural_sort = self.parameterAsBoolean(parameters, self.NATURAL_SORT, context)
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

        # Criterio secondario (tie-break) → ordinamento multi-criterio
        sec_idx = self.parameterAsEnum(parameters, self.SECONDARY_CRITERION, context)
        sec_key = self._SECONDARY_KEYS[sec_idx]
        multi_active = sec_key is not None and criterion in self._MULTI_PRIMARY_KEYS
        if sec_key is not None and not multi_active:
            feedback.pushWarning(
                "GeoSort: criterio secondario ignorato perché il criterio primario "
                "è basato su una linea di riferimento."
            )

        if multi_active:
            sorted_feats, values, excluded = self._run_multi(
                parameters, context, feedback, layer, features,
                criterion, sec_key, ascending, nulls_last, natural_sort,
            )

        elif criterion == "attribute":
            field = self.parameterAsString(parameters, self.ATTRIBUTE_FIELD, context)
            if not field:
                raise QgsProcessingException(
                    "Specificare un campo attributo per il criterio 'Attributo tabellare'."
                )
            sorted_feats = sort_by_attribute(features, field, ascending, nulls_last, natural_sort=natural_sort)
            values = [f[field] for f in sorted_feats]
            excluded = []

        elif criterion in ("centroid_x", "centroid_y", "centroid_dist"):
            axis_map = {
                "centroid_x": "x",
                "centroid_y": "y",
                "centroid_dist": "dist",
            }
            axis = axis_map[criterion]
            ref_point = QgsPointXY(0, 0) if axis == "dist" else None
            sorted_feats, values = sort_by_centroid(
                features, axis=axis, ascending=ascending, ref_point=ref_point
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

        elif criterion == "line_distance":
            ref_layer = self.parameterAsLayer(parameters, self.REF_LAYER, context)
            if not ref_layer:
                raise QgsProcessingException(
                    "Specificare un layer di riferimento per il criterio 'Distanza dalla linea'."
                )
            ref_feats = list(ref_layer.getFeatures())
            if not ref_feats:
                raise QgsProcessingException("Il layer di riferimento non contiene feature.")
            line_geom = QgsGeometry.unaryUnion([f.geometry() for f in ref_feats])
            dist_mode_keys = ["centroid", "element"]
            dist_mode_idx = self.parameterAsEnum(parameters, "LINE_DISTANCE_MODE", context)
            dist_mode = dist_mode_keys[dist_mode_idx]
            sorted_feats, values = sort_by_line_distance(
                features, line_geom, ascending, mode=dist_mode
            )
            excluded = []

        elif criterion == "expression":
            from .geosort_core import sort_by_expression
            expr_text = self.parameterAsExpression(parameters, "EXPRESSION", context)
            if not expr_text or not expr_text.strip():
                raise QgsProcessingException(
                    "Specificare un'espressione per il criterio 'Espressione QGIS'."
                )
            try:
                sorted_feats, values, warnings = sort_by_expression(
                    features, layer, expr_text, ascending, nulls_last,
                    natural_sort=natural_sort,
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
        out_fields.append(QgsField("sort_order", QMetaType.Type.Int))
        value_field_type = QMetaType.Type.Double
        if add_value and values:
            value_field_type = _infer_field_type(values)
            out_fields.append(QgsField("sort_value", value_field_type))

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
                val = values[i]
                if value_field_type == QMetaType.Type.Double:
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        val = None
                elif value_field_type == QMetaType.Type.Int:
                    try:
                        val = int(val)
                    except (TypeError, ValueError):
                        val = None
                else:
                    val = str(val) if val not in (None, NULL) else None
                new_feat["sort_value"] = val
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            if i % 100 == 0:
                feedback.setProgress(60 + int(40 * i / total))

        feedback.setProgress(100)
        return {self.OUTPUT: dest_id}
