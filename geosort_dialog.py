# -*- coding: utf-8 -*-
"""
GeoSort – Finestra di dialogo principale.

L'intera UI è costruita programmaticamente (nessun file .ui).
"""

import os

from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
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
    QProgressDialog,
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsFieldProxyModel,
    QgsWkbTypes,
    QgsPointXY,
    QgsGeometry,
    QgsProject,
    QgsMessageLog,
    QgsUnitTypes,
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
        if event.key() == Qt.Key.Key_Escape:
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

        self.setWindowTitle(self.tr("GeoSort – Advanced Geometry Sorting"))
        self.setMinimumWidth(520)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

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
        grp = QGroupBox(self.tr("Input Layer"))
        layout = QFormLayout(grp)

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        layout.addRow(self.tr("Layer:"), self.layer_combo)

        self.chk_selected_only = QCheckBox(self.tr("Ordina solo le feature selezionate"))
        self.chk_selected_only.setToolTip(self.tr(
            "Se attivo, l'ordinamento considera solo le feature attualmente\n"
            "selezionate sul layer. In modalità 'Aggiorna layer corrente' il\n"
            "campo sort_order viene scritto solo su quelle feature."
        ))
        layout.addRow("", self.chk_selected_only)

        self.lbl_crs = QLabel("–")
        self.lbl_crs.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow(self.tr("CRS / Units:"), self.lbl_crs)

        return grp

    def _build_criterion_group(self):
        grp = QGroupBox(self.tr("Criterio di ordinamento"))
        outer = QVBoxLayout(grp)
        self._crit_bg = QButtonGroup(self)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)   # colonna combobox: tutta la larghezza disponibile
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        # ── Riga 0: Attributo / espressione ─────────────────────────────────
        self.rb_attribute = QRadioButton(self.tr("Per attributo / espressione"))
        self.rb_attribute.setChecked(True)
        self._crit_bg.addButton(self.rb_attribute, 0)
        self.combo_field = QgsFieldComboBox()
        self.combo_field.setFilters(QgsFieldProxyModel.Filter.AllTypes)
        self.btn_expression_builder = QPushButton()
        _expr_icon_path = os.path.join(os.path.dirname(__file__), "icon_expression.svg")
        self.btn_expression_builder.setIcon(QIcon(_expr_icon_path))
        self.btn_expression_builder.setIconSize(QSize(20, 20))
        self.btn_expression_builder.setFixedSize(28, 28)
        self.btn_expression_builder.setToolTip(self.tr(
            "Apri il Field Calculator di QGIS\n"
            "Permette di costruire un'espressione personalizzata come criterio di ordinamento\n"
            "Es: \"area_kmq\" / \"popolazione\"   oppure   length($geometry)"
        ))
        grid.addWidget(self.rb_attribute,           0, 0)
        grid.addWidget(self.combo_field,            0, 1)
        grid.addWidget(self.btn_expression_builder, 0, 2)

        # Etichetta espressione attiva + pulsante rimozione
        self._active_expression = ""
        self.lbl_active_expr = QLabel("")
        self.lbl_active_expr.setStyleSheet("font-size: 10px; color: #1D9E75; padding-left: 4px;")
        self.lbl_active_expr.setVisible(False)
        self.btn_remove_expression = QPushButton(self.tr("Rimuovi"))
        self.btn_remove_expression.setFixedHeight(22)
        self.btn_remove_expression.setVisible(False)
        self.btn_remove_expression.setToolTip(self.tr("Rimuovi l'espressione attiva e torna al campo singolo"))
        grid.addWidget(self.lbl_active_expr,       1, 0, 1, 2)
        grid.addWidget(self.btn_remove_expression, 1, 2)

        self.lbl_expr_warning = QLabel("")
        self.lbl_expr_warning.setStyleSheet("font-size: 10px; color: #e67e22; padding-left: 4px;")
        self.lbl_expr_warning.setVisible(False)
        grid.addWidget(self.lbl_expr_warning, 2, 0, 1, 3)

        # ── Riga 3: Centroide ────────────────────────────────────────────────
        self.rb_centroid = QRadioButton(self.tr("Per coordinate centroide"))
        self._crit_bg.addButton(self.rb_centroid, 1)
        self.combo_centroid = QComboBox()
        self.combo_centroid.addItems([
            self.tr("Coordinata X"), self.tr("Coordinata Y"), self.tr("Distanza da punto di riferimento")
        ])
        grid.addWidget(self.rb_centroid,    3, 0)
        grid.addWidget(self.combo_centroid, 3, 1, 1, 2)

        # Punto di riferimento (mostrato solo per "Distanza")
        self.ref_point_group = QGroupBox(self.tr("Punto di riferimento (X, Y)"))
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
            self.btn_pick_point = QPushButton(self.tr("Seleziona punto sulla mappa"))
            ref_layout.addRow(self.btn_pick_point)
        self.ref_point_group.setVisible(False)
        grid.addWidget(self.ref_point_group, 4, 0, 1, 3)

        # ── Riga 5: Proprietà geometrica ────────────────────────────────────
        self.rb_geometry = QRadioButton(self.tr("Per proprietà geometrica"))
        self._crit_bg.addButton(self.rb_geometry, 2)
        self.combo_geom = QComboBox()
        self.combo_geom.addItems([
            self.tr("Area"),
            self.tr("Perimetro"),
            self.tr("Lunghezza"),
            self.tr("Numero di vertici"),
            self.tr("Larghezza Bounding Box"),
            self.tr("Altezza Bounding Box"),
            self.tr("Area Bounding Box"),
            self.tr("Xmin Bounding Box"),
            self.tr("Ymin Bounding Box"),
        ])
        grid.addWidget(self.rb_geometry, 5, 0)
        grid.addWidget(self.combo_geom,  5, 1, 1, 2)

        # ── Riga 6: Distanza dalla linea + modalità ──────────────────────────
        self.rb_line_distance = QRadioButton(self.tr("Per distanza dalla linea"))
        self._crit_bg.addButton(self.rb_line_distance, 3)
        self.combo_ref_layer_dist = QgsMapLayerComboBox()
        self.combo_ref_layer_dist.setFilters(QgsMapLayerProxyModel.Filter.LineLayer)
        self.combo_line_distance_mode = QComboBox()
        self.combo_line_distance_mode.addItem(self.tr("Distanza dal centroide"), "centroid")
        self.combo_line_distance_mode.addItem(self.tr("Distanza dall'elemento"), "element")
        self.combo_line_distance_mode.setToolTip(self.tr(
            "Distanza dal centroide: distanza dal centro della feature.\n"
            "Distanza dall'elemento: distanza dal punto più vicino della geometria."
        ))
        grid.addWidget(self.rb_line_distance,         6, 0)
        grid.addWidget(self.combo_ref_layer_dist,     6, 1)
        grid.addWidget(self.combo_line_distance_mode, 6, 2)

        # ── Riga 7: Posizione lungo linea + modalità ─────────────────────────
        self.rb_spatial = QRadioButton(self.tr("Per posizione lungo linea"))
        self._crit_bg.addButton(self.rb_spatial, 4)
        self.combo_ref_layer = QgsMapLayerComboBox()
        self.combo_ref_layer.setFilters(QgsMapLayerProxyModel.Filter.LineLayer)
        self.combo_line_mode = QComboBox()
        self.combo_line_mode.addItem(
            self.tr("Proiezione centroide  –  tutte le feature"),
            "centroid_projection"
        )
        self.combo_line_mode.addItem(
            self.tr("Solo intersecanti  –  proiezione centroide"),
            "intersecting_projection"
        )
        self.combo_line_mode.addItem(
            self.tr("Solo intersecanti  –  primo punto di intersezione"),
            "intersecting_first_pt"
        )
        self.combo_line_mode.setToolTip(self.tr(
            "Proiezione centroide: include tutte le feature, usa il centroide proiettato sulla linea.\n"
            "Solo intersecanti – centroide: esclude le feature che non intersecano la linea.\n"
            "Solo intersecanti – primo punto: usa il punto in cui la feature tocca per primo la linea."
        ))
        grid.addWidget(self.rb_spatial,      7, 0)
        grid.addWidget(self.combo_ref_layer, 7, 1)
        grid.addWidget(self.combo_line_mode, 7, 2)

        outer.addLayout(grid)

        return grp

    def _build_options_group(self):
        grp = QGroupBox(self.tr("Opzioni"))
        layout = QVBoxLayout(grp)

        # Direzione
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel(self.tr("Direzione:")))
        self._dir_bg = QButtonGroup(self)
        self.rb_asc = QRadioButton(self.tr("Ascendente ↑"))
        self.rb_asc.setChecked(True)
        self.rb_desc = QRadioButton(self.tr("Discendente ↓"))
        self._dir_bg.addButton(self.rb_asc, 0)
        self._dir_bg.addButton(self.rb_desc, 1)
        dir_row.addWidget(self.rb_asc)
        dir_row.addWidget(self.rb_desc)
        dir_row.addStretch()
        layout.addLayout(dir_row)

        self.chk_nulls_last = QCheckBox(self.tr("Valori NULL in fondo (attributo e espressione)"))
        self.chk_nulls_last.setChecked(True)
        layout.addWidget(self.chk_nulls_last)

        self.chk_natural_sort = QCheckBox(self.tr("Ordinamento naturale – Natural Sort (es. 1, 2, 10 invece di 1, 10, 2)"))
        self.chk_natural_sort.setChecked(False)
        self.chk_natural_sort.setToolTip(self.tr(
            "<b>Lessicografico</b> (default): confronto carattere per carattere.\n"
            "Esempio: «1010» precede «11» precede «1111».\n\n"
            "<b>Natural Sort</b>: le sequenze di cifre sono confrontate come numeri interi.\n"
            "Esempio: «11» precede «1010» precede «1111».\n\n"
            "Attivalo con campi alfanumerici (FILE1, FILE2, FILE10)\n"
            "o espressioni di concatenazione come \"fid\" || \"id_poly\"."
        ))
        layout.addWidget(self.chk_natural_sort)

        # ── Criterio secondario (tie-break) per l'ordinamento multi-criterio ──
        sec_row = QHBoxLayout()
        sec_row.addWidget(QLabel(self.tr("Criterio secondario (pareggi):")))
        self.combo_secondary = QComboBox()
        self.combo_secondary.addItem(self.tr("(nessuno)"), None)
        self.combo_secondary.addItem(self.tr("Attributo tabellare"), "attribute")
        self.combo_secondary.addItem(self.tr("Centroide – coordinata X"), "centroid_x")
        self.combo_secondary.addItem(self.tr("Centroide – coordinata Y"), "centroid_y")
        self.combo_secondary.addItem(self.tr("Area (poligoni)"), "area")
        self.combo_secondary.addItem(self.tr("Perimetro (poligoni)"), "perimeter")
        self.combo_secondary.addItem(self.tr("Lunghezza (linee)"), "length")
        self.combo_secondary.addItem(self.tr("Numero di vertici"), "n_vertices")
        self.combo_secondary.setToolTip(self.tr(
            "Spezza i pareggi del criterio primario (es. primario = Regione, secondario = Area). Non disponibile se il criterio primario è basato su linea."
        ))
        sec_row.addWidget(self.combo_secondary)
        self.combo_secondary_field = QgsFieldComboBox()
        self.combo_secondary_field.setEnabled(False)
        sec_row.addWidget(self.combo_secondary_field)
        sec_row.addStretch()
        layout.addLayout(sec_row)

        self.chk_secondary_desc = QCheckBox(self.tr("Criterio secondario discendente ↓"))
        layout.addWidget(self.chk_secondary_desc)

        # ── Misura geodetica ─────────────────────────────────────────────────
        geo_row = QHBoxLayout()
        geo_row.addWidget(QLabel(self.tr("Misura su CRS geografico:")))
        self.combo_geodesic = QComboBox()
        self.combo_geodesic.addItem(
            self.tr("Misura geodetica: automatica (CRS geografico)"), "auto"
        )
        self.combo_geodesic.addItem(
            self.tr("Misura geodetica: sempre"), "always"
        )
        self.combo_geodesic.addItem(
            self.tr("Misura geodetica: mai (planare)"), "never"
        )
        self.combo_geodesic.setCurrentIndex(0)
        self.combo_geodesic.setToolTip(self.tr(
            "Su CRS geografico (gradi, es. EPSG:4326), area/lunghezza/distanze\n"
            "vengono misurate sull'ellissoide (m²/m) invece che in gradi.\n"
            "• Automatica: geodetica solo se il CRS è geografico (consigliato).\n"
            "• Sempre: geodetica anche su CRS proiettati.\n"
            "• Mai (planare): misura nelle unità native del CRS."
        ))
        geo_row.addWidget(self.combo_geodesic)
        geo_row.addStretch()
        layout.addLayout(geo_row)

        return grp

    def _build_output_group(self):
        grp = QGroupBox(self.tr("Output"))
        layout = QVBoxLayout(grp)

        self._out_bg = QButtonGroup(self)
        self.rb_update = QRadioButton(self.tr("Aggiorna layer corrente (aggiunge/aggiorna il campo 'sort_order')"))
        self.rb_update.setChecked(True)
        self.rb_new_layer = QRadioButton(self.tr("Crea nuovo layer in memoria"))
        self._out_bg.addButton(self.rb_update, 0)
        self._out_bg.addButton(self.rb_new_layer, 1)
        layout.addWidget(self.rb_update)
        layout.addWidget(self.rb_new_layer)

        self.chk_add_value = QCheckBox(self.tr(
            "Aggiungi campo con il valore del criterio usato (es. sort_area, sort_dist)"
        ))
        layout.addWidget(self.chk_add_value)

        return grp

    def _build_preview_group(self):
        grp = QGroupBox(self.tr("Anteprima (prime 10 feature ordinate)"))
        layout = QVBoxLayout(grp)

        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels([self.tr("FID"), self.tr("sort_order"), self.tr("Valore criterio")])
        self.preview_table.setMaximumHeight(180)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table)

        self.btn_preview = QPushButton(self.tr("Aggiorna anteprima"))
        layout.addWidget(self.btn_preview)

        return grp

    def _build_buttons(self):
        row = QHBoxLayout()
        self.btn_help = QPushButton(self.tr("Help"))
        self.btn_apply = QPushButton(self.tr("Applica"))
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton(self.tr("Annulla"))
        self.btn_close = QPushButton(self.tr("Chiudi"))
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
        for rb in (self.rb_attribute, self.rb_centroid, self.rb_geometry, self.rb_spatial, self.rb_line_distance):
            rb.toggled.connect(self._on_criterion_changed)
        self.combo_centroid.currentIndexChanged.connect(self._on_centroid_mode_changed)
        self.combo_secondary.currentIndexChanged.connect(self._on_secondary_changed)

        self.btn_preview.clicked.connect(self._update_preview)
        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_close.clicked.connect(self.close)
        self.btn_help.clicked.connect(self._on_help)
        self.btn_expression_builder.clicked.connect(self._open_expression_builder)
        self.btn_remove_expression.clicked.connect(self._clear_expression)

        if self.iface and hasattr(self, "btn_pick_point"):
            self.btn_pick_point.clicked.connect(self._pick_point_on_map)

    # ──────────────────────────────────────────────────────────────────────────
    # Slot
    # ──────────────────────────────────────────────────────────────────────────

    def _on_layer_changed(self):
        layer = self.layer_combo.currentLayer()
        if layer:
            self.combo_field.setLayer(layer)
            self.combo_secondary_field.setLayer(layer)
            crs = layer.crs()
            # QgsUnitTypes.toString: robusto ai cambi di valore dell'enum tra
            # versioni QGIS e già tradotto nella lingua dell'interfaccia.
            unit_str = QgsUnitTypes.toString(crs.mapUnits())
            is_geographic = crs.isGeographic()
            self.lbl_crs.setText(f"{crs.authid()} – unità: {unit_str}")
            if is_geographic:
                self.lbl_crs.setStyleSheet("color: #e67e22; font-size: 10px; font-weight: bold;")
                self.lbl_crs.setText(
                    self.lbl_crs.text()
                    + self.tr(
                        " ⚠ CRS geografico: GeoSort applica automaticamente la misura"
                        " ellissoidica (geodetica) per area/lunghezza/distanze (m²/m)."
                    )
                )
            else:
                self.lbl_crs.setStyleSheet("color: gray; font-size: 10px;")
        self._on_criterion_changed()

    def _on_criterion_changed(self):
        is_attr = self.rb_attribute.isChecked()
        is_centroid = self.rb_centroid.isChecked()
        is_geom = self.rb_geometry.isChecked()
        is_spatial = self.rb_spatial.isChecked()
        is_line_distance = self.rb_line_distance.isChecked()

        self.combo_field.setEnabled(is_attr)
        self.btn_expression_builder.setEnabled(is_attr)
        self.chk_nulls_last.setEnabled(is_attr)
        self.chk_natural_sort.setEnabled(is_attr)
        self.combo_centroid.setEnabled(is_centroid)
        self.combo_geom.setEnabled(is_geom)
        self.combo_ref_layer.setEnabled(is_spatial)
        self.combo_line_mode.setEnabled(is_spatial)
        self.combo_ref_layer_dist.setEnabled(is_line_distance)
        self.combo_line_distance_mode.setEnabled(is_line_distance)

        # Il criterio secondario (multi-criterio) non è disponibile per i criteri
        # basati su linea (posizione/distanza lungo linea).
        is_line_based = is_spatial or is_line_distance
        self.combo_secondary.setEnabled(not is_line_based)
        self.chk_secondary_desc.setEnabled(not is_line_based)
        if is_line_based:
            self.combo_secondary_field.setEnabled(False)
        else:
            self._on_secondary_changed()

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
        unquoted = expr_text.strip('"')
        if unquoted in layer_fields and expr_text in (unquoted, f'"{unquoted}"'):
            # Espressione = singolo campo → torna alla combo
            self.combo_field.setField(unquoted)
            self._clear_expression()
            return

        # Espressione composta → attivala
        self._active_expression = expr_text
        short = expr_text if len(expr_text) <= 60 else expr_text[:57] + "…"
        self.lbl_active_expr.setText(f"Espressione: {short}")
        self.lbl_active_expr.setToolTip(f"Espressione attiva: {expr_text}")
        self.lbl_active_expr.setVisible(True)
        self.btn_remove_expression.setVisible(True)
        # Grisa la combo per segnalare che non è usata
        self.combo_field.setEnabled(False)

    def _clear_expression(self):
        """Rimuove l'espressione attiva e riabilita la combo campo."""
        self._active_expression = ""
        self.lbl_active_expr.setVisible(False)
        self.btn_remove_expression.setVisible(False)
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

    def _on_secondary_changed(self):
        """Abilita il selettore di campo solo per il criterio secondario 'Attributo'."""
        is_attr = self.combo_secondary.currentData() == "attribute"
        self.combo_secondary_field.setEnabled(is_attr)
        if is_attr:
            layer = self.layer_combo.currentLayer()
            if layer:
                self.combo_secondary_field.setLayer(layer)

    def _geodesic_mode(self):
        """Restituisce la modalità geodetica selezionata: 'auto', 'always' o 'never'."""
        return self.combo_geodesic.currentData()

    def _load_features(self, layer):
        """Feature da ordinare: tutte, o solo le selezionate se richiesto.

        Raises:
            ValueError: checkbox attiva ma nessuna feature selezionata.
        """
        if self.chk_selected_only.isChecked():
            feats = layer.selectedFeatures()
            if not feats:
                raise ValueError(self.tr(
                    "Nessuna feature selezionata sul layer "
                    "(è attivo 'Ordina solo le feature selezionate')."
                ))
            return feats
        return list(layer.getFeatures())

    def _primary_spec_for_multi(self):
        """Descrittore del criterio primario per sort_multi.

        Returns:
            dict | None: ``None`` se il primario è basato su linea (multi non
            supportato), altrimenti lo spec del criterio.

        Raises:
            ValueError: se il primario è 'Attributo' senza campo selezionato.
        """
        ascending = self.rb_asc.isChecked()
        nulls_last = self.chk_nulls_last.isChecked()
        natural = self.chk_natural_sort.isChecked()

        if self.rb_attribute.isChecked():
            if self._active_expression:
                return {"key": "expression", "expression": self._active_expression,
                        "ascending": ascending, "nulls_last": nulls_last,
                        "natural_sort": natural}
            field = self.combo_field.currentField()
            if not field:
                raise ValueError("Nessun campo selezionato.")
            return {"key": "attribute", "field": field, "ascending": ascending,
                    "nulls_last": nulls_last, "natural_sort": natural}

        if self.rb_centroid.isChecked():
            key = {0: "centroid_x", 1: "centroid_y", 2: "centroid_dist"}[
                self.combo_centroid.currentIndex()]
            spec = {"key": key, "ascending": ascending}
            if key == "centroid_dist":
                spec["ref_point"] = QgsPointXY(self.spin_ref_x.value(),
                                               self.spin_ref_y.value())
            return spec

        if self.rb_geometry.isChecked():
            crit_map = {0: "area", 1: "perimeter", 2: "length", 3: "n_vertices",
                        4: "bbox_width", 5: "bbox_height", 6: "bbox_area",
                        7: "bbox_xmin", 8: "bbox_ymin"}
            return {"key": crit_map[self.combo_geom.currentIndex()],
                    "ascending": ascending}

        return None  # criteri basati su linea → multi non supportato

    def _secondary_spec(self, key):
        """Descrittore del criterio secondario per sort_multi."""
        spec = {"key": key,
                "ascending": not self.chk_secondary_desc.isChecked(),
                "nulls_last": self.chk_nulls_last.isChecked(),
                "natural_sort": self.chk_natural_sort.isChecked()}
        if key == "attribute":
            field = self.combo_secondary_field.currentField()
            if not field:
                raise ValueError("Nessun campo selezionato per il criterio secondario.")
            spec["field"] = field
        return spec

    def _collect_sorted(self, progress_callback=None, features=None):
        """Esegue l'ordinamento e restituisce (sorted_features, values, crit_field_name, excluded).

        Args:
            progress_callback (callable | None): se fornita, chiamata con percentuale 0-100.
            features (list[QgsFeature] | None): feature pre-caricate (se None le carica dal layer).

        Raises:
            ValueError: in caso di input non valido o criterio incompatibile.
        """
        from .geosort_core import (
            sort_by_attribute,
            sort_by_centroid,
            sort_by_geometry_property,
            sort_by_line_position,
            sort_by_line_distance,
            build_distance_area,
            resolve_geodesic,
            should_build_distance_area,
            geographic_crs_warning,
        )

        layer = self.layer_combo.currentLayer()
        if not layer:
            raise ValueError("Nessun layer selezionato.")
        if features is None:
            features = self._load_features(layer)
        if not features:
            raise ValueError("Il layer non contiene feature.")

        ascending = self.rb_asc.isChecked()
        geo_mode = self._geodesic_mode()
        self._last_geodesic_warning = ""

        # ── Multi-criterio: criterio secondario per i pareggi ────────────────
        sec_key = self.combo_secondary.currentData()
        if sec_key is not None:
            primary_spec = self._primary_spec_for_multi()
            if primary_spec is not None:
                from .geosort_core import sort_multi
                secondary_spec = self._secondary_spec(sec_key)
                # Costruisce distance_area se almeno un criterio può beneficiarne
                da_multi = None
                if should_build_distance_area(layer.crs(), geo_mode):
                    da_multi = build_distance_area(
                        layer.crs(), QgsProject.instance().transformContext()
                    )
                sorted_feats, values = sort_multi(
                    features, [primary_spec, secondary_spec], layer,
                    progress_callback=progress_callback,
                    distance_area=da_multi,
                )
                # Avviso geodetico basato sul criterio primario
                prim_key = primary_spec.get("key", "")
                self._last_geodesic_warning = geographic_crs_warning(
                    layer.crs(), prim_key, da_multi is not None
                )
                return sorted_feats, values, "sort_value", []
            # Primario basato su linea: secondario ignorato, prosegue il flusso normale.

        # ── Per attributo / espressione ──────────────────────────────────────
        if self.rb_attribute.isChecked():
            nulls_last = self.chk_nulls_last.isChecked()
            natural_sort = self.chk_natural_sort.isChecked()

            if self._active_expression:
                # Modalità espressione
                from .geosort_core import sort_by_expression
                sorted_feats, values, warnings = sort_by_expression(
                    features, layer, self._active_expression, ascending, nulls_last,
                    natural_sort=natural_sort, progress_callback=progress_callback,
                )
                if warnings:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"Espressione: {len(warnings)} avvisi. Vedere il log per i dettagli.",
                        "GeoSort", Qgis.MessageLevel.Warning,
                    )
                return sorted_feats, values, "sort_expr", []

            else:
                # Modalità campo singolo
                field = self.combo_field.currentField()
                if not field:
                    raise ValueError("Nessun campo selezionato.")
                sorted_feats = sort_by_attribute(
                    features, field, ascending, nulls_last, natural_sort=natural_sort,
                    progress_callback=progress_callback,
                )
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
            # Misura geodetica solo per "distanza da punto di riferimento"
            da_centroid = None
            if axis == "dist" and resolve_geodesic(layer.crs(), "centroid_dist", geo_mode):
                da_centroid = build_distance_area(
                    layer.crs(), QgsProject.instance().transformContext()
                )
            sorted_feats, values = sort_by_centroid(
                features, axis, ascending, ref_point,
                progress_callback=progress_callback,
                distance_area=da_centroid,
            )
            self._last_geodesic_warning = geographic_crs_warning(
                layer.crs(), "centroid_dist" if axis == "dist" else axis,
                da_centroid is not None,
            )
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
            # Misura geodetica per area/perimetro/lunghezza; bbox_* e n_vertices restano planari
            da_geom = None
            if resolve_geodesic(layer.crs(), criterion, geo_mode):
                da_geom = build_distance_area(
                    layer.crs(), QgsProject.instance().transformContext()
                )
            sorted_feats, values = sort_by_geometry_property(
                features, criterion, ascending,
                progress_callback=progress_callback,
                distance_area=da_geom,
            )
            self._last_geodesic_warning = geographic_crs_warning(
                layer.crs(), criterion, da_geom is not None
            )
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
                features, line_geom, ascending, mode=mode,
                progress_callback=progress_callback,
            )
            return sorted_feats, values, "sort_dist", excluded

        # ── Per distanza dalla linea ─────────────────────────────────────────
        if self.rb_line_distance.isChecked():
            ref_layer = self.combo_ref_layer_dist.currentLayer()
            if not ref_layer:
                raise ValueError("Nessun layer di riferimento selezionato.")
            ref_feats = list(ref_layer.getFeatures())
            if not ref_feats:
                raise ValueError("Il layer di riferimento non contiene feature.")
            line_geom = QgsGeometry.unaryUnion([f.geometry() for f in ref_feats])
            mode = self.combo_line_distance_mode.currentData()
            da_linedist = None
            if resolve_geodesic(layer.crs(), "line_distance", geo_mode):
                da_linedist = build_distance_area(
                    layer.crs(), QgsProject.instance().transformContext()
                )
            sorted_feats, values = sort_by_line_distance(
                features, line_geom, ascending, mode=mode,
                progress_callback=progress_callback,
                distance_area=da_linedist,
            )
            self._last_geodesic_warning = geographic_crs_warning(
                layer.crs(), "line_distance", da_linedist is not None
            )
            return sorted_feats, values, "sort_dist", []

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

        layer = self.layer_combo.currentLayer()
        if not layer:
            QMessageBox.warning(self, "GeoSort", "Nessun layer selezionato.")
            return False

        try:
            features = self._load_features(layer)
        except ValueError as exc:
            QMessageBox.warning(self, "GeoSort", str(exc))
            return False
        total = len(features)
        if not total:
            QMessageBox.warning(self, "GeoSort", "Il layer non contiene feature.")
            return False

        # Controllo sovrascrittura (prima di avviare il progress)
        if self.rb_update.isChecked() and layer.fields().indexOf("sort_order") != -1:
            reply = QMessageBox.question(
                self,
                "GeoSort",
                "Il campo 'sort_order' esiste già nel layer.\n"
                "Sovrascriverlo con il nuovo ordinamento?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        # ── Progress dialog ───────────────────────────────────────────────────
        progress = QProgressDialog(
            "Ordinamento in corso...", "Annulla", 0, 100, self
        )
        progress.setWindowTitle("GeoSort")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)
        progress.setValue(0)

        def _check_cancel():
            QApplication.processEvents()
            if progress.wasCanceled():
                raise RuntimeError("Operazione annullata dall'utente.")

        try:
            # Fase 1: raccolta e ordinamento (0% → 50%)
            def sort_progress(pct):
                progress.setValue(int(pct * 0.5))
                _check_cancel()

            progress.setLabelText("Ordinamento in corso...")
            sorted_feats, values, crit_name, excluded = self._collect_sorted(
                progress_callback=sort_progress, features=features,
            )
            _check_cancel()

            add_crit = self.chk_add_value.isChecked()
            n = len(sorted_feats)
            excl_msg = (f"\n{len(excluded)} feature escluse (non intersecano la linea)."
                        if excluded else "")

            # Fase 2: scrittura (50% → 100%)
            def write_progress(pct):
                progress.setValue(50 + int(pct * 0.5))
                _check_cancel()

            geo_warn = getattr(self, "_last_geodesic_warning", "")
            geo_suffix = f"\n\nℹ {geo_warn}" if geo_warn else ""

            if self.rb_update.isChecked():
                progress.setLabelText("Scrittura sul layer...")
                ok = apply_sort_order(
                    layer, sorted_feats, add_crit, values, crit_name,
                    progress_callback=write_progress,
                )
                _check_cancel()
                if ok:
                    layer.triggerRepaint()
                    progress.close()
                    QMessageBox.information(
                        self,
                        "GeoSort",
                        f"Ordinamento applicato con successo.\n"
                        f"Campo 'sort_order' aggiornato su {n} feature.{excl_msg}"
                        f"{geo_suffix}",
                    )
                else:
                    progress.close()
                    QMessageBox.critical(
                        self, "GeoSort",
                        "Errore durante l'applicazione dell'ordinamento.\n"
                        "Controllare il log messaggi di QGIS per i dettagli."
                    )
                return ok

            else:
                progress.setLabelText("Creazione layer in memoria...")
                mem_layer = create_memory_layer(
                    layer, sorted_feats, add_crit, values, crit_name,
                    progress_callback=write_progress,
                )
                _check_cancel()
                QgsProject.instance().addMapLayer(mem_layer)
                progress.close()
                QMessageBox.information(
                    self,
                    "GeoSort",
                    f"Nuovo layer 'GeoSort_output' aggiunto al progetto\n"
                    f"con {n} feature ordinate.{excl_msg}"
                    f"{geo_suffix}",
                )
                return True

        except RuntimeError:
            # Utente ha premuto Annulla
            progress.close()
            QMessageBox.information(
                self, "GeoSort", "Operazione annullata dall'utente."
            )
            return False
        except Exception as exc:
            progress.close()
            QMessageBox.warning(self, "GeoSort", str(exc))
            return False

    def _on_ok(self):
        if self._run():
            self.accept()

    def _on_apply(self):
        self._run()

    def _on_help(self):
        from qgis.PyQt.QtWidgets import QTextBrowser, QVBoxLayout, QDialogButtonBox
        help_path = os.path.join(os.path.dirname(__file__), "help.html")
        try:
            with open(help_path, encoding="utf-8") as f:
                html = f.read()
        except OSError:
            html = "<p>File di guida non trovato.</p>"

        dlg = QDialog(self)
        dlg.setWindowTitle("GeoSort – Guida rapida")
        dlg.setMinimumSize(520, 420)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("QTextBrowser { background-color: #ffffff; color: #222222; }")
        browser.setHtml(html)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.close)
        layout.addWidget(buttons)
        dlg.exec()

    # ──────────────────────────────────────────────────────────────────────────
    # Metodi pubblici per i test
    # ──────────────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """ESC chiude il dialog (equivalente ad Annulla)."""
        if event.key() == Qt.Key.Key_Escape:
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
