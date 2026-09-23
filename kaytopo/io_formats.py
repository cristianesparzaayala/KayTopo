# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Iterable, Optional
from xml.etree import ElementTree as ET

from .models import ImportResult, SourceMetadata, TopoPoint

_META_RE = re.compile(r"^\s*#\s*([A-Za-z0-9_\-]+)\s*=\s*(.*?)\s*$")
_DMS_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*(?:°|d|deg)?\s*"
    r"(?:(\d+(?:\.\d+)?)\s*(?:'|m|min))?\s*"
    r"(?:(\d+(?:\.\d+)?)\s*(?:\"|s|sec))?\s*([NSEW])?\s*$",
    re.IGNORECASE,
)


def parse_number_or_dms(value: str) -> float:
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    m = _DMS_RE.match(value)
    if not m:
        raise ValueError(f"Valor numérico/coordenada no reconocido: {value!r}")
    degrees = float(m.group(1))
    minutes = float(m.group(2) or 0)
    seconds = float(m.group(3) or 0)
    hemi = (m.group(4) or "").upper()
    sign = -1.0 if degrees < 0 else 1.0
    degrees = abs(degrees) + minutes / 60.0 + seconds / 3600.0
    if hemi in {"S", "W"}:
        sign = -1.0
    elif hemi in {"N", "E"}:
        sign = 1.0
    return sign * degrees


def _metadata_from_pairs(pairs: dict[str, str]) -> SourceMetadata:
    md = SourceMetadata()
    for key, raw in pairs.items():
        k = key.strip().upper()
        v = raw.strip()
        if k in {"CRS", "CRS_TYPE", "TYPE"}:
            md.crs_type = v.upper()
        elif k in {"DATUM", "FRAME", "MARCO"}:
            md.datum = v.upper()
        elif k in {"ZONE", "ZONA", "UTM_ZONE"}:
            md.zone = int(v)
        elif k in {"HEMISPHERE", "HEMISFERIO", "HEMI"}:
            md.hemisphere = v.upper()[0]
        elif k in {"CENTRAL_MERIDIAN", "MERIDIANO_CENTRAL", "LON_0"}:
            md.central_meridian = parse_number_or_dms(v)
        elif k == "EPSG":
            md.epsg = int(v)
            md.crs_type = md.crs_type or "EPSG"
        elif k in {"COLUMNS", "COLUMNAS"}:
            md.columns = [c.strip().upper() for c in re.split(r"[,;\s]+", v) if c.strip()]
        elif k in {"UNITS", "UNIDADES"}:
            md.units = v
        elif k in {"NOTE", "NOTES", "NOTA", "NOTAS"}:
            md.notes.append(v)
    return md


def _looks_like_header(tokens: list[str]) -> bool:
    known = {"N", "NO", "NUM", "NUMERO", "ID", "P", "X", "Y", "Z", "E", "NORTE", "ESTE", "LAT", "LON", "LONG", "LATITUD", "LONGITUD"}
    upper = {t.strip().upper() for t in tokens}
    return bool(upper & known) and any(not _can_parse_number(t) for t in tokens)


def _can_parse_number(v: str) -> bool:
    try:
        parse_number_or_dms(v)
        return True
    except Exception:
        return False


def _normalize_column_name(name: str) -> str:
    n = name.strip().upper().replace(" ", "_")
    mapping = {
        "N": "ID", "NO": "ID", "NUM": "ID", "NUMERO": "ID", "NÚMERO": "ID", "P": "ID",
        "E": "X", "ESTE": "X", "EASTING": "X",
        "NORTE": "Y", "NORTHING": "Y",
        "LON": "X", "LONG": "X", "LONGITUD": "X", "LONGITUDE": "X",
        "LAT": "Y", "LATITUD": "Y", "LATITUDE": "Y",
        "COTA": "Z", "ELEV": "Z", "ELEVACION": "Z", "ELEVACIÓN": "Z", "ALT": "Z",
    }
    return mapping.get(n, n)


def _infer_columns(rows: list[list[str]]) -> list[str]:
    if not rows:
        raise ValueError("El archivo no contiene filas de coordenadas.")
    width = len(rows[0])
    if width < 2:
        raise ValueError("Se requieren al menos dos columnas de coordenadas.")

    # Common survey convention: sequential/integer point number first.
    first_vals = [r[0].strip() for r in rows[: min(20, len(rows))] if len(r) == width]
    first_is_id = bool(first_vals) and all(re.fullmatch(r"[A-Za-z]*\d+", v) for v in first_vals)

    if width == 2:
        return ["X", "Y"]
    if width == 3:
        return ["ID", "X", "Y"] if first_is_id else ["X", "Y", "Z"]
    if width >= 4:
        return ["ID", "X", "Y", "Z"] + [f"EXTRA{i}" for i in range(5, width + 1)]
    raise ValueError("No fue posible inferir las columnas.")


def _split_text_rows(text: str, extension: str) -> tuple[SourceMetadata, list[list[str]]]:
    metadata_pairs: dict[str, str] = {}
    data_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _META_RE.match(line)
        if m and not data_lines:
            metadata_pairs[m.group(1)] = m.group(2)
            continue
        if line.lstrip().startswith("#") and not data_lines:
            continue
        data_lines.append(line)

    md = _metadata_from_pairs(metadata_pairs)
    if not data_lines:
        return md, []

    sample = "\n".join(data_lines[:20])
    delimiter: Optional[str] = None
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = None

    rows: list[list[str]] = []
    if delimiter:
        reader = csv.reader(io.StringIO("\n".join(data_lines)), delimiter=delimiter)
        rows = [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    else:
        # Whitespace separated files, common in CivilCAD point files.
        rows = [re.split(r"\s+", line.strip()) for line in data_lines if line.strip()]

    if rows and _looks_like_header(rows[0]):
        if not md.columns:
            md.columns = [_normalize_column_name(c) for c in rows[0]]
        rows = rows[1:]
    return md, rows


def read_delimited(path: str | Path) -> ImportResult:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    md, rows = _split_text_rows(text, path.suffix.lower())
    md.source_file = path.name
    md.source_format = path.suffix.lower().lstrip(".").upper()
    if not rows:
        raise ValueError("No se encontraron coordenadas en el archivo.")

    columns = md.columns or _infer_columns(rows)
    columns = [_normalize_column_name(c) for c in columns]
    md.columns = columns
    if "X" not in columns or "Y" not in columns:
        raise ValueError(f"Las columnas deben incluir X e Y. Interpretación actual: {columns}")

    points: list[TopoPoint] = []
    for idx, row in enumerate(rows, 1):
        if len(row) < len([c for c in columns if not c.startswith("EXTRA")]):
            raise ValueError(f"Fila {idx}: número insuficiente de columnas: {row}")
        values = {columns[i]: row[i] for i in range(min(len(columns), len(row)))}
        pid = values.get("ID", str(idx)).strip() or str(idx)
        x = parse_number_or_dms(values["X"])
        y = parse_number_or_dms(values["Y"])
        z = None
        if "Z" in values and values["Z"].strip() != "":
            z = parse_number_or_dms(values["Z"])
        points.append(TopoPoint(id=pid, x_original=x, y_original=y, z_original=z, z=z, z_source="SURVEY" if z is not None else "NONE"))

    warnings: list[str] = []
    if md.crs_type is None:
        # Only a candidate; never silently treated as definitive by the app.
        xs = [p.x_original for p in points]
        ys = [p.y_original for p in points]
        if all(-180 <= x <= 180 for x in xs) and all(-90 <= y <= 90 for y in ys):
            md.crs_type = "GEOGRAPHIC_CANDIDATE"
            warnings.append("Las magnitudes parecen coordenadas geográficas; confirme CRS/datum antes de convertir.")
        elif all(10000 <= abs(x) <= 1_000_000 for x in xs) and all(0 <= abs(y) <= 10_500_000 for y in ys):
            md.crs_type = "PROJECTED_CANDIDATE"
            warnings.append("Las magnitudes parecen coordenadas proyectadas (UTM/TME); confirme sistema, zona/meridiano y datum.")
        else:
            md.crs_type = "UNKNOWN"
            warnings.append("No fue posible inferir con seguridad el sistema de coordenadas.")

    return ImportResult(points=points, metadata=md, boundary_closed=False, warnings=warnings)


def _parse_kml_bytes(data: bytes, source_name: str) -> ImportResult:
    root = ET.fromstring(data)
    coord_nodes = root.findall(".//{*}coordinates")
    altitude_modes = [(n.text or "").strip().lower() for n in root.findall(".//{*}altitudeMode")]
    trust_altitude = any(m == "absolute" for m in altitude_modes)
    if not coord_nodes:
        raise ValueError("El KML/KMZ no contiene elementos <coordinates>.")

    # Prefer polygon/ring coordinate sequences with >2 points, otherwise first geometry found.
    sequences: list[list[tuple[float, float, Optional[float]]]] = []
    for node in coord_nodes:
        text = (node.text or "").strip()
        if not text:
            continue
        seq = []
        for chunk in re.split(r"\s+", text):
            parts = chunk.split(",")
            if len(parts) < 2:
                continue
            lon = float(parts[0])
            lat = float(parts[1])
            raw_alt = float(parts[2]) if len(parts) >= 3 and parts[2] != "" else None
            # KML defaults to clampToGround; a numeric third component (often 0) is not
            # treated as a surveyed elevation unless altitudeMode is explicitly absolute.
            alt = raw_alt if trust_altitude else None
            seq.append((lon, lat, alt))
        if seq:
            sequences.append(seq)

    if not sequences:
        raise ValueError("No se pudieron leer coordenadas válidas del KML/KMZ.")
    seq = max(sequences, key=len)
    boundary_closed = len(seq) > 2 and seq[0][:2] == seq[-1][:2]
    if boundary_closed:
        seq = seq[:-1]

    points = [
        TopoPoint(
            id=str(i),
            x_original=lon,
            y_original=lat,
            z_original=alt,
            z=alt,
            z_source="SURVEY" if alt is not None else "NONE",
        )
        for i, (lon, lat, alt) in enumerate(seq, 1)
    ]
    md = SourceMetadata(
        crs_type="GEOGRAPHIC",
        datum="WGS84",
        columns=["ID", "X", "Y", "Z"],
        units="degrees",
        source_file=source_name,
        source_format="KML",
    )
    return ImportResult(points=points, metadata=md, boundary_closed=boundary_closed)


def read_kml(path: str | Path) -> ImportResult:
    path = Path(path)
    return _parse_kml_bytes(path.read_bytes(), path.name)


def read_kmz(path: str | Path) -> ImportResult:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
        if not names:
            raise ValueError("El KMZ no contiene ningún archivo KML.")
        preferred = "doc.kml" if "doc.kml" in names else names[0]
        result = _parse_kml_bytes(zf.read(preferred), path.name)
        result.metadata.source_format = "KMZ"
        return result


def read_input(path: str | Path) -> ImportResult:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".kml":
        return read_kml(path)
    if ext == ".kmz":
        return read_kmz(path)
    if ext in {".csv", ".txt", ".dat"}:
        return read_delimited(path)
    raise ValueError(f"Formato no compatible: {ext}. Use KML, KMZ, CSV o TXT.")
