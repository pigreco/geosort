# GeoSort – Ordinamento Avanzato delle Geometrie

Plugin QGIS per ordinare le feature di un layer vettoriale in base a criteri
geometrici e attributivi, con assegnazione automatica del campo progressivo
`sort_order`.

Compatibile con **QGIS 3.16+** (Qt5 / PyQt5) e **QGIS 4.x** (Qt6 / PyQt6).

![](gui.png)

---

## Funzionalità

| Criterio | Tipi di geometria | Descrizione |
|---|---|---|
| Attributo tabellare | Tutti | Ordina per il valore di qualsiasi campo (String, Int, Double, Date) |
| Coordinata centroide X / Y | Tutti | Ordina per la posizione geografica del centroide |
| Distanza da origine | Tutti | Distanza euclidea del centroide dall'origine (0, 0) |
| Area | Poligoni | Superficie della geometria |
| Perimetro | Poligoni | Lunghezza del perimetro |
| Lunghezza | Linee | Lunghezza totale della linea |
| Numero di vertici | Tutti | Conteggio dei vertici della geometria |
| Bounding Box | Tutti | Larghezza, altezza, area, Xmin, Ymin del bounding box |
| Posizione lungo linea | Tutti | Proiezione del centroide su una linea di riferimento |
| Espressione QGIS | Tutti | Ordina per il risultato di un'espressione QGIS arbitraria |

### Modalità di ordinamento testuale

Per i criteri **Attributo tabellare** ed **Espressione QGIS** è possibile scegliere tra due modalità:

| Modalità | Comportamento | Esempio |
|---|---|---|
| **Lessicografico** (default) | Confronto carattere per carattere | `"1010"` < `"11"` < `"1111"` |
| **Natural Sort** | Le sequenze di cifre sono confrontate come numeri interi | `"11"` < `"1010"` < `"1111"` |

Il Natural Sort è utile con espressioni di concatenazione (es. `"fid" || "id_poly"`)
o con campi alfanumerici come `FILE1`, `FILE2`, `FILE10`.

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

Il campo `sort_order` viene aggiunto/aggiornato sul layer (o su un nuovo layer
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
    'ATTRIBUTE_FIELD': 'area',
    'DIRECTION': True,        # True = Ascendente
    'NULLS_LAST': True,
    'NATURAL_SORT': False,   # True = Natural Sort (cifre come numeri)
    'ADD_VALUE_FIELD': False,
    'OUTPUT': 'memory:'
})
output_layer = result['OUTPUT']
```

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
```

I test del dialog richiedono QGIS nel PATH:

```bash
python -m pytest tests/test_dialog.py -v
```

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
