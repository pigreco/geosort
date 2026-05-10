# -*- coding: utf-8 -*-
"""
GeoSort – Finestra di dialogo principale.

L'intera UI è costruita programmaticamente (nessun file .ui).
"""

import os

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QRadioButton,
    QComboBox,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QPushButton,
    QButtonGroup,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsFieldProxyModel,
    QgsWkbTypes,
    QgsPointXY,
    QgsGeometry,
    QgsProject,
    QgsMessageLog,
    Qgis,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsMapToolEmitPoint


class _PointPickerTool(QgsMapToolEmitPoint):
    """Map tool per selezionare un punto sulla mappa.

    Estende QgsMapToolEmitPoint aggiungendo:
    - segnale ``cancelled`` emesso quando l'utente preme ESC
    - override di ``keyPressEvent`` per intercettare ESC senza propagarlo a QGIS
    """

    cancelled = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)


class GeoSortDialog(QDialog):
    """Finestra di dialogo principale di GeoSort.

    Tutti i widget sono costruiti in ``_build_ui()``.
    I metodi pubblici ``get_*`` espongono i valori correnti per i test.
    """

    def __init__(self, parent=None, iface=None):
        super().__init__(parent)
        self.iface = iface
        self._prev_map_tool = None
        self._map_tool = None
        self._pick_completed = False   # flag anti-doppio-trigger per ESC

        self.setWindowTitle("GeoSort – Ordinamento Avanzato delle Geometrie")
        self.setMinimumWidth(520)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self._build_ui()
        self._connect_signals()
        self._on_layer_changed()
        self._on_criterion_changed()

    # ──────────────────────────────────────────────────────────────────────────
    # Costruzione UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(8)

        main.addWidget(self._build_layer_group())
        main.addWidget(self._build_criterion_group())
        main.addWidget(self._build_options_group())
        main.addWidget(self._build_output_group())
        main.addWidget(self._build_preview_group())
        main.addLayout(self._build_buttons())

        self.setLayout(main)

    def _build_layer_group(self):
        grp = QGroupBox("Layer di input")
        layout = QFormLayout(grp)

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        layout.addRow("Layer:", self.layer_combo)

        self.lbl_crs = QLabel("–")
        self.lbl_crs.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow("CRS / unità:", self.lbl_crs)

        return grp

    def _build_criterion_group(self):
        grp = QGroupBox("Criterio di ordinamento")
        layout = QVBoxLayout(grp)
        self._crit_bg = QButtonGroup(self)

        # 1 – Attributo tabellare / espressione
        row1 = QHBoxLayout()
        self.rb_attribute = QRadioButton("Per attributo / espressione")
        self.rb_attribute.setChecked(True)
        self._crit_bg.addButton(self.rb_attribute, 0)
        self.combo_field = QgsFieldComboBox()
        self.combo_field.setFilters(QgsFieldProxyModel.AllTypes)
        self.btn_expression_builder = QPushButton()
        _expr_icon_path = os.path.join(os.path.dirname(__file__), "icon_expression.svg")
        self.btn_expression_builder.setIcon(QIcon(_expr_icon_path))
        self.btn_expression_builder.setIconSize(QSize(20, 20))
        self.btn_expression_builder.setFixedWidth(28)
        self.btn_expression_builder.setFixedHeight(28)
        self.btn_expression_builder.setToolTip(
            "Apri il Field Calculator di QGIS\n"
            "Permette di costruire un'espressione personalizzata come criterio di ordinamento\n"
            "Es: \"area_kmq\" / \"popolazione\"   oppure   length($geometry)"
        )
        row1.addWidget(self.rb_attribute)
        row1.addWidget(self.combo_field, 1)
        row1.addWidget(self.btn_expression_builder)
        layout.addLayout(row1)

        # Etichetta espressione attiva (visibile solo quando si usa il builder)
        self._active_expression = ""   # stringa vuota = usa la combo
        self.lbl_active_expr = QLabel("")
        self.lbl_active_expr.setStyleSheet("font-size: 10px; color: #1D9E75; padding-left: 4px;")
        self.lbl_active_expr.setVisible(False)
        layout.addWidget(self.lbl_active_expr)

        self.lbl_expr_warning = QLabel("")
        self.lbl_expr_warning.setStyleSheet("font-size: 10px; color: #e67e22; padding-left: 4px;")
        self.lbl_expr_warning.setVisible(False)
        layout.addWidget(self.lbl_expr_warning)

        # 2 – Centroide
        row2 = QHBoxLayout()
        self.rb_centroid = QRadioButton("Per coordinate centroide")
        self._crit_bg.addButton(self.rb_centroid, 1)
        self.combo_centroid = QComboBox()
        self.combo_centroid.addItems(
            ["Coordinata X", "Coordinata Y", "Distanza da punto di riferimento"]
        )
        row2.addWidget(self.rb_centroid)
        row2.addWidget(self.combo_centroid, 1)
        layout.addLayout(row2)

        # Punto di riferimento (mostrato solo per "Distanza")
        self.ref_point_group = QGroupBox("Punto di riferimento (X, Y)")
        ref_layout = QFormLayout(self.ref_point_group)
        self.spin_ref_x = QDoubleSpinBox()
        self.spin_ref_x.setRange(-1e9, 1e9)
        self.spin_ref_x.setDecimals(6)
        self.spin_ref_x.setSingleStep(1.0)
        self.spin_ref_y = QDoubleSpinBox()
        self.spin_ref_y.setRange(-1e9, 1e9)
        self.spin_ref_y.setDecimals(6)
        self.spin_ref_y.setSingleStep(1.0)
        ref_layout.addRow("X:", self.spin_ref_x)
        ref_layout.addRow("Y:", self.spin_ref_y)

        if self.iface:
            self.btn_pick_point = QPushButton("📍  Seleziona punto sulla mappa")
            ref_layout.addRow(self.btn_pick_point)

        self.ref_point_group.setVisible(False)
        layout.addWidget(self.ref_point_group)

        # 3 – Proprietà geometrica
        row3 = QHBoxLayout()
        self.rb_geometry = QRadioButton("Per proprietà geometrica")
        self._crit_bg.addButton(self.rb_geometry, 2)
        self.combo_geom = QComboBox()
        self.combo_geom.addItems(
            [
                "Area",
                "Perimetro",
                "Lunghezza",
                "Numero di vertici",
                "Larghezza Bounding Box",
                "Altezza Bounding Box",
                "Area Bounding Box",
                "Xmin Bounding Box",
                "Ymin Bounding Box",
            ]
        )
        row3.addWidget(self.rb_geometry)
        row3.addWidget(self.combo_geom, 1)
        layout.addLayout(row3)

        # 4 – Posizione lungo linea
        row4 = QHBoxLayout()
        self.rb_spatial = QRadioButton("Per posizione lungo linea")
        self._crit_bg.addButton(self.rb_spatial, 3)
        self.combo_ref_layer = QgsMapLayerComboBox()
        self.combo_ref_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        row4.addWidget(self.rb_spatial)
        row4.addWidget(self.combo_ref_layer, 1)
        layout.addLayout(row4)

        # Modalità calcolo (visibile solo con rb_spatial attivo)
        self.combo_line_mode = QComboBox()
        self.combo_line_mode.addItem(
            "Proiezione centroide  –  tutte le feature",
            "centroid_projection"
        )
        self.combo_line_mode.addItem(
            "Solo intersecanti  –  proiezione centroide",
            "intersecting_projection"
        )
        self.combo_line_mode.addItem(
            "Solo intersecanti  –  primo punto di intersezione",
            "intersecting_first_pt"
        )
        self.combo_line_mode.setToolTip(
            "Proiezione centroide: include tutte le feature, usa il centroide proiettato sulla linea.\n"
            "Solo intersecanti – centroide: esclude le feature che non intersecano la linea.\n"
            "Solo intersecanti – primo punto: usa il punto in cui la feature tocca per primo la linea."
        )
        layout.addWidget(self.combo_line_mode)

        return grp

    def _build_options_group(self):
        grp = QGroupBox("Opzioni")
        layout = QVBoxLayout(grp)

        # Direzione
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Direzione:"))
        self._dir_bg = QButtonGroup(self)
        self.rb_asc = QRadioButton("Ascendente ↑")
        self.rb_asc.setChecked(True)
        self.rb_desc = QRadioButton("Discendente ↓")
        self._dir_bg.addButton(self.rb_asc, 0)
        self._dir_bg.addButton(self.rb_desc, 1)
        dir_row.addWidget(self.rb_asc)
        dir_row.addWidget(self.rb_desc)
        dir_row.addStretch()
        layout.addLayout(dir_row)

        self.chk_nulls_last = QCheckBox("Valori NULL in fondo (attributo e espressione)")
        self.chk_nulls_last.setChecked(True)
        layout.addWidget(self.chk_nulls_last)

        return grp

    def _build_output_group(self):
        grp = QGroupBox("Output")
        layout = QVBoxLayout(grp)

        self._out_bg = QButtonGroup(self)
        self.rb_update = QRadioButton("Aggiorna layer corrente (aggiunge/aggiorna il campo 'sort_order')")
        self.rb_update.setChecked(True)
        self.rb_new_layer = QRadioButton("Crea nuovo layer in memoria")
        self._out_bg.addButton(self.rb_update, 0)
        self._out_bg.addButton(self.rb_new_layer, 1)
        layout.addWidget(self.rb_update)
        layout.addWidget(self.rb_new_layer)

        self.chk_add_value = QCheckBox(
            "Aggiungi campo con il valore del criterio usato (es. sort_area, sort_dist)"
        )
        layout.addWidget(self.chk_add_value)

        return grp

    def _build_preview_group(self):
        grp = QGroupBox("Anteprima (prime 10 feature ordinate)")
        layout = QVBoxLayout(grp)

        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(["FID", "sort_order", "Valore criterio"])
        self.preview_table.setMaximumHeight(180)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table)

        self.btn_preview = QPushButton("🔍  Aggiorna anteprima")
        layout.addWidget(self.btn_preview)

        return grp

    def _build_buttons(self):
        row = QHBoxLayout()
        self.btn_help = QPushButton("Help")
        self.btn_apply = QPushButton("Applica")
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Annulla")
        self.btn_close = QPushButton("Chiudi")
        self.btn_ok.setDefault(True)
        row.addWidget(self.btn_help)
        row.addStretch()
        row.addWidget(self.btn_apply)
        row.addWidget(self.btn_ok)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_close)
        return row

    # ──────────────────────────────────────────────────────────────────────────
    # Segnali
    # ──────────────────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.layer_combo.layerChanged.connect(self._on_layer_changed)
        for rb in (self.rb_attribute, self.rb_centroid, self.rb_geometry, self.rb_spatial):
            rb.toggled.connect(self._on_criterion_changed)
        self.combo_centroid.currentIndexChanged.connect(self._on_centroid_mode_changed)

        self.btn_preview.clicked.connect(self._update_preview)
        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_close.clicked.connect(self.close)
        self.btn_help.clicked.connect(self._on_help)
        self.btn_expression_builder.clicked.connect(self._open_expression_builder)

        if self.iface and hasattr(self, "btn_pick_point"):
            self.btn_pick_point.clicked.connect(self._pick_point_on_map)

    # ──────────────────────────────────────────────────────────────────────────
    # Slot
    # ──────────────────────────────────────────────────────────────────────────

    def _on_layer_changed(self):
        layer = self.layer_combo.currentLayer()
        if layer:
            self.combo_field.setLayer(layer)
            crs = layer.crs()
            unit_map = {
                0: "metri",
                1: "piedi",
                2: "gradi decimali",
                3: "gradi decimali",
                7: "chilometri",
            }
            unit_str = unit_map.get(int(crs.mapUnits()), "unità sconosciute")
            is_geographic = crs.isGeographic()
            self.lbl_crs.setText(f"{crs.authid()} – unità: {unit_str}")
            if is_geographic:
                self.lbl_crs.setStyleSheet("color: #e67e22; font-size: 10px; font-weight: bold;")
                self.lbl_crs.setText(
                    self.lbl_crs.text()
                    + " ⚠ CRS geografico: i calcoli di area/lunghezza saranno in gradi. "
                    "Si consiglia la riproiezione in CRS proiettato."
                )
            else:
                self.lbl_crs.setStyleSheet("color: gray; font-size: 10px;")
        self._on_criterion_changed()

    def _on_criterion_changed(self):
        is_attr = self.rb_attribute.isChecked()
        is_centroid = self.rb_centroid.isChecked()
        is_geom = self.rb_geometry.isChecked()
        is_spatial = self.rb_spatial.isChecked()

        self.combo_field.setEnabled(is_attr)
        self.btn_expression_builder.setEnabled(is_attr)
        self.chk_nulls_last.setEnabled(is_attr)
        self.combo_centroid.setEnabled(is_centroid)
        self.combo_geom.setEnabled(is_geom)
        self.combo_ref_layer.setEnabled(is_spatial)
        self.combo_line_mode.setEnabled(is_spatial)

        # Se si cambia criterio, resetta l'espressione attiva
        if not is_attr:
            self._clear_expression()

        show_ref = is_centroid and self.combo_centroid.currentIndex() == 2
        self.ref_point_group.setVisible(show_ref)
        self.ref_point_group.setEnabled(show_ref)

        self.adjustSize()

    def _on_centroid_mode_changed(self):
        self._on_criterion_changed()

    def _open_expression_builder(self):
        """Apre il Field Calculator di QGIS per costruire l'espressione di ordinamento.

        Se l'utente conferma un'espressione, questa ha la precedenza sul campo
        selezionato nella combo. Un'etichetta verde mostra l'espressione attiva.
        Il pulsante ε sul criterio attributo rimane sempre accessibile; premere
        di nuovo il builder mentre c'è già un'espressione attiva permette di
        modificarla. Per tornare al campo singolo basta cliccare la X accanto
        all'etichetta verde.
        """
        from qgis.gui import QgsExpressionBuilderDialog
        from qgis.core import QgsExpression

        layer = self.layer_combo.currentLayer()
        # Parte dall'espressione attiva (se c'è) o dal campo corrente della combo
        start_expr = self._active_expression or self.combo_field.currentField() or ""
        dlg = QgsExpressionBuilderDialog(layer, start_expr, self)
        dlg.setWindowTitle("GeoSort – Espressione di ordinamento")
        if not dlg.exec():
            return

        expr_text = dlg.expressionText().strip()
        if not expr_text:
            return

        # Valida subito
        expr = QgsExpression(expr_text)
        if expr.hasParserError():
            self.lbl_expr_warning.setText(f"⚠  {expr.parserErrorString()}")
            self.lbl_expr_warning.setVisible(True)
            return

        self.lbl_expr_warning.setVisible(False)

        # Se è solo il nome di un campo esistente, usa la combo (reset a campo semplice)
        layer_fields = [layer.fields().field(i).name() for i in range(layer.fields().count())] if layer else []
        if expr_text.strip('"') in layer_fields and expr_text == f'"{expr_text.strip(chr(34))}"' or expr_text in layer_fields:
            # Espressione = singolo campo → torna alla combo
            self.combo_field.setField(expr_text.strip('"'))
            self._clear_expression()
            return

        # Espressione composta → attivala
        self._active_expression = expr_text
        short = expr_text if len(expr_text) <= 60 else expr_text[:57] + "…"
        self.lbl_active_expr.setText(f"ε  {short}  [×]")
        self.lbl_active_expr.setToolTip(
            f"Espressione attiva: {expr_text}\nClicca per rimuoverla e tornare al campo."
        )
        self.lbl_active_expr.mousePressEvent = lambda _: self._clear_expression()
        self.lbl_active_expr.setCursor(Qt.PointingHandCursor)
        self.lbl_active_expr.setVisible(True)
        # Grisa la combo per segnalare che non è usata
        self.combo_field.setEnabled(False)

    def _clear_expression(self):
        """Rimuove l'espressione attiva e riabilita la combo campo."""
        self._active_expression = ""
        self.lbl_active_expr.setVisible(False)
        self.lbl_expr_warning.setVisible(False)
        if self.rb_attribute.isChecked():
            self.combo_field.setEnabled(True)

    def _pick_point_on_map(self):
        """Attiva il tool di selezione punto sulla mappa.

        Il dialog NON viene nascosto: viene abbassato con lower() così il canvas
        è accessibile. Nascondere il dialog non funziona perché il parent window
        (QGIS) riceve il focus ma il canvas non è in cima alla Z-order.

        Il segnale deactivated è il meccanismo più affidabile per ESC:
        QGIS può intercettare ESC a livello applicazione prima che arrivi al tool,
        ma in ogni caso deactivate() viene chiamato quando il tool viene rimpiazzato.
        """
        canvas = self.iface.mapCanvas()
        self._prev_map_tool = canvas.mapTool()
        self._pick_completed = False

        self._map_tool = _PointPickerTool(canvas)
        # Punto selezionato con click
        self._map_tool.canvasClicked.connect(self._on_point_picked)
        # ESC intercettato dal keyPressEvent del tool (se arriva al tool)
        self._map_tool.cancelled.connect(self._on_pick_cancelled)
        # Fallback: deactivated viene emesso ogni volta che il tool viene
        # disattivato, incluso quando QGIS gestisce ESC internamente
        self._map_tool.deactivated.connect(self._on_tool_deactivated)

        canvas.setMapTool(self._map_tool)

        # Status bar: istruzione visibile all'utente
        self.iface.mainWindow().statusBar().showMessage(
            "GeoSort: clicca sulla mappa per selezionare il punto  |  ESC per annullare"
        )

        # Aggiorna pulsante
        if hasattr(self, "btn_pick_point"):
            self.btn_pick_point.setText("⏳  In attesa del click… (ESC per annullare)")
            self.btn_pick_point.setEnabled(False)

        # Abbassa il dialog (non lo nasconde) e porta il canvas in primo piano.
        # lower() è sufficiente perché il dialog è non-modale (aperto con show()).
        self.lower()

    def _on_point_picked(self, point, _button):
        """Punto selezionato: aggiorna coordinate e ripristina."""
        if self._pick_completed:
            return
        self._pick_completed = True
        self._restore_map_tool()
        self.spin_ref_x.setValue(point.x())
        self.spin_ref_y.setValue(point.y())
        self._restore_dialog()

    def _on_pick_cancelled(self):
        """ESC intercettato dal keyPressEvent del tool."""
        if self._pick_completed:
            return
        self._pick_completed = True
        self._restore_map_tool()
        self._restore_dialog()

    def _on_tool_deactivated(self):
        """Fallback: il tool è stato disattivato (ESC a livello QGIS o tool-switch).

        Questo segnale viene sempre emesso quando il tool viene rimosso dal canvas,
        indipendentemente da chi ha gestito ESC. Il flag _pick_completed evita
        di eseguire _restore_dialog() due volte se canvasClicked + deactivated
        arrivano entrambi.
        """
        if self._pick_completed:
            return
        self._pick_completed = True
        # Il tool è già disattivato: non chiamare setMapTool, azzera solo il ref
        self._map_tool = None
        self._restore_dialog()

    def _restore_map_tool(self):
        """Ripristina il map tool precedente e pulisce i riferimenti interni."""
        if self._map_tool is not None:
            canvas = self.iface.mapCanvas()
            if self._prev_map_tool:
                canvas.setMapTool(self._prev_map_tool)
            else:
                canvas.unsetMapTool(self._map_tool)
            self._map_tool = None

    def _restore_dialog(self):
        """Riporta il dialog in primo piano."""
        if self.iface:
            self.iface.mainWindow().statusBar().clearMessage()
        if hasattr(self, "btn_pick_point"):
            self.btn_pick_point.setText("📍  Seleziona punto sulla mappa")
            self.btn_pick_point.setEnabled(True)
        self.raise_()
        self.activateWindow()

    # ──────────────────────────────────────────────────────────────────────────
    # Ordinamento
    # ──────────────────────────────────────────────────────────────────────────

    def _collect_sorted(self):
        """Esegue l'ordinamento e restituisce (sorted_features, values, crit_field_name).

        Raises:
            ValueError: in caso di input non valido o criterio incompatibile.
        """
        from .geosort_core import (
            sort_by_attribute,
            sort_by_centroid,
            sort_by_geometry_property,
            sort_by_line_position,
        )

        layer = self.layer_combo.currentLayer()
        if not layer:
            raise ValueError("Nessun layer selezionato.")
        features = list(layer.getFeatures())
        if not features:
            raise ValueError("Il layer non contiene feature.")

        ascending = self.rb_asc.isChecked()

        # ── Per attributo / espressione ──────────────────────────────────────
        if self.rb_attribute.isChecked():
            nulls_last = self.chk_nulls_last.isChecked()

            if self._active_expression:
                # Modalità espressione
                from .geosort_core import sort_by_expression
                sorted_feats, values, warnings = sort_by_expression(
                    features, layer, self._active_expression, ascending, nulls_last
                )
                if warnings:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"Espressione: {len(warnings)} avvisi. Vedere il log per i dettagli.",
                        "GeoSort", Qgis.Warning,
                    )
                return sorted_feats, values, "sort_expr", []

            else:
                # Modalità campo singolo
                field = self.combo_field.currentField()
                if not field:
                    raise ValueError("Nessun campo selezionato.")
                sorted_feats = sort_by_attribute(features, field, ascending, nulls_last)
                values = [f[field] for f in sorted_feats]
                crit_name = f"sort_{field[:8]}"
                return sorted_feats, values, crit_name, []

        # ── Per centroide ────────────────────────────────────────────────────
        if self.rb_centroid.isChecked():
            axis_map = {0: "x", 1: "y", 2: "dist"}
            axis = axis_map[self.combo_centroid.currentIndex()]
            ref_point = None
            if axis == "dist":
                ref_point = QgsPointXY(self.spin_ref_x.value(), self.spin_ref_y.value())
            sorted_feats, values = sort_by_centroid(features, axis, ascending, ref_point)
            crit_name = {"x": "sort_x", "y": "sort_y", "dist": "sort_dist"}[axis]
            return sorted_feats, values, crit_name, []

        # ── Per proprietà geometrica ─────────────────────────────────────────
        if self.rb_geometry.isChecked():
            crit_map = {
                0: "area", 1: "perimeter", 2: "length",
                3: "n_vertices", 4: "bbox_width", 5: "bbox_height",
                6: "bbox_area", 7: "bbox_xmin", 8: "bbox_ymin",
            }
            crit_name_map = {
                0: "sort_area", 1: "sort_perim", 2: "sort_len",
                3: "sort_nv", 4: "sort_bw", 5: "sort_bh",
                6: "sort_ba", 7: "sort_bx", 8: "sort_by_",
            }
            idx = self.combo_geom.currentIndex()
            criterion = crit_map[idx]
            sorted_feats, values = sort_by_geometry_property(features, criterion, ascending)
            return sorted_feats, values, crit_name_map[idx], []

        # ── Per posizione lungo linea ─────────────────────────────────────────
        if self.rb_spatial.isChecked():
            ref_layer = self.combo_ref_layer.currentLayer()
            if not ref_layer:
                raise ValueError("Nessun layer di riferimento selezionato.")
            ref_feats = list(ref_layer.getFeatures())
            if not ref_feats:
                raise ValueError("Il layer di riferimento non contiene feature.")
            line_geom = QgsGeometry.unaryUnion([f.geometry() for f in ref_feats])
            mode = self.combo_line_mode.currentData()
            sorted_feats, values, excluded = sort_by_line_position(
                features, line_geom, ascending, mode=mode
            )
            return sorted_feats, values, "sort_dist", excluded

        raise ValueError("Nessun criterio selezionato.")

    # ──────────────────────────────────────────────────────────────────────────
    # Anteprima
    # ──────────────────────────────────────────────────────────────────────────

    def _update_preview(self):
        self.preview_table.setRowCount(0)
        try:
            sorted_feats, values, _, excluded = self._collect_sorted()
        except Exception as exc:
            QMessageBox.warning(self, "GeoSort – Anteprima", str(exc))
            return

        n = min(10, len(sorted_feats))
        self.preview_table.setRowCount(n)
        for i in range(n):
            feat = sorted_feats[i]
            val = values[i] if i < len(values) else ""
            if isinstance(val, float):
                val_str = f"{val:.4f}"
            else:
                val_str = str(val) if val is not None else "NULL"
            self.preview_table.setItem(i, 0, QTableWidgetItem(str(feat.id())))
            self.preview_table.setItem(i, 1, QTableWidgetItem(str(i + 1)))
            self.preview_table.setItem(i, 2, QTableWidgetItem(val_str))
        self.preview_table.resizeColumnsToContents()

        # Mostra conteggio feature escluse nell'intestazione del gruppo
        parent_grp = self.preview_table.parent()
        if excluded and hasattr(parent_grp, "setTitle"):
            parent_grp.setTitle(
                f"Anteprima (prime {n} di {len(sorted_feats)} feature ordinate"
                f" · {len(excluded)} escluse per non intersezione)"
            )
        elif hasattr(parent_grp, "setTitle"):
            parent_grp.setTitle(
                f"Anteprima (prime {n} feature ordinate)"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Esecuzione
    # ──────────────────────────────────────────────────────────────────────────

    def _run(self):
        from .geosort_core import apply_sort_order, create_memory_layer

        try:
            sorted_feats, values, crit_name, excluded = self._collect_sorted()
        except Exception as exc:
            QMessageBox.warning(self, "GeoSort", str(exc))
            return False

        layer = self.layer_combo.currentLayer()
        add_crit = self.chk_add_value.isChecked()
        n = len(sorted_feats)
        excl_msg = (f"\n{len(excluded)} feature escluse (non intersecano la linea)."
                    if excluded else "")

        if self.rb_update.isChecked():
            ok = apply_sort_order(layer, sorted_feats, add_crit, values, crit_name)
            if ok:
                layer.triggerRepaint()
                QMessageBox.information(
                    self,
                    "GeoSort",
                    f"Ordinamento applicato con successo.\n"
                    f"Campo 'sort_order' aggiornato su {n} feature.{excl_msg}",
                )
            else:
                QMessageBox.critical(
                    self, "GeoSort", "Errore durante l'applicazione dell'ordinamento.\n"
                    "Controllare il log messaggi di QGIS per i dettagli."
                )
            return ok

        else:
            mem_layer = create_memory_layer(layer, sorted_feats, add_crit, values, crit_name)
            QgsProject.instance().addMapLayer(mem_layer)
            QMessageBox.information(
                self,
                "GeoSort",
                f"Nuovo layer 'GeoSort_output' aggiunto al progetto\n"
                f"con {n} feature ordinate.{excl_msg}",
            )
            return True

    def _on_ok(self):
        if self._run():
            self.accept()

    def _on_apply(self):
        self._run()

    def _on_help(self):
        QMessageBox.information(
            self,
            "GeoSort – Guida rapida",
            "GeoSort ordina le feature di un layer vettoriale e assegna un numero\n"
            "progressivo 'sort_order' (1 = prima feature nell'ordine scelto).\n\n"
            "─── Criteri ────────────────────────────────────\n"
            "• Attributo / espressione\n"
            "  Scegli un campo dalla lista, oppure clicca ε per aprire\n"
            "  il Field Calculator e costruire un'espressione personalizzata:\n"
            "    - combinazione di campi: \"area_kmq\" / \"pop\"\n"
            "    - funzioni geometriche: length($geometry), area($geometry)\n"
            "    - espressioni condizionali: CASE WHEN \"tipo\"=\'A\' THEN 1 ELSE 2 END\n"
            "  L'espressione attiva è evidenziata in verde; clicca [×] per rimuoverla.\n\n"
            "• Coordinate centroide – per X, Y o distanza da un punto\n"
            "• Proprietà geometrica – area, lunghezza, vertici, bounding box\n"
            "• Posizione lungo linea – con tre modalità:\n"
            "    - proiezione centroide (tutte le feature)\n"
            "    - solo intersecanti, via centroide\n"
            "    - solo intersecanti, via primo punto di contatto\n\n"
            "─── Output ──────────────────────────────────────\n"
            "• Aggiorna il layer corrente (aggiunge/aggiorna 'sort_order')\n"
            "• Crea un nuovo layer in memoria con le feature ordinate\n"
            "• Opzione: aggiungi il campo con il valore del criterio usato\n\n"
            "─── Suggerimenti ────────────────────────────────\n"
            "• Usa 'Anteprima' per verificare l'ordine prima di applicare\n"
            "• Valori NULL: scegli se posizionarli in cima o in fondo\n"
            "• CRS geografico: i calcoli di area/lunghezza sono in gradi²\n"
            "  → si consiglia la riproiezione in un CRS proiettato",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Metodi pubblici per i test
    # ──────────────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """ESC chiude il dialog (equivalente ad Annulla)."""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def get_selected_layer(self):
        """Restituisce il layer attualmente selezionato."""
        return self.layer_combo.currentLayer()

    def get_criterion(self):
        """Restituisce il criterio selezionato come stringa.

        Per il criterio "attribute", se è attiva un'espressione personalizzata
        ``get_active_expression()`` restituisce il testo dell'espressione.
        """
        if self.rb_attribute.isChecked():
            return "attribute"
        if self.rb_centroid.isChecked():
            return "centroid"
        if self.rb_geometry.isChecked():
            return "geometry"
        if self.rb_spatial.isChecked():
            return "spatial"
        return None

    def get_active_expression(self):
        """Restituisce l'espressione attiva (stringa vuota se si usa il campo singolo)."""
        return self._active_expression

    def get_direction(self):
        """Restituisce 'ascending' o 'descending'."""
        return "ascending" if self.rb_asc.isChecked() else "descending"

    def get_output_mode(self):
        """Restituisce 'update' o 'new_layer'."""
        return "update" if self.rb_update.isChecked() else "new_layer"
