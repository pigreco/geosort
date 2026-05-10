# -*- coding: utf-8 -*-
"""
GeoSort – Processing Provider.
Registra l'algoritmo GeoSort nel Processing Toolbox di QGIS.
"""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os


class GeoSortProvider(QgsProcessingProvider):
    """Provider Processing per GeoSort."""

    def loadAlgorithms(self):
        from .geosort_algorithm import GeoSortAlgorithm

        self.addAlgorithm(GeoSortAlgorithm())

    def id(self):
        return "geosort"

    def name(self):
        return "GeoSort"

    def longName(self):
        return "GeoSort – Ordinamento Avanzato delle Geometrie"

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
        return QIcon(icon_path)
