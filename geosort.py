# -*- coding: utf-8 -*-
"""
GeoSort – Classe principale del plugin.
"""

import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
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
