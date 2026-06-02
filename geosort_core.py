# -*- coding: utf-8 -*-
"""
GeoSort – Logica di ordinamento pura.

Questo modulo non dipende dall'UI ed è testabile in modo autonomo.
Contiene tutte le funzioni di ordinamento e le utility per applicare
il campo sort_order al layer o creare un layer in memoria.
"""

import math
import re

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
    QgsDistanceArea,
    QgsCoordinateTransformContext,
    QgsUnitTypes,
    QgsMessageLog,
    Qgis,
    NULL,
)
from qgis.PyQt.QtCore import QMetaType, Qt

# Compatibilita Qt5/Qt6 per Qt.ISODate
try:
    _ISODATE = Qt.DateFormat.ISODate       # Qt6 / PyQt6
except AttributeError:
    _ISODATE = Qt.ISODate                   # Qt5 / PyQt5

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
# Robustezza CRS – misura ellissoidica (geodetica)
# ──────────────────────────────────────────────────────────────────────────────
#
# Su un CRS geografico (gradi, es. EPSG:4326) i calcoli planari di area,
# lunghezza, perimetro e distanza restituiscono valori in gradi/gradi², privi di
# senso metrico, e l'ordinamento può risultare distorto quando le feature
# spaziano latitudini diverse (1° di longitudine "vale" meno alle alte
# latitudini). La soluzione è misurare sull'ellissoide tramite QgsDistanceArea,
# esattamente come fanno ``$area``/``$length`` del field calculator di QGIS.

# Criteri le cui misure dipendono dalle unità del CRS (potenzialmente fuorvianti
# su CRS geografico).
METRIC_CRITERIA = frozenset({
    "area", "perimeter", "length",
    "centroid_dist", "line_position", "line_distance",
    "bbox_width", "bbox_height", "bbox_area",
})

# Sottoinsieme dei criteri metrici convertibili in misura ellissoidica
# (metri / m²). I criteri di bounding box e ``line_position`` restano planari:
# il bounding box è un concetto in coordinate native, e la posizione lungo una
# singola linea è comunque monotòna (l'ordinamento si conserva).
GEODESIC_CRITERIA = frozenset({
    "area", "perimeter", "length",
    "centroid_dist", "line_distance",
})

# Modalità di applicazione della misura geodetica.
GEODESIC_AUTO = "auto"      # geodetica solo se il CRS è geografico (default)
GEODESIC_ALWAYS = "always"  # geodetica sempre (anche su CRS proiettati)
GEODESIC_NEVER = "never"    # disattiva: misura planare nelle unità del CRS


def build_distance_area(crs, transform_context=None, ellipsoid=None):
    """Costruisce un :class:`QgsDistanceArea` per misure ellissoidiche.

    Args:
        crs (QgsCoordinateReferenceSystem): CRS sorgente delle geometrie.
        transform_context (QgsCoordinateTransformContext | None): contesto di
            trasformazione del progetto; se ``None`` ne usa uno vuoto.
        ellipsoid (str | None): acronimo ellissoide. Default: quello del CRS,
            con fallback "WGS84".

    Returns:
        QgsDistanceArea: configurato e con ellissoide attivo, pronto per
        ``measureArea`` / ``measureLength`` / ``measureLine`` (risultati in
        m² / m).
    """
    da = QgsDistanceArea()
    if transform_context is None:
        transform_context = QgsCoordinateTransformContext()
    da.setSourceCrs(crs, transform_context)
    da.setEllipsoid(ellipsoid or crs.ellipsoidAcronym() or "WGS84")
    return da


def resolve_geodesic(crs, criterion, mode=GEODESIC_AUTO):
    """Decide se per ``criterion`` su ``crs`` va usata la misura geodetica.

    Args:
        crs (QgsCoordinateReferenceSystem | None): CRS del layer.
        criterion (str): chiave di criterio.
        mode (str): ``GEODESIC_AUTO`` | ``GEODESIC_ALWAYS`` | ``GEODESIC_NEVER``.

    Returns:
        bool: ``True`` se va costruito/passato un :class:`QgsDistanceArea`.
    """
    if mode == GEODESIC_NEVER:
        return False
    if criterion not in GEODESIC_CRITERIA:
        return False
    if mode == GEODESIC_ALWAYS:
        return True
    return bool(crs is not None and crs.isGeographic())


def should_build_distance_area(crs, mode=GEODESIC_AUTO):
    """Decide se costruire un :class:`QgsDistanceArea` per il CRS dato.

    Utile per il percorso multi-criterio, dove un singolo ``distance_area`` viene
    passato a tutti i livelli e applicato solo a quelli geodetici. In modalità
    ``auto`` dipende solo dal fatto che il CRS sia geografico, a prescindere dal
    criterio specifico.

    Returns:
        bool: ``True`` se conviene costruire il misuratore ellissoidico.
    """
    if mode == GEODESIC_NEVER:
        return False
    if mode == GEODESIC_ALWAYS:
        return True
    return bool(crs is not None and crs.isGeographic())


def geographic_crs_warning(crs, criterion, applied_geodesic):
    """Messaggio d'avviso per un criterio metrico su CRS geografico.

    Args:
        crs (QgsCoordinateReferenceSystem | None): CRS del layer.
        criterion (str): chiave di criterio.
        applied_geodesic (bool): ``True`` se la misura geodetica è stata applicata.

    Returns:
        str: testo pronto da mostrare; stringa vuota se non rilevante (CRS
        proiettato o criterio non metrico).
    """
    if crs is None or not crs.isGeographic() or criterion not in METRIC_CRITERIA:
        return ""
    authid = crs.authid() or "CRS geografico"
    ellipsoid = crs.ellipsoidAcronym() or "WGS84"
    if applied_geodesic:
        return (
            f"CRS geografico ({authid}): misura ellissoidica (geodetica) applicata "
            f"automaticamente. I valori del criterio sono in metri/m² "
            f"sull'ellissoide {ellipsoid}, non in gradi."
        )
    if criterion in GEODESIC_CRITERIA:
        return (
            f"CRS geografico ({authid}): i valori di '{criterion}' sono calcolati in "
            f"gradi e l'ordinamento può risultare distorto alle diverse latitudini. "
            f"Attiva la misura geodetica o riproietta in un CRS proiettato (metrico)."
        )
    # bbox_* : nessun equivalente ellissoidico (concetto in coordinate native).
    return (
        f"CRS geografico ({authid}): '{criterion}' è calcolato in gradi (concetto "
        f"planare in coordinate native). Per misure metriche riproietta in un CRS "
        f"proiettato."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Type inference per field creation
# ──────────────────────────────────────────────────────────────────────────────

def _infer_field_type(values):
    """Rileva il QMetaType appropriato dal primo valore non-NULL.

    Args:
        values (list): lista di valori.

    Returns:
        QMetaType.Type: tipo rilevato (Double, Int, o QString).
    """
    for v in values:
        if v is None or v == NULL:
            continue
        if isinstance(v, bool):
            return QMetaType.Type.Int
        if isinstance(v, int):
            return QMetaType.Type.Int
        if isinstance(v, float):
            return QMetaType.Type.Double
        return QMetaType.Type.QString
    return QMetaType.Type.Double  # fallback


def _coerce_value(val, field_type):
    """Converte ``val`` al tipo del campo, restituendo NULL se non convertibile.

    Centralizza la logica di coercizione condivisa da :func:`apply_sort_order`
    e :func:`create_memory_layer`.

    Args:
        val: valore grezzo del criterio.
        field_type (QMetaType.Type): tipo di destinazione del campo.

    Returns:
        Il valore convertito (float/int/str) oppure ``NULL``.
    """
    if field_type == QMetaType.Type.Double:
        try:
            return float(val)
        except (TypeError, ValueError):
            return NULL
    if field_type == QMetaType.Type.Int:
        try:
            return int(val)
        except (TypeError, ValueError):
            return NULL
    return str(val) if val not in (None, NULL) else NULL


# ──────────────────────────────────────────────────────────────────────────────
# Normalizzazione valori data/ora
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_val(val):
    """Converte tipi data/ora in una rappresentazione stringa confrontabile.

    QDate, QDateTime, QTime e i corrispondenti tipi Python ``datetime``
    vengono convertiti in formato ISO-8601 in modo che l'ordinamento
    lessicografico coincida con l'ordinamento cronologico.
    Tutti gli altri tipi vengono restituiti invariati.
    """
    # PyQt date/time
    try:
        return val.toString(_ISODATE)
    except AttributeError:
        pass
    # Python datetime.date / datetime.datetime
    try:
        return val.isoformat()
    except AttributeError:
        pass
    return val


# ──────────────────────────────────────────────────────────────────────────────
# Natural Sort
# ──────────────────────────────────────────────────────────────────────────────

def _natural_key(val):
    """Chiave per ordinamento naturale: spezza la stringa in segmenti int/str.

    Esempi: "11" < "1010" < "1111" invece di "1010" < "11" < "1111".
    """
    return [int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r"(\d+)", str(val))]


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per attributo
# ──────────────────────────────────────────────────────────────────────────────

from typing import List, Tuple, Any, Callable, Optional

def sort_by_attribute(features: List[QgsFeature], field: str, ascending: bool = True,
                      nulls_last: bool = True, natural_sort: bool = False,
                      progress_callback: Optional[Callable[[float], None]] = None) -> List[QgsFeature]:
    """Ordina le feature per valore di un campo attributo.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        field (str): nome del campo.
        ascending (bool): True = crescente.
        nulls_last (bool): True = NULL in fondo; False = NULL in cima.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        list[QgsFeature]: lista ordinata.
    """
    null_priority = 1 if nulls_last else -1
    total = len(features)

    def key(f):
        val = f[field]
        is_null = val is None or val == NULL
        if is_null:
            return (null_priority, [])
        if natural_sort:
            return (0, _natural_key(val))
        try:
            return (0, _normalize_val(val))
        except TypeError:
            return (0, str(val))

    sorted_feats = sorted(features, key=key, reverse=not ascending)

    if progress_callback:
        progress_callback(100)

    return sorted_feats


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per espressione QGIS
# ──────────────────────────────────────────────────────────────────────────────

def sort_by_expression(features, layer, expression_str, ascending=True, nulls_last=True,
                       natural_sort=False, progress_callback=None):
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
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

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
    total = len(features)

    for i, feat in enumerate(features):
        context.setFeature(feat)
        val = expr.evaluate(context)

        if expr.hasEvalError():
            msg = f"FID {feat.id()}: {expr.evalErrorString()}"
            warnings.append(msg)
            QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.MessageLevel.Warning)
            val = None

        # Normalizza NULL e None allo stesso trattamento
        is_null = val is None or val == NULL
        pairs.append((feat, val, is_null))

        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    def sort_key(item):
        _feat, val, is_null = item
        if is_null:
            return (null_priority, [])
        if natural_sort:
            return (0, _natural_key(val))
        try:
            return (0, _normalize_val(val))
        except TypeError:
            return (0, str(val))

    pairs.sort(key=sort_key, reverse=not ascending)
    sorted_feats = [p[0] for p in pairs]
    values       = [p[1] for p in pairs]

    if progress_callback:
        progress_callback(100)

    return sorted_feats, values, warnings

def _is_empty_geom(geom):
    """True se la geometria è assente, nulla o vuota (feature non ordinabile spazialmente)."""
    return geom is None or geom.isNull() or geom.isEmpty()


def sort_by_centroid(features, axis="x", ascending=True, ref_point=None,
                     progress_callback=None, distance_area=None):
    """Ordina le feature per coordinata X/Y del centroide o distanza da un punto.

    Le feature prive di geometria (NULL/vuota) non vengono scartate: sono
    relegate in fondo all'elenco con valore ``None``, indipendentemente dalla
    direzione di ordinamento.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        axis (str): "x", "y" o "dist".
        ascending (bool): True = crescente.
        ref_point (QgsPointXY | None): punto di riferimento (solo per axis=="dist").
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
        distance_area (QgsDistanceArea | None): se fornito e ``axis=="dist"``, la
            distanza dal punto di riferimento è misurata sull'ellissoide (m).

    Returns:
        tuple[list[QgsFeature], list[float]]: (feature ordinate, valori criterio).
    """
    def _value(f):
        geom = f.geometry()
        if _is_empty_geom(geom):
            return None
        pt = (geom.pointOnSurface() if geom.isMultipart() else geom.centroid()).asPoint()
        if axis == "dist" and ref_point is not None:
            if distance_area is not None:
                return distance_area.measureLine(pt, ref_point)
            return math.sqrt(
                (pt.x() - ref_point.x()) ** 2 + (pt.y() - ref_point.y()) ** 2
            )
        return pt.x() if axis == "x" else pt.y()

    # Decorate-sort-undecorate: la chiave geometrica è calcolata una sola volta.
    valid = []
    invalid = []
    for f in features:
        v = _value(f)
        (invalid if v is None else valid).append((f, v))

    valid.sort(key=lambda p: p[1], reverse=not ascending)
    sorted_feats = [p[0] for p in valid] + [p[0] for p in invalid]
    values = [p[1] for p in valid] + [None] * len(invalid)

    if progress_callback:
        progress_callback(100)

    return sorted_feats, values


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento per proprietà geometrica
# ──────────────────────────────────────────────────────────────────────────────

def _geom_value(feature, criterion, distance_area=None):
    """Calcola il valore del criterio geometrico per una feature.

    Args:
        feature (QgsFeature): feature da misurare.
        criterion (str): chiave in :data:`GEOM_CRITERIA`.
        distance_area (QgsDistanceArea | None): se fornito, area/perimetro/
            lunghezza sono misurati sull'ellissoide (m² / m); altrimenti planari
            nelle unità del CRS.

    Raises:
        ValueError: se il criterio non è compatibile con il tipo di geometria.
    """
    geom = feature.geometry()
    wkb_type = geom.wkbType()
    geom_type = QgsWkbTypes.geometryType(wkb_type)
    type_name = QgsWkbTypes.displayString(wkb_type)

    if criterion == "area":
        if geom_type != QgsWkbTypes.GeometryType.PolygonGeometry:
            raise ValueError(
                f"Criterio 'area' richiede geometrie poligonali, trovato: {type_name}."
            )
        return distance_area.measureArea(geom) if distance_area else geom.area()

    elif criterion == "perimeter":
        if geom_type != QgsWkbTypes.GeometryType.PolygonGeometry:
            raise ValueError(
                f"Criterio 'perimeter' richiede geometrie poligonali, trovato: {type_name}."
            )
        return distance_area.measurePerimeter(geom) if distance_area else geom.length()

    elif criterion == "length":
        if geom_type != QgsWkbTypes.GeometryType.LineGeometry:
            raise ValueError(
                f"Criterio 'length' richiede geometrie lineari, trovato: {type_name}."
            )
        return distance_area.measureLength(geom) if distance_area else geom.length()

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


def sort_by_geometry_property(features: List[QgsFeature], criterion: str, ascending: bool = True,
                               progress_callback = None, distance_area = None) -> Tuple[List[QgsFeature], List[float]]:
    """Ordina le feature per proprietà geometrica.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        criterion (str): chiave in GEOM_CRITERIA.
        ascending (bool): True = crescente.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
        distance_area (QgsDistanceArea | None): se fornito, area/perimetro/lunghezza
            sono misurati sull'ellissoide (m² / m). Vedi :func:`build_distance_area`.

    Returns:
        tuple[list[QgsFeature], list[float]]: (feature ordinate, valori criterio).

    Le feature prive di geometria o con un tipo di geometria incompatibile col
    criterio (es. layer a geometria mista) non interrompono l'ordinamento: sono
    relegate in fondo con valore ``None``.

    Raises:
        ValueError: se *nessuna* feature è compatibile con il criterio scelto
                    (criterio errato per il dato o criterio sconosciuto).
    """
    # Decorate-sort-undecorate con validazione per-feature.
    valid = []
    invalid = []
    incompatible = 0
    first_error = None
    for f in features:
        geom = f.geometry()
        if _is_empty_geom(geom):
            invalid.append(f)
            continue
        try:
            valid.append((f, _geom_value(f, criterion, distance_area)))
        except ValueError as exc:
            incompatible += 1
            if first_error is None:
                first_error = exc
            invalid.append(f)

    # Se il criterio non è compatibile con nessuna feature, è un errore d'uso.
    if not valid and first_error is not None:
        raise first_error

    valid.sort(key=lambda p: p[1], reverse=not ascending)
    sorted_feats = [p[0] for p in valid] + invalid
    values = [p[1] for p in valid] + [None] * len(invalid)

    if progress_callback:
        progress_callback(100)

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

LINE_DISTANCE_MODES = {
    "centroid": "Distanza dal centroide",
    "element":  "Distanza dall'elemento",
}


def _extract_points_from_geometry(geom):
    """Restituisce una lista di QgsGeometry (punti) estratti da una geometria qualsiasi.

    Usato per trovare i punti di intersezione tra una feature e la linea.
    Gestisce: Point, MultiPoint, LineString (vertici), MultiLineString,
    GeometryCollection.
    """
    geom_type = QgsWkbTypes.geometryType(geom.wkbType())
    pts = []

    if geom_type == QgsWkbTypes.GeometryType.PointGeometry:
        if geom.isMultipart():
            for p in geom.asMultiPoint():
                pts.append(QgsGeometry.fromPointXY(QgsPointXY(p.x(), p.y())))
        else:
            pts.append(geom)

    elif geom_type == QgsWkbTypes.GeometryType.LineGeometry:
        # Usa tutti i vertici della linea
        if geom.isMultipart():
            for part in geom.asMultiPolyline():
                for v in part:
                    pts.append(QgsGeometry.fromPointXY(QgsPointXY(v.x(), v.y())))
        else:
            for v in geom.asPolyline():
                pts.append(QgsGeometry.fromPointXY(QgsPointXY(v.x(), v.y())))

    elif geom_type == QgsWkbTypes.GeometryType.PolygonGeometry:
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
                          mode="centroid_projection", progress_callback=None):
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
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        tuple[list[QgsFeature], list[float], list[QgsFeature]]:
            (feature ordinate, valori distanza, feature escluse).
            Le feature escluse sono quelle che non intersecano la linea
            (rilevanti solo per le modalità ``intersecting_*``).
            Anche le feature prive di geometria finiscono fra le escluse.

    Raises:
        ValueError: se la geometria di riferimento è assente o vuota.
    """
    if _is_empty_geom(line_geometry):
        raise ValueError("La geometria della linea di riferimento è assente o vuota.")

    sorted_feats = []
    values = []
    excluded = []
    total = len(features)

    for i, f in enumerate(features):
        geom = f.geometry()
        if _is_empty_geom(geom):
            excluded.append(f)
            continue
        geom_type = QgsWkbTypes.geometryType(geom.wkbType())

        # ── Punto rappresentativo della feature (centroide / punto stesso) ──
        if geom_type == QgsWkbTypes.GeometryType.PointGeometry:
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

        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    # Ordina per distanza mantenendo l'associazione con i valori
    paired = sorted(zip(values, sorted_feats), reverse=not ascending)
    sorted_feats = [f for _, f in paired]
    values = [v for v, _ in paired]

    if progress_callback:
        progress_callback(100)

    return sorted_feats, values, excluded


def sort_by_line_distance(features, line_geometry, ascending=True, mode="element",
                          progress_callback=None, distance_area=None):
    """Ordina le feature per distanza (perpendicolare) dalla linea di riferimento.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        line_geometry (QgsGeometry): geometria LineString (o MultiLineString) di riferimento.
        ascending (bool): True = crescente (più vicine prima).
        mode (str): modalità di calcolo, una delle chiavi di ``LINE_DISTANCE_MODES``:
            * ``centroid`` – distanza dal centroide della feature.
            * ``element`` – distanza dal punto più vicino della geometria.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
        distance_area (QgsDistanceArea | None): se fornito, la distanza è misurata
            sull'ellissoide (m) sul segmento più breve feature↔linea.

    Returns:
        tuple[list[QgsFeature], list[float]]: (feature ordinate, valori distanza).
        Le feature prive di geometria sono relegate in fondo con valore ``None``.

    Raises:
        ValueError: se la modalità non è valida o la linea di riferimento è vuota.
    """
    if mode not in LINE_DISTANCE_MODES:
        raise ValueError(f"Modalità sconosciuta: '{mode}'. "
                         f"Valori ammessi: {list(LINE_DISTANCE_MODES.keys())}")
    if _is_empty_geom(line_geometry):
        raise ValueError("La geometria della linea di riferimento è assente o vuota.")

    valid = []        # (dist, idx, feat) – idx stabilizza i pari-distanza
    invalid = []
    total = len(features)

    for i, f in enumerate(features):
        geom = f.geometry()
        if _is_empty_geom(geom):
            invalid.append(f)
            continue

        src = geom.centroid() if mode == "centroid" else geom
        if distance_area is not None:
            # Segmento più breve feature↔linea, misurato sull'ellissoide.
            dist = distance_area.measureLength(src.shortestLine(line_geometry))
        else:
            dist = src.distance(line_geometry)
        valid.append((dist, i, f))

        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    valid.sort(reverse=not ascending)
    sorted_feats = [f for _, _, f in valid] + invalid
    values = [v for v, _, _ in valid] + [None] * len(invalid)

    if progress_callback:
        progress_callback(100)

    return sorted_feats, values


# ──────────────────────────────────────────────────────────────────────────────
# Ordinamento multi-criterio (gerarchico)
# ──────────────────────────────────────────────────────────────────────────────

def _numeric_extractor(key, spec, distance_area=None):
    """Restituisce una funzione ``feat -> float | None`` per i criteri geometrici.

    Le feature prive di geometria (o non compatibili/intersecanti) producono
    ``None`` e verranno relegate in fondo.

    Args:
        key (str): chiave di criterio numerico/geometrico.
        spec (dict): descrittore del criterio (vedi :func:`_multi_level`).
        distance_area (QgsDistanceArea | None): se fornito, i criteri geodetici
            (area/perimetro/lunghezza/centroid_dist/line_distance) sono misurati
            sull'ellissoide.

    Raises:
        ValueError: criterio sconosciuto o linea di riferimento mancante.
    """
    if key in ("centroid_x", "centroid_y", "centroid_dist"):
        axis = {"centroid_x": "x", "centroid_y": "y", "centroid_dist": "dist"}[key]
        ref = spec.get("ref_point")

        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            pt = (geom.pointOnSurface() if geom.isMultipart() else geom.centroid()).asPoint()
            if axis == "dist" and ref is not None:
                if distance_area is not None:
                    return distance_area.measureLine(pt, ref)
                return math.sqrt((pt.x() - ref.x()) ** 2 + (pt.y() - ref.y()) ** 2)
            return pt.x() if axis == "x" else pt.y()
        return _ex

    if key in GEOM_CRITERIA:
        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            try:
                return _geom_value(f, key, distance_area)
            except ValueError:
                return None
        return _ex

    if key == "line_position":
        line = spec.get("line_geometry")
        mode = spec.get("mode", "centroid_projection")
        if _is_empty_geom(line):
            raise ValueError("Linea di riferimento assente o vuota.")

        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            if mode == "intersecting_first_pt":
                return _first_intersection_distance(line, geom)
            if mode == "intersecting_projection" and not line.intersects(geom):
                return None
            gt = QgsWkbTypes.geometryType(geom.wkbType())
            pt_geom = (QgsGeometry(geom)
                       if gt == QgsWkbTypes.GeometryType.PointGeometry
                       else geom.centroid())
            return line.lineLocatePoint(line.nearestPoint(pt_geom))
        return _ex

    if key == "line_distance":
        line = spec.get("line_geometry")
        mode = spec.get("mode", "element")
        if _is_empty_geom(line):
            raise ValueError("Linea di riferimento assente o vuota.")

        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            src = geom.centroid() if mode == "centroid" else geom
            if distance_area is not None:
                return distance_area.measureLength(src.shortestLine(line))
            return src.distance(line)
        return _ex

    raise ValueError(f"Criterio multi-livello sconosciuto: '{key}'.")


def _multi_level(features, spec, layer, distance_area=None):
    """Calcola, per un singolo livello, le chiavi di ordinamento e i valori grezzi.

    Args:
        features (list[QgsFeature]): feature in ordine originale.
        spec (dict): descrittore del criterio. Chiavi riconosciute:
            ``key`` (obbligatoria), ``ascending``, ``nulls_last``,
            ``natural_sort``, e parametri specifici del criterio
            (``field``, ``expression``, ``ref_point``, ``line_geometry``, ``mode``).
        layer (QgsVectorLayer | None): necessario per i criteri a espressione.

    Returns:
        tuple[list, bool, list]: (chiavi allineate a ``features``, reverse, valori grezzi).
    """
    key = spec["key"]
    ascending = spec.get("ascending", True)
    nulls_last = spec.get("nulls_last", True)
    natural = spec.get("natural_sort", False)
    null_priority = 1 if nulls_last else -1
    n = len(features)
    raw = [None] * n
    keys = [None] * n

    if key in ("attribute", "expression"):
        expr = None
        ctx = None
        if key == "expression":
            expr = QgsExpression(spec["expression"])
            if expr.hasParserError():
                raise ValueError(
                    f"Espressione non valida: {expr.parserErrorString()}"
                )
            ctx = QgsExpressionContext()
            ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        field = spec.get("field")

        for i, f in enumerate(features):
            if key == "attribute":
                val = f[field]
            else:
                ctx.setFeature(f)
                val = expr.evaluate(ctx)
                if expr.hasEvalError():
                    val = None
            is_null = val is None or val == NULL
            raw[i] = None if is_null else val
            if is_null:
                keys[i] = (null_priority, "")
            elif natural:
                keys[i] = (0, _natural_key(val))
            else:
                try:
                    keys[i] = (0, _normalize_val(val))
                except TypeError:
                    keys[i] = (0, str(val))
    else:
        extract = _numeric_extractor(key, spec, distance_area)
        for i, f in enumerate(features):
            v = extract(f)
            raw[i] = v
            keys[i] = (null_priority, 0.0) if v is None else (0, v)

    return keys, (not ascending), raw


def sort_multi(features, criteria, layer=None, progress_callback=None, distance_area=None):
    """Ordina le feature per più criteri in ordine di priorità (sort gerarchico).

    ``criteria[0]`` è il criterio primario; i successivi spezzano i pareggi.
    Ogni livello ha la propria direzione (``ascending``) e gestione dei NULL,
    coerente con le funzioni di ordinamento a singolo criterio.

    Tecnica: ordinamenti stabili successivi, dal criterio meno significativo al
    più significativo (Timsort è stabile), così ogni livello può avere direzione
    indipendente senza costruire una chiave composta a direzione mista.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        criteria (list[dict]): descrittori di criterio (vedi :func:`_multi_level`).
        layer (QgsVectorLayer | None): necessario se un livello usa un'espressione.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
        distance_area (QgsDistanceArea | None): se fornito, i criteri geodetici di
            ogni livello sono misurati sull'ellissoide. Vedi :func:`build_distance_area`.

    Returns:
        tuple[list[QgsFeature], list]: (feature ordinate, valori del criterio primario
        nello stesso ordine — utili come campo criterio opzionale).
    """
    features = list(features)
    n = len(features)
    if not criteria:
        return features, [None] * n

    levels = [_multi_level(features, spec, layer, distance_area) for spec in criteria]

    order = list(range(n))
    for keys, reverse, _raw in reversed(levels):
        order.sort(key=lambda idx, k=keys: k[idx], reverse=reverse)

    sorted_feats = [features[i] for i in order]
    primary_raw = levels[0][2]
    primary_values = [primary_raw[i] for i in order]

    if progress_callback:
        progress_callback(100)

    return sorted_feats, primary_values


# ──────────────────────────────────────────────────────────────────────────────
# Applicazione al layer
# ──────────────────────────────────────────────────────────────────────────────

def apply_sort_order(
    layer,
    sorted_features,
    add_criterion_field=False,
    criterion_values=None,
    criterion_field_name="sort_value",
    progress_callback=None,
):
    """Scrive il campo sort_order (e opzionalmente il campo criterio) sul layer.

    Avvia automaticamente una sessione di editing se il layer non è già in edit mode.

    Args:
        layer (QgsVectorLayer): layer di destinazione.
        sorted_features (list[QgsFeature]): feature nell'ordine desiderato.
        add_criterion_field (bool): se True aggiunge il campo con il valore del criterio.
        criterion_values (list | None): valori numerici corrispondenti a sorted_features.
        criterion_field_name (str): nome del campo criterio aggiuntivo.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        bool: True se riuscito, False in caso di errore.
    """
    try:
        was_editing = layer.isEditable()
        if not was_editing:
            if not layer.startEditing():
                QgsMessageLog.logMessage(
                    "Impossibile avviare la sessione di editing.", LOG_TAG, Qgis.MessageLevel.Critical
                )
                return False

        # ── Campo sort_order ──────────────────────────────────────────────────
        sort_idx = layer.fields().indexOf("sort_order")
        if sort_idx == -1:
            layer.addAttribute(QgsField("sort_order", QMetaType.Type.Int))
            layer.updateFields()
            sort_idx = layer.fields().indexOf("sort_order")

        # ── Campo criterio (opzionale) ────────────────────────────────────────
        crit_idx = -1
        crit_field_type = QMetaType.Type.Double
        if add_criterion_field and criterion_values:
            crit_idx = layer.fields().indexOf(criterion_field_name)
            if crit_idx == -1:
                crit_field_type = _infer_field_type(criterion_values)
                layer.addAttribute(QgsField(criterion_field_name, crit_field_type))
                layer.updateFields()
                crit_idx = layer.fields().indexOf(criterion_field_name)

        # ── Assegnazione valori ───────────────────────────────────────────────
        total = len(sorted_features)
        for i, feat in enumerate(sorted_features):
            fid = feat.id()
            layer.changeAttributeValue(fid, sort_idx, i + 1)
            if add_criterion_field and criterion_values and crit_idx != -1:
                val = _coerce_value(criterion_values[i], crit_field_type)
                layer.changeAttributeValue(fid, crit_idx, val)
            if progress_callback and i % 50 == 0:
                progress_callback(i * 100.0 / total)

        if not layer.commitChanges():
            layer.rollBack()
            QgsMessageLog.logMessage(
                "Errore nel commit delle modifiche.", LOG_TAG, Qgis.MessageLevel.Critical
            )
            return False

        if progress_callback:
            progress_callback(100)

        return True

    except Exception as exc:
        QgsMessageLog.logMessage(str(exc), LOG_TAG, Qgis.MessageLevel.Critical)
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
    progress_callback=None,
):
    """Crea un nuovo layer in memoria con le feature ordinate e il campo sort_order.

    Args:
        source_layer (QgsVectorLayer): layer sorgente (per CRS, tipo geometria, campi).
        sorted_features (list[QgsFeature]): feature nell'ordine desiderato.
        add_criterion_field (bool): se True aggiunge il campo con il valore del criterio.
        criterion_values (list | None): valori numerici corrispondenti a sorted_features.
        criterion_field_name (str): nome del campo criterio aggiuntivo.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        QgsVectorLayer: nuovo layer in memoria con 'sort_order' aggiunto.
    """
    geom_type_str = QgsWkbTypes.displayString(source_layer.wkbType())
    crs_auth = source_layer.crs().authid()
    uri = f"{geom_type_str}?crs={crs_auth}"

    mem_layer = QgsVectorLayer(uri, "GeoSort_output", "memory")
    provider = mem_layer.dataProvider()

    original_fields = source_layer.fields().toList()
    new_fields = original_fields + [QgsField("sort_order", QMetaType.Type.Int)]
    crit_field_type = QMetaType.Type.Double
    if add_criterion_field and criterion_values:
        crit_field_type = _infer_field_type(criterion_values)
        new_fields.append(QgsField(criterion_field_name, crit_field_type))

    provider.addAttributes(new_fields)
    mem_layer.updateFields()

    total = len(sorted_features)
    out_features = []
    for i, feat in enumerate(sorted_features):
        new_feat = QgsFeature(mem_layer.fields())
        new_feat.setGeometry(feat.geometry())
        for field in original_fields:
            new_feat[field.name()] = feat[field.name()]
        new_feat["sort_order"] = i + 1
        if add_criterion_field and criterion_values:
            new_feat[criterion_field_name] = _coerce_value(
                criterion_values[i], crit_field_type
            )
        out_features.append(new_feat)
        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    provider.addFeatures(out_features)
    mem_layer.updateExtents()

    if progress_callback:
        progress_callback(100)

    return mem_layer
