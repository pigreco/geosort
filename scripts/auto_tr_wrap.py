#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrap automatico di stringhe con self.tr() in file Python.
Smartly evita di wrappare: f-string, raw string, percorsi, URL, stringhe già in self.tr().
"""

import re
import sys
from pathlib import Path

def should_translate(s):
    """Determina se una stringa dovrebbe essere tradotta."""
    # Stringhe troppo corte (< 3 char)
    if len(s) < 3:
        return False

    # Stringhe con solo numeri, spazi, punteggiatura
    if re.match(r'^[\d\s\-\.:,;=]+$', s):
        return False

    # Percorsi file, URL
    if any(x in s for x in ['/', '\\', '.svg', '.png', '.qm', '.ts', 'http', 'file']):
        return False

    # Stringhe di CSS/stylesheet
    if any(x in s for x in ['color:', 'font-', 'padding', 'margin', '{', '}']):
        return False

    # Stringhe di formato (con %)
    if '%' in s:
        return False

    # Stringhe di sola punteggiatura
    if re.match(r'^[\s\-\—–=:,.!?/\\()«»\'"]+$', s):
        return False

    return True

def auto_wrap_tr(filepath):
    """Avvolge automaticamente le stringhe con self.tr()."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Strategia: process riga per riga, evitando:
    # - Commenti
    # - String già in self.tr() o tr()
    # - f-string, raw string
    # - QCoreApplication.translate() (le convertiamo a self.tr())

    lines = content.split('\n')
    modified_lines = []
    in_docstring = False

    for line_num, line in enumerate(lines, 1):
        original_line = line

        # Rileva docstring
        if '"""' in line or "'''" in line:
            in_docstring = not in_docstring

        if in_docstring:
            modified_lines.append(line)
            continue

        # Salta linee di commento puro
        stripped = line.lstrip()
        if stripped.startswith('#'):
            modified_lines.append(line)
            continue

        # Salta linee che già hanno self.tr() o tr()
        if 'self.tr(' in line or ' tr(' in line:
            modified_lines.append(line)
            continue

        # Salta f-string, raw string
        if "f'" in line or 'f"' in line or "r'" in line or 'r"' in line:
            modified_lines.append(line)
            continue

        # Converti QCoreApplication.translate(..., "text") -> self.tr("text")
        line = re.sub(
            r'QCoreApplication\.translate\(["\'].*?["\']\s*,\s*(["\'])(.+?)\1',
            r'self.tr(\1\2\1',
            line
        )

        # Wrap stringhe in contesti comuni:
        # 1. setText("..."), setToolTip("..."), ecc.
        patterns = [
            (r'(\.setText|setToolTip|setStatusTip|setPlaceholderText|setWhatsThis)\(\s*(["\'])(.+?)\2\s*\)',
             lambda m: (
                f'{m.group(1)}(self.tr({m.group(2)}{m.group(3)}{m.group(2)}))'
                if should_translate(m.group(3)) else m.group(0)
             )),
            # 2. QGroupBox("..."), QLabel("..."), ecc.
            (r'(QGroupBox|QLabel|QPushButton|QCheckBox|QRadioButton|QAction|QMessageBox)\(\s*(["\'])(.+?)\2',
             lambda m: (
                f'{m.group(1)}(self.tr({m.group(2)}{m.group(3)}{m.group(2)})'
                if should_translate(m.group(3)) else m.group(0)
             )),
            # 3. addRow("...", ...), addItem("..."), ecc.
            (r'(addRow|addItem|setHeader|setTitle)\(\s*(["\'])(.+?)\2',
             lambda m: (
                f'{m.group(1)}(self.tr({m.group(2)}{m.group(3)}{m.group(2)})'
                if should_translate(m.group(3)) else m.group(0)
             )),
        ]

        for pattern, replacement in patterns:
            line = re.sub(pattern, replacement, line)

        modified_lines.append(line)

    return '\n'.join(modified_lines)

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 auto_tr_wrap.py <file.py> [<file2.py> ...]")
        sys.exit(1)

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"❌ {filepath} non trovato")
            continue

        print(f"Processing: {filepath}")

        try:
            modified = auto_wrap_tr(filepath)

            # Backup
            backup = filepath.with_suffix('.py.bak')
            backup.unlink(missing_ok=True)
            filepath.rename(backup)

            # Scrivi
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified)

            print(f"  ✓ Modificato (backup: {backup.name})")
        except Exception as e:
            print(f"  ❌ Errore: {e}")

if __name__ == '__main__':
    main()
