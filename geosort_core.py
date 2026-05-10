# -*- coding: utf-8 -*-
"""
GeoSort – Logica di ordinamento pura.

Questo modulo non dipende dall'UI ed è testabile in modo autonomo.
Contiene tutte le funzioni di ordinamento e le utility per applicare
il campo sort_order al layer o creare un layer in memoria.
"""

import math

from qgis.core import (
    QgsWkbTypes,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsFeature,
    QgsFields,
    QgsVectorLayer,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsMessageLog,
    Qgis,
    NULL,
)
from qgis.PyQt.QtCore import QVariant

# ──────────────────────────────────────────────────────────────────────────────
# Costanti
# ──────────────────────────────────────────────────────────────────────────────

GEOM_CRITERIA = {
    "area":        "Area (poligoni)",
    "perimeter":   "Perimetro (poligoni)",
    "length":      "Lunghezza (linee)",
    "n_vertices":  "Numero di vertici",
    "bbox_width":  "Larghezza Bounding Box",
    "bbox_height": "Altezza Bounding Box",
    "bbox_area":   "Area Bounding Box",
    "bbox_xmin":   "Xmin Bounding Box",
    "bbox_ymin":   "Ymin Bounding Box",
}

CENTROID_AXES = {
    "x":    "Coordinata X",
    "y":    "Coordinata Y",
    "dist": "Distanza da punto di riferimento",
}

LOG_TAG = "GeoSort"


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per attributo
# ──────────────────────────────────────────────────────────────────────────────

def sort_by_attribute(features, field, ascending=True, nulls_last=True):
    """Ordina le feature per valore di un campo attributo.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        field (str): nome del campo.
        ascending (bool): True = crescente.
        nulls_last (bool): True = NULL in fondo; False = NULL in cima.

    Returns:
        list[QgsFeature]: lista ordinata.
    """
    null_priority = 1 if nulls_last else -1

    def key(f):
        val = f[field]
        is_null = val is None or val == NULL
        if is_null:
            return (null_priority, "")
        try:
            return (0, val)
        except TypeError:
            return (0, str(val))

    return sorted(features, key=key, reverse=not ascending)


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per espressione QGIS
# ──────────────────────────────────────────────────────────────────────────────

def sort_by_expression(features, layer, expression_str, ascending=True, nulls_last=True):
    """Ordina le feature valutando un'espressione QGIS per ciascuna.

    Supporta qualsiasi espressione valida nel field calculator di QGIS:
    combinazioni di campi, funzioni geometriche, espressioni condizionali,
    calcoli al volo (es. ``"area_kmq" / "popolazione"``).

    Args:
        features (list[QgsFeature]): feature da ordinare.
        layer (QgsVectorLayer): layer sorgente (necessario per il contesto
            dell'espressione: CRS, campi, variabili di progetto).
        expression_str (str): testo dell'espressione QGIS.
        ascending (bool): True = crescente.
        nulls_last (bool): True = NULL/errori in fondo; False = in cima.

    Returns:
        tuple[list[QgsFeature], list, list[str]]:
            * feature ordinate
            * valori calcolati (uno per feature, nello stesso ordine)
            * lista di messaggi di errore/avviso (vuota se tutto ok)

    Raises:
        ValueError: se l'espressione non è sintatticamente valida.
    """
    expr = QgsExpression(expression_str)
    if expr.hasParserError():
        raise ValueError(
            f"Espressione non valida: {expr.parserErrorString()}\n"
            f"Espressione: {expression_str!r}"
        )

    # Contesto base: variabili di progetto + campi del layer
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

    null_priority = 1 if nulls_last else -1
    warnings = []
    pairs = []

    for feat in features:
        context.setFeature(feat)
        val = expr.evaluate(context)

        if expr.hasEvalError():
            msg = f"FID {feat.id()}: {expr.evalErrorString()}"
            warnings.append(msg)
            QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Warning)
            val = None

        # Normalizza NULL e None allo stesso trattamento
        is_null = val is None or val == NULL
        pairs.append((feat, val, is_null))

    def sort_key(item):
        _feat, val, is_null = item
        if is_null:
            return (null_priority, "")
        try:
            return (0, val)
        except TypeError:
            return (0, str(val))

    pairs.sort(key=sort_key, reverse=not ascending)
    sorted_feats = [p[0] for p in pairs]
    values       = [p[1] for p in pairs]

    return sorted_feats, values, warnings

def sort_by_centroid(features, axis="x", ascending=True, ref_point=None):
    """Ordina le feature per coordinata X/Y del centroide o distanza da un punto.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        axis (str): "x", "y" o "dist".
        ascending (bool): True = crescente.
        ref_point (QgsPointXY | None): punto di riferimento (solo per axis=="dist").

    Returns:
        tuple[list[QgsFeature], list[float]]: (feature ordinate, valori criterio).
    """
    def _centroid(f):
        geom = f.geometry()
        if geom.isMultipart():
            return geom.pointOnSurface().asPoint()
        return geom.centroid().asPoint()

    def key(f):
        pt = _centroid(f)
        if axis == "dist" and ref_point is not None:
            return math.sqrt(
                (pt.x() - ref_point.x()) ** 2 + (pt.y() - ref_point.y()) ** 2
            )
        return pt.x() if axis == "x" else pt.y()

    sorted_feats = sorted(features, key=key, reverse=not ascending)
    values = [key(f) for f in sorted_feats]
    return sorted_feats, values


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per proprietà geometrica
# ──────────────────────────────────────────────────────────────────────────────

def _geom_value(feature, criterion):
    """Calcola il valore del criterio geometrico per una feature.

    Raises:
        ValueError: se il criterio non è compatibile con il tipo di geometria.
    """
    geom = feature.geometry()
    wkb_type = geom.wkbType()
    geom_type = QgsWkbTypes.geometryType(wkb_type)
    type_name = QgsWkbTypes.displayString(wkb_type)

    if criterion == "area":
        if geom_type != QgsWkbTypes.PolygonGeometry:
            raise ValueError(
                f"Criterio 'area' richiede geometrie poligonali, trovato: {type_name}."
            )
        return geom.area()

    elif criterion == "perimeter":
        if geom_type != QgsWkbTypes.PolygonGeometry:
            raise ValueError(
                f"Criterio 'perimeter' richiede geometrie poligonali, trovato: {type_name}."
            )
        return geom.length()

    elif criterion == "length":
        if geom_type != QgsWkbTypes.LineGeometry:
            raise ValueError(
                f"Criterio 'length' richiede geometrie lineari, trovato: {type_name}."
            )
        return geom.length()

    elif criterion == "n_vertices":
        return geom.constGet().nCoordinates()

    elif criterion == "bbox_width":
        return geom.boundingBox().width()

    elif criterion == "bbox_height":
        return geom.boundingBox().height()

    elif criterion == "bbox_area":
        bb = geom.boundingBox()
        return bb.width() * bb.height()

    elif criterion == "bbox_xmin":
        return geom.boundingBox().xMinimum()

    elif criterion == "bbox_ymin":
        return geom.boundingBox().yMinimum()

    else:
        raise ValueError(f"Criterio sconosciuto: '{criterion}'.")


def sort_by_geometry_property(features, criterion, ascending=True):
    """Ordina le feature per proprietà geometrica.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        criterion (str): chiave in GEOM_CRITERIA.
        ascending (bool): True = crescente.

    Returns:
        tuple[list[QgsFeature], list[float]]: (feature ordinate, valori criterio).

    Raises:
        ValueError: se il criterio non è compatibile con il tipo di geometria della
                    prima feature (validazione anticipata).
    """
    if features:
        _geom_value(features[0], criterion)  # solleva subito se incompatibile

    def key(f):
        try:
            return _geom_value(f, criterion)
        except Exception as exc:
            QgsMessageLog.logMessage(str(exc), LOG_TAG, Qgis.Warning)
            return 0.0

    sorted_feats = sorted(features, key=key, reverse=not ascending)
    values = [key(f) for f in sorted_feats]
    return sorted_feats, values


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per posizione lungo una linea
# ──────────────────────────────────────────────────────────────────────────────

# Modalità disponibili per l'ordinamento lungo linea
LINE_MODES = {
    "centroid_projection":     "Proiezione centroide (tutte le feature)",
    "intersecting_projection": "Solo intersecanti – proiezione centroide",
    "intersecting_first_pt":   "Solo intersecanti – primo punto di intersezione",
}


def _extract_points_from_geometry(geom):
    """Restituisce una lista di QgsGeometry (punti) estratti da una geometria qualsiasi.

    Usato per trovare i punti di intersezione tra una feature e la linea.
    Gestisce: Point, MultiPoint, LineString (vertici), MultiLineString,
    GeometryCollection.
    """
    geom_type = QgsWkbTypes.geometryType(geom.wkbType())
    pts = []

    if geom_type == QgsWkbTypes.PointGeometry:
        if geom.isMultipart():
            for p in geom.asMultiPoint():
                pts.append(QgsGeometry.fromPointXY(QgsPointXY(p.x(), p.y())))
        else:
            pts.append(geom)

    elif geom_type == QgsWkbTypes.LineGeometry:
        # Usa tutti i vertici della linea
        if geom.isMultipart():
            for part in geom.asMultiPolyline():
                for v in part:
                    pts.append(QgsGeometry.fromPointXY(QgsPointXY(v.x(), v.y())))
        else:
            for v in geom.asPolyline():
                pts.append(QgsGeometry.fromPointXY(QgsPointXY(v.x(), v.y())))

    elif geom_type == QgsWkbTypes.PolygonGeometry:
        # Per poligoni usa il centroide dell'intersezione
        pts.append(geom.centroid())

    else:
        # GeometryCollection: ricorsione sui componenti
        for i in range(geom.constGet().numGeometries()):
            sub = QgsGeometry(geom.constGet().geometryN(i).clone())
            pts.extend(_extract_points_from_geometry(sub))

    return pts


def _first_intersection_distance(line_geom, feature_geom):
    """Distanza lungo ``line_geom`` del *primo* punto di intersezione con ``feature_geom``.

    "Primo" = minore distanza curvilinea dall'inizio della linea.

    Returns:
        float | None: distanza in unità mappa, o None se non c'è intersezione.
    """
    intersection = line_geom.intersection(feature_geom)
    if intersection is None or intersection.isEmpty():
        return None

    points = _extract_points_from_geometry(intersection)
    if not points:
        return None

    distances = []
    for pt in points:
        try:
            distances.append(line_geom.lineLocatePoint(pt))
        except Exception:
            pass

    return min(distances) if distances else None


def sort_by_line_position(features, line_geometry, ascending=True,
                          mode="centroid_projection"):
    """Ordina le feature in base alla loro posizione lungo una linea di riferimento.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        line_geometry (QgsGeometry): geometria LineString (o MultiLineString) di riferimento.
        ascending (bool): True = dalla testa della linea.
        mode (str): modalità di calcolo, una delle chiavi di ``LINE_MODES``:

            * ``centroid_projection`` – proietta il centroide sulla linea.
              Tutte le feature vengono incluse, anche quelle lontane dalla linea.
            * ``intersecting_projection`` – include solo le feature che intersecano
              fisicamente la linea; per ognuna proietta il centroide.
            * ``intersecting_first_pt`` – include solo le feature che intersecano
              la linea; usa il *primo punto di intersezione* (distanza minima
              dall'inizio della linea) invece del centroide.

    Returns:
        tuple[list[QgsFeature], list[float], list[QgsFeature]]:
            (feature ordinate, valori distanza, feature escluse).
            Le feature escluse sono quelle che non intersecano la linea
            (rilevanti solo per le modalità ``intersecting_*``).
    """
    sorted_feats = []
    values = []
    excluded = []

    for f in features:
        geom = f.geometry()
        geom_type = QgsWkbTypes.geometryType(geom.wkbType())

        # ── Punto rappresentativo della feature (centroide / punto stesso) ──
        if geom_type == QgsWkbTypes.PointGeometry:
            pt_geom = QgsGeometry(geom)
        else:
            pt_geom = geom.centroid()

        # ── Calcolo distanza in base alla modalità ───────────────────────────

        if mode == "centroid_projection":
            # Proiezione del centroide: include sempre la feature
            nearest = line_geometry.nearestPoint(pt_geom)
            dist = line_geometry.lineLocatePoint(nearest)
            sorted_feats.append(f)
            values.append(dist)

        elif mode == "intersecting_projection":
            # Solo feature che intersecano fisicamente la linea
            if not line_geometry.intersects(geom):
                excluded.append(f)
                continue
            nearest = line_geometry.nearestPoint(pt_geom)
            dist = line_geometry.lineLocatePoint(nearest)
            sorted_feats.append(f)
            values.append(dist)

        elif mode == "intersecting_first_pt":
            # Solo feature che intersecano; usa il primo punto di intersezione
            dist = _first_intersection_distance(line_geometry, geom)
            if dist is None:
                excluded.append(f)
                continue
            sorted_feats.append(f)
            values.append(dist)

        else:
            raise ValueError(f"Modalità sconosciuta: '{mode}'. "
                             f"Valori ammessi: {list(LINE_MODES.keys())}")

    # Ordina per distanza mantenendo l'associazione con i valori
    paired = sorted(zip(values, sorted_feats), reverse=not ascending)
    sorted_feats = [f for _, f in paired]
    values = [v for v, _ in paired]

    return sorted_feats, values, excluded


# ──────────────────────────────────────────────────────────────────────────────
# Applicazione al layer
# ──────────────────────────────────────────────────────────────────────────────

def apply_sort_order(
    layer,
    sorted_features,
    add_criterion_field=False,
    criterion_values=None,
    criterion_field_name="sort_value",
):
    """Scrive il campo sort_order (e opzionalmente il campo criterio) sul layer.

    Avvia automaticamente una sessione di editing se il layer non è già in edit mode.

    Args:
        layer (QgsVectorLayer): layer di destinazione.
        sorted_features (list[QgsFeature]): feature nell'ordine desiderato.
        add_criterion_field (bool): se True aggiunge il campo con il valore del criterio.
        criterion_values (list | None): valori numerici corrispondenti a sorted_features.
        criterion_field_name (str): nome del campo criterio aggiuntivo.

    Returns:
        bool: True se riuscito, False in caso di errore.
    """
    try:
        was_editing = layer.isEditable()
        if not was_editing:
            if not layer.startEditing():
                QgsMessageLog.logMessage(
                    "Impossibile avviare la sessione di editing.", LOG_TAG, Qgis.Critical
                )
                return False

        # ── Campo sort_order ──────────────────────────────────────────────────
        sort_idx = layer.fields().indexOf("sort_order")
        if sort_idx == -1:
            layer.addAttribute(QgsField("sort_order", QVariant.Int))
            layer.updateFields()
            sort_idx = layer.fields().indexOf("sort_order")

        # ── Campo criterio (opzionale) ────────────────────────────────────────
        crit_idx = -1
        if add_criterion_field and criterion_values:
            crit_idx = layer.fields().indexOf(criterion_field_name)
            if crit_idx == -1:
                layer.addAttribute(QgsField(criterion_field_name, QVariant.Double))
                layer.updateFields()
                crit_idx = layer.fields().indexOf(criterion_field_name)

        # ── Assegnazione valori ───────────────────────────────────────────────
        for i, feat in enumerate(sorted_features):
            fid = feat.id()
            layer.changeAttributeValue(fid, sort_idx, i + 1)
            if add_criterion_field and criterion_values and crit_idx != -1:
                try:
                    layer.changeAttributeValue(fid, crit_idx, float(criterion_values[i]))
                except (TypeError, ValueError):
                    pass

        if not layer.commitChanges():
            layer.rollBack()
            QgsMessageLog.logMessage(
                "Errore nel commit delle modifiche.", LOG_TAG, Qgis.Critical
            )
            return False

        return True

    except Exception as exc:
        QgsMessageLog.logMessage(str(exc), LOG_TAG, Qgis.Critical)
        if layer.isEditable():
            layer.rollBack()
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Creazione layer in memoria
# ──────────────────────────────────────────────────────────────────────────────

def create_memory_layer(
    source_layer,
    sorted_features,
    add_criterion_field=False,
    criterion_values=None,
    criterion_field_name="sort_value",
):
    """Crea un nuovo layer in memoria con le feature ordinate e il campo sort_order.

    Args:
        source_layer (QgsVectorLayer): layer sorgente (per CRS, tipo geometria, campi).
        sorted_features (list[QgsFeature]): feature nell'ordine desiderato.
        add_criterion_field (bool): se True aggiunge il campo con il valore del criterio.
        criterion_values (list | None): valori numerici corrispondenti a sorted_features.
        criterion_field_name (str): nome del campo criterio aggiuntivo.

    Returns:
        QgsVectorLayer: nuovo layer in memoria con 'sort_order' aggiunto.
    """
    geom_type_str = QgsWkbTypes.displayString(source_layer.wkbType())
    crs_auth = source_layer.crs().authid()
    uri = f"{geom_type_str}?crs={crs_auth}"

    mem_layer = QgsVectorLayer(uri, "GeoSort_output", "memory")
    provider = mem_layer.dataProvider()

    original_fields = source_layer.fields().toList()
    new_fields = original_fields + [QgsField("sort_order", QVariant.Int)]
    if add_criterion_field and criterion_values:
        new_fields.append(QgsField(criterion_field_name, QVariant.Double))

    provider.addAttributes(new_fields)
    mem_layer.updateFields()

    out_features = []
    for i, feat in enumerate(sorted_features):
        new_feat = QgsFeature(mem_layer.fields())
        new_feat.setGeometry(feat.geometry())
        for field in original_fields:
            new_feat[field.name()] = feat[field.name()]
        new_feat["sort_order"] = i + 1
        if add_criterion_field and criterion_values:
            try:
                new_feat[criterion_field_name] = float(criterion_values[i])
            except (TypeError, ValueError):
                pass
        out_features.append(new_feat)

    provider.addFeatures(out_features)
    mem_layer.updateExtents()
    return mem_layer
