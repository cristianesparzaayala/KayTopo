# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGraphicsScene,
    QGraphicsView, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget, QDoubleSpinBox
)

from .dem import dem_info
from .models import OutputCRS
from .service import KayTopoProject
from .exporters import VERSION
from .resources import app_icon_path


class DropFileLineEdit(QLineEdit):
    """Compact read-only field that also accepts supported files from Explorer."""

    def __init__(self, extensions: set[str], on_drop, parent=None) -> None:
        super().__init__(parent)
        self.extensions = {ext.lower() for ext in extensions}
        self.on_drop = on_drop
        self.setReadOnly(True)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Selecciona o arrastra un archivo aquí")

    def _first_supported_path(self, event) -> str | None:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in self.extensions:
                return path
        return None

    def dragEnterEvent(self, event) -> None:
        if self._first_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._first_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = self._first_supported_path(event)
        if not path:
            event.ignore()
            return
        self.on_drop(path)
        event.acceptProposedAction()


class PreviewView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(self.renderHints())
        self.setMinimumHeight(420)

    def set_project(self, project: KayTopoProject) -> None:
        scene = self.scene()
        scene.clear()
        pts = project.transformed
        if not pts:
            return
        xs = [p.final_xyz()[0] for p in pts]
        ys = [p.final_xyz()[1] for p in pts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        span = max(maxx - minx, maxy - miny, 1.0)
        sx = 700.0 / span

        def xy(p):
            x, y, _ = p.final_xyz()
            return (x - minx) * sx, -(y - miny) * sx

        boundary_pen = QPen(QColor(220, 70, 70), 2)
        point_pen = QPen(QColor(70, 200, 100), 1)
        relief_pen = QPen(QColor(150, 150, 150), 1)
        relief_brush = QBrush(QColor(150, 150, 150))

        if len(pts) >= 2:
            coords = [xy(p) for p in pts]
            for i in range(len(coords)):
                x1, y1 = coords[i]
                x2, y2 = coords[(i + 1) % len(coords)]
                scene.addLine(x1, y1, x2, y2, boundary_pen)

        marker = max(4.0, min(9.0, span * sx / 120.0))
        for p in pts:
            x, y = xy(p)
            r = marker / 2
            scene.addEllipse(x-r, y-r, marker, marker, point_pen)
            scene.addLine(x-r, y, x+r, y, point_pen)
            scene.addLine(x, y-r, x, y+r, point_pen)
            t = scene.addText(str(p.id))
            t.setDefaultTextColor(QColor(230, 230, 230))
            t.setScale(0.75)
            t.setPos(x + r + 2, y - r - 4)

        # Relief is intentionally rendered as subtle dots in preview.
        for p in project.relief[:100_000]:
            x, y = xy(p)
            scene.addEllipse(x-1, y-1, 2, 2, relief_pen, relief_brush)

        rect = scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        scene.setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)


class KayTopoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.project = KayTopoProject()
        self.setWindowTitle(f"KayTopo {VERSION}")
        icon_path = app_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1060, 720)

        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("KayTopo")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("Conversión y preparación topográfica · © 2026 Cristian Esparza Ayala")
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.stack = QStackedWidget()
        self.pages = [self._page_import(), self._page_crs(), self._page_elevation(), self._page_preview(), self._page_export()]
        for p in self.pages:
            self.stack.addWidget(p)
        layout.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Atrás")
        self.next_btn = QPushButton("Siguiente →")
        self.back_btn.clicked.connect(self.go_back)
        self.next_btn.clicked.connect(self.go_next)
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)
        self.setCentralWidget(root)
        self._sync_nav()

    def _page_import(self) -> QWidget:
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("1 · Importar datos"))
        box = QGroupBox("Archivo de entrada")
        form = QFormLayout(box)
        self.file_edit = DropFileLineEdit({".kml", ".kmz", ".csv", ".txt", ".dat"}, self._load_input_path)
        browse = QPushButton("Seleccionar KML / KMZ / CSV / TXT")
        browse.clicked.connect(self.choose_input)
        row = QHBoxLayout(); row.addWidget(self.file_edit); row.addWidget(browse)
        w = QWidget(); w.setLayout(row); form.addRow("Archivo:", w)
        drag_hint = QLabel("También puedes arrastrar el archivo desde el Explorador de Windows.")
        drag_hint.setStyleSheet("color: #777; font-size: 11px;")
        form.addRow("", drag_hint)
        self.import_summary = QTextEdit(); self.import_summary.setReadOnly(True); self.import_summary.setMinimumHeight(260)
        form.addRow(self.import_summary)
        lay.addWidget(box)
        help_lbl = QLabel(
            "CSV/TXT puede incluir metadatos opcionales al inicio con líneas # CLAVE=VALOR. "
            "Si no existen, KayTopo pedirá CRS, zona, hemisferio o meridiano central antes de convertir."
        )
        help_lbl.setWordWrap(True); lay.addWidget(help_lbl)
        capabilities = QLabel(
            "Formatos de entrada: KML · KMZ · CSV · TXT  |  "
            "Coordenadas compatibles: geográficas/geodésicas · UTM · TME · CRS por EPSG  |  Salida: UTM"
        )
        capabilities.setWordWrap(True)
        capabilities.setStyleSheet("color: #777; font-size: 11px;")
        lay.addWidget(capabilities); lay.addStretch(1)
        return page

    def _page_crs(self) -> QWidget:
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("2 · Sistema de coordenadas"))
        box = QGroupBox("Origen"); form = QFormLayout(box)
        self.src_type = QComboBox(); self.src_type.addItems(["GEOGRAPHIC", "UTM", "TME", "EPSG"])
        self.src_datum = QComboBox(); self.src_datum.addItems(["WGS84", "ITRF2008"])
        self.src_zone = QSpinBox(); self.src_zone.setRange(1,60); self.src_zone.setValue(14)
        self.src_hemi = QComboBox(); self.src_hemi.addItems(["N","S"])
        self.src_meridian = QDoubleSpinBox(); self.src_meridian.setRange(-180,180); self.src_meridian.setDecimals(8); self.src_meridian.setValue(-99)
        self.src_epsg = QSpinBox(); self.src_epsg.setRange(1,999999); self.src_epsg.setValue(4326)
        form.addRow("Tipo:", self.src_type); form.addRow("Datum / marco:", self.src_datum)
        form.addRow("Zona UTM:", self.src_zone); form.addRow("Hemisferio:", self.src_hemi)
        form.addRow("Meridiano central TME:", self.src_meridian); form.addRow("EPSG:", self.src_epsg)
        lay.addWidget(box)

        out = QGroupBox("Salida UTM"); of = QFormLayout(out)
        self.out_frame = QComboBox(); self.out_frame.addItems(["WGS84", "ITRF2008"])
        self.out_zone = QSpinBox(); self.out_zone.setRange(1,60); self.out_zone.setValue(14)
        self.out_hemi = QComboBox(); self.out_hemi.addItems(["N","S"])
        suggest = QPushButton("Sugerir zona desde los datos")
        suggest.clicked.connect(self.suggest_utm)
        of.addRow("Marco:", self.out_frame); of.addRow("Zona:", self.out_zone); of.addRow("Hemisferio:", self.out_hemi); of.addRow(suggest)
        lay.addWidget(out)
        note = QLabel("KayTopo nunca decide silenciosamente un CRS ambiguo. Revise esta pantalla antes de transformar.")
        note.setWordWrap(True); lay.addWidget(note); lay.addStretch(1)
        return page

    def _page_elevation(self) -> QWidget:
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("3 · Elevación (opcional)"))
        self.z_status = QLabel(); self.z_status.setWordWrap(True); lay.addWidget(self.z_status)
        box = QGroupBox("DEM / GeoTIFF"); form = QFormLayout(box)
        self.dem_edit = DropFileLineEdit({".tif", ".tiff", ".dem"}, self._load_dem_path)
        btn = QPushButton("Seleccionar DEM / TIFF")
        btn.clicked.connect(self.choose_dem)
        row = QHBoxLayout(); row.addWidget(self.dem_edit); row.addWidget(btn)
        w = QWidget(); w.setLayout(row); form.addRow("Raster:", w)
        dem_drag_hint = QLabel("También puedes arrastrar aquí un DEM/GeoTIFF desde el Explorador de Windows.")
        dem_drag_hint.setStyleSheet("color: #777; font-size: 11px;")
        form.addRow("", dem_drag_hint)
        self.dem_info_label = QLabel("Sin raster cargado.")
        self.dem_info_label.setWordWrap(True)
        self.dem_info_label.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow("Información:", self.dem_info_label)
        self.dem_sampling = QComboBox()
        self.dem_sampling.addItems([
            "Valor de celda (más cercano)",
            "Bilineal (interpolada)",
        ])
        form.addRow("Método para Z:", self.dem_sampling)
        sampling_note = QLabel(
            "Bilineal suaviza la Z entre cuatro celdas vecinas; no aumenta la resolución ni la precisión real del DEM."
        )
        sampling_note.setWordWrap(True)
        sampling_note.setStyleSheet("color: #777; font-size: 11px;")
        form.addRow("", sampling_note)
        self.relief_check = QCheckBox("Generar puntos interiores de relieve desde celdas del DEM")
        self.relief_check.setChecked(True)
        form.addRow(self.relief_check)
        self.max_relief = QSpinBox(); self.max_relief.setRange(1000, 500000); self.max_relief.setSingleStep(10000); self.max_relief.setValue(100000)
        form.addRow("Máximo de puntos de relieve:", self.max_relief)
        lay.addWidget(box)
        warn = QLabel("Si no existe Z y no carga un DEM, puede continuar: KayTopo generará un archivo 2D X/Y.")
        warn.setWordWrap(True); lay.addWidget(warn); lay.addStretch(1)
        return page

    def _page_preview(self) -> QWidget:
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("4 · Vista previa"))
        self.preview_stats = QLabel(); self.preview_stats.setWordWrap(True)
        lay.addWidget(self.preview_stats)
        self.preview = PreviewView(); lay.addWidget(self.preview, 1)
        return page

    def _page_export(self) -> QWidget:
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(QLabel("5 · Exportar"))
        box = QGroupBox("Archivos"); form = QFormLayout(box)
        self.out_dir = QLineEdit(str(Path.home() / "Desktop")); choose = QPushButton("Carpeta…"); choose.clicked.connect(self.choose_output_dir)
        r = QHBoxLayout(); r.addWidget(self.out_dir); r.addWidget(choose); rw=QWidget(); rw.setLayout(r); form.addRow("Destino:", rw)
        self.basename = QLineEdit("KayTopo_export"); form.addRow("Nombre base:", self.basename)
        self.exp_csv = QCheckBox("CSV (CivilCAD)"); self.exp_csv.setChecked(True)
        self.exp_txt = QCheckBox("TXT (CivilCAD)")
        self.exp_dxf = QCheckBox("DXF (AutoCAD/CAD)"); self.exp_dxf.setChecked(True)
        fr = QHBoxLayout(); fr.addWidget(self.exp_csv); fr.addWidget(self.exp_txt); fr.addWidget(self.exp_dxf); fw=QWidget(); fw.setLayout(fr); form.addRow("Formatos:", fw)
        self.layers_label = QLabel("Capas DXF:")
        self.layers_mode = QComboBox(); self.layers_mode.addItems(["KayTopo Standard", "DXF limpio"]); form.addRow(self.layers_label, self.layers_mode)
        self.scale_label = QLabel("Escala de referencia 1:")
        self.scale = QComboBox(); self.scale.addItems(["50","100","200","250","500","1000"]); self.scale.setCurrentText("100"); form.addRow(self.scale_label, self.scale)
        self.scale_note = QLabel(
            "Solo ajusta el tamaño gráfico de los símbolos y números del DXF. "
            "No escala las coordenadas ni fija la escala final del proyecto."
        )
        self.scale_note.setWordWrap(True); self.scale_note.setStyleSheet("color: #777; font-size: 11px;")
        form.addRow("", self.scale_note)
        self.decimals = QSpinBox(); self.decimals.setRange(0,10); self.decimals.setValue(3); form.addRow("Decimales:", self.decimals)
        self.exp_dxf.toggled.connect(self._sync_dxf_options)
        self._sync_dxf_options(self.exp_dxf.isChecked())
        self.export_btn = QPushButton("EXPORTAR")
        self.export_btn.clicked.connect(self.do_export); form.addRow(self.export_btn)
        lay.addWidget(box)
        self.export_log = QTextEdit(); self.export_log.setReadOnly(True); lay.addWidget(self.export_log,1)
        return page

    def choose_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "Datos (*.kml *.kmz *.csv *.txt *.dat)")
        if path:
            self._load_input_path(path)

    def _load_input_path(self, path: str) -> None:
        try:
            r = self.project.load(path)
            self.file_edit.setText(path)
            zc = sum(1 for p in r.points if p.z_original is not None)
            self.import_summary.setPlainText(
                f"Puntos/vértices: {len(r.points)}\n"
                f"Z presentes: {zc}\n"
                f"Formato: {r.metadata.source_format}\n"
                f"CRS interpretado: {r.metadata.crs_type or 'No definido'}\n"
                f"Datum/marco: {r.metadata.datum or 'No definido'}\n"
                + ("\nAdvertencias:\n- " + "\n- ".join(r.warnings) if r.warnings else "")
            )
            self._prefill_crs_from_metadata()
        except Exception as e:
            QMessageBox.critical(self, "No se pudo importar", str(e))

    def _prefill_crs_from_metadata(self) -> None:
        md = self.project.metadata
        ctype = (md.crs_type or "").replace("_CANDIDATE", "")
        if ctype in [self.src_type.itemText(i) for i in range(self.src_type.count())]: self.src_type.setCurrentText(ctype)
        if md.datum and md.datum.upper() in {"WGS84","ITRF2008"}: self.src_datum.setCurrentText(md.datum.upper())
        if md.zone: self.src_zone.setValue(md.zone)
        if md.hemisphere in {"N","S"}: self.src_hemi.setCurrentText(md.hemisphere)
        if md.central_meridian is not None: self.src_meridian.setValue(md.central_meridian)
        if md.epsg: self.src_epsg.setValue(md.epsg)

    def _apply_source_form(self) -> None:
        md = self.project.metadata
        md.crs_type = self.src_type.currentText()
        md.datum = self.src_datum.currentText()
        md.zone = self.src_zone.value() if md.crs_type == "UTM" else None
        md.hemisphere = self.src_hemi.currentText() if md.crs_type == "UTM" else None
        md.central_meridian = self.src_meridian.value() if md.crs_type == "TME" else None
        md.epsg = self.src_epsg.value() if md.crs_type == "EPSG" else None

    def suggest_utm(self) -> None:
        try:
            self._apply_source_form()
            out = self.project.suggest_utm(self.out_frame.currentText())
            self.out_zone.setValue(out.zone); self.out_hemi.setCurrentText(out.hemisphere)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo sugerir la zona", str(e))

    def choose_dem(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "DEM / GeoTIFF", "", "Raster (*.tif *.tiff *.dem);;Todos (*.*)")
        if path:
            self._load_dem_path(path)

    def _load_dem_path(self, path: str) -> None:
        if Path(path).suffix.lower() not in {".tif", ".tiff", ".dem"}:
            QMessageBox.warning(self, "DEM / GeoTIFF", "Formato de raster no compatible. Use TIF, TIFF o DEM.")
            return
        try:
            info = dem_info(path)
        except Exception as e:
            QMessageBox.warning(self, "DEM / GeoTIFF", f"No se pudo leer el raster:\n{e}")
            return
        self.dem_edit.setText(path)
        rx, ry = info["resolution"]
        nodata = info["nodata"] if info["nodata"] is not None else "No definido"
        self.dem_info_label.setText(
            f"CRS: {info['crs'] or 'No definido'} · Resolución: {rx:g} × {ry:g} · "
            f"Tamaño: {info['width']:,} × {info['height']:,} celdas · NoData: {nodata}"
        )

    def _sync_dxf_options(self, enabled: bool) -> None:
        for widget in (self.layers_label, self.layers_mode, self.scale_label, self.scale, self.scale_note):
            widget.setEnabled(enabled)

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Carpeta de exportación", self.out_dir.text())
        if path: self.out_dir.setText(path)

    def go_back(self) -> None:
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex()-1); self._sync_nav()

    def go_next(self) -> None:
        i = self.stack.currentIndex()
        try:
            if i == 0:
                if not self.project.imported: raise ValueError("Seleccione primero un archivo de entrada.")
            elif i == 1:
                self._apply_source_form()
                out = OutputCRS(self.out_zone.value(), self.out_hemi.currentText(), self.out_frame.currentText())
                self.project.transform(out)
                have_z = sum(1 for p in self.project.transformed if p.z is not None)
                if have_z:
                    self.z_status.setText(f"Se detectaron elevaciones Z en {have_z} de {len(self.project.transformed)} vértices. KayTopo las conservará.")
                else:
                    self.z_status.setText("No se detectó Z. Puede cargar un DEM/GeoTIFF o continuar en 2D con X/Y.")
            elif i == 2:
                dem = self.dem_edit.text().strip()
                if dem:
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    try:
                        sampling_method = "bilinear" if self.dem_sampling.currentIndex() == 1 else "nearest"
                        self.project.apply_dem(
                            dem,
                            self.relief_check.isChecked(),
                            self.max_relief.value(),
                            sampling_method=sampling_method,
                        )
                    finally:
                        QApplication.restoreOverrideCursor()
                elif not any(p.z is not None for p in self.project.transformed):
                    ok = QMessageBox.question(
                        self, "Continuar sin elevaciones",
                        "No se agregó DEM/GeoTIFF y las coordenadas no incluyen Z. El archivo se generará en 2D (X/Y). ¿Desea continuar?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                    )
                    if ok != QMessageBox.Yes: return
                self.preview.set_project(self.project)
                zc = sum(1 for p in self.project.transformed if p.z is not None)
                self.preview_stats.setText(
                    f"Vértices: {len(self.project.transformed):,} · Con Z: {zc:,} · "
                    f"Puntos de relieve: {len(self.project.relief):,} · Salida: {self.project.output_crs.label if self.project.output_crs else ''}"
                )
            if i < self.stack.count()-1:
                self.stack.setCurrentIndex(i+1); self._sync_nav()
        except Exception as e:
            QMessageBox.critical(self, "KayTopo", str(e))

    def do_export(self) -> None:
        if not any([self.exp_csv.isChecked(), self.exp_txt.isChecked(), self.exp_dxf.isChecked()]):
            QMessageBox.warning(self, "Exportación", "Seleccione al menos un formato."); return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                files = self.project.export(
                    self.out_dir.text(), self.basename.text(), self.exp_csv.isChecked(), self.exp_txt.isChecked(),
                    self.exp_dxf.isChecked(), self.decimals.value(), int(self.scale.currentText()),
                    self.layers_mode.currentIndex() == 0,
                )
            finally:
                QApplication.restoreOverrideCursor()
            self.export_log.setPlainText("Exportación terminada:\n\n" + "\n".join(str(p) for p in files))
            QMessageBox.information(self, "KayTopo", "Exportación completada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error de exportación", str(e))

    def _sync_nav(self) -> None:
        i = self.stack.currentIndex()
        self.back_btn.setEnabled(i > 0)
        self.next_btn.setVisible(i < self.stack.count()-1)


def _frozen_smoke_test() -> None:
    """Validate critical runtime pieces without opening the GUI."""
    import ezdxf  # noqa: F401
    import rasterio  # noqa: F401
    import shapely  # noqa: F401
    from pyproj import Transformer

    if not app_icon_path().exists():
        raise RuntimeError("No se encontró el icono empaquetado de KayTopo.")

    tr = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True)
    x, y = tr.transform(-99.1332, 19.4326)
    if not (485000 < x < 487000 and 2147000 < y < 2150000):
        raise RuntimeError("PROJ no pudo realizar la transformación de prueba.")


def run() -> None:
    if os.environ.get("KAYTOPO_SMOKE_TEST") == "1":
        _frozen_smoke_test()
        print("KAYTOPO_SMOKE_OK")
        return

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CristianEsparzaAyala.KayTopo")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("KayTopo")
    app.setApplicationDisplayName("KayTopo")
    app.setOrganizationName("Cristian Esparza Ayala")
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = KayTopoWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    run()
