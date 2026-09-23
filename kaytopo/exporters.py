# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import ezdxf

from .crs import output_crs_definition
from .models import OutputCRS, SourceMetadata, TopoPoint

APP_NAME = "KayTopo"
VERSION = "0.1.2-alpha"
AUTHOR = "Cristian Esparza Ayala"
COPYRIGHT = f"Copyright (c) 2026 {AUTHOR}"

LAYER_SPECS = {
    "KTOPO_LIMITE": (1, "CONTINUOUS", 35),
    "KTOPO_VERTICES": (3, "CONTINUOUS", 25),
    "KTOPO_NUMEROS": (7, "CONTINUOUS", 18),
    "KTOPO_RELIEVE": (8, "CONTINUOUS", 9),
    "KTOPO_CONTROL": (6, "CONTINUOUS", 30),
    "KTOPO_REFERENCIA": (4, "DASHED", 13),
    "KTOPO_AUX": (8, "DASHED", 9),
}


def _safe_float(v: Optional[float], decimals: int) -> str:
    return "" if v is None else f"{v:.{decimals}f}"


def _renumber_points(points: list[TopoPoint], preserve_ids: bool = True) -> list[TopoPoint]:
    """Return export-only copies with stable point numbering.

    Vertex IDs are preserved by default because imported survey numbering may be meaningful.
    Relief points are intentionally renumbered 1..N inside their own file so they never
    depend on the number of polygon vertices.
    """
    out: list[TopoPoint] = []
    for i, p in enumerate(points, 1):
        pid = str(p.id).strip() if preserve_ids and str(p.id).strip() else str(i)
        if not preserve_ids:
            pid = str(i)
        out.append(
            TopoPoint(
                id=pid,
                x_original=p.x_original,
                y_original=p.y_original,
                z_original=p.z_original,
                x=p.x,
                y=p.y,
                z=p.z,
                z_source=p.z_source,
                kind=p.kind,
            )
        )
    return out


def export_csv(path: str | Path, points: list[TopoPoint], decimals: int = 3, preserve_ids: bool = True) -> Path:
    """CivilCAD-friendly clean CSV. No headers or copyright rows are inserted."""
    path = Path(path)
    exported = _renumber_points(points, preserve_ids=preserve_ids)
    include_z = any(p.final_xyz()[2] is not None for p in exported)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",", lineterminator="\n")
        for p in exported:
            x, y, z = p.final_xyz()
            row = [p.id, _safe_float(x, decimals), _safe_float(y, decimals)]
            if include_z:
                row.append(_safe_float(z, decimals))
            writer.writerow(row)
    return path


def export_txt(path: str | Path, points: list[TopoPoint], decimals: int = 3, preserve_ids: bool = True) -> Path:
    """CivilCAD-friendly tab-delimited point file. No metadata preamble."""
    path = Path(path)
    exported = _renumber_points(points, preserve_ids=preserve_ids)
    include_z = any(p.final_xyz()[2] is not None for p in exported)
    with path.open("w", encoding="utf-8", newline="") as f:
        for p in exported:
            x, y, z = p.final_xyz()
            row = [p.id, _safe_float(x, decimals), _safe_float(y, decimals)]
            if include_z:
                row.append(_safe_float(z, decimals))
            f.write("\t".join(row) + "\n")
    return path


def _ensure_layer(doc: ezdxf.document.Drawing, name: str) -> None:
    color, ltype, lw = LAYER_SPECS[name]
    if ltype == "DASHED" and "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[0.6, 0.3, -0.3], description="Dashed __ __ __")
    if name not in doc.layers:
        doc.layers.add(name=name, color=color, linetype=ltype, lineweight=lw)


def _inject_dxf_comments(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "0\nSECTION\n2\nHEADER\n"
    comments = (
        "999\nKayTopo\n"
        f"999\n{COPYRIGHT}\n"
        f"999\nGenerated with KayTopo {VERSION}\n"
        "999\nSPDX-License-Identifier: GPL-3.0-or-later\n"
    )
    if marker in text:
        text = text.replace(marker, marker + comments, 1)
    else:
        text = comments + text
    path.write_text(text, encoding="utf-8", newline="\n")


def export_dxf(
    path: str | Path,
    vertices: list[TopoPoint],
    relief: list[TopoPoint] | None = None,
    scale: int = 100,
    standard_layers: bool = True,
) -> Path:
    path = Path(path)
    relief = relief or []
    doc = ezdxf.new("R2013", setup=True)
    doc.units = 6  # meters
    doc.header["$INSUNITS"] = 6
    doc.header["$PDMODE"] = 34  # plus + circle
    symbol_size_m = 5.0 * scale / 1000.0  # 5 mm on paper
    text_height_m = 3.0 * scale / 1000.0  # 3 mm on paper
    doc.header["$PDSIZE"] = symbol_size_m
    try:
        doc.header["$PROJECTNAME"] = "KayTopo"
        doc.header["$LASTSAVEDBY"] = AUTHOR
    except Exception:
        pass

    xrec = doc.rootdict.add_xrecord("KAYTOPO_METADATA")
    xrec.reset([
        (1, "KayTopo"),
        (1, COPYRIGHT),
        (1, f"Version {VERSION}"),
        (1, "SPDX-License-Identifier: GPL-3.0-or-later"),
    ])

    msp = doc.modelspace()
    if standard_layers:
        used = {"KTOPO_VERTICES", "KTOPO_NUMEROS"}
        if len(vertices) >= 2:
            used.add("KTOPO_LIMITE")
        if relief:
            used.add("KTOPO_RELIEVE")
        if any(p.kind == "CONTROL" for p in vertices):
            used.add("KTOPO_CONTROL")
        for layer in used:
            _ensure_layer(doc, layer)
    else:
        for name in ("BOUNDARY", "POINTS", "LABELS", "RELIEF"):
            if name not in doc.layers:
                doc.layers.add(name=name, color=7)

    layer_limit = "KTOPO_LIMITE" if standard_layers else "BOUNDARY"
    layer_vertices = "KTOPO_VERTICES" if standard_layers else "POINTS"
    layer_labels = "KTOPO_NUMEROS" if standard_layers else "LABELS"
    layer_relief = "KTOPO_RELIEVE" if standard_layers else "RELIEF"

    if len(vertices) >= 2:
        poly = [(p.final_xyz()[0], p.final_xyz()[1]) for p in vertices]
        msp.add_lwpolyline(poly, close=True, dxfattribs={"layer": layer_limit})

    label_offset = symbol_size_m * 0.65
    for p in vertices:
        x, y, z = p.final_xyz()
        layer = "KTOPO_CONTROL" if standard_layers and p.kind == "CONTROL" else layer_vertices
        msp.add_point((x, y, z or 0.0), dxfattribs={"layer": layer})
        txt = msp.add_text(str(p.id), height=text_height_m, dxfattribs={"layer": layer_labels})
        txt.dxf.insert = (x + label_offset, y + label_offset, 0.0)

    for p in relief:
        x, y, z = p.final_xyz()
        msp.add_point((x, y, z or 0.0), dxfattribs={"layer": layer_relief})

    doc.saveas(path)
    _inject_dxf_comments(path)
    return path


def write_info_file(
    path: str | Path,
    source: SourceMetadata,
    out_crs: OutputCRS,
    vertices: list[TopoPoint],
    relief: list[TopoPoint] | None = None,
    dem_path: str | None = None,
    warnings: list[str] | None = None,
    dem_sampling_method: str = "nearest",
) -> Path:
    path = Path(path)
    relief = relief or []
    warnings = warnings or []
    z_survey = sum(1 for p in vertices if p.z_source == "SURVEY")
    z_dem = sum(1 for p in vertices if p.z_source == "DEM")
    z_none = sum(1 for p in vertices if p.z is None)
    dst = output_crs_definition(out_crs)
    lines = [
        "KayTopo - Registro de exportación",
        f"{COPYRIGHT}",
        f"Versión: {VERSION}",
        "Licencia del software: GPL-3.0-or-later",
        "",
        f"Fecha UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Archivo origen: {source.source_file or 'N/D'}",
        f"Formato origen: {source.source_format or 'N/D'}",
        f"CRS origen declarado: {source.crs_type or 'N/D'}",
        f"Datum/marco origen: {source.datum or 'N/D'}",
        f"Zona origen: {source.zone if source.zone is not None else 'N/D'}",
        f"Hemisferio origen: {source.hemisphere or 'N/D'}",
        f"Meridiano central TME: {source.central_meridian if source.central_meridian is not None else 'N/D'}",
        "",
        f"CRS destino: {out_crs.label}",
        f"Definición destino: {dst.to_string()}",
        "Unidades de salida: metros",
        f"Vértices: {len(vertices)}",
        f"Puntos interiores de relieve: {len(relief)}",
        f"Z desde archivo/levantamiento: {z_survey}",
        f"Z desde DEM: {z_dem}",
        f"Puntos sin Z: {z_none}",
        f"DEM/GeoTIFF: {dem_path or 'No utilizado'}",
        f"Método de muestreo Z: {dem_sampling_method if dem_path else 'No utilizado'}",
        "",
        "Nota: KayTopo no transforma datums verticales. Las elevaciones del archivo se conservan;",
        "si se usa un DEM, su Z se toma del raster únicamente para puntos sin elevación original.",
    ]
    if warnings:
        lines.extend(["", "Advertencias:"] + [f"- {w}" for w in warnings])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
