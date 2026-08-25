# -*- coding: utf-8 -*-
"""
Test su TsTranslator (geosort_translator.py).

Richiedono QGIS installato e avviabile tramite qgis.testing.
Eseguibili con: python -m pytest tests/test_translator.py

Se QGIS non è disponibile nel PATH, i test vengono saltati automaticamente.

Regressione issue #23: installato globalmente su QApplication, il
traduttore di GeoSort interrompeva la catena di traduzione anche per
stringhe non sue, riportando in inglese tutti i menu di QGIS. Vedi
docstring di TsTranslator.translate() per il meccanismo esatto (QString
nulla vs vuota).
"""

import sys
import os
import unittest


def _qgis_available():
    try:
        import qgis  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_qgis_available(), "QGIS non disponibile in questo ambiente di test")
class TestTsTranslator(unittest.TestCase):
    """Test sul comportamento di TsTranslator.translate()."""

    @classmethod
    def setUpClass(cls):
        from qgis.testing import start_app
        cls.qgis_app = start_app()

        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(plugin_root)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from geosort.geosort_translator import TsTranslator
        cls.TsTranslator = TsTranslator

    def test_known_string_in_geosort_context_is_translated(self):
        """Una stringa presente nel dizionario, nel contesto GeoSort, viene tradotta."""
        tr = self.TsTranslator("it")
        self.assertEqual(tr.translate("GeoSort", "Help"), "Aiuto")

    def test_unknown_string_in_geosort_context_returns_none(self):
        """Stringa assente dal dizionario -> None (QString nulla), non ''."""
        tr = self.TsTranslator("it")
        result = tr.translate("GeoSort", "Una stringa che GeoSort non conosce")
        self.assertIsNone(result)

    def test_string_from_other_context_returns_none(self):
        """Contesto diverso da 'GeoSort' -> None, anche se il testo combacia per caso.

        Regressione issue #23: prima della fix, il traduttore rispondeva a
        qualunque contesto, oscurando le traduzioni di QGIS e di altri plugin.
        """
        tr = self.TsTranslator("it")
        result = tr.translate("QDialogButtonBox", "Help")
        self.assertIsNone(result)

    def test_does_not_shadow_qgis_translator_when_chained(self):
        """Con più traduttori installati su QApplication, GeoSort deve farsi
        da parte (None) sulle stringhe che non conosce, lasciando che la
        ricerca prosegua verso il traduttore di QGIS.

        Riproduce esattamente lo scenario dell'issue #23: menu QGIS in
        italiano che, con il plugin attivo, tornavano in inglese.
        """
        from qgis.PyQt.QtWidgets import QApplication
        from qgis.PyQt.QtCore import QCoreApplication, QTranslator

        class _FakeQgisTranslator(QTranslator):
            """Simula il traduttore italiano di QGIS."""
            def translate(self, context, source_text, *args):
                if source_text == "Close":
                    return "Chiudi"
                return None

        qgis_tr = _FakeQgisTranslator()
        geosort_tr = self.TsTranslator("it")

        QApplication.installTranslator(qgis_tr)
        QApplication.installTranslator(geosort_tr)
        try:
            # 'Close' non appartiene a GeoSort: deve arrivare al traduttore QGIS.
            result = QCoreApplication.translate("SomeOtherDialog", "Close")
            self.assertEqual(result, "Chiudi")
        finally:
            QApplication.removeTranslator(geosort_tr)
            QApplication.removeTranslator(qgis_tr)


if __name__ == "__main__":
    unittest.main()
