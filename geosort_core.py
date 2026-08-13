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
from qgis.PyQt.QtCore import QMetaType, Qt, QCoreApplication


def _tr(text):
    """Traduce una stringa nel contesto 'GeoSort' (QtCore, nessuna dipendenza UI)."""
    return QCoreApplication.translate("GeoSort", text)

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
        return _tr(
            "CRS geografico ({authid}): misura ellissoidica (geodetica) applicata automaticamente. "
            "I valori del criterio sono in metri/m² sull'ellissoide {ellipsoid}, non in gradi."
        ).format(authid=authid, ellipsoid=ellipsoid)
    if criterion in GEODESIC_CRITERIA:
        return _tr(
            "CRS geografico ({authid}): i valori di '{criterion}' sono calcolati in gradi "
            "e l'ordinamento può risultare distorto alle diverse latitudini. "
            "Attiva la misura geodetica o riproietta in un CRS proiettato (metrico)."
        ).format(authid=authid, criterion=criterion)
    # bbox_* : nessun equivalente ellissoidico (concetto in coordinate native).
    return _tr(
        "CRS geografico ({authid}): '{criterion}' è calcolato in gradi (concetto planare "
        "in coordinate native). Per misure metriche riproietta in un CRS proiettato."
    ).format(authid=authid, criterion=criterion)


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


def _comparable_key(val):
    """Chiave di ordinamento sempre confrontabile, anche con tipi eterogenei.

    I numeri (bool inclusi) vengono prima delle stringhe; date/ora sono già
    normalizzate in ISO-8601 da :func:`_normalize_val` e confrontate come
    stringhe. Evita il ``TypeError`` di ``sorted()`` quando un campo o
    un'espressione restituisce tipi misti (es. a volte numeri, a volte testo).
    """
    v = _normalize_val(val)
    if isinstance(v, (bool, int, float)):
        return (0, float(v), "")
    return (1, 0.0, str(v))


def _null_priority(nulls_last, ascending):
    """Priorità di ordinamento dei NULL, compensata per la direzione.

    ``sorted(..., reverse=True)`` invertirebbe anche la posizione dei NULL:
    la compensazione garantisce che ``nulls_last`` valga a prescindere dalla
    direzione di ordinamento.
    """
    priority = 1 if nulls_last else -1
    return priority if ascending else -priority


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
        nulls_last (bool): True = NULL in fondo; False = NULL in cima
            (indipendentemente dalla direzione di ordinamento).
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        list[QgsFeature]: lista ordinata.
    """
    null_priority = _null_priority(nulls_last, ascending)
    total = len(features)
    # Risolve l'indice del campo una sola volta: f[idx] evita di ririsolvere
    # il nome ad ogni accesso durante l'ordinamento (misurabile su layer grandi).
    # Se il campo non esiste, ricade su f[field] cosi' l'errore resta lo stesso.
    idx = features[0].fields().indexOf(field) if features else -1
    use_idx = idx != -1

    def key(f):
        val = f[idx] if use_idx else f[field]
        is_null = val is None or val == NULL
        if is_null:
            return (null_priority, [])
        if natural_sort:
            return (0, _natural_key(val))
        return (0, _comparable_key(val))

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
        nulls_last (bool): True = NULL/errori in fondo; False = in cima
            (indipendentemente dalla direzione di ordinamento).
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
            _tr("Espressione non valida: {error}\nEspressione: {expr}")
            .format(error=expr.parserErrorString(), expr=expression_str)
        )

    # Contesto base: variabili di progetto + campi del layer
    context = _expression_context(layer)

    null_priority = _null_priority(nulls_last, ascending)
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
        return (0, _comparable_key(val))

    pairs.sort(key=sort_key, reverse=not ascending)
    sorted_feats = [p[0] for p in pairs]
    values       = [p[1] for p in pairs]

    if progress_callback:
        progress_callback(100)

    return sorted_feats, values, warnings

def _expression_context(layer):
    """Contesto di valutazione per le espressioni QGIS.

    Con ``layer`` include variabili globali, di progetto e di layer; senza
    (``None``, es. sorgente Processing non riconducibile a un layer) ricade
    sul solo scope globale — i riferimenti ai campi si risolvono comunque
    dalla feature impostata con ``setFeature``.
    """
    context = QgsExpressionContext()
    if layer is not None:
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
    else:
        context.appendScope(QgsExpressionContextUtils.globalScope())
    return context


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
# Ordinamento per curva di Hilbert (ordinamento spaziale)
# ──────────────────────────────────────────────────────────────────────────────

def _hilbert_index(order, x, y):
    """Indice (distanza) lungo la curva di Hilbert del punto intero ``(x, y)``.

    Implementazione standard ``xy2d`` (curva di Hilbert, algoritmo iterativo):
    ``x`` e ``y`` devono essere interi in ``[0, 2**order - 1]``. Costo O(order),
    trascurabile anche per ordini elevati.

    Args:
        order (int): ordine della curva (lato griglia = ``2**order``).
        x (int): coordinata X discretizzata.
        y (int): coordinata Y discretizzata.

    Returns:
        int: indice lungo la curva (0 .. 2**(2*order) - 1).
    """
    n = 1 << order
    d = 0
    s = n >> 1
    while s > 0:
        rx = 1 if (x & s) > 0 else 0
        ry = 1 if (y & s) > 0 else 0
        d += s * s * ((3 * rx) ^ ry)
        # Ruota/riflette il quadrante corrente (stessa logica della funzione
        # rot() di riferimento): allinea la sotto-griglia successiva
        # all'orientamento della curva.
        if ry == 0:
            if rx == 1:
                x = n - 1 - x
                y = n - 1 - y
            x, y = y, x
        s >>= 1
    return d


def sort_by_hilbert(features, ascending=True, order=16, progress_callback=None):
    """Ordina le feature lungo una curva di Hilbert calcolata sui centroidi.

    Le feature vicine nello spazio diventano vicine nell'ordine di uscita: è il
    criterio "mancante" nella maggior parte degli strumenti di ordinamento di
    QGIS, utile per atlanti a percorso continuo (nessun salto tra pagine
    consecutive) e per scrivere GeoPackage con feature spazialmente coerenti
    (letture più veloci, perché le feature vicine finiscono vicine anche sul
    disco).

    Le coordinate del centroide (``pointOnSurface`` per le geometrie
    multiparte, così il punto rappresentativo resta sempre dentro la
    geometria) sono normalizzate sul bounding box complessivo delle feature
    valide e discretizzate su una griglia di lato ``2**order`` prima di
    calcolare l'indice di Hilbert.

    Args:
        features (list[QgsFeature]): feature da ordinare.
        ascending (bool): True = crescente (percorso "in avanti" lungo la curva).
        order (int): ordine della curva (lato griglia = 2**order, default 16
            → griglia 65536×65536). Un ordine più alto aumenta la risoluzione
            spaziale; il costo per feature resta O(order).
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.

    Returns:
        tuple[list[QgsFeature], list[int]]: (feature ordinate, indici di Hilbert).
        Le feature prive di geometria sono relegate in fondo con valore ``None``.
    """
    pts = []
    invalid = []
    for f in features:
        geom = f.geometry()
        if _is_empty_geom(geom):
            invalid.append(f)
            continue
        pt = (geom.pointOnSurface() if geom.isMultipart() else geom.centroid()).asPoint()
        pts.append((f, pt.x(), pt.y()))

    if not pts:
        if progress_callback:
            progress_callback(100)
        return invalid, [None] * len(invalid)

    xs = [p[1] for p in pts]
    ys = [p[2] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    # Extent degenere (una sola X o Y, es. tutti i punti allineati): evita la
    # divisione per zero, tutte le feature finiscono sullo stesso bordo della griglia.
    xspan = (xmax - xmin) or 1.0
    yspan = (ymax - ymin) or 1.0

    side = (1 << order) - 1
    valid = []
    for f, x, y in pts:
        gx = int((x - xmin) / xspan * side)
        gy = int((y - ymin) / yspan * side)
        valid.append((f, _hilbert_index(order, gx, gy)))

    valid.sort(key=lambda p: p[1], reverse=not ascending)
    sorted_feats = [p[0] for p in valid] + invalid
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
                _tr("Criterio 'area' richiede geometrie poligonali, trovato: {type}.")
                .format(type=type_name)
            )
        return distance_area.measureArea(geom) if distance_area else geom.area()

    elif criterion == "perimeter":
        if geom_type != QgsWkbTypes.GeometryType.PolygonGeometry:
            raise ValueError(
                _tr("Criterio 'perimeter' richiede geometrie poligonali, trovato: {type}.")
                .format(type=type_name)
            )
        return distance_area.measurePerimeter(geom) if distance_area else geom.length()

    elif criterion == "length":
        if geom_type != QgsWkbTypes.GeometryType.LineGeometry:
            raise ValueError(
                _tr("Criterio 'length' richiede geometrie lineari, trovato: {type}.")
                .format(type=type_name)
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
        raise ValueError(_tr("Criterio sconosciuto: '{criterion}'.").format(criterion=criterion))


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


def _intersection_extremal_points(geom):
    """Punti candidati per la distanza curvilinea minima di un'intersezione con una linea.

    L'intersezione fra la linea di riferimento e una feature giace, per
    costruzione, sulla linea stessa: lungo ciascuna parte lineare
    dell'intersezione la distanza curvilinea è quindi monotona, e basta
    valutarne i due estremi invece di tutti i vertici intermedi (a differenza
    di :func:`_extract_points_from_geometry`, pensata per geometrie qualsiasi).
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
        parts = geom.asMultiPolyline() if geom.isMultipart() else [geom.asPolyline()]
        for part in parts:
            if not part:
                continue
            pts.append(QgsGeometry.fromPointXY(QgsPointXY(part[0].x(), part[0].y())))
            if len(part) > 1:
                last = part[-1]
                pts.append(QgsGeometry.fromPointXY(QgsPointXY(last.x(), last.y())))

    elif geom_type == QgsWkbTypes.GeometryType.PolygonGeometry:
        pts.append(geom.centroid())

    else:
        for i in range(geom.constGet().numGeometries()):
            sub = QgsGeometry(geom.constGet().geometryN(i).clone())
            pts.extend(_intersection_extremal_points(sub))

    return pts


def _first_intersection_distance(line_geom, feature_geom, line_engine=None, locate=None):
    """Distanza lungo ``line_geom`` del *primo* punto di intersezione con ``feature_geom``.

    "Primo" = minore distanza curvilinea dall'inizio della linea.

    Args:
        line_geom (QgsGeometry): linea di riferimento.
        feature_geom (QgsGeometry): geometria della feature.
        line_engine (QgsGeometryEngine | None): motore GEOS preparato su
            ``line_geom`` (vedi :func:`sort_by_line_position`); se fornito,
            evita di riconvertire la linea in GEOS ad ogni chiamata.
        locate (callable | None): funzione ``pt_geom -> float`` (vedi
            :func:`_make_line_locator`); se assente, ricade su
            ``line_geom.lineLocatePoint``.

    Returns:
        float | None: distanza in unità mappa, o None se non c'è intersezione.
    """
    if line_engine is not None:
        raw = line_engine.intersection(feature_geom.constGet())
        intersection = QgsGeometry(raw) if raw is not None else None
    else:
        intersection = line_geom.intersection(feature_geom)
    if intersection is None or intersection.isEmpty():
        return None

    points = _intersection_extremal_points(intersection)
    if not points:
        return None

    _locate = locate or line_geom.lineLocatePoint
    distances = []
    for pt in points:
        try:
            distances.append(_locate(pt))
        except Exception:
            pass

    return min(distances) if distances else None


def _make_line_locator(line_geometry, line_engine):
    """Funzione ``pt_geom -> float``: distanza curvilinea del punto sulla linea.

    Se il binding lo consente, usa ``QgsGeos.lineLocatePoint`` sul motore
    preparato (una sola conversione GEOS della linea, riusata per tutte le
    feature). In caso contrario, o per punti multiparte, ricade sulla coppia
    ``nearestPoint`` + ``lineLocatePoint`` di :class:`QgsGeometry`.
    """
    engine_locate = getattr(line_engine, "lineLocatePoint", None)

    def _locate(pt_geom):
        if engine_locate is not None and not pt_geom.isMultipart():
            res = engine_locate(pt_geom.constGet())
            # Il binding può restituire float oppure (float, msg_errore)
            return res[0] if isinstance(res, tuple) else res
        nearest = line_geometry.nearestPoint(pt_geom)
        return line_geometry.lineLocatePoint(nearest)

    return _locate


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
        raise ValueError(_tr("La geometria della linea di riferimento è assente o vuota."))

    # Motore geometrico preparato sulla linea: i predicati di intersezione
    # ripetuti evitano di riconvertire la linea in GEOS a ogni feature
    # (determinante quando la linea di riferimento ha molti vertici).
    line_engine = QgsGeometry.createGeometryEngine(line_geometry.constGet())
    line_engine.prepareGeometry()
    _locate = _make_line_locator(line_geometry, line_engine)

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
            sorted_feats.append(f)
            values.append(_locate(pt_geom))

        elif mode == "intersecting_projection":
            # Solo feature che intersecano fisicamente la linea
            if not line_engine.intersects(geom.constGet()):
                excluded.append(f)
                continue
            sorted_feats.append(f)
            values.append(_locate(pt_geom))

        elif mode == "intersecting_first_pt":
            # Solo feature che intersecano; usa il primo punto di intersezione.
            # Il predicato preparato evita l'intersezione GEOS (costosa) per le
            # feature che non toccano la linea.
            dist = (_first_intersection_distance(line_geometry, geom, line_engine, _locate)
                    if line_engine.intersects(geom.constGet()) else None)
            if dist is None:
                excluded.append(f)
                continue
            sorted_feats.append(f)
            values.append(dist)

        else:
            raise ValueError(
                _tr("Modalità sconosciuta: '{mode}'. Valori ammessi: {valid}")
                .format(mode=mode, valid=list(LINE_MODES.keys())))

        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    # Ordina per distanza mantenendo l'associazione con i valori.
    # key= evita che i pareggi di distanza confrontino i QgsFeature (TypeError).
    paired = sorted(zip(values, sorted_feats), key=lambda p: p[0],
                    reverse=not ascending)
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
        raise ValueError(
            _tr("Modalità sconosciuta: '{mode}'. Valori ammessi: {valid}")
            .format(mode=mode, valid=list(LINE_DISTANCE_MODES.keys())))
    if _is_empty_geom(line_geometry):
        raise ValueError(_tr("La geometria della linea di riferimento è assente o vuota."))

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
            raise ValueError(_tr("Linea di riferimento assente o vuota."))
        line_engine = QgsGeometry.createGeometryEngine(line.constGet())
        line_engine.prepareGeometry()
        _locate = _make_line_locator(line, line_engine)

        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            if mode == "intersecting_first_pt":
                if not line_engine.intersects(geom.constGet()):
                    return None
                return _first_intersection_distance(line, geom, line_engine, _locate)
            if mode == "intersecting_projection" and not line_engine.intersects(geom.constGet()):
                return None
            gt = QgsWkbTypes.geometryType(geom.wkbType())
            pt_geom = (QgsGeometry(geom)
                       if gt == QgsWkbTypes.GeometryType.PointGeometry
                       else geom.centroid())
            return _locate(pt_geom)
        return _ex

    if key == "line_distance":
        line = spec.get("line_geometry")
        mode = spec.get("mode", "element")
        if _is_empty_geom(line):
            raise ValueError(_tr("Linea di riferimento assente o vuota."))

        def _ex(f):
            geom = f.geometry()
            if _is_empty_geom(geom):
                return None
            src = geom.centroid() if mode == "centroid" else geom
            if distance_area is not None:
                return distance_area.measureLength(src.shortestLine(line))
            return src.distance(line)
        return _ex

    raise ValueError(_tr("Criterio multi-livello sconosciuto: '{key}'.").format(key=key))


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
    null_priority = _null_priority(nulls_last, ascending)
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
                    _tr("Espressione non valida: {error}")
                    .format(error=expr.parserErrorString())
                )
            ctx = _expression_context(layer)
        field = spec.get("field")
        # Vedi sort_by_attribute: risolve l'indice del campo una sola volta.
        idx = features[0].fields().indexOf(field) if (key == "attribute" and features) else -1
        use_idx = idx != -1

        for i, f in enumerate(features):
            if key == "attribute":
                val = f[idx] if use_idx else f[field]
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
                keys[i] = (0, _comparable_key(val))
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
    start=1,
    step=1,
    order_field_name="sort_order",
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
        start (int): valore iniziale della numerazione (default 1).
        step (int): incremento fra feature consecutive (default 1).
        order_field_name (str): nome del campo progressivo (default "sort_order").

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
        sort_idx = layer.fields().indexOf(order_field_name)
        if sort_idx == -1:
            layer.addAttribute(QgsField(order_field_name, QMetaType.Type.Int))
            layer.updateFields()
            sort_idx = layer.fields().indexOf(order_field_name)

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
        write_crit = add_criterion_field and criterion_values and crit_idx != -1
        # beginEditCommand/endEditCommand raggruppa tutte le changeAttributeValues
        # in un unico blocco di undo (altrimenti ogni feature sarebbe uno step
        # separato: su layer grandi, migliaia di Ctrl+Z per annullare l'ordinamento).
        # "GeoSort" è il nome del plugin (compare nel menu Undo di QGIS): un nome
        # proprio, identico in ogni lingua, non va tradotto con _tr().
        layer.beginEditCommand("GeoSort")
        try:
            for i, feat in enumerate(sorted_features):
                changes = {sort_idx: start + i * step}
                if write_crit:
                    changes[crit_idx] = _coerce_value(criterion_values[i], crit_field_type)
                layer.changeAttributeValues(feat.id(), changes)
                if progress_callback and i % 50 == 0:
                    progress_callback(i * 100.0 / total)
        except Exception:
            layer.destroyEditCommand()
            raise
        layer.endEditCommand()

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
    start=1,
    step=1,
    order_field_name="sort_order",
):
    """Crea un nuovo layer in memoria con le feature ordinate e il campo sort_order.

    Se il layer sorgente contiene già un campo ``order_field_name``, il campo
    esistente viene riutilizzato (i valori sono sovrascritti) invece di
    aggiungerne un duplicato.

    Args:
        source_layer (QgsVectorLayer): layer sorgente (per CRS, tipo geometria, campi).
        sorted_features (list[QgsFeature]): feature nell'ordine desiderato.
        add_criterion_field (bool): se True aggiunge il campo con il valore del criterio.
        criterion_values (list | None): valori numerici corrispondenti a sorted_features.
        criterion_field_name (str): nome del campo criterio aggiuntivo.
        progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
        start (int): valore iniziale della numerazione (default 1).
        step (int): incremento fra feature consecutive (default 1).
        order_field_name (str): nome del campo progressivo (default "sort_order").

    Returns:
        QgsVectorLayer: nuovo layer in memoria con 'sort_order' aggiunto.
    """
    geom_type_str = QgsWkbTypes.displayString(source_layer.wkbType())
    crs_auth = source_layer.crs().authid()
    uri = f"{geom_type_str}?crs={crs_auth}"

    mem_layer = QgsVectorLayer(uri, "GeoSort_output", "memory")
    provider = mem_layer.dataProvider()

    original_fields = source_layer.fields().toList()
    order_idx = source_layer.fields().indexOf(order_field_name)
    new_fields = list(original_fields)
    if order_idx == -1:
        new_fields.append(QgsField(order_field_name, QMetaType.Type.Int))
    crit_field_type = QMetaType.Type.Double
    if add_criterion_field and criterion_values:
        crit_field_type = _infer_field_type(criterion_values)
        new_fields.append(QgsField(criterion_field_name, crit_field_type))

    provider.addAttributes(new_fields)
    mem_layer.updateFields()

    total = len(sorted_features)
    out_features = []
    write_crit = add_criterion_field and criterion_values
    for i, feat in enumerate(sorted_features):
        new_feat = QgsFeature(mem_layer.fields())
        new_feat.setGeometry(feat.geometry())
        # setAttributes: una sola chiamata invece di un lookup per nome per campo
        order_value = start + i * step
        attrs = list(feat.attributes())
        if order_idx == -1:
            attrs.append(order_value)
        else:
            attrs[order_idx] = order_value
        if write_crit:
            attrs.append(_coerce_value(criterion_values[i], crit_field_type))
        new_feat.setAttributes(attrs)
        out_features.append(new_feat)
        if progress_callback and i % 50 == 0:
            progress_callback(i * 100.0 / total)

    provider.addFeatures(out_features)
    mem_layer.updateExtents()

    if progress_callback:
        progress_callback(100)

    return mem_layer
