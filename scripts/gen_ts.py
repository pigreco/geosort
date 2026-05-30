# -*- coding: utf-8 -*-
"""Rigenera i18n/geosort_it.ts e geosort_en.ts da tutte le stringhe self.tr()
del codice. Mantiene i due file perfettamente sincronizzati e ben formati.

Uso:  python3 scripts/gen_ts.py
"""
import os
import re
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = ["geosort_dialog.py", "geosort_algorithm.py", "geosort_core.py"]

# Stringhe tradotte fuori da self.tr() (azione di menu in geosort.py)
EXTRA = [
    "GeoSort – Advanced Geometry Sorting",
    "Ordina le feature di un layer vettoriale per criteri geometrici e attributivi",
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
    "Anteprima (prime 10 feature ordinate)": "Preview (first 10 sorted features)",
    "FID": "FID",
    "sort_order": "sort_order",
    "Valore criterio": "Criterion value",
    "Aggiorna anteprima": "Refresh preview",
    "Help": "Help",
    "Applica": "Apply",
    "Annulla": "Cancel",
    "Chiudi": "Close",
}

# Traduzioni italiane: identità tranne i source in inglese
IT_OVERRIDE = {
    "GeoSort – Advanced Geometry Sorting": "GeoSort – Ordinamento Avanzato delle Geometrie",
    "Input Layer": "Layer di input",
    "CRS / Units:": "CRS / Unità:",
    "Help": "Aiuto",
}

TR_RE = re.compile(r'self\.tr\(\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')')


def collect_sources():
    seen, out = set(), []
    for name in EXTRA:
        if name not in seen:
            seen.add(name)
            out.append(name)
    for fname in MODULES:
        text = open(os.path.join(ROOT, fname), encoding="utf-8").read()
        for m in TR_RE.finditer(text):
            val = eval(m.group(1))
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
