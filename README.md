# GeoSort – Ordinamento Avanzato delle Geometrie

🇮🇹 **Italiano** | [🇬🇧 English](README.en.md)

[![Version](https://img.shields.io/badge/version-1.11.0-blue.svg)](https://github.com/pigreco/geosort/releases)
[![Languages](https://img.shields.io/badge/languages-IT%20%7C%20EN-green.svg)](#lingue--languages)
[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B%20%7C%204.x-orange.svg)](#requisiti)
[![License](https://img.shields.io/badge/license-GPLv2-red.svg)](LICENSE)
[![Tests](https://github.com/pigreco/geosort/actions/workflows/tests.yml/badge.svg)](https://github.com/pigreco/geosort/actions/workflows/tests.yml)

---

Plugin QGIS per ordinare le feature di un layer vettoriale in base a criteri
geometrici e attributivi, con assegnazione automatica di un campo progressivo
(default `sort_order`, nome/valore iniziale/passo personalizzabili).

Compatibile con **QGIS 3.16+** (Qt5 / PyQt5) e **QGIS 4.x** (Qt6 / PyQt6).

![](gui.png)

---

## Funzionalità

| Criterio | Tipi di geometria | Descrizione |
|---|---|---|
| Attributo tabellare | Tutti | Ordina per il valore di qualsiasi campo (String, Int, Double, Date) |
| Coordinata centroide X / Y | Tutti | Ordina per la posizione geografica del centroide |
| Distanza da punto di riferimento | Tutti | Distanza euclidea del centroide da un punto configurabile (default origine 0, 0) |
| Area | Poligoni | Superficie della geometria |
| Perimetro | Poligoni | Lunghezza del perimetro |
| Lunghezza | Linee | Lunghezza totale della linea |
| Numero di vertici | Tutti | Conteggio dei vertici della geometria |
| Bounding Box | Tutti | Larghezza, altezza, area, Xmin, Ymin del bounding box |
| Distanza dalla linea | Tutti | Distanza perpendicolare da una linea di riferimento (due modalità: centroide o elemento) |
| Posizione lungo linea | Tutti | Proiezione del centroide su una linea di riferimento (tre modalità) |
| Curva di Hilbert | Tutti | Ordina lungo una curva di Hilbert calcolata sui centroidi normalizzati sull'extent: le feature vicine nello spazio restano vicine nell'ordine |
| Espressione QGIS | Tutti | Ordina per il risultato di un'espressione QGIS arbitraria |
| Serpentina (bande orizzontali) | Tutti | Bande orizzontali per Y, X alternato crescente/decrescente da una banda alla successiva (boustrophedon) — l'ordine classico per serie cartografiche a taglio regolare e percorsi di volo fotogrammetrico |
| **Multi-criterio (gerarchico)** | Tutti | Criterio secondario per spezzare i pareggi del primario (es. regione → area) |

> **Robustezza:** le feature con geometria NULL/vuota e i layer a geometria mista non
> causano errori — le feature non ordinabili spazialmente vengono relegate in fondo.

> **Solo feature selezionate:** l'ordinamento può essere limitato alle feature
> selezionate, sia nel dialogo (checkbox *Ordina solo le feature selezionate*) sia
> nel Processing (spunta nativa di QGIS sul layer di input). In modalità *Aggiorna
> layer corrente* il campo `sort_order` viene scritto solo su quelle feature.

### Misura geodetica (CRS geografici)

Su layer con CRS in gradi (es. EPSG:4326) le misure planari di area e lunghezza sono
espresse in gradi² — metricamente inutili e potenzialmente fuorvianti alle alte latitudini.
GeoSort risolve il problema misurando **area, perimetro, lunghezza e distanze
sull'ellissoide** (misura geodetica, risultati in m² o m).

| Modalità | Comportamento |
|---|---|
| **Auto** (default) | Geodetica attivata automaticamente su CRS geografico; planare su CRS proiettato. Un avviso non bloccante segnala l'attivazione. |
| **Sempre** | Geodetica sempre attiva, indipendentemente dal CRS. |
| **Mai** | Sempre planare, indipendentemente dal CRS. |

I criteri **bounding box** e **posizione lungo linea** restano sempre planari (il bounding
box è un concetto nelle coordinate native; la posizione lungo linea è monotona e invariante
rispetto alla scala).

### Ordinamento multi-criterio

È possibile impostare un **criterio secondario** che spezza i pareggi del criterio primario.
Esempio tipico: ordinare per *regione* (crescente) e, a parità di regione, per *area*
(decrescente). Ogni livello ha la propria direzione. Disponibile sia nel dialogo
(menu a tendina **Criterio secondario**) sia nel Processing (parametri `SECONDARY_*`).
Non disponibile quando il criterio primario è basato su una linea di riferimento, è la
curva di Hilbert o la serpentina.

### Modalità di ordinamento testuale

Per i criteri **Attributo tabellare** ed **Espressione QGIS** è possibile scegliere tra due modalità:

| Modalità | Comportamento | Esempio |
|---|---|---|
| **Lessicografico** (default) | Confronto carattere per carattere | `"1010"` < `"11"` < `"1111"` |
| **Natural Sort** | Le sequenze di cifre sono confrontate come numeri interi | `"11"` < `"1010"` < `"1111"` |

Il Natural Sort è utile con espressioni di concatenazione (es. `"fid" || "id_poly"`)
o con campi alfanumerici come `FILE1`, `FILE2`, `FILE10`.

### Numerazione personalizzata

Il campo progressivo è configurabile su tre assi, sia nel dialogo che nel Processing:

| Parametro | Default | Esempio |
|---|---|---|
| Nome del campo | `sort_order` | `rank`, `ordine` — se il campo esiste già sul layer, viene sovrascritto invece di duplicato |
| Valore iniziale | `1` | `0` per una numerazione da zero |
| Passo | `1` | `10` → `10, 20, 30…`, per lasciare spazio a inserimenti futuri |

---

## Installazione

1. Scarica il file `.zip` del plugin
2. In QGIS: **Plugin → Gestisci e Installa Plugin → Installa da ZIP**
3. Seleziona il file `geosort.zip`
4. Il plugin sarà disponibile nel menu **Vettore → GeoSort**

---

## Utilizzo

1. Carica un layer vettoriale nel progetto QGIS
2. Apri **Vettore → GeoSort → GeoSort – Ordinamento geometrie**
3. Seleziona il layer di input e il criterio di ordinamento
4. Scegli la direzione (Ascendente / Discendente)
5. Usa il pulsante **Anteprima** per verificare il risultato
6. Premi **OK** per applicare o **Applica** per mantenere il dialogo aperto

Il campo progressivo (default `sort_order`, personalizzabile — nome, valore
iniziale, passo) viene aggiunto/aggiornato sul layer (o su un nuovo layer
in memoria, se selezionata l'opzione corrispondente).

---

## Processing Toolbox

GeoSort è disponibile anche nel Processing Toolbox di QGIS:
**Toolbox → GeoSort → Ordina feature (GeoSort)**

Questo permette di usarlo in batch, nel modellatore grafico e via PyQGIS headless:

```python
import processing
result = processing.run("geosort:geosort_sort", {
    'INPUT': layer,
    'CRITERION': 0,          # 0 = Attributo tabellare
    'ATTRIBUTE_FIELD': 'regione',
    'DIRECTION': True,        # True = Ascendente
    'NULLS_LAST': True,
    'NATURAL_SORT': False,   # True = Natural Sort (cifre come numeri)
    # Criterio secondario (tie-break): 0 = nessuno, 1 = attributo, 2 = espressione,
    # 3 = centroide X, 4 = centroide Y, 5 = area, ...
    'SECONDARY_CRITERION': 5,    # 5 = Area (poligoni)
    'SECONDARY_DIRECTION': False,  # False = Discendente
    'ADD_VALUE_FIELD': False,
    # Numerazione personalizzata (parametri avanzati, tutti opzionali):
    'START': 0,               # default 1
    'STEP': 10,                # default 1 → 0, 10, 20, 30...
    'ORDER_FIELD': 'rank',    # default 'sort_order'
    'OUTPUT': 'memory:'
})
output_layer = result['OUTPUT']
```

> Il criterio secondario è ignorato se il criterio primario è basato su una linea
> (`line_position` / `line_distance`).

Per il criterio `centroid_dist` (indice `3`, distanza dal centroide) è possibile
indicare un punto di riferimento diverso dall'origine con il parametro
`REF_POINT` (opzionale, formato `"x,y [EPSG:xxxx]"` o `QgsPointXY`):

```python
result = processing.run("geosort:geosort_sort", {
    'INPUT': layer,
    'CRITERION': 3,                          # centroide – distanza
    'REF_POINT': '500000,4649776 [EPSG:32633]',
    'DIRECTION': True,
    'OUTPUT': 'memory:'
})
```

Per ordinare solo le feature selezionate da PyQGIS:

```python
from qgis.core import QgsProcessingFeatureSourceDefinition
result = processing.run("geosort:geosort_sort", {
    'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True),
    'CRITERION': 1,
    'OUTPUT': 'memory:'
})
```

---

## Lingue / Languages

GeoSort supporta **Italiano** e **Inglese** con traduzioni complete. La lingua è rilevata 
automaticamente dalla configurazione di QGIS — non è richiesto nessun intervento da parte 
dell'utente.

Le traduzioni sono fornite sia in formato sorgente (`.ts`) che compilato (`.qm` binario), 
permettendo il caricamento istantaneo senza dipendenze di compilazione.

### Aggiungere una nuova lingua

I file `.ts` **non vanno modificati a mano**: sono generati da `scripts/gen_ts.py`, unica
fonte di verità che estrae tutte le stringhe `self.tr()` dal codice e riscrive entrambi i
file `i18n/geosort_*.ts` sincronizzati e ben formati.

```bash
# 1. Aggiungi le traduzioni nella mappa del generatore scripts/gen_ts.py
#    (dizionario EN per l'inglese; per una nuova lingua aggiungi una mappa
#     XX e una chiamata build('xx', XX))

# 2. Rigenera i file .ts (IT ed EN sempre allineati)
python3 scripts/gen_ts.py

# 3. (Opzionale) Compila i .qm per la distribuzione
lrelease i18n/geosort_*.ts
```

Il plugin rileva automaticamente i file `.qm` compilati; se non disponibili, carica i `.ts`
come fallback.

---

## Requisiti

- QGIS ≥ 3.16 LTR oppure QGIS 4.x
- Python ≥ 3.9
- Nessuna dipendenza esterna (solo API PyQGIS e librerie standard Python)

---

## Compatibilità Qt5 / Qt6

Il plugin utilizza le API PyQGIS standard e non dipende direttamente da Qt5 o Qt6.
L'adattamento a QGIS 4 / PyQt6 riguarda:

- Enum qualificati (`QgsWkbTypes.GeometryType.PointGeometry` invece di `QgsWkbTypes.PointGeometry`)
- `QMetaType.Type` al posto di `QVariant.Type` per la definizione dei campi
- `exec()` al posto di `exec_()` per i dialoghi modali (deprecato in PyQt6)

Nessuna modifica è richiesta all'utente finale: lo stesso file `.zip` funziona
su entrambe le versioni di QGIS.

---

## Test

I test della logica di ordinamento non richiedono QGIS:

```bash
cd geosort
python -m unittest tests.test_sorting -v
# 173 test sulla logica core (sort_by_attribute, sort_by_centroid, sort_multi, robustezza geometrie NULL, misura geodetica, ecc.)
```

I test del dialog e dell'algoritmo Processing richiedono QGIS nel PATH:

```bash
python -m unittest tests.test_dialog -v     # Test UI (32 test)
python -m unittest tests.test_algorithm -v  # Test Processing Toolbox, tutti e 17 i criteri (52 test)
```

Eseguire tutti i test:

```bash
python -m unittest discover tests -p "test_*.py" -v
# Output: 248 tests (173 ok, 75 skipped che richiedono QGIS)
```

Ogni push e pull request esegue automaticamente l'intera suite su GitHub Actions:
i test core su Python puro e i test QGIS sui container `qgis/qgis:ltr` e
`qgis/qgis:latest` (quindi anche QGIS 4).

---

## Contributing

### Clonare e preparare l'ambiente

```bash
git clone https://github.com/<user>/geosort.git
cd geosort
# Nessuna dipendenza pip: il plugin usa solo PyQGIS e la stdlib Python
```

### Eseguire i test

I test della logica core non richiedono QGIS:

```bash
python3 -m unittest tests.test_sorting -v
# oppure, se pytest è installato:
python3 -m pytest tests/test_sorting.py -v
```

I test del dialog richiedono QGIS nel PATH:

```bash
python3 -m pytest tests/test_dialog.py -v
```

### Stile dei commit

- Messaggi in italiano, presente indicativo: `Aggiunge`, `Corregge`, `Rimuove`
- Prima riga ≤ 72 caratteri; dettagli nel corpo dopo una riga vuota
- Un commit per funzionalità/fix logicamente separata

### Convenzioni di naming

- **Moduli**: `snake_case` (`geosort_core.py`)
- **Classi**: `PascalCase` (`GeoSortDialog`)
- **Metodi e variabili**: `snake_case`; slot `_on_<evento>`, builder `_build_<widget>`
- **Costanti**: `UPPER_SNAKE_CASE` (`LOG_TAG`, `GEOM_CRITERIA`)

### Struttura ZIP per la release

```
geosort.zip
└── geosort/          ← cartella radice (stessa del repository)
    ├── metadata.txt
    ├── __init__.py
    └── ...
```

Il nome del file ZIP **non include** il numero di versione.

---

## Licenza

GPL v2 o superiore – vedi file `LICENSE`.

---

## Ringraziamenti

Questo plugin è stato realizzato con l'ausilio di [Claude Code](https://claude.ai/code) (Anthropic).
