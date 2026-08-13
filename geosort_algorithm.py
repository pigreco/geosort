# -*- coding: utf-8 -*-
"""
GeoSort – Processing Algorithm.
Compatibile con il Processing Toolbox, il modellatore grafico e PyQGIS headless.
"""

import os

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterExpression,
    QgsProcessingParameterPoint,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterDefinition,
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
    QgsCoordinateTransform,
    QgsCsException,
    QgsMessageLog,
    Qgis,
    NULL,
)
from qgis.PyQt.QtCore import QMetaType, QCoreApplication
from qgis.PyQt.QtGui import QIcon


# Mappa indice enum → modalità geodetica (stringa accettata da geosort_core)
_GEODESIC_MODES = ["auto", "always", "never"]

# Compatibilità del flag "Advanced" dei parametri Processing fra QGIS 3.16-3.34
# (Qt5, ``QgsProcessingParameterDefinition.FlagAdvanced``) e QGIS 3.36+/4.x
# (``Qgis.ProcessingParameterFlag.Advanced``).
try:
    _FLAG_ADVANCED = Qgis.ProcessingParameterFlag.Advanced
except AttributeError:
    _FLAG_ADVANCED = QgsProcessingParameterDefinition.FlagAdvanced

# Stessa compatibilità per il tipo numerico intero dei parametri Processing
# (QGIS 3.36+/4.x: ``Qgis.ProcessingNumberParameterType``; 3.16-3.34:
# ``QgsProcessingParameterNumber.Integer``).
try:
    _NUMBER_INTEGER = Qgis.ProcessingNumberParameterType.Integer
except AttributeError:
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Integer


class _Canceled(Exception):
    """Segnala che l'utente ha annullato l'esecuzione dal feedback di Processing."""


def _spec_from(key, field, expression, ascending, nulls_last, natural_sort,
               ref_point=None):
    """Costruisce un descrittore di criterio per ``geosort_core.sort_multi``.

    Supporta solo i criteri "semplici" (senza geometria di riferimento esterna):
    attributo, espressione, centroide X/Y/distanza-da-punto, proprietà geometriche.
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
        spec["ref_point"] = ref_point if ref_point is not None else QgsPointXY(0, 0)
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
    GEODESIC = "GEODESIC"
    REF_LAYER = "REF_LAYER"
    REF_POINT = "REF_POINT"
    HILBERT_ORDER = "HILBERT_ORDER"
    BAND_SIZE = "BAND_SIZE"
    BAND_AXIS = "BAND_AXIS"
    CROSS_ASCENDING = "CROSS_ASCENDING"
    ADD_VALUE_FIELD = "ADD_VALUE_FIELD"
    START = "START"
    STEP = "STEP"
    ORDER_FIELD = "ORDER_FIELD"
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
        "hilbert",
        "expression",
        "serpentine",
    ]

    # ── Criterio secondario (tie-break) per l'ordinamento multi-criterio ──
    SECONDARY_CRITERION = "SECONDARY_CRITERION"
    SECONDARY_FIELD = "SECONDARY_FIELD"
    SECONDARY_EXPRESSION = "SECONDARY_EXPRESSION"
    SECONDARY_DIRECTION = "SECONDARY_DIRECTION"

    # Criteri ammessi come primario in modalità multi-criterio (no linea: niente
    # geometria di riferimento esterna né semantica di esclusione; niente Hilbert
    # né serpentina: richiedono l'extent/le bande calcolate su tutte le feature,
    # non un valore per-feature indipendente come richiesto da _numeric_extractor).
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
        "Centroide – distanza da punto di riferimento (default 0,0)",
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
        "Curva di Hilbert (ordinamento spaziale)",
        "Espressione QGIS",
        "Serpentina (boustrophedon)",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # Metadati algoritmo
    # ──────────────────────────────────────────────────────────────────────────

    def tr(self, text):
        """Traduce una stringa nel contesto 'GeoSort'."""
        return QCoreApplication.translate("GeoSort", text)

    def name(self):
        return "geosort_sort"

    def displayName(self):
        return self.tr("Ordina feature (GeoSort)")

    def group(self):
        return "GeoSort"

    def groupId(self):
        return "geosort"

    def shortHelpString(self):
        return self.tr(
            "Ordina le feature di un layer vettoriale per criteri geometrici o attributivi "
            "e aggiunge il campo <b>sort_order</b> (numero progressivo, 1 = prima feature).\n\n"
            "Criteri disponibili: attributo tabellare, coordinate del centroide, "
            "area, lunghezza, perimetro, numero di vertici, bounding box, "
            "posizione lungo una linea di riferimento, distanza dalla linea di riferimento, "
            "curva di Hilbert (ordinamento spaziale), espressione QGIS, serpentina "
            "(boustrophedon, bande orizzontali o verticali).\n\n"
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
            "<b>Punto di riferimento:</b> per il criterio «Centroide – distanza» è possibile "
            "indicare un punto di riferimento (anche col pulsante «... sulla mappa»); "
            "se lasciato vuoto si usa l'origine (0,0) come nelle versioni precedenti.\n\n"
            "<b>Layer di riferimento (posizione/distanza lungo linea):</b> se il layer di "
            "riferimento ha un CRS diverso da quello del layer di input, viene riproiettato "
            "automaticamente prima del calcolo (con un avviso non bloccante).\n\n"
            "<b>Curva di Hilbert:</b> ordina le feature lungo una curva di Hilbert calcolata "
            "sui centroidi, normalizzati sull'extent complessivo del layer — le feature "
            "vicine nello spazio diventano vicine nell'ordine. Utile per atlanti a percorso "
            "continuo e per scrivere GeoPackage con feature spazialmente coerenti (letture "
            "più veloci). Il parametro avanzato <code>HILBERT_ORDER</code> regola la "
            "risoluzione della griglia (default 16, lato 2^16); non è disponibile come "
            "criterio primario in modalità multi-criterio.\n\n"
            "<b>Serpentina (boustrophedon):</b> ordina le feature a bande, con l'asse "
            "trasversale alternato crescente/decrescente da una banda alla successiva — "
            "l'ordine classico per numerare le tavole di una serie cartografica a taglio "
            "regolare o un percorso di volo fotogrammetrico, senza il salto lungo da fine "
            "banda a inizio banda successiva tipico di un ordinamento a righe semplice. "
            "Il parametro <code>BAND_AXIS</code> sceglie l'orientamento: bande orizzontali "
            "(per Y, X alternato — default) o verticali (per X, Y alternato). Il parametro "
            "avanzato <code>BAND_SIZE</code> imposta la dimensione di banda nelle unità del "
            "CRS — altezza per bande orizzontali, larghezza per verticali (0/vuoto = "
            "automatica, dalla dimensione media delle bounding box delle feature). Il "
            "parametro avanzato <code>CROSS_ASCENDING</code> sceglie l'angolo di partenza: "
            "con <code>DIRECTION</code> (quale banda è la prima) e <code>CROSS_ASCENDING</code> "
            "(verso dell'asse trasversale nella prima banda) sono raggiungibili tutti e "
            "quattro gli angoli della griglia. Non disponibile come criterio primario in "
            "modalità multi-criterio.\n\n"
            "<b>Numerazione personalizzata (parametri avanzati):</b> valore iniziale "
            "(es. 0), passo (es. 10 → 10, 20, 30...) e nome del campo progressivo "
            "(default <b>sort_order</b>). Se il campo esiste già nel layer di input, "
            "i suoi valori vengono sovrascritti invece di creare un duplicato.\n\n"
            "<b>Misura geodetica (ellissoidale):</b> quando il CRS del layer è geografico "
            "(coordinate in gradi, es. EPSG:4326), le misure planari di area, lunghezza, "
            "perimetro e distanza sarebbero in gradi — metricamente prive di senso. "
            "Con la modalità <i>Automatica</i> (default) GeoSort usa automaticamente il calcolo "
            "ellissoidale (QgsDistanceArea) restituendo valori in m² / m. "
            "Selezionare <i>Mai</i> per forzare la misura planare nelle unità del CRS.\n\n"
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
        # FeatureSource (non VectorLayer): abilita la spunta "Solo feature
        # selezionate" nel Processing e l'uso diretto di output intermedi
        # nel modellatore.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Layer di input"),
                types=[QgsProcessing.SourceType.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CRITERION,
                self.tr("Criterio di ordinamento"),
                options=[self.tr(s) for s in self._CRITERIA_LABELS],
                defaultValue=0,
            )
        )
        param_field = QgsProcessingParameterField(
            self.ATTRIBUTE_FIELD,
            self.tr("Campo attributo (solo per criterio 'Attributo tabellare')"),
            parentLayerParameterName=self.INPUT,
            optional=True,
        )
        self.addParameter(param_field)

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DIRECTION, self.tr("Ordine ascendente"), defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NULLS_LAST,
                self.tr("Valori NULL in fondo (solo per criterio attributo)"),
                defaultValue=True,
            )
        )
        # Natural Sort e misura geodetica sono condizionali (rilevanti solo per
        # alcuni criteri): marcati "Advanced" per non affollare la finestra
        # principale del Processing.
        param_natural_sort = QgsProcessingParameterBoolean(
            self.NATURAL_SORT,
            self.tr("Ordinamento naturale – Natural Sort (solo per criterio attributo/espressione)"),
            defaultValue=False,
        )
        param_natural_sort.setFlags(param_natural_sort.flags() | _FLAG_ADVANCED)
        self.addParameter(param_natural_sort)

        param_geodesic = QgsProcessingParameterEnum(
            self.GEODESIC,
            self.tr("Modalità di misura geodetica (per area/lunghezza/distanza)"),
            options=[
                self.tr("Automatica – geodetica su CRS geografico (consigliato)"),
                self.tr("Sempre geodetica"),
                self.tr("Mai (misura planare nelle unità del CRS)"),
            ],
            defaultValue=0,
        )
        param_geodesic.setFlags(param_geodesic.flags() | _FLAG_ADVANCED)
        self.addParameter(param_geodesic)

        param_ref = QgsProcessingParameterFeatureSource(
            self.REF_LAYER,
            self.tr("Layer linea di riferimento (solo per criteri 'Posizione/Distanza dalla linea')"),
            types=[QgsProcessing.SourceType.TypeVectorLine],
            optional=True,
        )
        self.addParameter(param_ref)

        # Punto di riferimento per il criterio "Centroide – distanza da punto".
        # Se non impostato si usa l'origine (0,0), come nelle versioni precedenti.
        param_ref_point = QgsProcessingParameterPoint(
            self.REF_POINT,
            self.tr("Punto di riferimento (solo per criterio 'Centroide – distanza'; vuoto = origine 0,0)"),
            optional=True,
        )
        self.addParameter(param_ref_point)

        # Modalità di calcolo per il criterio "Posizione lungo linea" (condizionale)
        param_line_mode = QgsProcessingParameterEnum(
            "LINE_MODE",
            self.tr("Modalità di calcolo – Posizione lungo linea"),
            options=[
                self.tr("Proiezione centroide  –  tutte le feature"),
                self.tr("Solo intersecanti –  proiezione centroide"),
                self.tr("Solo intersecanti –  primo punto di intersezione"),
            ],
            defaultValue=0,
        )
        param_line_mode.setFlags(param_line_mode.flags() | _FLAG_ADVANCED)
        self.addParameter(param_line_mode)

        # Modalità di calcolo per il criterio "Distanza dalla linea" (condizionale)
        param_line_dist_mode = QgsProcessingParameterEnum(
            "LINE_DISTANCE_MODE",
            self.tr("Modalità di calcolo – Distanza dalla linea"),
            options=[
                self.tr("Distanza dal centroide"),
                self.tr("Distanza dall'elemento"),
            ],
            defaultValue=1,
        )
        param_line_dist_mode.setFlags(param_line_dist_mode.flags() | _FLAG_ADVANCED)
        self.addParameter(param_line_dist_mode)

        # Ordine della curva (condizionale, solo per il criterio "Curva di Hilbert")
        param_hilbert_order = QgsProcessingParameterNumber(
            self.HILBERT_ORDER,
            self.tr("Curva di Hilbert – ordine (risoluzione griglia = 2^ordine)"),
            type=_NUMBER_INTEGER,
            defaultValue=16,
            minValue=1,
            maxValue=24,
        )
        param_hilbert_order.setFlags(param_hilbert_order.flags() | _FLAG_ADVANCED)
        self.addParameter(param_hilbert_order)

        # Orientamento bande (condizionale, solo per il criterio "Serpentina").
        param_band_axis = QgsProcessingParameterEnum(
            self.BAND_AXIS,
            self.tr("Serpentina – orientamento bande"),
            options=[
                self.tr("Orizzontali (bande per Y, X alternato)"),
                self.tr("Verticali (bande per X, Y alternato)"),
            ],
            defaultValue=0,
        )
        param_band_axis.setFlags(param_band_axis.flags() | _FLAG_ADVANCED)
        self.addParameter(param_band_axis)

        # Dimensione banda (condizionale, solo per il criterio "Serpentina"). 0/vuoto
        # → calcolata automaticamente dalla dimensione media delle bbox delle feature
        # (altezza per bande orizzontali, larghezza per verticali).
        param_band_size = QgsProcessingParameterNumber(
            self.BAND_SIZE,
            self.tr(
                "Serpentina – dimensione banda, unità del CRS (0 = automatica, "
                "da altezza/larghezza media delle feature)"
            ),
            defaultValue=0.0,
            minValue=0.0,
            optional=True,
        )
        param_band_size.setFlags(param_band_size.flags() | _FLAG_ADVANCED)
        self.addParameter(param_band_size)

        # Verso dell'asse trasversale nella prima banda percorsa (condizionale,
        # solo per il criterio "Serpentina"): combinato con DIRECTION (quale
        # banda è la prima) permette di scegliere uno qualunque dei quattro
        # angoli di partenza della griglia.
        param_cross_ascending = QgsProcessingParameterBoolean(
            self.CROSS_ASCENDING,
            self.tr("Serpentina – prima banda in verso crescente (altrimenti decrescente)"),
            defaultValue=True,
        )
        param_cross_ascending.setFlags(param_cross_ascending.flags() | _FLAG_ADVANCED)
        self.addParameter(param_cross_ascending)

        self.addParameter(
            QgsProcessingParameterExpression(
                "EXPRESSION",
                self.tr("Espressione QGIS (solo per criterio 'Espressione QGIS')"),
                defaultValue="",
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )

        # ── Criterio secondario (tie-break) – ordinamento multi-criterio ──
        # Tutti condizionali (rilevanti solo se si imposta un criterio secondario).
        param_sec_crit = QgsProcessingParameterEnum(
            self.SECONDARY_CRITERION,
            self.tr("Criterio secondario per i pareggi (opzionale)"),
            options=[self.tr(s) for s in self._SECONDARY_LABELS],
            defaultValue=0,
        )
        param_sec_crit.setFlags(param_sec_crit.flags() | _FLAG_ADVANCED)
        self.addParameter(param_sec_crit)

        param_sec_field = QgsProcessingParameterField(
            self.SECONDARY_FIELD,
            self.tr("Campo del criterio secondario (solo se 'Attributo tabellare')"),
            parentLayerParameterName=self.INPUT,
            optional=True,
        )
        param_sec_field.setFlags(param_sec_field.flags() | _FLAG_ADVANCED)
        self.addParameter(param_sec_field)

        param_sec_expr = QgsProcessingParameterExpression(
            self.SECONDARY_EXPRESSION,
            self.tr("Espressione del criterio secondario (solo se 'Espressione QGIS')"),
            defaultValue="",
            parentLayerParameterName=self.INPUT,
            optional=True,
        )
        param_sec_expr.setFlags(param_sec_expr.flags() | _FLAG_ADVANCED)
        self.addParameter(param_sec_expr)

        param_sec_dir = QgsProcessingParameterBoolean(
            self.SECONDARY_DIRECTION,
            self.tr("Criterio secondario: ordine ascendente"),
            defaultValue=True,
        )
        param_sec_dir.setFlags(param_sec_dir.flags() | _FLAG_ADVANCED)
        self.addParameter(param_sec_dir)

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_VALUE_FIELD,
                self.tr("Aggiungi campo con il valore del criterio (sort_value)"),
                defaultValue=False,
            )
        )

        # ── Numerazione del campo progressivo (avanzati) ──────────────────────
        param_start = QgsProcessingParameterNumber(
            self.START,
            self.tr("Numerazione: valore iniziale"),
            type=_NUMBER_INTEGER,
            defaultValue=1,
        )
        param_start.setFlags(param_start.flags() | _FLAG_ADVANCED)
        self.addParameter(param_start)

        param_step = QgsProcessingParameterNumber(
            self.STEP,
            self.tr("Numerazione: passo (incremento fra feature)"),
            type=_NUMBER_INTEGER,
            defaultValue=1,
            minValue=1,
        )
        param_step.setFlags(param_step.flags() | _FLAG_ADVANCED)
        self.addParameter(param_step)

        param_order_field = QgsProcessingParameterString(
            self.ORDER_FIELD,
            self.tr("Nome del campo progressivo"),
            defaultValue="sort_order",
            optional=True,
        )
        param_order_field.setFlags(param_order_field.flags() | _FLAG_ADVANCED)
        self.addParameter(param_order_field)

        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Layer ordinato"))
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Esecuzione
    # ──────────────────────────────────────────────────────────────────────────

    def _ref_point_from(self, parameters, context, crs):
        """Punto di riferimento per 'centroid_dist': REF_POINT o origine (0,0).

        Il punto è riproiettato nel CRS della sorgente da ``parameterAsPoint``.
        """
        raw = parameters.get(self.REF_POINT)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return QgsPointXY(0, 0)
        return self.parameterAsPoint(parameters, self.REF_POINT, context, crs)

    def _ref_line_geom(self, parameters, context, feedback, target_crs, no_layer_message):
        """Geometria unificata del REF_LAYER (line_position / line_distance),
        riproiettata nel CRS ``target_crs`` (quello del layer di input) se il
        layer di riferimento ha un CRS diverso.

        A differenza di REF_POINT — dove ``parameterAsPoint(..., crs)`` riproietta
        automaticamente — QgsProcessingParameterFeatureSource non offre un
        equivalente: la trasformazione va applicata esplicitamente, altrimenti
        geometrie in CRS differenti verrebbero confrontate come se fossero nello
        stesso sistema di coordinate (risultati silenziosamente sbagliati, fino a
        NaN se i due CRS divergono molto, es. gradi vs proiezione metrica).

        Args:
            no_layer_message (str): messaggio d'errore (già tradotto) se
                REF_LAYER non è impostato — specifico per criterio, per un
                messaggio d'errore più chiaro.
        """
        ref_source = self.parameterAsSource(parameters, self.REF_LAYER, context)
        if ref_source is None:
            raise QgsProcessingException(no_layer_message)
        ref_feats = list(ref_source.getFeatures())
        if not ref_feats:
            raise QgsProcessingException(self.tr("Il layer di riferimento non contiene feature."))
        line_geom = QgsGeometry.unaryUnion([f.geometry() for f in ref_feats])

        ref_crs = ref_source.sourceCrs()
        if ref_crs.isValid() and target_crs.isValid() and ref_crs != target_crs:
            transform = QgsCoordinateTransform(ref_crs, target_crs, context.transformContext())
            try:
                line_geom.transform(transform)
            except QgsCsException as exc:
                raise QgsProcessingException(self.tr(
                    "Impossibile riproiettare il layer di riferimento dal CRS {ref} "
                    "al CRS {target} del layer di input: {error}"
                ).format(ref=ref_crs.authid(), target=target_crs.authid(), error=str(exc)))
            feedback.pushInfo(self.tr(
                "GeoSort: layer di riferimento riproiettato da {ref} a {target} "
                "(CRS del layer di input)."
            ).format(ref=ref_crs.authid(), target=target_crs.authid()))

        return line_geom

    def _run_multi(self, parameters, context, feedback, crs, expr_layer, features,
                   primary_key, sec_key, ascending, nulls_last, natural_sort,
                   geodesic_mode="auto", progress_callback=None):
        """Esegue l'ordinamento gerarchico (primario + secondario) via sort_multi.

        Args:
            crs (QgsCoordinateReferenceSystem): CRS della sorgente.
            expr_layer (QgsVectorLayer | None): layer per il contesto delle
                espressioni (None se la sorgente non è un layer di progetto).
            geodesic_mode (str): modalità geodetica ("auto" | "always" | "never").
            progress_callback (callable | None): vedi :func:`processAlgorithm`.

        Returns:
            tuple[list, list, list]: (feature ordinate, valori primario, escluse=[]).
        """
        from .geosort_core import sort_multi, build_distance_area, should_build_distance_area

        primary_field = self.parameterAsString(parameters, self.ATTRIBUTE_FIELD, context)
        primary_expr = self.parameterAsExpression(parameters, "EXPRESSION", context)
        if primary_key == "attribute" and not primary_field:
            raise QgsProcessingException(
                self.tr("Specificare un campo attributo per il criterio primario.")
            )
        if primary_key == "expression" and not (primary_expr and primary_expr.strip()):
            raise QgsProcessingException(
                self.tr("Specificare un'espressione per il criterio primario.")
            )
        primary_spec = _spec_from(
            primary_key, primary_field, primary_expr, ascending, nulls_last, natural_sort,
            ref_point=self._ref_point_from(parameters, context, crs),
        )

        sec_field = self.parameterAsString(parameters, self.SECONDARY_FIELD, context)
        sec_expr = self.parameterAsExpression(parameters, self.SECONDARY_EXPRESSION, context)
        sec_asc = self.parameterAsBoolean(parameters, self.SECONDARY_DIRECTION, context)
        if sec_key == "attribute" and not sec_field:
            raise QgsProcessingException(
                self.tr("Specificare un campo per il criterio secondario.")
            )
        if sec_key == "expression" and not (sec_expr and sec_expr.strip()):
            raise QgsProcessingException(
                self.tr("Specificare un'espressione per il criterio secondario.")
            )
        secondary_spec = _spec_from(
            sec_key, sec_field, sec_expr, sec_asc, nulls_last, natural_sort
        )

        # Costruisce il misuratore ellissoidale se almeno un criterio richiede geodesica
        da = None
        if should_build_distance_area(crs, geodesic_mode):
            da = build_distance_area(crs, context.transformContext())

        feedback.pushInfo(self.tr("GeoSort: ordinamento multi-criterio (primario + secondario)."))
        try:
            sorted_feats, values = sort_multi(
                features, [primary_spec, secondary_spec], expr_layer, distance_area=da,
                progress_callback=progress_callback,
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
            sort_by_hilbert,
            sort_by_serpentine,
            _infer_field_type,
            _coerce_value,
            build_distance_area,
            resolve_geodesic,
            geographic_crs_warning,
        )

        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.tr("Layer di input non trovato."))
        # Layer di progetto corrispondente (se esiste): serve solo al contesto
        # delle espressioni; feature, campi e CRS arrivano dalla sorgente.
        expr_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)

        crit_idx = self.parameterAsEnum(parameters, self.CRITERION, context)
        criterion = self._CRITERIA_KEYS[crit_idx]
        ascending = self.parameterAsBoolean(parameters, self.DIRECTION, context)
        nulls_last = self.parameterAsBoolean(parameters, self.NULLS_LAST, context)
        natural_sort = self.parameterAsBoolean(parameters, self.NATURAL_SORT, context)
        add_value = self.parameterAsBoolean(parameters, self.ADD_VALUE_FIELD, context)
        geodesic_mode = _GEODESIC_MODES[self.parameterAsEnum(parameters, self.GEODESIC, context)]
        crs = source.sourceCrs()
        source_fields = source.fields()

        feedback.setProgressText(self.tr("Caricamento feature..."))
        features = list(source.getFeatures())
        if not features:
            raise QgsProcessingException(self.tr("Il layer non contiene feature."))

        feedback.setProgress(10)
        if feedback.isCanceled():
            return {}

        # ── Ordinamento ──────────────────────────────────────────────────────
        feedback.setProgressText(self.tr("Ordinamento in corso..."))
        values = []

        # Avanza la progress bar dal 10% al 60% durante l'ordinamento, e
        # permette di annullare l'esecuzione anche a metà di un criterio
        # costoso (es. posizione lungo una linea con molte feature).
        def _progress_cb(p):
            if feedback.isCanceled():
                raise _Canceled()
            feedback.setProgress(10 + int(p * 0.5))

        # Criterio secondario (tie-break) → ordinamento multi-criterio
        sec_idx = self.parameterAsEnum(parameters, self.SECONDARY_CRITERION, context)
        sec_key = self._SECONDARY_KEYS[sec_idx]
        multi_active = sec_key is not None and criterion in self._MULTI_PRIMARY_KEYS
        if sec_key is not None and not multi_active:
            feedback.pushWarning(self.tr(
                "GeoSort: criterio secondario ignorato perché il criterio primario "
                "non supporta l'ordinamento multi-criterio "
                "(linea di riferimento, curva di Hilbert o serpentina)."
            ))

        try:
            if multi_active:
                sorted_feats, values, excluded = self._run_multi(
                    parameters, context, feedback, crs, expr_layer, features,
                    criterion, sec_key, ascending, nulls_last, natural_sort,
                    geodesic_mode=geodesic_mode, progress_callback=_progress_cb,
                )
                # Avviso geodetico sul criterio primario (se pertinente)
                applied = resolve_geodesic(crs, criterion, geodesic_mode)
                msg = geographic_crs_warning(crs, criterion, applied)
                if msg:
                    feedback.pushWarning("GeoSort: " + msg)

            elif criterion == "attribute":
                field = self.parameterAsString(parameters, self.ATTRIBUTE_FIELD, context)
                if not field:
                    raise QgsProcessingException(
                        self.tr("Specificare un campo attributo per il criterio 'Attributo tabellare'.")
                    )
                sorted_feats = sort_by_attribute(
                    features, field, ascending, nulls_last, natural_sort=natural_sort,
                    progress_callback=_progress_cb,
                )
                values = [f[field] for f in sorted_feats]
                excluded = []

            elif criterion in ("centroid_x", "centroid_y", "centroid_dist"):
                axis_map = {
                    "centroid_x": "x",
                    "centroid_y": "y",
                    "centroid_dist": "dist",
                }
                axis = axis_map[criterion]
                ref_point = (
                    self._ref_point_from(parameters, context, crs)
                    if axis == "dist" else None
                )
                # Geodesica solo per centroid_dist (distanza euclidea sull'ellissoide)
                da = None
                if resolve_geodesic(crs, criterion, geodesic_mode):
                    da = build_distance_area(crs, context.transformContext())
                msg = geographic_crs_warning(crs, criterion, da is not None)
                if msg:
                    feedback.pushWarning("GeoSort: " + msg)
                sorted_feats, values = sort_by_centroid(
                    features, axis=axis, ascending=ascending, ref_point=ref_point,
                    distance_area=da, progress_callback=_progress_cb,
                )
                excluded = []

            elif criterion == "line_position":
                line_geom = self._ref_line_geom(
                    parameters, context, feedback, crs,
                    self.tr("Specificare un layer di riferimento per il criterio 'Posizione lungo linea'."),
                )
                line_mode_keys = ["centroid_projection", "intersecting_projection", "intersecting_first_pt"]
                line_mode_idx = self.parameterAsEnum(parameters, "LINE_MODE", context)
                line_mode = line_mode_keys[line_mode_idx]
                sorted_feats, values, excluded = sort_by_line_position(
                    features, line_geom, ascending, mode=line_mode, progress_callback=_progress_cb,
                )
                if excluded:
                    feedback.pushWarning(self.tr(
                        "GeoSort: {n} feature escluse perché non intersecano la linea."
                    ).format(n=len(excluded)))

            elif criterion == "line_distance":
                line_geom = self._ref_line_geom(
                    parameters, context, feedback, crs,
                    self.tr("Specificare un layer di riferimento per il criterio 'Distanza dalla linea'."),
                )
                dist_mode_keys = ["centroid", "element"]
                dist_mode_idx = self.parameterAsEnum(parameters, "LINE_DISTANCE_MODE", context)
                dist_mode = dist_mode_keys[dist_mode_idx]
                da = None
                if resolve_geodesic(crs, criterion, geodesic_mode):
                    da = build_distance_area(crs, context.transformContext())
                msg = geographic_crs_warning(crs, criterion, da is not None)
                if msg:
                    feedback.pushWarning("GeoSort: " + msg)
                sorted_feats, values = sort_by_line_distance(
                    features, line_geom, ascending, mode=dist_mode, distance_area=da,
                    progress_callback=_progress_cb,
                )
                excluded = []

            elif criterion == "hilbert":
                hilbert_order = self.parameterAsInt(parameters, self.HILBERT_ORDER, context)
                sorted_feats, values = sort_by_hilbert(
                    features, ascending, order=hilbert_order, progress_callback=_progress_cb,
                )
                excluded = []

            elif criterion == "serpentine":
                band_size = self.parameterAsDouble(parameters, self.BAND_SIZE, context)
                axis_keys = ["horizontal", "vertical"]
                band_axis = axis_keys[self.parameterAsEnum(parameters, self.BAND_AXIS, context)]
                cross_ascending = self.parameterAsBoolean(parameters, self.CROSS_ASCENDING, context)
                sorted_feats, values = sort_by_serpentine(
                    features, band_size=band_size or None, ascending=ascending,
                    axis=band_axis, cross_ascending=cross_ascending,
                    progress_callback=_progress_cb,
                )
                excluded = []

            elif criterion == "expression":
                from .geosort_core import sort_by_expression
                expr_text = self.parameterAsExpression(parameters, "EXPRESSION", context)
                if not expr_text or not expr_text.strip():
                    raise QgsProcessingException(
                        self.tr("Specificare un'espressione per il criterio 'Espressione QGIS'.")
                    )
                try:
                    sorted_feats, values, warnings = sort_by_expression(
                        features, expr_layer, expr_text, ascending, nulls_last,
                        natural_sort=natural_sort, progress_callback=_progress_cb,
                    )
                except ValueError as exc:
                    raise QgsProcessingException(str(exc))
                if warnings:
                    for w in warnings:
                        feedback.pushWarning(f"GeoSort espressione: {w}")
                excluded = []

            else:
                # Tutti i criteri geometrici (area, perimetro, lunghezza, n_vertices, bbox_*)
                da = None
                if resolve_geodesic(crs, criterion, geodesic_mode):
                    da = build_distance_area(crs, context.transformContext())
                msg = geographic_crs_warning(crs, criterion, da is not None)
                if msg:
                    feedback.pushWarning("GeoSort: " + msg)
                try:
                    sorted_feats, values = sort_by_geometry_property(
                        features, criterion, ascending, distance_area=da,
                        progress_callback=_progress_cb,
                    )
                except ValueError as exc:
                    raise QgsProcessingException(str(exc))
                excluded = []
        except _Canceled:
            return {}

        feedback.setProgress(60)
        if feedback.isCanceled():
            return {}

        # ── Costruzione layer output ─────────────────────────────────────────
        feedback.setProgressText(self.tr("Scrittura output..."))

        start = self.parameterAsInt(parameters, self.START, context)
        step = self.parameterAsInt(parameters, self.STEP, context)
        order_field = self.parameterAsString(parameters, self.ORDER_FIELD, context)
        order_field = (order_field or "").strip() or "sort_order"
        if add_value and order_field == "sort_value":
            raise QgsProcessingException(self.tr(
                "Il nome del campo progressivo non può essere 'sort_value' "
                "quando è attivo il campo con il valore del criterio."
            ))

        out_fields = QgsFields()
        for field in source_fields:
            out_fields.append(field)
        # Se il campo progressivo esiste già nella sorgente lo si riutilizza
        # (valori sovrascritti) invece di aggiungerne un duplicato.
        order_idx = source_fields.indexOf(order_field)
        if order_idx == -1:
            out_fields.append(QgsField(order_field, QMetaType.Type.Int))
        else:
            feedback.pushInfo(self.tr(
                "GeoSort: il campo '{name}' esiste già, i valori saranno sovrascritti."
            ).format(name=order_field))
        value_field_type = QMetaType.Type.Double
        if add_value and values:
            value_field_type = _infer_field_type(values)
            out_fields.append(QgsField("sort_value", value_field_type))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            out_fields,
            source.wkbType(),
            crs,
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Impossibile creare il layer di output."))

        total = len(sorted_feats)
        has_value_field = add_value and values
        for i, feat in enumerate(sorted_feats):
            if feedback.isCanceled():
                break
            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            # setAttributes: una sola chiamata invece di un lookup per nome per campo
            order_value = start + i * step
            attrs = list(feat.attributes())
            if order_idx == -1:
                attrs.append(order_value)
            else:
                attrs[order_idx] = order_value
            if has_value_field:
                attrs.append(
                    _coerce_value(values[i], value_field_type)
                    if i < len(values) else NULL
                )
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            if i % 100 == 0:
                feedback.setProgress(60 + int(40 * i / total))

        feedback.setProgress(100)
        return {self.OUTPUT: dest_id}
