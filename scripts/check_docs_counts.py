#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica che i numeri (conteggio criteri, conteggio test) citati in
README.md, README.en.md e CLAUDE.md corrispondano ai valori reali del
codice/della test suite.

Non richiede QGIS: il conteggio criteri legge `_CRITERIA_KEYS` per regex
(il modulo geosort_algorithm.py non è importabile senza PyQGIS), e i test
di test_dialog.py / test_algorithm.py si auto-saltano senza QGIS ma
restano comunque *contati* da unittest.

Uso:
    python scripts/check_docs_counts.py

Uscita non-zero e diff leggibile se un numero documentato non combacia
con quello reale. Pensato per girare in CI accanto al check di
sincronizzazione dei file .ts (vedi .github/workflows/tests.yml).
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count_criteria():
    """Numero di criteri in _CRITERIA_KEYS, letto per regex (no import QGIS)."""
    text = (ROOT / "geosort_algorithm.py").read_text(encoding="utf-8")
    m = re.search(r"_CRITERIA_KEYS\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        sys.exit("ERRORE: _CRITERIA_KEYS non trovato in geosort_algorithm.py")
    items = [
        line.strip()
        for line in m.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return len(items)


def run_unittest(*targets):
    """Esegue `python -m unittest <targets> -v` e ne estrae (ran, ok, skipped)."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", *targets],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = proc.stderr  # unittest scrive il summary su stderr
    ran_m = re.search(r"Ran (\d+) test", out)
    skipped_m = re.search(r"skipped=(\d+)", out)
    ran = int(ran_m.group(1)) if ran_m else None
    skipped = int(skipped_m.group(1)) if skipped_m else 0
    if ran is None:
        sys.exit(f"ERRORE: impossibile leggere l'output di unittest per {targets}:\n{out}")
    return ran, ran - skipped, skipped


def check(label, file_path, pattern, expected, mismatches):
    """Cerca `pattern` (con un gruppo numerico) in file_path e lo confronta con expected."""
    text = file_path.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if not m:
        mismatches.append(f"{label}: pattern non trovato in {file_path.name} ({pattern!r})")
        return
    found = int(m.group(1))
    if found != expected:
        mismatches.append(
            f"{label}: {file_path.name} dice {found}, valore reale è {expected}"
        )


def main():
    n_criteria = count_criteria()
    sorting_ran, sorting_ok, sorting_skip = run_unittest("tests.test_sorting")
    dialog_ran, dialog_ok, dialog_skip = run_unittest("tests.test_dialog")
    algo_ran, algo_ok, algo_skip = run_unittest("tests.test_algorithm")
    total_ran = sorting_ran + dialog_ran + algo_ran
    total_ok = sorting_ok + dialog_ok + algo_ok
    total_skip = sorting_skip + dialog_skip + algo_skip

    mismatches = []

    for readme, testui_word, criteri_word in (
        (ROOT / "README.md", "Test UI", "criteri"),
        (ROOT / "README.en.md", "UI tests", "criteria"),
    ):
        check("test_sorting", readme, r"#\s*(\d+)\s+test[si]?\s+(?:sulla logica core|on core logic)",
              sorting_ran, mismatches)
        check("test_dialog", readme, re.escape(testui_word) + r"\s*\((\d+)\s+test",
              dialog_ran, mismatches)
        check("test_algorithm", readme,
              r"(?:tutti e|all)\s+\d+\s+i?\s*" + re.escape(criteri_word) + r"\s*\((\d+)\s+test",
              algo_ran, mismatches)
        check("n_criteria", readme,
              r"(?:tutti e|all)\s+(\d+)\s+i?\s*" + re.escape(criteri_word),
              n_criteria, mismatches)
        check("totale", readme, r"Output:\s*(\d+)\s+tests", total_ran, mismatches)
        check("ok", readme, r"\((\d+)\s+ok", total_ok, mismatches)
        check("skipped", readme, r"ok,\s*(\d+)\s+skipped", total_skip, mismatches)

    check("n_criteria (CLAUDE.md)", ROOT / "CLAUDE.md",
          r"Defines the (\d+) sort criteria", n_criteria, mismatches)

    print(f"Criteri reali:        {n_criteria}")
    print(f"test_sorting reali:   {sorting_ran}")
    print(f"test_dialog reali:    {dialog_ran}")
    print(f"test_algorithm reali: {algo_ran}")
    print(f"Totale reale:         {total_ran} ({total_ok} ok, {total_skip} skipped)")
    print()

    if mismatches:
        print("MISMATCH tra documentazione e valori reali:")
        for m in mismatches:
            print(f"  - {m}")
        sys.exit(1)

    print("OK: tutti i conteggi documentati corrispondono ai valori reali.")


if __name__ == "__main__":
    main()
