#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per generare i file .ts (Translation Source) dai file Python.
Estrae le stringhe con self.tr("...") e le raccogli in file .ts XML.
"""

import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

def extract_strings_from_file(filepath):
    """Estrae tutte le stringhe con self.tr("...") da un file Python."""
    strings = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern per self.tr("...") e self.tr('...')
    pattern = r'self\.tr\((["\'])(.+?)\1\)'
    matches = re.findall(pattern, content, re.DOTALL)

    for _, string in matches:
        # Pulisci spazi e newline extra
        string = string.replace('\n', ' ').strip()
        if string and string not in strings:
            strings.append(string)

    return strings

def create_ts_file(output_path, strings):
    """Crea un file .ts con le stringhe estratte."""
    # Radice XML
    root = ET.Element('TS')
    root.set('version', '2.1')
    output_str = str(output_path)
    root.set('language', 'it' if 'it' in output_str else 'en')

    context = ET.SubElement(root, 'context')
    name = ET.SubElement(context, 'name')
    name.text = 'GeoSort'

    for string in sorted(strings):
        message = ET.SubElement(context, 'message')
        source = ET.SubElement(message, 'source')
        source.text = string
        translation = ET.SubElement(message, 'translation')
        translation.set('type', 'unfinished')
        translation.text = ''

    # Pretty-print con indentazione
    _indent(root)
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"✓ Creato: {output_path}")

def _indent(elem, level=0):
    """Indenta un elemento XML per leggibilità."""
    indent = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent

def main():
    plugin_dir = Path(__file__).parent.parent
    i18n_dir = plugin_dir / 'i18n'
    i18n_dir.mkdir(exist_ok=True)

    # Raccogli tutte le stringhe da tutti i file Python
    all_strings = set()
    for py_file in plugin_dir.glob('*.py'):
        if py_file.name.startswith('test_'):
            continue
        strings = extract_strings_from_file(py_file)
        all_strings.update(strings)

    # Crea i file .ts per italiano e inglese
    for lang in ['it', 'en']:
        ts_file = i18n_dir / f'geosort_{lang}.ts'
        create_ts_file(ts_file, sorted(all_strings))

    print(f"\n✓ Estratte {len(all_strings)} stringhe")
    print(f"Prossimi step:")
    print(f"  1. Aprire i file .ts in Qt Linguist e tradurre")
    print(f"  2. Compilare con lrelease: lrelease i18n/geosort_*.ts")

if __name__ == '__main__':
    main()
