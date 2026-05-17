#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggiungi le traduzioni italiane al file .ts
"""

from pathlib import Path
from xml.etree import ElementTree as ET

TRANSLATIONS = {
    "Aggiorna anteprima": "Aggiorna anteprima",
    "Annulla": "Annulla",
    "Anteprima (prime 10 feature ordinate)": "Anteprima (prime 10 feature ordinate)",
    "Applica": "Applica",
    "Ascendente ↑": "Ascendente ↑",
    "CRS / Units:": "CRS / Unità:",
    "Chiudi": "Chiudi",
    "Crea nuovo layer in memoria": "Crea nuovo layer in memoria",
    "Criterio di ordinamento": "Criterio di ordinamento",
    "Direzione:": "Direzione:",
    "Discendente ↓": "Discendente ↓",
    "Distanza dal centroide": "Distanza dal centroide",
    "Distanza dall'elemento": "Distanza dall'elemento",
    "GeoSort – Advanced Geometry Sorting": "GeoSort – Ordinamento Avanzato delle Geometrie",
    "Help": "Aiuto",
    "Input Layer": "Layer di input",
    "Layer:": "Layer:",
    "Opzioni": "Opzioni",
    "Ordinamento naturale – Natural Sort (es. 1, 2, 10 invece di 1, 10, 2)":
        "Ordinamento naturale – Natural Sort (es. 1, 2, 10 invece di 1, 10, 2)",
    "Output": "Output",
    "Per coordinate centroide": "Per coordinate centroide",
    "Per distanza dalla linea": "Per distanza dalla linea",
    "Per posizione lungo linea": "Per posizione lungo linea",
    "Per proprietà geometrica": "Per proprietà geometrica",
    "Punto di riferimento (X, Y)": "Punto di riferimento (X, Y)",
    "Rimuovi": "Rimuovi",
    "Rimuovi l'espressione attiva e torna al campo singolo":
        "Rimuovi l'espressione attiva e torna al campo singolo",
    "Seleziona punto sulla mappa": "Seleziona punto sulla mappa",
    "Valori NULL in fondo (attributo e espressione)":
        "Valori NULL in fondo (attributo e espressione)",
}

def add_translations():
    ts_file = Path("i18n/geosort_it.ts")
    tree = ET.parse(ts_file)
    root = tree.getroot()

    # Trova tutti i tag <translation>
    for message in root.findall(".//message"):
        source = message.find("source")
        translation = message.find("translation")

        if source is not None and translation is not None:
            text = source.text
            if text in TRANSLATIONS:
                translation.text = TRANSLATIONS[text]
                translation.set('type', '')  # Rimuovi type="unfinished"

    # Scrivi
    tree.write(ts_file, encoding='utf-8', xml_declaration=True)
    print(f"✓ Traduzioni italiane aggiunte: {ts_file}")

if __name__ == '__main__':
    add_translations()
