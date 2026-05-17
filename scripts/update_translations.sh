#!/bin/bash
# Script per aggiornare i file di traduzione .ts
# Uso: ./scripts/update_translations.sh

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
I18N_DIR="$PLUGIN_DIR/i18n"
LANGUAGES=("it" "en")

# Prova pylupdate6 (Qt6/PyQt6), altrimenti pylupdate5
PYLUPDATE=$(which pylupdate6 || which pylupdate5)

if [ -z "$PYLUPDATE" ]; then
    echo "Errore: pylupdate6 o pylupdate5 non trovati in PATH"
    exit 1
fi

echo "Usando: $PYLUPDATE"

# Genera i file .ts per ogni lingua
for LANG in "${LANGUAGES[@]}"; do
    TS_FILE="$I18N_DIR/geosort_$LANG.ts"
    echo "Generando $TS_FILE..."
    $PYLUPDATE -tr-function-alias QCoreApplication.translate=tr "$PLUGIN_DIR"/*.py -ts "$TS_FILE"
done

echo "✓ File .ts aggiornati in $I18N_DIR/"
echo "Prossimo step: aprire i file .ts con Qt Linguist per tradurre"
