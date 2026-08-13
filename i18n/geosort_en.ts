<?xml version="1.0" encoding="utf-8"?>
<TS version="2.1" language="en">
  <context>
    <name>GeoSort</name>
    <message>
      <source> ⚠ CRS geografico: GeoSort applica automaticamente la misura ellissoidica (geodetica) per area/lunghezza/distanze (m²/m).</source>
      <translation> ⚠ Geographic CRS: GeoSort automatically applies ellipsoidal (geodesic) measurement for area/length/distances (m²/m).</translation>
    </message>
    <message>
      <source>(nessuno)</source>
      <translation>(none)</translation>
    </message>
    <message>
      <source>&lt;b&gt;Lessicografico&lt;/b&gt; (default): confronto carattere per carattere.
Esempio: «1010» precede «11» precede «1111».

&lt;b&gt;Natural Sort&lt;/b&gt;: le sequenze di cifre sono confrontate come numeri interi.
Esempio: «11» precede «1010» precede «1111».

Attivalo con campi alfanumerici (FILE1, FILE2, FILE10)
o espressioni di concatenazione come "fid" || "id_poly".</source>
      <translation>&lt;b&gt;Lexicographic&lt;/b&gt; (default): character-by-character comparison.
Example: «1010» before «11» before «1111».

&lt;b&gt;Natural Sort&lt;/b&gt;: digit sequences are compared as integers.
Example: «11» before «1010» before «1111».

Enable it with alphanumeric fields (FILE1, FILE2, FILE10)
or concatenation expressions such as "fid" || "id_poly".</translation>
    </message>
    <message>
      <source>Aggiorna anteprima</source>
      <translation>Refresh preview</translation>
    </message>
    <message>
      <source>Aggiorna layer corrente (aggiunge/aggiorna il campo 'sort_order')</source>
      <translation>Update current layer (adds/updates the 'sort_order' field)</translation>
    </message>
    <message>
      <source>Aggiungi campo con il valore del criterio (sort_value)</source>
      <translation>Add a field with the criterion value (sort_value)</translation>
    </message>
    <message>
      <source>Aggiungi campo con il valore del criterio usato (es. sort_area, sort_dist)</source>
      <translation>Add a field with the used criterion value (e.g. sort_area, sort_dist)</translation>
    </message>
    <message>
      <source>Altezza Bounding Box</source>
      <translation>Bounding Box Height</translation>
    </message>
    <message>
      <source>Annulla</source>
      <translation>Cancel</translation>
    </message>
    <message>
      <source>Anteprima (prime 10 feature ordinate)</source>
      <translation>Preview (first 10 sorted features)</translation>
    </message>
    <message>
      <source>Applica</source>
      <translation>Apply</translation>
    </message>
    <message>
      <source>Apri il Field Calculator di QGIS
Permette di costruire un'espressione personalizzata come criterio di ordinamento
Es: "area_kmq" / "popolazione"   oppure   length($geometry)</source>
      <translation>Open the QGIS Field Calculator
Lets you build a custom expression as sort criterion
E.g.: "area_kmq" / "popolazione"   or   length($geometry)</translation>
    </message>
    <message>
      <source>Area</source>
      <translation>Area</translation>
    </message>
    <message>
      <source>Area (poligoni)</source>
      <translation>Area (polygons)</translation>
    </message>
    <message>
      <source>Area Bounding Box</source>
      <translation>Bounding Box Area</translation>
    </message>
    <message>
      <source>Ascendente ↑</source>
      <translation>Ascending ↑</translation>
    </message>
    <message>
      <source>Attributo tabellare</source>
      <translation>Table attribute</translation>
    </message>
    <message>
      <source>Automatica – geodetica su CRS geografico (consigliato)</source>
      <translation>Automatic – geodesic on geographic CRS (recommended)</translation>
    </message>
    <message>
      <source>CRS / Units:</source>
      <translation>CRS / Units:</translation>
    </message>
    <message>
      <source>CRS geografico ({authid}): '{criterion}' è calcolato in gradi (concetto planare in coordinate native). Per misure metriche riproietta in un CRS proiettato.</source>
      <translation>Geographic CRS ({authid}): '{criterion}' is computed in degrees (a planar concept in native coordinates). For metric measures reproject to a projected CRS.</translation>
    </message>
    <message>
      <source>CRS geografico ({authid}): i valori di '{criterion}' sono calcolati in gradi e l'ordinamento può risultare distorto alle diverse latitudini. Attiva la misura geodetica o riproietta in un CRS proiettato (metrico).</source>
      <translation>Geographic CRS ({authid}): '{criterion}' values are computed in degrees and sorting may be distorted across latitudes. Enable geodesic measurement or reproject to a projected (metric) CRS.</translation>
    </message>
    <message>
      <source>CRS geografico ({authid}): misura ellissoidica (geodetica) applicata automaticamente. I valori del criterio sono in metri/m² sull'ellissoide {ellipsoid}, non in gradi.</source>
      <translation>Geographic CRS ({authid}): ellipsoidal (geodesic) measurement applied automatically. Criterion values are in meters/m² on the {ellipsoid} ellipsoid, not in degrees.</translation>
    </message>
    <message>
      <source>Campo attributo (solo per criterio 'Attributo tabellare')</source>
      <translation>Attribute field (only for 'Table attribute' criterion)</translation>
    </message>
    <message>
      <source>Campo del criterio secondario (solo se 'Attributo tabellare')</source>
      <translation>Secondary criterion field (only if 'Table attribute')</translation>
    </message>
    <message>
      <source>Campo:</source>
      <translation>Field:</translation>
    </message>
    <message>
      <source>Caricamento feature...</source>
      <translation>Loading features...</translation>
    </message>
    <message>
      <source>Centroide – coordinata X</source>
      <translation>Centroid – X coordinate</translation>
    </message>
    <message>
      <source>Centroide – coordinata Y</source>
      <translation>Centroid – Y coordinate</translation>
    </message>
    <message>
      <source>Centroide – distanza da punto di riferimento (default 0,0)</source>
      <translation>Centroid – distance from reference point (default 0,0)</translation>
    </message>
    <message>
      <source>Chiudi</source>
      <translation>Close</translation>
    </message>
    <message>
      <source>Coordinata X</source>
      <translation>X Coordinate</translation>
    </message>
    <message>
      <source>Coordinata Y</source>
      <translation>Y Coordinate</translation>
    </message>
    <message>
      <source>Crea nuovo layer in memoria</source>
      <translation>Create new memory layer</translation>
    </message>
    <message>
      <source>Criterio 'area' richiede geometrie poligonali, trovato: {type}.</source>
      <translation>The 'area' criterion requires polygon geometries, found: {type}.</translation>
    </message>
    <message>
      <source>Criterio 'length' richiede geometrie lineari, trovato: {type}.</source>
      <translation>The 'length' criterion requires line geometries, found: {type}.</translation>
    </message>
    <message>
      <source>Criterio 'perimeter' richiede geometrie poligonali, trovato: {type}.</source>
      <translation>The 'perimeter' criterion requires polygon geometries, found: {type}.</translation>
    </message>
    <message>
      <source>Criterio di ordinamento</source>
      <translation>Sort Criterion</translation>
    </message>
    <message>
      <source>Criterio multi-livello sconosciuto: '{key}'.</source>
      <translation>Unknown multi-level criterion: '{key}'.</translation>
    </message>
    <message>
      <source>Criterio sconosciuto: '{criterion}'.</source>
      <translation>Unknown criterion: '{criterion}'.</translation>
    </message>
    <message>
      <source>Criterio secondario (pareggi):</source>
      <translation>Secondary criterion (ties):</translation>
    </message>
    <message>
      <source>Criterio secondario discendente ↓</source>
      <translation>Secondary criterion descending ↓</translation>
    </message>
    <message>
      <source>Criterio secondario per i pareggi (opzionale)</source>
      <translation>Secondary criterion for ties (optional)</translation>
    </message>
    <message>
      <source>Criterio secondario: ordine ascendente</source>
      <translation>Secondary criterion: ascending order</translation>
    </message>
    <message>
      <source>Direzione:</source>
      <translation>Direction:</translation>
    </message>
    <message>
      <source>Discendente ↓</source>
      <translation>Descending ↓</translation>
    </message>
    <message>
      <source>Distanza da punto di riferimento</source>
      <translation>Distance from reference point</translation>
    </message>
    <message>
      <source>Distanza dal centroide</source>
      <translation>Distance from centroid</translation>
    </message>
    <message>
      <source>Distanza dal centroide: distanza dal centro della feature.
Distanza dall'elemento: distanza dal punto più vicino della geometria.</source>
      <translation>Distance from centroid: distance from the center of the feature.
Distance from feature: distance from the nearest point of the geometry.</translation>
    </message>
    <message>
      <source>Distanza dall'elemento</source>
      <translation>Distance from feature</translation>
    </message>
    <message>
      <source>Distanza dalla linea di riferimento</source>
      <translation>Distance from reference line</translation>
    </message>
    <message>
      <source>Espressione QGIS</source>
      <translation>QGIS expression</translation>
    </message>
    <message>
      <source>Espressione QGIS (solo per criterio 'Espressione QGIS')</source>
      <translation>QGIS expression (only for 'QGIS expression' criterion)</translation>
    </message>
    <message>
      <source>Espressione del criterio secondario (solo se 'Espressione QGIS')</source>
      <translation>Secondary criterion expression (only if 'QGIS expression')</translation>
    </message>
    <message>
      <source>Espressione non valida: {error}</source>
      <translation>Invalid expression: {error}</translation>
    </message>
    <message>
      <source>Espressione non valida: {error}
Espressione: {expr}</source>
      <translation>Invalid expression: {error}
Expression: {expr}</translation>
    </message>
    <message>
      <source>FID</source>
      <translation>FID</translation>
    </message>
    <message>
      <source>GeoSort – Advanced Geometry Sorting</source>
      <translation>GeoSort – Advanced Geometry Sorting</translation>
    </message>
    <message>
      <source>GeoSort: criterio secondario ignorato perché il criterio primario è basato su una linea di riferimento.</source>
      <translation>GeoSort: secondary criterion ignored because the primary criterion is line-based.</translation>
    </message>
    <message>
      <source>GeoSort: il campo '{name}' esiste già, i valori saranno sovrascritti.</source>
      <translation>GeoSort: field '{name}' already exists, its values will be overwritten.</translation>
    </message>
    <message>
      <source>GeoSort: layer di riferimento riproiettato da {ref} a {target} (CRS del layer di input).</source>
      <translation>GeoSort: reference layer reprojected from {ref} to {target} (input layer's CRS).</translation>
    </message>
    <message>
      <source>GeoSort: ordinamento multi-criterio (primario + secondario).</source>
      <translation>GeoSort: multi-criteria sorting (primary + secondary).</translation>
    </message>
    <message>
      <source>GeoSort: {n} feature escluse perché non intersecano la linea.</source>
      <translation>GeoSort: {n} features excluded because they do not intersect the line.</translation>
    </message>
    <message>
      <source>Help</source>
      <translation>Help</translation>
    </message>
    <message>
      <source>Il campo '{name}' esiste già nel layer.
Sovrascriverlo con il nuovo ordinamento?</source>
      <translation>The field '{name}' already exists in the layer.
Overwrite it with the new ordering?</translation>
    </message>
    <message>
      <source>Il layer di riferimento non contiene feature.</source>
      <translation>The reference layer contains no features.</translation>
    </message>
    <message>
      <source>Il layer non contiene feature.</source>
      <translation>The layer contains no features.</translation>
    </message>
    <message>
      <source>Il nome del campo progressivo non può essere 'sort_value' quando è attivo il campo con il valore del criterio.</source>
      <translation>The progressive field name cannot be 'sort_value' when the criterion value field is enabled.</translation>
    </message>
    <message>
      <source>Impossibile creare il layer di output.</source>
      <translation>Could not create the output layer.</translation>
    </message>
    <message>
      <source>Impossibile riproiettare il layer di riferimento dal CRS {ref} al CRS {target} del layer di input: {error}</source>
      <translation>Could not reproject the reference layer from CRS {ref} to the input layer's CRS {target}: {error}</translation>
    </message>
    <message>
      <source>Incremento fra feature consecutive (es. 10 → 10, 20, 30...).</source>
      <translation>Increment between consecutive features (e.g. 10 → 10, 20, 30...).</translation>
    </message>
    <message>
      <source>Inizio:</source>
      <translation>Start:</translation>
    </message>
    <message>
      <source>Input Layer</source>
      <translation>Input Layer</translation>
    </message>
    <message>
      <source>La geometria della linea di riferimento è assente o vuota.</source>
      <translation>The reference line geometry is missing or empty.</translation>
    </message>
    <message>
      <source>Larghezza Bounding Box</source>
      <translation>Bounding Box Width</translation>
    </message>
    <message>
      <source>Layer di input</source>
      <translation>Input layer</translation>
    </message>
    <message>
      <source>Layer di input non trovato.</source>
      <translation>Input layer not found.</translation>
    </message>
    <message>
      <source>Layer linea di riferimento (solo per criteri 'Posizione/Distanza dalla linea')</source>
      <translation>Reference line layer (only for 'Position along/Distance from line' criteria)</translation>
    </message>
    <message>
      <source>Layer ordinato</source>
      <translation>Sorted layer</translation>
    </message>
    <message>
      <source>Layer:</source>
      <translation>Layer:</translation>
    </message>
    <message>
      <source>Linea di riferimento assente o vuota.</source>
      <translation>Reference line missing or empty.</translation>
    </message>
    <message>
      <source>Lunghezza</source>
      <translation>Length</translation>
    </message>
    <message>
      <source>Lunghezza (linee)</source>
      <translation>Length (lines)</translation>
    </message>
    <message>
      <source>Mai (misura planare nelle unità del CRS)</source>
      <translation>Never (planar measurement in CRS units)</translation>
    </message>
    <message>
      <source>Misura geodetica: automatica (CRS geografico)</source>
      <translation>Geodesic measurement: automatic (geographic CRS)</translation>
    </message>
    <message>
      <source>Misura geodetica: mai (planare)</source>
      <translation>Geodesic measurement: never (planar)</translation>
    </message>
    <message>
      <source>Misura geodetica: sempre</source>
      <translation>Geodesic measurement: always</translation>
    </message>
    <message>
      <source>Misura su CRS geografico:</source>
      <translation>Geographic CRS measurement:</translation>
    </message>
    <message>
      <source>Modalità di calcolo – Distanza dalla linea</source>
      <translation>Calculation mode – Distance from line</translation>
    </message>
    <message>
      <source>Modalità di calcolo – Posizione lungo linea</source>
      <translation>Calculation mode – Position along line</translation>
    </message>
    <message>
      <source>Modalità di misura geodetica (per area/lunghezza/distanza)</source>
      <translation>Geodesic measurement mode (for area/length/distance)</translation>
    </message>
    <message>
      <source>Modalità sconosciuta: '{mode}'. Valori ammessi: {valid}</source>
      <translation>Unknown mode: '{mode}'. Allowed values: {valid}</translation>
    </message>
    <message>
      <source>Nessuna feature selezionata sul layer (è attivo 'Ordina solo le feature selezionate').</source>
      <translation>No features selected on the layer ('Sort only selected features' is enabled).</translation>
    </message>
    <message>
      <source>Nome del campo progressivo</source>
      <translation>Progressive field name</translation>
    </message>
    <message>
      <source>Nome del campo progressivo (default: sort_order).
Se esiste già, i valori vengono sovrascritti.</source>
      <translation>Progressive field name (default: sort_order).
If it already exists, its values are overwritten.</translation>
    </message>
    <message>
      <source>Numerazione: passo (incremento fra feature)</source>
      <translation>Numbering: step (increment between features)</translation>
    </message>
    <message>
      <source>Numerazione: valore iniziale</source>
      <translation>Numbering: starting value</translation>
    </message>
    <message>
      <source>Numero di vertici</source>
      <translation>Number of vertices</translation>
    </message>
    <message>
      <source>Opzioni</source>
      <translation>Options</translation>
    </message>
    <message>
      <source>Ordina feature (GeoSort)</source>
      <translation>Sort features (GeoSort)</translation>
    </message>
    <message>
      <source>Ordina le feature di un layer vettoriale per criteri geometrici e attributivi</source>
      <translation>Sort vector layer features by geometric and attribute criteria</translation>
    </message>
    <message>
      <source>Ordina le feature di un layer vettoriale per criteri geometrici o attributivi e aggiunge il campo &lt;b&gt;sort_order&lt;/b&gt; (numero progressivo, 1 = prima feature).

Criteri disponibili: attributo tabellare, coordinate del centroide, area, lunghezza, perimetro, numero di vertici, bounding box, posizione lungo una linea di riferimento, distanza dalla linea di riferimento, espressione QGIS.

&lt;b&gt;Modalità di ordinamento testuale (attributo/espressione):&lt;/b&gt;
• &lt;b&gt;Lessicografico&lt;/b&gt; (default): confronto carattere per carattere. Esempio: «1010» &amp;lt; «11» &amp;lt; «1111».
• &lt;b&gt;Natural Sort&lt;/b&gt;: le sequenze di cifre sono confrontate come numeri. Esempio: «11» &amp;lt; «1010» &amp;lt; «1111». Utile con campi alfanumerici (FILE1, FILE2, FILE10) o espressioni di concatenazione come &lt;code&gt;"fid" || "id_poly"&lt;/code&gt;.

&lt;b&gt;Ordinamento multi-criterio:&lt;/b&gt; imposta un &lt;b&gt;criterio secondario&lt;/b&gt; per spezzare i pareggi del criterio primario (es. primario = regione, secondario = area decrescente). Disponibile per i criteri non basati su linea.

&lt;b&gt;Punto di riferimento:&lt;/b&gt; per il criterio «Centroide – distanza» è possibile indicare un punto di riferimento (anche col pulsante «... sulla mappa»); se lasciato vuoto si usa l'origine (0,0) come nelle versioni precedenti.

&lt;b&gt;Layer di riferimento (posizione/distanza lungo linea):&lt;/b&gt; se il layer di riferimento ha un CRS diverso da quello del layer di input, viene riproiettato automaticamente prima del calcolo (con un avviso non bloccante).

&lt;b&gt;Numerazione personalizzata (parametri avanzati):&lt;/b&gt; valore iniziale (es. 0), passo (es. 10 → 10, 20, 30...) e nome del campo progressivo (default &lt;b&gt;sort_order&lt;/b&gt;). Se il campo esiste già nel layer di input, i suoi valori vengono sovrascritti invece di creare un duplicato.

&lt;b&gt;Misura geodetica (ellissoidale):&lt;/b&gt; quando il CRS del layer è geografico (coordinate in gradi, es. EPSG:4326), le misure planari di area, lunghezza, perimetro e distanza sarebbero in gradi — metricamente prive di senso. Con la modalità &lt;i&gt;Automatica&lt;/i&gt; (default) GeoSort usa automaticamente il calcolo ellissoidale (QgsDistanceArea) restituendo valori in m² / m. Selezionare &lt;i&gt;Mai&lt;/i&gt; per forzare la misura planare nelle unità del CRS.

Compatibile con il Processing Toolbox, il modellatore grafico e PyQGIS headless.</source>
      <translation>Sorts vector layer features by geometric or attribute criteria and adds the &lt;b&gt;sort_order&lt;/b&gt; field (progressive number, 1 = first feature).

Available criteria: table attribute, centroid coordinates, area, length, perimeter, number of vertices, bounding box, position along a reference line, distance from the reference line, QGIS expression.

&lt;b&gt;Text sorting mode (attribute/expression):&lt;/b&gt;
• &lt;b&gt;Lexicographic&lt;/b&gt; (default): character-by-character comparison. Example: «1010» &amp;lt; «11» &amp;lt; «1111».
• &lt;b&gt;Natural Sort&lt;/b&gt;: digit sequences are compared as numbers. Example: «11» &amp;lt; «1010» &amp;lt; «1111». Useful with alphanumeric fields (FILE1, FILE2, FILE10) or concatenation expressions such as &lt;code&gt;"fid" || "id_poly"&lt;/code&gt;.

&lt;b&gt;Multi-criteria sorting:&lt;/b&gt; set a &lt;b&gt;secondary criterion&lt;/b&gt; to break ties of the primary criterion (e.g. primary = region, secondary = descending area). Available for non line-based criteria.

&lt;b&gt;Reference point:&lt;/b&gt; for the «Centroid – distance» criterion you can provide a reference point (also via the «... on map» button); if left empty, the origin (0,0) is used, as in previous versions.

&lt;b&gt;Reference layer (position/distance along line):&lt;/b&gt; if the reference layer has a CRS different from the input layer's, it is automatically reprojected before the calculation (with a non-blocking warning).

&lt;b&gt;Custom numbering (advanced parameters):&lt;/b&gt; starting value (e.g. 0), step (e.g. 10 → 10, 20, 30...) and the name of the progressive field (default &lt;b&gt;sort_order&lt;/b&gt;). If the field already exists in the input layer, its values are overwritten instead of creating a duplicate.

&lt;b&gt;Geodesic (ellipsoidal) measurement:&lt;/b&gt; when the layer CRS is geographic (coordinates in degrees, e.g. EPSG:4326), planar measures of area, length, perimeter and distance would be in degrees — metrically meaningless. With the &lt;i&gt;Automatic&lt;/i&gt; mode (default) GeoSort automatically uses ellipsoidal calculation (QgsDistanceArea) returning values in m² / m. Select &lt;i&gt;Never&lt;/i&gt; to force planar measurement in CRS units.

Compatible with the Processing Toolbox, the graphical modeler and headless PyQGIS.</translation>
    </message>
    <message>
      <source>Ordina solo le feature selezionate</source>
      <translation>Sort only selected features</translation>
    </message>
    <message>
      <source>Ordinamento in corso...</source>
      <translation>Sorting...</translation>
    </message>
    <message>
      <source>Ordinamento naturale – Natural Sort (es. 1, 2, 10 invece di 1, 10, 2)</source>
      <translation>Natural Sort (e.g. 1, 2, 10 instead of 1, 10, 2)</translation>
    </message>
    <message>
      <source>Ordinamento naturale – Natural Sort (solo per criterio attributo/espressione)</source>
      <translation>Natural Sort (attribute/expression criterion only)</translation>
    </message>
    <message>
      <source>Ordine ascendente</source>
      <translation>Ascending order</translation>
    </message>
    <message>
      <source>Output</source>
      <translation>Output</translation>
    </message>
    <message>
      <source>Passo:</source>
      <translation>Step:</translation>
    </message>
    <message>
      <source>Per attributo / espressione</source>
      <translation>By attribute / expression</translation>
    </message>
    <message>
      <source>Per coordinate centroide</source>
      <translation>By centroid coordinates</translation>
    </message>
    <message>
      <source>Per distanza dalla linea</source>
      <translation>By distance from line</translation>
    </message>
    <message>
      <source>Per posizione lungo linea</source>
      <translation>By position along line</translation>
    </message>
    <message>
      <source>Per proprietà geometrica</source>
      <translation>By geometric property</translation>
    </message>
    <message>
      <source>Perimetro</source>
      <translation>Perimeter</translation>
    </message>
    <message>
      <source>Perimetro (poligoni)</source>
      <translation>Perimeter (polygons)</translation>
    </message>
    <message>
      <source>Posizione lungo linea di riferimento</source>
      <translation>Position along reference line</translation>
    </message>
    <message>
      <source>Proiezione centroide  –  tutte le feature</source>
      <translation>Centroid projection  –  all features</translation>
    </message>
    <message>
      <source>Proiezione centroide: include tutte le feature, usa il centroide proiettato sulla linea.
Solo intersecanti – centroide: esclude le feature che non intersecano la linea.
Solo intersecanti – primo punto: usa il punto in cui la feature tocca per primo la linea.</source>
      <translation>Centroid projection: includes all features, uses the centroid projected onto the line.
Intersecting only – centroid: excludes features that do not intersect the line.
Intersecting only – first point: uses the point where the feature first touches the line.</translation>
    </message>
    <message>
      <source>Punto di riferimento (X, Y)</source>
      <translation>Reference point (X, Y)</translation>
    </message>
    <message>
      <source>Punto di riferimento (solo per criterio 'Centroide – distanza'; vuoto = origine 0,0)</source>
      <translation>Reference point (only for the 'Centroid – distance' criterion; empty = origin 0,0)</translation>
    </message>
    <message>
      <source>Rimuovi</source>
      <translation>Remove</translation>
    </message>
    <message>
      <source>Rimuovi l'espressione attiva e torna al campo singolo</source>
      <translation>Remove the active expression and return to single field</translation>
    </message>
    <message>
      <source>Scrittura output...</source>
      <translation>Writing output...</translation>
    </message>
    <message>
      <source>Se attivo, l'ordinamento considera solo le feature attualmente
selezionate sul layer. In modalità 'Aggiorna layer corrente' il
campo sort_order viene scritto solo su quelle feature.</source>
      <translation>If enabled, sorting only considers the features currently
selected on the layer. In 'Update current layer' mode the
sort_order field is written only for those features.</translation>
    </message>
    <message>
      <source>Seleziona punto sulla mappa</source>
      <translation>Pick point on map</translation>
    </message>
    <message>
      <source>Sempre geodetica</source>
      <translation>Always geodesic</translation>
    </message>
    <message>
      <source>Solo intersecanti  –  primo punto di intersezione</source>
      <translation>Intersecting only  –  first intersection point</translation>
    </message>
    <message>
      <source>Solo intersecanti  –  proiezione centroide</source>
      <translation>Intersecting only  –  centroid projection</translation>
    </message>
    <message>
      <source>Solo intersecanti –  primo punto di intersezione</source>
      <translation>Intersecting only –  first intersection point</translation>
    </message>
    <message>
      <source>Solo intersecanti –  proiezione centroide</source>
      <translation>Intersecting only –  centroid projection</translation>
    </message>
    <message>
      <source>Specificare un campo attributo per il criterio 'Attributo tabellare'.</source>
      <translation>Specify an attribute field for the 'Table attribute' criterion.</translation>
    </message>
    <message>
      <source>Specificare un campo attributo per il criterio primario.</source>
      <translation>Specify an attribute field for the primary criterion.</translation>
    </message>
    <message>
      <source>Specificare un campo per il criterio secondario.</source>
      <translation>Specify a field for the secondary criterion.</translation>
    </message>
    <message>
      <source>Specificare un layer di riferimento per il criterio 'Distanza dalla linea'.</source>
      <translation>Specify a reference layer for the 'Distance from line' criterion.</translation>
    </message>
    <message>
      <source>Specificare un layer di riferimento per il criterio 'Posizione lungo linea'.</source>
      <translation>Specify a reference layer for the 'Position along line' criterion.</translation>
    </message>
    <message>
      <source>Specificare un'espressione per il criterio 'Espressione QGIS'.</source>
      <translation>Specify an expression for the 'QGIS expression' criterion.</translation>
    </message>
    <message>
      <source>Specificare un'espressione per il criterio primario.</source>
      <translation>Specify an expression for the primary criterion.</translation>
    </message>
    <message>
      <source>Specificare un'espressione per il criterio secondario.</source>
      <translation>Specify an expression for the secondary criterion.</translation>
    </message>
    <message>
      <source>Spezza i pareggi del criterio primario (es. primario = Regione, secondario = Area). Non disponibile se il criterio primario è basato su linea.</source>
      <translation>Breaks ties of the primary criterion (e.g. primary = Region, secondary = Area). Not available when the primary criterion is line-based.</translation>
    </message>
    <message>
      <source>Su CRS geografico (gradi, es. EPSG:4326), area/lunghezza/distanze
vengono misurate sull'ellissoide (m²/m) invece che in gradi.
• Automatica: geodetica solo se il CRS è geografico (consigliato).
• Sempre: geodetica anche su CRS proiettati.
• Mai (planare): misura nelle unità native del CRS.</source>
      <translation>On a geographic CRS (degrees, e.g. EPSG:4326), area/length/distances
are measured on the ellipsoid (m²/m) instead of degrees.
• Automatic: geodesic only if the CRS is geographic (recommended).
• Always: geodesic even on projected CRS.
• Never (planar): measured in the native CRS units.</translation>
    </message>
    <message>
      <source>Valore criterio</source>
      <translation>Criterion value</translation>
    </message>
    <message>
      <source>Valore iniziale della numerazione (es. 0 o 1).</source>
      <translation>Starting value of the numbering (e.g. 0 or 1).</translation>
    </message>
    <message>
      <source>Valori NULL in fondo (attributo e espressione)</source>
      <translation>NULL values last (attribute and expression)</translation>
    </message>
    <message>
      <source>Valori NULL in fondo (solo per criterio attributo)</source>
      <translation>NULL values last (attribute criterion only)</translation>
    </message>
    <message>
      <source>Xmin Bounding Box</source>
      <translation>Bounding Box Xmin</translation>
    </message>
    <message>
      <source>Ymin Bounding Box</source>
      <translation>Bounding Box Ymin</translation>
    </message>
    <message>
      <source>sort_order</source>
      <translation>sort_order</translation>
    </message>
  </context>
</TS>
