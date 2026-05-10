# GeoSort – Ordinamento Avanzato delle Geometrie

Plugin QGIS (≥ 3.16) per ordinare le feature di un layer vettoriale in base
a criteri geometrici e attributivi, con assegnazione automatica del campo
progressivo `sort_order`.

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
    'ADD_VALUE_FIELD': False,
    'OUTPUT': 'memory:'
})
output_layer = result['OUTPUT']
```

---

## Requisiti

- QGIS ≥ 3.16 LTR
- Python ≥ 3.9
- Nessuna dipendenza esterna (solo API PyQGIS e librerie standard Python)

---

## Test

I test della logica di ordinamento non richiedono QGIS:

```bash
cd geosort
python -m pytest tests/test_sorting.py -v
# oppure
python -m unittest tests.test_sorting -v
```

I test del dialog richiedono QGIS nel PATH:

```bash
python -m pytest tests/test_dialog.py -v
```

---

## Licenza

GPL v2 o superiore – vedi file `LICENSE`.
