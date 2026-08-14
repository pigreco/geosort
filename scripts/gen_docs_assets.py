# -*- coding: utf-8 -*-
"""Genera gli screenshot "prima/dopo" usati in docs/index.html e docs/en/index.html.

A differenza di test_empirici/ (dati con casi limite scomodi per l'esplorazione
manuale), qui i dataset sono puliti e minimi: servono a illustrare in modo
leggibile *un* criterio alla volta, non a stressare la robustezza del codice.
L'ordinamento vero e proprio usa le funzioni pubbliche di geosort_core.py
(nessuna logica di ordinamento reinventata qui).

Uso (ambiente QGIS headless, vedi skill qgis-headless):

    MAMBA_ROOT_PREFIX=$HOME/micromamba QT_QPA_PLATFORM=offscreen \
      micromamba run -n qgis python scripts/gen_docs_assets.py

Rigenera sempre da zero (sovrascrive) i PNG in docs/assets/img/.
"""
import os
import sys

from qgis.PyQt.QtCore import QMetaType

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # per "import geosort_core" diretto (nessun import relativo al suo interno)
OUT_DIR = os.path.join(ROOT, "docs", "assets", "img")

CRS = "EPSG:32633"  # UTM 33N, metri — coordinate locali arbitrarie, nessun significato geografico
OX, OY = 500000.0, 4649776.0  # origine locale per tenere le coordinate piccole e leggibili

LIGHT = (255, 224, 145)
DARK = (150, 32, 32)
ACCENT = "#2c5f8a"


def _rank_color(i, n):
    t = i / max(n - 1, 1)
    r, g, b = (int(LIGHT[c] + (DARK[c] - LIGHT[c]) * t) for c in range(3))
    return "#%02x%02x%02x" % (r, g, b)


def _layer(wkb_type, fields_spec, rows, name="layer"):
    from qgis.core import QgsVectorLayer, QgsFeature
    uri = f"{wkb_type}?crs={CRS}" + (f"&{fields_spec}" if fields_spec else "")
    layer = QgsVectorLayer(uri, name, "memory")
    layer.startEditing()
    for geom, attrs in rows:
        f = QgsFeature()
        if geom is not None:
            f.setGeometry(geom)
        if attrs:
            f.setAttributes(attrs)
        layer.addFeature(f)
    if not layer.commitChanges():
        raise RuntimeError(f"Commit fallito per '{name}': {layer.commitErrors()}")
    return layer


def _add_field(layer, name, qtype, values_by_fid):
    """Aggiunge un campo e lo popola da un dict {fid: valore}."""
    from qgis.core import QgsField
    layer.startEditing()
    layer.addAttribute(QgsField(name, qtype))
    layer.commitChanges()
    idx = layer.fields().indexOf(name)
    layer.startEditing()
    for fid, val in values_by_fid.items():
        layer.changeAttributeValue(fid, idx, val)
    layer.commitChanges()


def _categorized(layer, field, category_colors, geom_kind, outline="#3a3a3a"):
    """category_colors: lista di (valore_categoria, colore_hex) nell'ordine desiderato."""
    from qgis.core import QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer
    from PyQt5.QtGui import QColor
    cats = []
    for value, color in category_colors:
        sym = QgsSymbol.defaultSymbol(geom_kind)
        sym.setColor(QColor(color))
        if hasattr(sym, "symbolLayer") and sym.symbolLayer(0) is not None:
            try:
                sym.symbolLayer(0).setStrokeColor(QColor(outline))
            except Exception:
                pass
        cats.append(QgsRendererCategory(value, sym, str(value)))
    layer.setRenderer(QgsCategorizedSymbolRenderer(field, cats))


def _labeling(layer, field, size=10.5, color="#202225", bold=True):
    from qgis.core import (
        QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings,
        QgsVectorLayerSimpleLabeling,
    )
    from PyQt5.QtGui import QColor, QFont
    pal = QgsPalLayerSettings()
    pal.fieldName = field
    fmt = QgsTextFormat()
    fmt.setSize(size)
    fmt.setColor(QColor(color))
    font = fmt.font()
    font.setBold(bold)
    fmt.setFont(font)
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1.1)
    buf.setColor(QColor("white"))
    fmt.setBuffer(buf)
    pal.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)


def _simple_line_layer(points, color=ACCENT, width=0.9, dash=True, name="path"):
    from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsLineSymbol
    layer = QgsVectorLayer(f"LineString?crs={CRS}", name, "memory")
    layer.startEditing()
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPolylineXY(points))
    layer.addFeature(f)
    layer.commitChanges()
    props = {"color": color, "width": str(width)}
    if dash:
        props["line_style"] = "dash"
    layer.renderer().setSymbol(QgsLineSymbol.createSimple(props))
    return layer


def _endpoint_layer(first_pt, last_pt, name="endpoints"):
    from qgis.core import (
        QgsVectorLayer, QgsFeature, QgsGeometry, QgsSymbol,
        QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsMarkerSymbol,
    )
    from PyQt5.QtGui import QColor
    layer = QgsVectorLayer(f"Point?crs={CRS}&field=kind:string", name, "memory")
    layer.startEditing()
    f1, f2 = QgsFeature(), QgsFeature()
    f1.setGeometry(QgsGeometry.fromPointXY(first_pt))
    f1.setAttributes(["start"])
    f2.setGeometry(QgsGeometry.fromPointXY(last_pt))
    f2.setAttributes(["end"])
    layer.addFeature(f1)
    layer.addFeature(f2)
    layer.commitChanges()
    start_sym = QgsMarkerSymbol.createSimple({"color": "#2e7d32", "size": "4", "name": "circle"})
    end_sym = QgsMarkerSymbol.createSimple({"color": "#c62828", "name": "triangle", "size": "4.5"})
    cats = [
        QgsRendererCategory("start", start_sym, "Inizio"),
        QgsRendererCategory("end", end_sym, "Fine"),
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer("kind", cats))
    return layer


def _extent_of(layers, margin_ratio=0.16):
    # Nota: QgsRectangle.isEmpty() è True anche per un rettangolo di altezza o
    # larghezza zero (es. feature allineate sulla stessa Y) — usare isNull()
    # insieme al conteggio feature per non scartare un extent degenere ma valido.
    from qgis.core import QgsRectangle
    rect = QgsRectangle()
    rect.setMinimal()
    have_any = False
    for lyr in layers:
        if lyr.featureCount() == 0:
            continue
        ext = lyr.extent()
        if ext.isNull():
            continue
        rect.combineExtentWith(ext)
        have_any = True
    if not have_any:
        rect = QgsRectangle(-10, -10, 10, 10)
    dx = max(rect.width() * margin_ratio, 20)
    dy = max(rect.height() * margin_ratio, 20)
    rect.setXMinimum(rect.xMinimum() - dx)
    rect.setXMaximum(rect.xMaximum() + dx)
    rect.setYMinimum(rect.yMinimum() - dy)
    rect.setYMaximum(rect.yMaximum() + dy)
    return rect


def render(layers, out_name, size=(900, 620), extent=None):
    from qgis.core import QgsMapSettings, QgsMapRendererParallelJob
    from PyQt5.QtCore import QSize
    from PyQt5.QtGui import QColor
    ms = QgsMapSettings()
    ms.setLayers(layers)  # primo elemento = disegnato sopra
    ms.setBackgroundColor(QColor("white"))
    ms.setOutputSize(QSize(*size))
    ms.setExtent(extent or _extent_of(layers))
    ms.setOutputDpi(110)
    job = QgsMapRendererParallelJob(ms)
    job.start()
    job.waitForFinished()
    path = os.path.join(OUT_DIR, out_name)
    ok = job.renderedImage().save(path, "PNG")
    print(f"  {'OK' if ok else 'ERRORE'}: {out_name}")
    return ok


# ──────────────────────────────────────────────────────────────────────────
# 1) Attributo: lessicografico vs Natural Sort
# ──────────────────────────────────────────────────────────────────────────

def gen_attribute():
    from qgis.core import QgsGeometry, QgsPointXY
    import geosort_core as gc

    codici = ["FILE1", "FILE2", "FILE3", "FILE9", "FILE10"]
    rows = [(QgsGeometry.fromPointXY(QgsPointXY(OX + i * 140, OY)), [i + 1, c])
            for i, c in enumerate(codici)]

    for natural, out_name in [(False, "shot-attribute-lexicographic.png"),
                               (True, "shot-attribute-natural.png")]:
        layer = _layer("Point", "field=id:integer&field=codice:string", rows, "attributo")
        feats = list(layer.getFeatures())
        sorted_feats = gc.sort_by_attribute(feats, "codice", ascending=True, natural_sort=natural)
        rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
        _add_field(layer, "etichetta", QMetaType.Type.QString,
                   {fid: f"{layer.getFeature(fid)['codice']} · #{r}" for fid, r in rank.items()})
        # Colora per rango (non per id): categorie sul campo "id", mappate al colore del rango
        color_by_id = {}
        n = len(rank)
        for fid, r in rank.items():
            fid_id = layer.getFeature(fid)["id"]
            color_by_id[fid_id] = _rank_color(r - 1, n)
        _categorized(layer, "id", [(k, color_by_id[k]) for k in sorted(color_by_id)], layer.geometryType())
        _labeling(layer, "etichetta")
        render([layer], out_name, size=(900, 260))


# ──────────────────────────────────────────────────────────────────────────
# 2) Centroide — distanza da punto di riferimento (ordinamento radiale)
# ──────────────────────────────────────────────────────────────────────────

def gen_centroid():
    from qgis.core import QgsGeometry, QgsPointXY
    import geosort_core as gc

    ref = QgsPointXY(OX, OY)
    offsets = [(120, 40), (-80, 150), (200, -60), (-180, -120), (60, 220), (-40, -200), (260, 130)]
    rows = [(QgsGeometry.fromPointXY(QgsPointXY(OX + dx, OY + dy)), [i + 1])
            for i, (dx, dy) in enumerate(offsets)]
    layer = _layer("Point", "field=id:integer", rows, "centroide")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_by_centroid(feats, axis="dist", ascending=True, ref_point=ref)
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=12)

    ordered_points = [f.geometry().asPoint() for f in sorted_feats]
    path = _simple_line_layer(ordered_points, name="percorso")

    from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry as QG, QgsMarkerSymbol
    ref_layer = QgsVectorLayer(f"Point?crs={CRS}", "riferimento", "memory")
    ref_layer.startEditing()
    rf = QgsFeature()
    rf.setGeometry(QG.fromPointXY(ref))
    ref_layer.addFeature(rf)
    ref_layer.commitChanges()
    ref_layer.renderer().setSymbol(QgsMarkerSymbol.createSimple(
        {"color": "#f0a500", "name": "star", "size": "6"}))

    render([ref_layer, layer, path], "shot-centroid.png")


# ──────────────────────────────────────────────────────────────────────────
# 3) Proprietà geometrica — area (particelle catastali)
# ──────────────────────────────────────────────────────────────────────────

def _rect(cx, cy, w, h):
    from qgis.core import QgsGeometry, QgsPointXY
    hw, hh = w / 2, h / 2
    return QgsGeometry.fromPolygonXY([[
        QgsPointXY(cx - hw, cy - hh), QgsPointXY(cx + hw, cy - hh),
        QgsPointXY(cx + hw, cy + hh), QgsPointXY(cx - hw, cy + hh),
        QgsPointXY(cx - hw, cy - hh),
    ]])


def gen_geometry_area():
    import geosort_core as gc
    specs = [  # (dx, dy, larghezza, altezza)
        (0, 0, 90, 70), (150, 10, 140, 110), (330, -20, 60, 50),
        (0, 160, 180, 130), (250, 170, 100, 90), (420, 100, 70, 60),
    ]
    rows = [(_rect(OX + dx, OY + dy, w, h), [i + 1]) for i, (dx, dy, w, h) in enumerate(specs)]
    layer = _layer("Polygon", "field=id:integer", rows, "particelle")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_by_geometry_property(feats, "area", ascending=False)
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=13)
    render([layer], "shot-geometry-area.png")


# ──────────────────────────────────────────────────────────────────────────
# 4) Distanza dalla linea di riferimento (edifici vicino a una strada)
# ──────────────────────────────────────────────────────────────────────────

def gen_line_distance():
    from qgis.core import QgsGeometry, QgsPointXY
    import geosort_core as gc

    road = QgsGeometry.fromPolylineXY([
        QgsPointXY(OX - 60, OY - 220), QgsPointXY(OX + 420, OY + 180),
    ])
    specs = [(30, -150), (250, -30), (120, 120), (380, 40), (60, 200), (300, 220)]
    rows = [(_rect(OX + dx, OY + dy, 55, 45), [i + 1]) for i, (dx, dy) in enumerate(specs)]
    layer = _layer("Polygon", "field=id:integer", rows, "edifici")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_by_line_distance(feats, road, ascending=True, mode="element")
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=12)

    road_layer = _simple_line_layer(
        [road.asPolyline()[0], road.asPolyline()[-1]], color="#333", width=1.6, dash=False, name="strada")
    render([road_layer, layer], "shot-line-distance.png")


# ──────────────────────────────────────────────────────────────────────────
# 5) Posizione lungo linea (pali lungo una strada)
# ──────────────────────────────────────────────────────────────────────────

def gen_line_position():
    from qgis.core import QgsGeometry, QgsPointXY
    import geosort_core as gc

    road = QgsGeometry.fromPolylineXY([
        QgsPointXY(OX - 40, OY - 180), QgsPointXY(OX + 150, OY - 40),
        QgsPointXY(OX + 260, OY + 120), QgsPointXY(OX + 440, OY + 200),
    ])
    offsets = [(-20, -170), (60, -110), (140, -55), (200, 30), (270, 110), (350, 155), (430, 195)]
    rows = [(QgsGeometry.fromPointXY(QgsPointXY(OX + dx, OY + dy)), [i + 1])
            for i, (dx, dy) in enumerate(offsets)]
    layer = _layer("Point", "field=id:integer", rows, "pali")
    feats = list(layer.getFeatures())
    sorted_feats, _, _excluded = gc.sort_by_line_position(feats, road, ascending=True, mode="centroid_projection")
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=12)

    road_layer = _simple_line_layer(road.asPolyline(), color="#333", width=1.6, dash=False, name="strada")
    render([road_layer, layer], "shot-line-position.png")


# ──────────────────────────────────────────────────────────────────────────
# 6) Curva di Hilbert (griglia 4×4)
# ──────────────────────────────────────────────────────────────────────────

def gen_hilbert():
    from qgis.core import QgsGeometry, QgsPointXY
    import geosort_core as gc

    step = 90
    rows = []
    i = 0
    for row in range(4):
        for col in range(4):
            i += 1
            rows.append((QgsGeometry.fromPointXY(QgsPointXY(OX + col * step, OY + row * step)), [i]))
    layer = _layer("Point", "field=id:integer", rows, "hilbert")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_by_hilbert(feats, ascending=True, order=4)
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=11)

    ordered_points = [f.geometry().asPoint() for f in sorted_feats]
    path = _simple_line_layer(ordered_points, dash=False, width=1.1, name="curva")
    endpoints = _endpoint_layer(ordered_points[0], ordered_points[-1])
    render([endpoints, layer, path], "shot-hilbert.png")


# ──────────────────────────────────────────────────────────────────────────
# 7) Serpentina (griglia di tavole cartografiche 4×3)
# ──────────────────────────────────────────────────────────────────────────

def gen_serpentine():
    import geosort_core as gc

    w, h = 110, 80
    rows = []
    i = 0
    for r in range(3):
        for c in range(4):
            i += 1
            rows.append((_rect(OX + c * w, OY + r * h, w * 0.94, h * 0.94), [i]))
    layer = _layer("Polygon", "field=id:integer", rows, "tavole")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_by_serpentine(feats, ascending=True, axis="horizontal", cross_ascending=True)
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    n = len(rank)
    _add_field(layer, "rango", QMetaType.Type.Int,
               {fid: r for fid, r in rank.items()})
    _categorized(layer, "rango", [(r, _rank_color(r - 1, n)) for r in range(1, n + 1)],
                 layer.geometryType())
    _labeling(layer, "rango", size=12)

    ordered_points = [f.geometry().centroid().asPoint() for f in sorted_feats]
    path = _simple_line_layer(ordered_points, dash=False, width=1.1, name="percorso")
    endpoints = _endpoint_layer(ordered_points[0], ordered_points[-1])
    render([endpoints, layer, path], "shot-serpentine.png")


# ──────────────────────────────────────────────────────────────────────────
# 8) Multi-criterio: regione (asc.) poi area (desc.)
# ──────────────────────────────────────────────────────────────────────────

def gen_multicriterio():
    import geosort_core as gc

    region_colors = [("A", "#6fa8dc"), ("B", "#93c47d"), ("C", "#e06666")]
    clusters = {
        "A": [(0, 0, 130, 100), (60, 140, 90, 70), (150, 40, 60, 50)],
        "B": [(430, 0, 150, 120), (500, 150, 80, 60), (400, 160, 100, 80)],
        "C": [(850, 20, 100, 160), (940, 190, 70, 55), (800, 190, 90, 70)],
    }
    rows = []
    i = 0
    for region, boxes in clusters.items():
        for (dx, dy, w, h) in boxes:
            i += 1
            rows.append((_rect(OX + dx, OY + dy, w, h), [i, region]))
    layer = _layer("Polygon", "field=id:integer&field=regione:string", rows, "regioni")
    feats = list(layer.getFeatures())
    sorted_feats, _ = gc.sort_multi(
        feats,
        [
            {"key": "attribute", "field": "regione", "ascending": True},
            {"key": "area", "ascending": False},
        ],
        layer=layer,
    )
    rank = {f.id(): i + 1 for i, f in enumerate(sorted_feats)}
    _add_field(layer, "etichetta", QMetaType.Type.QString,
               {fid: f"#{r}" for fid, r in rank.items()})
    _categorized(layer, "regione", region_colors, layer.geometryType())
    _labeling(layer, "etichetta", size=12)
    render([layer], "shot-multicriterio.png")


def main():
    from qgis.testing import start_app
    start_app()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Generazione screenshot in {OUT_DIR}...")
    gen_attribute()
    gen_centroid()
    gen_geometry_area()
    gen_line_distance()
    gen_line_position()
    gen_hilbert()
    gen_serpentine()
    gen_multicriterio()
    print("Fatto.")


if __name__ == "__main__":
    main()
