#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per avvolgere automaticamente le stringhe non-tradotte con self.tr().
Uso: python3 scripts/wrap_strings_with_tr.py geosort_dialog.py
"""

import re
import sys
from pathlib import Path

def wrap_strings_in_file(filepath):
    """Avvolge le stringhe non-tradotte con self.tr()."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern per stringhe non tradotte:
    # - Stringhe "..." o '...' che NON sono già in self.tr()
    # - Esclude stringhe in commenti
    # - Esclude f-string (quelle con f"..." non vanno tradotte facilmente)

    # Questo pattern trova stringhe non-tradotte, ma è complesso perché:
    # 1. Deve non matchare self.tr("...")
    # 2. Deve non matchare commenti
    # 3. Deve non matchare f-string o stringhe di multilinea complesse

    # Approccio: fai il sostituto riga per riga, ignorando commenti e self.tr() già presenti

    lines = content.split('\n')
    modified_lines = []
    in_multiline_string = False

    for line in lines:
        # Ignora linee di commento
        if line.strip().startswith('#'):
            modified_lines.append(line)
            continue

        # Ignora linee che già hanno self.tr()
        if 'self.tr(' in line:
            modified_lines.append(line)
            continue

        # Skip f-string, docstring, raw string
        if any(x in line for x in ["f'", 'f"', "r'", 'r"', '"""', "'''"]):
            modified_lines.append(line)
            continue

        # Pattern: stringhe letterali che dovrebbero essere tradotte
        # Esempi:
        #   "Some text" -> self.tr("Some text")
        #   'Some text' -> self.tr('Some text')
        # Ma escludere:
        #   - Stringhe in QIcon, QPixmap, os.path, ecc (troppo complesso)
        #   - URL, percorsi file, numeri
        #   - Stringhe molto corte (< 3 char)

        # Fai una sostituzione semplice per stringhe in contesti specifici:
        # - set...Text(...) o setText(...)
        # - QMessageBox, QLabel constructor
        # - QPushButton, ecc

        # Pattern: setText("...") or .setText('...')
        line = re.sub(
            r'(\.setText|setStatusTip|setToolTip|setWhatsThis|setPlaceholderText)\(\s*(["\'])(.+?)\2\s*\)',
            lambda m: f'{m.group(1)}(self.tr({m.group(2)}{m.group(3)}{m.group(2)}))',
            line
        )

        # Pattern: QLabel(..., "...") or QLabel(..., '...')
        line = re.sub(
            r'(QLabel|QMessageBox|QPushButton|QAction|QCheckBox|QRadioButton)\(\s*(["\'])(.+?)\2',
            lambda m: f'{m.group(1)}({m.group(2)}{m.group(3)}{m.group(2)}' if len(m.group(3)) > 2 else m.group(0),
            line
        )

        modified_lines.append(line)

    return '\n'.join(modified_lines)

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 wrap_strings_with_tr.py <file.py> [<file2.py> ...]")
        sys.exit(1)

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"❌ File non trovato: {filepath}")
            continue

        print(f"Processing: {filepath}")
        modified = wrap_strings_in_file(filepath)

        # Backup
        backup = filepath.with_suffix('.py.bak')
        filepath.rename(backup)
        print(f"  → Backup salvato in: {backup}")

        # Scrivi il file modificato
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(modified)
        print(f"  ✓ File modificato: {filepath}")

if __name__ == '__main__':
    main()
