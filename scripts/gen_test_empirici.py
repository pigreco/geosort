# -*- coding: utf-8 -*-
"""Genera dati vettoriali "empirici" in test_empirici/ per test manuali/
esplorativi con la skill qgis-headless — NON fa parte della suite automatica
(vedi tests/test_sorting.py, tests/test_algorithm.py, tests/test_dialog.py).

La cartella test_empirici/ è in .gitignore: questo script (tracciato) è il
modo riproducibile di ripopolarla. A differenza dei fixture sintetici usati
nei test automatici (rettangoli puliti costruiti in Python), qui le
geometrie includono casi limite scomodi da costruire a mano in un test:
multipart, buchi, geometrie NULL, poligono auto-intersecante (invalido).

Uso (ambiente QGIS headless, vedi skill qgis-headless):

    MAMBA_ROOT_PREFIX=$HOME/micromamba QT_QPA_PLATFORM=offscreen \
      micromamba run -n qgis python scripts/gen_test_empirici.py

Rigenera sempre da zero (sovrascrive) i GeoPackage in test_empirici/.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "test_empirici")

# Area di riferimento: dintorni di Palermo (EPSG:4326), per esercitare anche
# il percorso di misura geodetica automatica (CRS geografico) usato da
# geosort_core.resolve_geodesic() su area/perimetro/lunghezza/distanze.
CRS = "EPSG:4326"
LON0, LAT0 = 13.36, 38.12


def _write(layer, filename):
    from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext
    path = os.path.join(OUT_DIR, filename)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    try:
        # API >= 3.20
        err = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, QgsCoordinateTransformContext(), options
        )[0]
    except AttributeError:
        # Fallback API 3.16-3.18
        err = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, path, QgsCoordinateTransformContext(), options
        )[0]
    ok = (err == QgsVectorFileWriter.WriterError.NoError
          if hasattr(QgsVectorFileWriter, "WriterError") else err == 0)
    print(f"  {'OK' if ok else 'ERRORE'}: {filename} ({layer.featureCount()} feature)")
    return ok


def _layer(uri, name, fields_spec, rows):
    """rows: lista di (geometria|None, [attributi]).

    ``uri`` va dichiarato col tipo Multi* (MultiPoint/MultiLineString/
    MultiPolygon): il provider "memory" applica un controllo di tipo rigido
    e rifiuterebbe silenziosamente (in fase di commit) le feature multipart
    se il layer fosse dichiarato a tipo singolo — mentre il tipo Multi
    accetta comunque anche le feature single-part senza conversione.
    """
    from qgis.core import QgsVectorLayer, QgsFeature
    layer = QgsVectorLayer(f"{uri}?crs={CRS}&{fields_spec}", name, "memory")
    layer.startEditing()
    for geom, attrs in rows:
        feat = QgsFeature()
        if geom is not None:
            feat.setGeometry(geom)
        feat.setAttributes(attrs)
        layer.addFeature(feat)
    if not layer.commitChanges():
        raise RuntimeError(
            f"Commit fallito per il layer temporaneo '{name}' "
            f"({layer.commitErrors()})"
        )
    return layer


def build_points():
    from qgis.core import QgsGeometry, QgsPointXY
    fields = "field=id:integer&field=name:string"
    rows = [
        (QgsGeometry.fromPointXY(QgsPointXY(LON0, LAT0)), [1, "origine"]),
        (QgsGeometry.fromPointXY(QgsPointXY(LON0 + 0.05, LAT0 + 0.03)), [2, "vicino"]),
        (QgsGeometry.fromPointXY(QgsPointXY(LON0 + 0.20, LAT0 - 0.10)), [3, "lontano"]),
        # Geometria NULL: robustezza (deve finire in fondo, non far crashare).
        (None, [4, "senza_geometria"]),
        # Stesse coordinate del punto 1: pareggio/stabilità dell'ordinamento.
        (QgsGeometry.fromPointXY(QgsPointXY(LON0, LAT0)), [5, "duplicato_di_1"]),
        # MultiPoint: sort_by_centroid usa pointOnSurface() per isMultipart().
        (QgsGeometry.fromMultiPointXY([
            QgsPointXY(LON0 - 0.05, LAT0), QgsPointXY(LON0 - 0.03, LAT0 + 0.02),
        ]), [6, "multipoint"]),
    ]
    return _layer("MultiPoint", "points", fields, rows)


def build_lines():
    from qgis.core import QgsGeometry, QgsPointXY
    fields = "field=id:integer&field=name:string"
    zigzag = [QgsPointXY(LON0 + 0.01 * i, LAT0 + (0.02 if i % 2 else 0)) for i in range(12)]
    rows = [
        (QgsGeometry.fromPolylineXY([QgsPointXY(LON0, LAT0), QgsPointXY(LON0 + 0.02, LAT0)]),
         [1, "corta_2_vertici"]),
        (QgsGeometry.fromPolylineXY(zigzag), [2, "zigzag_12_vertici"]),
        # MultiLineString: due segmenti disgiunti.
        (QgsGeometry.fromMultiPolylineXY([
            [QgsPointXY(LON0, LAT0 + 0.10), QgsPointXY(LON0 + 0.03, LAT0 + 0.10)],
            [QgsPointXY(LON0 + 0.05, LAT0 + 0.12), QgsPointXY(LON0 + 0.08, LAT0 + 0.12)],
        ]), [3, "multilinestring"]),
        # Linea chiusa (primo punto == ultimo) ma resta un LineString, non un poligono.
        (QgsGeometry.fromPolylineXY([
            QgsPointXY(LON0, LAT0 - 0.05), QgsPointXY(LON0 + 0.02, LAT0 - 0.05),
            QgsPointXY(LON0 + 0.02, LAT0 - 0.03), QgsPointXY(LON0, LAT0 - 0.05),
        ]), [4, "chiusa_ma_non_poligono"]),
        (None, [5, "senza_geometria"]),
    ]
    return _layer("MultiLineString", "lines", fields, rows)


def build_polygons():
    from qgis.core import QgsGeometry, QgsPointXY
    fields = "field=id:integer&field=name:string"

    def square(cx, cy, half_side):
        return [
            QgsPointXY(cx - half_side, cy - half_side), QgsPointXY(cx + half_side, cy - half_side),
            QgsPointXY(cx + half_side, cy + half_side), QgsPointXY(cx - half_side, cy + half_side),
            QgsPointXY(cx - half_side, cy - half_side),
        ]

    donut_outer = square(LON0 + 0.15, LAT0, 0.04)
    donut_inner = list(reversed(square(LON0 + 0.15, LAT0, 0.015)))

    # Poligono a farfalla (bowtie): gli anelli si autointersecano → geometria
    # topologicamente invalida, comune nei dati reali digitalizzati a mano.
    bowtie = [
        QgsPointXY(LON0 - 0.15, LAT0), QgsPointXY(LON0 - 0.11, LAT0 + 0.03),
        QgsPointXY(LON0 - 0.11, LAT0 - 0.03), QgsPointXY(LON0 - 0.15, LAT0),
    ]

    rows = [
        (QgsGeometry.fromPolygonXY([square(LON0, LAT0, 0.02)]), [1, "quadrato_semplice"]),
        (QgsGeometry.fromPolygonXY([donut_outer, donut_inner]), [2, "ciambella_con_buco"]),
        # MultiPolygon: due quadrati disgiunti.
        (QgsGeometry.fromMultiPolygonXY([
            [square(LON0 + 0.25, LAT0 + 0.10, 0.02)],
            [square(LON0 + 0.30, LAT0 + 0.10, 0.01)],
        ]), [3, "multipolygon"]),
        (QgsGeometry.fromPolygonXY([bowtie]), [4, "bowtie_invalido"]),
        (None, [5, "senza_geometria"]),
    ]
    return _layer("MultiPolygon", "polygons", fields, rows)


def build_ref_line():
    """Linea di riferimento per line_position/line_distance, attraversa l'area
    dei punti/poligoni sopra così da avere proiezioni e distanze non banali."""
    from qgis.core import QgsGeometry, QgsPointXY
    rows = [
        (QgsGeometry.fromPolylineXY([
            QgsPointXY(LON0 - 0.20, LAT0 - 0.15), QgsPointXY(LON0 + 0.35, LAT0 + 0.15),
        ]), [1, "diagonale"]),
    ]
    return _layer("LineString", "ref_line", "field=id:integer&field=name:string", rows)


def main():
    from qgis.testing import start_app
    start_app()

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Generazione in {OUT_DIR} (CRS {CRS})...")
    _write(build_points(), "points.gpkg")
    _write(build_lines(), "lines.gpkg")
    _write(build_polygons(), "polygons.gpkg")
    _write(build_ref_line(), "ref_line.gpkg")
    print("Fatto. Esempio d'uso con qgis-headless/run_algorithm.py:\n"
          '  --params \'{"INPUT": "test_empirici/polygons.gpkg", '
          '"CRITERION": 4, "OUTPUT": "memory:"}\'')


if __name__ == "__main__":
    main()
