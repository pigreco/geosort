# -*- coding: utf-8 -*-
"""
GeoSort – Ordinamento Avanzato delle Geometrie
Ordina le feature di un layer vettoriale per criteri geometrici e attributivi.
"""


def classFactory(iface):
    """Carica la classe principale del plugin.

    Args:
        iface: istanza di QgisInterface
    """
    from .geosort import GeoSort
    return GeoSort(iface)
