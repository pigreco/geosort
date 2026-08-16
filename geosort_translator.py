# -*- coding: utf-8 -*-
"""
Caricatore di traduzioni da file .ts.
Fallback quando lrelease non è disponibile.
"""

import os
from pathlib import Path
# ElementTree qui legge solo la risorsa .ts in bundle nel plugin stesso
# (i18n/geosort_*.ts), non input esterno/utente; defusedxml non è usato
# per non introdurre dipendenze esterne oltre PyQGIS (vedi CLAUDE.md).
from xml.etree import ElementTree as ET  # nosec B405
from qgis.PyQt.QtCore import QTranslator, QLocale

class TsTranslator(QTranslator):
    """QTranslator che carica direttamente da file .ts XML."""

    def __init__(self, locale='it'):
        super().__init__()
        self.locale = locale
        self.translations = {}
        self.load_from_ts()

    def load_from_ts(self):
        """Carica le traduzioni da file .ts."""
        plugin_dir = Path(__file__).parent
        ts_file = plugin_dir / 'i18n' / f'geosort_{self.locale}.ts'

        if not ts_file.exists():
            return False

        try:
            # nosec B314 - ts_file è una risorsa in bundle nel pacchetto del
            # plugin stesso (i18n/geosort_*.ts), non input esterno/utente;
            # defusedxml non è usato per non introdurre dipendenze esterne
            # oltre PyQGIS (vedi CLAUDE.md).
            tree = ET.parse(ts_file)  # nosec B314
            root = tree.getroot()

            for message in root.findall('.//message'):
                source = message.find('source')
                translation = message.find('translation')

                if source is not None and translation is not None:
                    source_text = source.text or ''
                    translated_text = translation.text or source_text

                    if translated_text:
                        self.translations[source_text] = translated_text

            return True
        except Exception as e:
            return False

    def translate(self, context, source_text, *args):
        """Implementa il metodo translate di QTranslator."""
        return self.translations.get(source_text, source_text)
