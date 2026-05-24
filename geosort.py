# -*- coding: utf-8 -*-
"""
GeoSort – Classe principale del plugin.
"""

import os

from qgis.PyQt.QtWidgets import QAction, QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QTranslator, QLocale
from qgis.core import QgsApplication


class GeoSort:
    """Classe principale del plugin GeoSort."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&GeoSort"
        self._provider = None
        self._dlg = None  # riferimento al dialog non-modale (evita GC)

        self.toolbar = self.iface.addToolBar("GeoSort")
        self.toolbar.setObjectName("GeoSortToolbar")

        self._setup_translator()

    # ──────────────────────────────────────────────────────────────────────────
    # Setup traduzioni
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_translator(self):
        """Carica il traduttore in base alla lingua di QGIS."""
        # Rileva la lingua da QGIS, non dal sistema
        qgis_locale = QgsApplication.instance().locale()
        locale_name = qgis_locale.name()  # es. 'it_IT', 'en_US'
        lang_code = locale_name.split('_')[0].lower()  # es. 'it', 'en'

        # Supportate solo it e en; fallback a en per altre lingue
        if lang_code not in ('it', 'en'):
            lang_code = 'en'

        i18n_dir = os.path.join(self.plugin_dir, 'i18n')
        qm_file = os.path.join(i18n_dir, f'geosort_{lang_code}.qm')
        ts_file = os.path.join(i18n_dir, f'geosort_{lang_code}.ts')

        # Prova a caricare il file .qm compilato (preferito)
        if os.path.exists(qm_file):
            translator = QTranslator()
            if translator.load(qm_file):
                QApplication.installTranslator(translator)
                return

        # Fallback: carica i .ts direttamente (utile in sviluppo)
        if os.path.exists(ts_file):
            from .geosort_translator import TsTranslator
            translator = TsTranslator(lang_code)
            QApplication.installTranslator(translator)

    # ──────────────────────────────────────────────────────────────────────────
    # Ciclo di vita QGIS
    # ──────────────────────────────────────────────────────────────────────────

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        action = QAction(
            QIcon(icon_path),
            "GeoSort – Ordinamento geometrie",
            self.iface.mainWindow(),
        )
        action.setStatusTip(
            "Ordina le feature di un layer vettoriale per criteri geometrici e attributivi"
        )
        action.triggered.connect(self.run)

        self.iface.addPluginToVectorMenu(self.menu, action)
        self.toolbar.addAction(action)
        self.actions.append(action)

        from .geosort_provider import GeoSortProvider
        self._provider = GeoSortProvider()
        QgsApplication.processingRegistry().addProvider(self._provider)

    def unload(self):
        if self._dlg:
            self._dlg.close()
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        if self._provider:
            QgsApplication.processingRegistry().removeProvider(self._provider)

    # ──────────────────────────────────────────────────────────────────────────
    # Azione principale
    # ──────────────────────────────────────────────────────────────────────────

    def run(self):
        """Apre la finestra di dialogo in modalità NON-MODALE.

        Usare show() invece di exec() è essenziale: exec() crea un event loop
        modale che blocca il canvas QGIS anche quando il dialog è nascosto,
        rendendo impossibile la selezione del punto sulla mappa.
        """
        from .geosort_dialog import GeoSortDialog

        if self._dlg is None:
            self._dlg = GeoSortDialog(parent=self.iface.mainWindow(), iface=self.iface)
            # WA_DeleteOnClose garantisce che Qt distrugga il widget alla chiusura
            self._dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self._dlg.finished.connect(self._on_dialog_finished)

        self._dlg.show()
        self._dlg.raise_()
        self._dlg.activateWindow()

    def _on_dialog_finished(self, _result):
        """Il dialog è stato chiuso: azzera il riferimento."""
        self._dlg = None
