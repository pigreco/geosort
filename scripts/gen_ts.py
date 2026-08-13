# -*- coding: utf-8 -*-
"""Rigenera i18n/geosort_it.ts e geosort_en.ts da tutte le stringhe self.tr()
del codice. Mantiene i due file perfettamente sincronizzati e ben formati.

Uso:  python3 scripts/gen_ts.py
"""
import os
import re
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = ["geosort_dialog.py", "geosort_algorithm.py", "geosort_core.py", "geosort.py"]

# Stringhe tradotte fuori da un letterale dentro tr() (liste di etichette a
# livello di classe in geosort_algorithm.py, tradotte con [self.tr(s) for s ...]).
EXTRA = [
    "(nessuno)",
    "Attributo tabellare", "Espressione QGIS",
    "Centroide – coordinata X", "Centroide – coordinata Y",
    "Centroide – distanza da punto di riferimento (default 0,0)",
    "Area (poligoni)", "Perimetro (poligoni)", "Lunghezza (linee)",
    "Numero di vertici", "Larghezza Bounding Box", "Altezza Bounding Box",
    "Area Bounding Box", "Xmin Bounding Box", "Ymin Bounding Box",
    "Posizione lungo linea di riferimento",
    "Distanza dalla linea di riferimento",
    "Curva di Hilbert (ordinamento spaziale)",
    "Serpentina (boustrophedon)",
]

# Traduzioni inglesi (source -> EN). I source sono in lingua mista IT/EN.
EN = {
    "GeoSort – Advanced Geometry Sorting": "GeoSort – Advanced Geometry Sorting",
    "Ordina le feature di un layer vettoriale per criteri geometrici e attributivi":
        "Sort vector layer features by geometric and attribute criteria",
    "Input Layer": "Input Layer",
    "Layer:": "Layer:",
    "CRS / Units:": "CRS / Units:",
    "Criterio di ordinamento": "Sort Criterion",
    "Per attributo / espressione": "By attribute / expression",
    "Apri il Field Calculator di QGIS\n": "Open the QGIS Field Calculator\n",
    "Rimuovi": "Remove",
    "Rimuovi l'espressione attiva e torna al campo singolo":
        "Remove the active expression and return to single field",
    "Per coordinate centroide": "By centroid coordinates",
    "Coordinata X": "X Coordinate",
    "Coordinata Y": "Y Coordinate",
    "Distanza da punto di riferimento": "Distance from reference point",
    "Punto di riferimento (X, Y)": "Reference point (X, Y)",
    "Seleziona punto sulla mappa": "Pick point on map",
    "Per proprietà geometrica": "By geometric property",
    "Area": "Area",
    "Perimetro": "Perimeter",
    "Lunghezza": "Length",
    "Numero di vertici": "Number of vertices",
    "Larghezza Bounding Box": "Bounding Box Width",
    "Altezza Bounding Box": "Bounding Box Height",
    "Area Bounding Box": "Bounding Box Area",
    "Xmin Bounding Box": "Bounding Box Xmin",
    "Ymin Bounding Box": "Bounding Box Ymin",
    "Per distanza dalla linea": "By distance from line",
    "Distanza dal centroide": "Distance from centroid",
    "Distanza dall'elemento": "Distance from feature",
    "Distanza dal centroide: distanza dal centro della feature.\n":
        "Distance from centroid: distance from the center of the feature.\n",
    "Per posizione lungo linea": "By position along line",
    "Proiezione centroide  –  tutte le feature": "Centroid projection  –  all features",
    "Solo intersecanti  –  proiezione centroide": "Intersecting only  –  centroid projection",
    "Solo intersecanti  –  primo punto di intersezione":
        "Intersecting only  –  first intersection point",
    "Proiezione centroide: include tutte le feature, usa il centroide proiettato sulla linea.\n":
        "Centroid projection: includes all features, uses the centroid projected onto the line.\n",
    "Opzioni": "Options",
    "Direzione:": "Direction:",
    "Ascendente ↑": "Ascending ↑",
    "Discendente ↓": "Descending ↓",
    "Valori NULL in fondo (attributo e espressione)":
        "NULL values last (attribute and expression)",
    "Ordinamento naturale – Natural Sort (es. 1, 2, 10 invece di 1, 10, 2)":
        "Natural Sort (e.g. 1, 2, 10 instead of 1, 10, 2)",
    "<b>Lessicografico</b> (default): confronto carattere per carattere.\n":
        "<b>Lexicographic</b> (default): character-by-character comparison.\n",
    "Output": "Output",
    "Aggiorna layer corrente (aggiunge/aggiorna il campo 'sort_order')":
        "Update current layer (adds/updates the 'sort_order' field)",
    "Crea nuovo layer in memoria": "Create new memory layer",
    "Aggiungi campo con il valore del criterio usato (es. sort_area, sort_dist)":
        "Add a field with the used criterion value (e.g. sort_area, sort_dist)",
    "Anteprima…": "Preview…",
    "Mostra le prime feature ordinate con il criterio corrente":
        "Show the first sorted features for the current criterion",
    "GeoSort – Anteprima": "GeoSort – Preview",
    "FID": "FID",
    "sort_order": "sort_order",
    "Valore criterio": "Criterion value",
    "Aggiorna anteprima": "Refresh preview",
    "Help": "Help",
    "Applica": "Apply",
    "Annulla": "Cancel",
    "Chiudi": "Close",
    # Ordinamento multi-criterio (criterio secondario)
    "Criterio secondario (pareggi):": "Secondary criterion (ties):",
    "(nessuno)": "(none)",
    "Attributo tabellare": "Table attribute",
    "Centroide – coordinata X": "Centroid – X coordinate",
    "Centroide – coordinata Y": "Centroid – Y coordinate",
    "Area (poligoni)": "Area (polygons)",
    "Perimetro (poligoni)": "Perimeter (polygons)",
    "Lunghezza (linee)": "Length (lines)",
    "discendente ↓": "descending ↓",
    "Criterio secondario discendente ↓": "Secondary criterion descending ↓",
    "Spezza i pareggi del criterio primario (es. primario = Regione, secondario = Area). Non disponibile se il criterio primario è basato su linea.":
        "Breaks ties of the primary criterion (e.g. primary = Region, secondary = Area). "
        "Not available when the primary criterion is line-based.",
    # Misura geodetica (robustezza CRS geografico)
    "Misura su CRS geografico:": "Geographic CRS measurement:",
    "Misura geodetica: automatica (CRS geografico)":
        "Geodesic measurement: automatic (geographic CRS)",
    "Misura geodetica: sempre": "Geodesic measurement: always",
    "Misura geodetica: mai (planare)": "Geodesic measurement: never (planar)",
    "Su CRS geografico (gradi, es. EPSG:4326), area/lunghezza/distanze\n":
        "On a geographic CRS (degrees, e.g. EPSG:4326), area/length/distances\n",
    " ⚠ CRS geografico: GeoSort applica automaticamente la misura":
        " ⚠ Geographic CRS: GeoSort automatically applies ellipsoidal (geodesic) measurement",
}

# Stringhe complete (multilinea) e nuove voci: algoritmo Processing, core,
# opzione "solo selezionate", tooltip estratti per intero.
EN.update({
    "Espressione QGIS": "QGIS expression",
    "Centroide – distanza da punto di riferimento (default 0,0)":
        "Centroid – distance from reference point (default 0,0)",
    "Posizione lungo linea di riferimento": "Position along reference line",
    "Distanza dalla linea di riferimento": "Distance from reference line",
    "Curva di Hilbert (ordinamento spaziale)": "Hilbert curve (spatial sorting)",
    "Per curva di Hilbert (ordinamento spaziale)": "By Hilbert curve (spatial sorting)",
    "Ordina le feature lungo una curva di Hilbert calcolata sui centroidi:\n"
    "le feature vicine nello spazio diventano vicine nell'ordine.\n"
    "Utile per atlanti «a percorso continuo» e per scrivere GeoPackage\n"
    "con feature spazialmente coerenti (letture più veloci).\n"
    "Non disponibile come criterio primario in modalità multi-criterio.":
        "Sorts features along a Hilbert curve calculated on the centroids:\n"
        "features near each other in space become near each other in the order.\n"
        "Useful for \"continuous path\" atlases and for writing GeoPackage files\n"
        "with spatially coherent features (faster reads).\n"
        "Not available as the primary criterion in multi-criteria mode.",
    "Curva di Hilbert – ordine (risoluzione griglia = 2^ordine)":
        "Hilbert curve – order (grid resolution = 2^order)",
    "Ordina solo le feature selezionate": "Sort only selected features",
    "Se attivo, l'ordinamento considera solo le feature attualmente\n"
    "selezionate sul layer. In modalità 'Aggiorna layer corrente' il\n"
    "campo sort_order viene scritto solo su quelle feature.":
        "If enabled, sorting only considers the features currently\n"
        "selected on the layer. In 'Update current layer' mode the\n"
        "sort_order field is written only for those features.",
    "Apri il Field Calculator di QGIS\n"
    "Permette di costruire un'espressione personalizzata come criterio di ordinamento\n"
    "Es: \"area_kmq\" / \"popolazione\"   oppure   length($geometry)":
        "Open the QGIS Field Calculator\n"
        "Lets you build a custom expression as sort criterion\n"
        "E.g.: \"area_kmq\" / \"popolazione\"   or   length($geometry)",
    "Distanza dal centroide: distanza dal centro della feature.\n"
    "Distanza dall'elemento: distanza dal punto più vicino della geometria.":
        "Distance from centroid: distance from the center of the feature.\n"
        "Distance from feature: distance from the nearest point of the geometry.",
    "Proiezione centroide: include tutte le feature, usa il centroide proiettato sulla linea.\n"
    "Solo intersecanti – centroide: esclude le feature che non intersecano la linea.\n"
    "Solo intersecanti – primo punto: usa il punto in cui la feature tocca per primo la linea.":
        "Centroid projection: includes all features, uses the centroid projected onto the line.\n"
        "Intersecting only – centroid: excludes features that do not intersect the line.\n"
        "Intersecting only – first point: uses the point where the feature first touches the line.",
    "<b>Lessicografico</b> (default): confronto carattere per carattere.\n"
    "Esempio: «1010» precede «11» precede «1111».\n\n"
    "<b>Natural Sort</b>: le sequenze di cifre sono confrontate come numeri interi.\n"
    "Esempio: «11» precede «1010» precede «1111».\n\n"
    "Attivalo con campi alfanumerici (FILE1, FILE2, FILE10)\n"
    "o espressioni di concatenazione come \"fid\" || \"id_poly\".":
        "<b>Lexicographic</b> (default): character-by-character comparison.\n"
        "Example: «1010» before «11» before «1111».\n\n"
        "<b>Natural Sort</b>: digit sequences are compared as integers.\n"
        "Example: «11» before «1010» before «1111».\n\n"
        "Enable it with alphanumeric fields (FILE1, FILE2, FILE10)\n"
        "or concatenation expressions such as \"fid\" || \"id_poly\".",
    "Su CRS geografico (gradi, es. EPSG:4326), area/lunghezza/distanze\n"
    "vengono misurate sull'ellissoide (m²/m) invece che in gradi.\n"
    "• Automatica: geodetica solo se il CRS è geografico (consigliato).\n"
    "• Sempre: geodetica anche su CRS proiettati.\n"
    "• Mai (planare): misura nelle unità native del CRS.":
        "On a geographic CRS (degrees, e.g. EPSG:4326), area/length/distances\n"
        "are measured on the ellipsoid (m²/m) instead of degrees.\n"
        "• Automatic: geodesic only if the CRS is geographic (recommended).\n"
        "• Always: geodesic even on projected CRS.\n"
        "• Never (planar): measured in the native CRS units.",
    " ⚠ CRS geografico: GeoSort applica automaticamente la misura"
    " ellissoidica (geodetica) per area/lunghezza/distanze (m²/m).":
        " ⚠ Geographic CRS: GeoSort automatically applies ellipsoidal"
        " (geodesic) measurement for area/length/distances (m²/m).",
    "Nessuna feature selezionata sul layer (è attivo 'Ordina solo le feature selezionate').":
        "No features selected on the layer ('Sort only selected features' is enabled).",
    # ── Algoritmo Processing ──
    "Ordina feature (GeoSort)": "Sort features (GeoSort)",
    "Layer di input": "Input layer",
    "Campo attributo (solo per criterio 'Attributo tabellare')":
        "Attribute field (only for 'Table attribute' criterion)",
    "Ordine ascendente": "Ascending order",
    "Valori NULL in fondo (solo per criterio attributo)":
        "NULL values last (attribute criterion only)",
    "Ordinamento naturale – Natural Sort (solo per criterio attributo/espressione)":
        "Natural Sort (attribute/expression criterion only)",
    "Modalità di misura geodetica (per area/lunghezza/distanza)":
        "Geodesic measurement mode (for area/length/distance)",
    "Automatica – geodetica su CRS geografico (consigliato)":
        "Automatic – geodesic on geographic CRS (recommended)",
    "Sempre geodetica": "Always geodesic",
    "Mai (misura planare nelle unità del CRS)": "Never (planar measurement in CRS units)",
    "Layer linea di riferimento (solo per criteri 'Posizione/Distanza dalla linea')":
        "Reference line layer (only for 'Position along/Distance from line' criteria)",
    "Modalità di calcolo – Posizione lungo linea": "Calculation mode – Position along line",
    "Solo intersecanti –  proiezione centroide": "Intersecting only –  centroid projection",
    "Solo intersecanti –  primo punto di intersezione":
        "Intersecting only –  first intersection point",
    "Modalità di calcolo – Distanza dalla linea": "Calculation mode – Distance from line",
    "Espressione QGIS (solo per criterio 'Espressione QGIS')":
        "QGIS expression (only for 'QGIS expression' criterion)",
    "Criterio secondario per i pareggi (opzionale)": "Secondary criterion for ties (optional)",
    "Campo del criterio secondario (solo se 'Attributo tabellare')":
        "Secondary criterion field (only if 'Table attribute')",
    "Espressione del criterio secondario (solo se 'Espressione QGIS')":
        "Secondary criterion expression (only if 'QGIS expression')",
    "Criterio secondario: ordine ascendente": "Secondary criterion: ascending order",
    "Aggiungi campo con il valore del criterio (sort_value)":
        "Add a field with the criterion value (sort_value)",
    "Layer ordinato": "Sorted layer",
    "Specificare un campo attributo per il criterio primario.":
        "Specify an attribute field for the primary criterion.",
    "Specificare un'espressione per il criterio primario.":
        "Specify an expression for the primary criterion.",
    "Specificare un campo per il criterio secondario.":
        "Specify a field for the secondary criterion.",
    "Specificare un'espressione per il criterio secondario.":
        "Specify an expression for the secondary criterion.",
    "GeoSort: ordinamento multi-criterio (primario + secondario).":
        "GeoSort: multi-criteria sorting (primary + secondary).",
    "Layer di input non trovato.": "Input layer not found.",
    "Caricamento feature...": "Loading features...",
    "Il layer non contiene feature.": "The layer contains no features.",
    "Ordinamento in corso...": "Sorting...",
    "GeoSort: criterio secondario ignorato perché il criterio primario "
    "non supporta l'ordinamento multi-criterio "
    "(linea di riferimento, curva di Hilbert o serpentina).":
        "GeoSort: secondary criterion ignored because the primary criterion does not "
        "support multi-criteria sorting "
        "(line-based, Hilbert curve, or serpentine).",
    "Specificare un campo attributo per il criterio 'Attributo tabellare'.":
        "Specify an attribute field for the 'Table attribute' criterion.",
    "Specificare un layer di riferimento per il criterio 'Posizione lungo linea'.":
        "Specify a reference layer for the 'Position along line' criterion.",
    "Il layer di riferimento non contiene feature.":
        "The reference layer contains no features.",
    "GeoSort: {n} feature escluse perché non intersecano la linea.":
        "GeoSort: {n} features excluded because they do not intersect the line.",
    "Specificare un layer di riferimento per il criterio 'Distanza dalla linea'.":
        "Specify a reference layer for the 'Distance from line' criterion.",
    "Specificare un'espressione per il criterio 'Espressione QGIS'.":
        "Specify an expression for the 'QGIS expression' criterion.",
    "Scrittura output...": "Writing output...",
    "Impossibile creare il layer di output.": "Could not create the output layer.",
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
    "Compatibile con il Processing Toolbox, il modellatore grafico e PyQGIS headless.":
        "Sorts vector layer features by geometric or attribute criteria "
        "and adds the <b>sort_order</b> field (progressive number, 1 = first feature).\n\n"
        "Available criteria: table attribute, centroid coordinates, "
        "area, length, perimeter, number of vertices, bounding box, "
        "position along a reference line, distance from the reference line, "
        "Hilbert curve (spatial sorting), QGIS expression, serpentine "
        "(boustrophedon, horizontal or vertical bands).\n\n"
        "<b>Text sorting mode (attribute/expression):</b>\n"
        "• <b>Lexicographic</b> (default): character-by-character comparison. "
        "Example: «1010» &lt; «11» &lt; «1111».\n"
        "• <b>Natural Sort</b>: digit sequences are compared as numbers. "
        "Example: «11» &lt; «1010» &lt; «1111». "
        "Useful with alphanumeric fields (FILE1, FILE2, FILE10) or concatenation "
        "expressions such as <code>\"fid\" || \"id_poly\"</code>.\n\n"
        "<b>Multi-criteria sorting:</b> set a <b>secondary criterion</b> "
        "to break ties of the primary criterion (e.g. primary = region, "
        "secondary = descending area). Available for non line-based criteria.\n\n"
        "<b>Reference point:</b> for the «Centroid – distance» criterion you can "
        "provide a reference point (also via the «... on map» button); "
        "if left empty, the origin (0,0) is used, as in previous versions.\n\n"
        "<b>Reference layer (position/distance along line):</b> if the reference "
        "layer has a CRS different from the input layer's, it is automatically "
        "reprojected before the calculation (with a non-blocking warning).\n\n"
        "<b>Hilbert curve:</b> sorts features along a Hilbert curve calculated "
        "on the centroids, normalized over the layer's overall extent — features "
        "near each other in space become near each other in the order. Useful for "
        "continuous-path atlases and for writing GeoPackage files with spatially "
        "coherent features (faster reads). The advanced <code>HILBERT_ORDER</code> "
        "parameter controls the grid resolution (default 16, side 2^16); not "
        "available as the primary criterion in multi-criteria mode.\n\n"
        "<b>Serpentine (boustrophedon):</b> sorts features into bands, with the "
        "cross axis alternating ascending/descending from one band to the next — "
        "the classic order for numbering the sheets of a regular-grid map series "
        "or a photogrammetric flight path, without the long jump from the end of "
        "a band to the start of the next one typical of a plain row-by-row sort. "
        "The <code>BAND_AXIS</code> parameter chooses the orientation: horizontal "
        "bands (by Y, X alternating — default) or vertical bands (by X, Y "
        "alternating). The advanced <code>BAND_SIZE</code> parameter sets the band "
        "size in CRS units — height for horizontal bands, width for vertical ones "
        "(0/empty = automatic, from the average bounding box size of the features). "
        "The advanced <code>CROSS_ASCENDING</code> parameter chooses the starting "
        "corner: combining <code>DIRECTION</code> (which band comes first) and "
        "<code>CROSS_ASCENDING</code> (the cross axis direction in the first band) "
        "reaches any of the four corners of the grid. Not available as the primary "
        "criterion in multi-criteria mode.\n\n"
        "<b>Custom numbering (advanced parameters):</b> starting value "
        "(e.g. 0), step (e.g. 10 → 10, 20, 30...) and the name of the progressive "
        "field (default <b>sort_order</b>). If the field already exists in the input "
        "layer, its values are overwritten instead of creating a duplicate.\n\n"
        "<b>Geodesic (ellipsoidal) measurement:</b> when the layer CRS is geographic "
        "(coordinates in degrees, e.g. EPSG:4326), planar measures of area, length, "
        "perimeter and distance would be in degrees — metrically meaningless. "
        "With the <i>Automatic</i> mode (default) GeoSort automatically uses ellipsoidal "
        "calculation (QgsDistanceArea) returning values in m² / m. "
        "Select <i>Never</i> to force planar measurement in CRS units.\n\n"
        "Compatible with the Processing Toolbox, the graphical modeler and headless PyQGIS.",
    "Punto di riferimento (solo per criterio 'Centroide – distanza'; vuoto = origine 0,0)":
        "Reference point (only for the 'Centroid – distance' criterion; empty = origin 0,0)",
    "Numerazione: valore iniziale": "Numbering: starting value",
    "Numerazione: passo (incremento fra feature)": "Numbering: step (increment between features)",
    "Nome del campo progressivo": "Progressive field name",
    "Il nome del campo progressivo non può essere 'sort_value' "
    "quando è attivo il campo con il valore del criterio.":
        "The progressive field name cannot be 'sort_value' "
        "when the criterion value field is enabled.",
    "GeoSort: il campo '{name}' esiste già, i valori saranno sovrascritti.":
        "GeoSort: field '{name}' already exists, its values will be overwritten.",
    "Campo:": "Field:",
    "Inizio:": "Start:",
    "Passo:": "Step:",
    "Nome del campo progressivo (default: sort_order).\n"
    "Se esiste già, i valori vengono sovrascritti.":
        "Progressive field name (default: sort_order).\n"
        "If it already exists, its values are overwritten.",
    "Valore iniziale della numerazione (es. 0 o 1).":
        "Starting value of the numbering (e.g. 0 or 1).",
    "Incremento fra feature consecutive (es. 10 → 10, 20, 30...).":
        "Increment between consecutive features (e.g. 10 → 10, 20, 30...).",
    "Il campo '{name}' esiste già nel layer.\nSovrascriverlo con il nuovo ordinamento?":
        "The field '{name}' already exists in the layer.\nOverwrite it with the new ordering?",
    "Impossibile riproiettare il layer di riferimento dal CRS {ref} al CRS {target} del layer di input: {error}":
        "Could not reproject the reference layer from CRS {ref} to the input layer's CRS {target}: {error}",
    "GeoSort: layer di riferimento riproiettato da {ref} a {target} (CRS del layer di input).":
        "GeoSort: reference layer reprojected from {ref} to {target} (input layer's CRS).",
    # ── Core (avvisi CRS geografico e messaggi d'errore) ──
    "CRS geografico ({authid}): misura ellissoidica (geodetica) applicata automaticamente. "
    "I valori del criterio sono in metri/m² sull'ellissoide {ellipsoid}, non in gradi.":
        "Geographic CRS ({authid}): ellipsoidal (geodesic) measurement applied automatically. "
        "Criterion values are in meters/m² on the {ellipsoid} ellipsoid, not in degrees.",
    "CRS geografico ({authid}): i valori di '{criterion}' sono calcolati in gradi "
    "e l'ordinamento può risultare distorto alle diverse latitudini. "
    "Attiva la misura geodetica o riproietta in un CRS proiettato (metrico).":
        "Geographic CRS ({authid}): '{criterion}' values are computed in degrees "
        "and sorting may be distorted across latitudes. "
        "Enable geodesic measurement or reproject to a projected (metric) CRS.",
    "CRS geografico ({authid}): '{criterion}' è calcolato in gradi (concetto planare "
    "in coordinate native). Per misure metriche riproietta in un CRS proiettato.":
        "Geographic CRS ({authid}): '{criterion}' is computed in degrees (a planar concept "
        "in native coordinates). For metric measures reproject to a projected CRS.",
    "Espressione non valida: {error}\nEspressione: {expr}":
        "Invalid expression: {error}\nExpression: {expr}",
    "Espressione non valida: {error}": "Invalid expression: {error}",
    "Criterio 'area' richiede geometrie poligonali, trovato: {type}.":
        "The 'area' criterion requires polygon geometries, found: {type}.",
    "Criterio 'perimeter' richiede geometrie poligonali, trovato: {type}.":
        "The 'perimeter' criterion requires polygon geometries, found: {type}.",
    "Criterio 'length' richiede geometrie lineari, trovato: {type}.":
        "The 'length' criterion requires line geometries, found: {type}.",
    "Criterio sconosciuto: '{criterion}'.": "Unknown criterion: '{criterion}'.",
    "La geometria della linea di riferimento è assente o vuota.":
        "The reference line geometry is missing or empty.",
    "Modalità sconosciuta: '{mode}'. Valori ammessi: {valid}":
        "Unknown mode: '{mode}'. Allowed values: {valid}",
    "Linea di riferimento assente o vuota.": "Reference line missing or empty.",
    "Criterio multi-livello sconosciuto: '{key}'.": "Unknown multi-level criterion: '{key}'.",
    # ── Serpentina (boustrophedon) ──
    "Serpentina (boustrophedon)": "Serpentine (boustrophedon)",
    "A serpentina (boustrophedon)": "Serpentine (boustrophedon)",
    "Ordina le feature a bande (orizzontali o verticali), con l'asse\n"
    "trasversale alternato crescente/decrescente da una banda alla\n"
    "successiva (boustrophedon): l'ordine classico per numerare le\n"
    "tavole di una serie cartografica a taglio regolare, senza il\n"
    "salto lungo da fine banda a inizio banda successiva tipico di\n"
    "un ordinamento a righe semplice.\n"
    "Non disponibile come criterio primario in modalità multi-criterio.":
        "Sorts features into bands (horizontal or vertical), with the\n"
        "cross axis alternating ascending/descending from one band to\n"
        "the next (boustrophedon): the classic order for numbering the\n"
        "sheets of a regular-grid map series, without the long jump from\n"
        "the end of a band to the start of the next one typical of a\n"
        "plain row-by-row sort.\n"
        "Not available as the primary criterion in multi-criteria mode.",
    "Orizzontali (bande per Y, X alternato)": "Horizontal (bands by Y, X alternating)",
    "Verticali (bande per X, Y alternato)": "Vertical (bands by X, Y alternating)",
    "Orizzontali: raggruppa per Y, alterna il verso di lettura della X.\n"
    "Verticali: raggruppa per X, alterna il verso di lettura della Y.":
        "Horizontal: groups by Y, alternates the X reading direction.\n"
        "Vertical: groups by X, alternates the Y reading direction.",
    "Automatica": "Automatic",
    "Dimensione di ciascuna banda nelle unità del CRS del layer\n"
    "(altezza se orizzontali, larghezza se verticali).\n"
    "0 = automatica (dimensione media delle bounding box delle feature).":
        "Size of each band in the layer's CRS units\n"
        "(height if horizontal, width if vertical).\n"
        "0 = automatic (average bounding box size of the features).",
    "Serpentina – orientamento bande": "Serpentine – band orientation",
    "Serpentina – dimensione banda, unità del CRS (0 = automatica, "
    "da altezza/larghezza media delle feature)":
        "Serpentine – band size, CRS units (0 = automatic, "
        "from average feature height/width)",
    "Prima banda in verso crescente": "First band in ascending direction",
    "Verso dell'asse trasversale nella prima banda percorsa (X per bande\n"
    "orizzontali, Y per verticali): crescente (default) o decrescente.\n"
    "Combinato con la Direzione generale (quale banda è la prima),\n"
    "sceglie l'angolo di partenza del percorso a serpentina.":
        "Direction of the cross axis in the first band visited (X for\n"
        "horizontal bands, Y for vertical): ascending (default) or descending.\n"
        "Combined with the general Direction (which band comes first),\n"
        "it chooses the starting corner of the serpentine path.",
    "Serpentina – prima banda in verso crescente (altrimenti decrescente)":
        "Serpentine – first band in ascending direction (otherwise descending)",
})

# Traduzioni italiane: identità tranne i source in inglese
IT_OVERRIDE = {
    "GeoSort – Advanced Geometry Sorting": "GeoSort – Ordinamento Avanzato delle Geometrie",
    "Input Layer": "Layer di input",
    "CRS / Units:": "CRS / Unità:",
    "Help": "Aiuto",
}

# Cattura l'INTERA sequenza di letterali adiacenti dentro tr(): le stringhe
# multilinea concatenate vengono estratte per intero (il sorgente completo è
# ciò che Qt cerca a runtime), non solo il primo frammento.
_STR = r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
TR_RE = re.compile(r'\b(?:self\.tr|_tr)\(\s*(' + _STR + r'(?:\s*' + _STR + r')*)', re.S)


def collect_sources():
    seen, out = set(), []
    for name in EXTRA:
        if name not in seen:
            seen.add(name)
            out.append(name)
    for fname in MODULES:
        text = open(os.path.join(ROOT, fname), encoding="utf-8").read()
        for m in TR_RE.finditer(text):
            val = eval("(" + m.group(1) + ")")
            if val not in seen:
                seen.add(val)
                out.append(val)
    return out


def build(lang, table):
    rows = []
    for s in sorted(collect_sources()):
        rows.append(
            "    <message>\n"
            f"      <source>{escape(s)}</source>\n"
            f"      <translation>{escape(table[s])}</translation>\n"
            "    </message>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<TS version="2.1" language="{lang}">\n'
        "  <context>\n    <name>GeoSort</name>\n"
        + "\n".join(rows)
        + "\n  </context>\n</TS>\n"
    )


def main():
    srcs = collect_sources()
    missing = [s for s in srcs if s not in EN]
    if missing:
        raise SystemExit("Traduzioni EN mancanti per:\n  " + "\n  ".join(map(repr, missing)))
    it = {s: IT_OVERRIDE.get(s, s) for s in srcs}
    i18n = os.path.join(ROOT, "i18n")
    open(os.path.join(i18n, "geosort_it.ts"), "w", encoding="utf-8").write(build("it", it))
    open(os.path.join(i18n, "geosort_en.ts"), "w", encoding="utf-8").write(build("en", EN))
    print(f"OK: {len(srcs)} messaggi scritti in geosort_it.ts e geosort_en.ts")


if __name__ == "__main__":
    main()
