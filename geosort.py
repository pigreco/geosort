# -*- coding: utf-8 -*-
"""
GeoSort – Classe principale del plugin.
"""

import os

from qgis.PyQt.QtWidgets import QAction, QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.core import QgsApplication, QgsMessageLog, Qgis


class GeoSort:
    """Classe principale del plugin GeoSort."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&GeoSort"
        self._provider = None
        self._dlg = None  # riferimento al dialog non-modale (evita GC)
        self.translator = None  # riferimento al traduttore (evita GC)

        self.toolbar = self.iface.addToolBar("GeoSort")
        self.toolbar.setObjectName("GeoSortToolbar")

        self._setup_translator()

    # ──────────────────────────────────────────────────────────────────────────
    # Setup traduzioni
    # ──────────────────────────────────────────────────────────────────────────

    def tr(self, message):
        """Traduce una stringa nel contesto 'GeoSort'.

        Usabile anche fuori da un QObject (questa classe non lo è): instrada
        attraverso i traduttori installati su QCoreApplication.
        """
        return QCoreApplication.translate("GeoSort", message)

    def _setup_translator(self):
        """Carica il traduttore in base alla lingua dell'interfaccia QGIS."""
        # Rileva la lingua da QGIS (rispetta l'override in Opzioni), non dal sistema
        qgis_locale = QgsApplication.instance().locale()
        # In QGIS 3.44+ locale() può restituire una stringa, non un QLocale
        if isinstance(qgis_locale, str):
            locale_name = qgis_locale
        else:
            locale_name = qgis_locale.name()  # es. 'it_IT', 'en_US'
        lang_code = locale_name.split('_')[0].lower()  # es. 'it', 'en'

        # Supportate solo it e en; fallback a en per altre lingue
        if lang_code not in ('it', 'en'):
            lang_code = 'en'

        ts_file = os.path.join(self.plugin_dir, 'i18n', f'geosort_{lang_code}.ts')
        if not os.path.exists(ts_file):
            QgsMessageLog.logMessage(
                f"File traduzione non trovato: {ts_file}", "GeoSort", Qgis.MessageLevel.Warning
            )
            return

        from .geosort_translator import TsTranslator
        # Mantenuto come attributo: installTranslator() non acquisisce ownership
        # dell'oggetto Python, che altrimenti verrebbe garbage-collected.
        self.translator = TsTranslator(lang_code)
        QApplication.installTranslator(self.translator)

    # ──────────────────────────────────────────────────────────────────────────
    # Ciclo di vita QGIS
    # ──────────────────────────────────────────────────────────────────────────

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        action = QAction(
            QIcon(icon_path),
            self.tr("GeoSort – Advanced Geometry Sorting"),
            self.iface.mainWindow(),
        )
        action.setStatusTip(
            self.tr("Ordina le feature di un layer vettoriale per criteri geometrici e attributivi")
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
        if self.translator is not None:
            QApplication.removeTranslator(self.translator)
            self.translator = None
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
