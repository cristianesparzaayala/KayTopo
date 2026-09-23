# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from pyproj import CRS, Transformer

from .models import OutputCRS, SourceMetadata, TopoPoint

MEXICO_ITRF2008_UTM_EPSG = {11: 6366, 12: 6367, 13: 6368, 14: 6369, 15: 6370, 16: 6371}


class CRSConfigurationError(ValueError):
    pass


def utm_zone_from_longitude(lon: float) -> int:
    if not -180 <= lon <= 180:
        raise CRSConfigurationError(f"Longitud fuera de rango: {lon}")
    return int(math.floor((lon + 180.0) / 6.0) + 1)


def output_crs_definition(out: OutputCRS) -> CRS:
    hemi = out.hemisphere.upper()
    frame = out.frame.upper()
    if not 1 <= out.zone <= 60:
        raise CRSConfigurationError("La zona UTM debe estar entre 1 y 60.")
    if hemi not in {"N", "S"}:
        raise CRSConfigurationError("El hemisferio debe ser N o S.")
    if frame in {"WGS84", "WGS 84"}:
        epsg = (32600 if hemi == "N" else 32700) + out.zone
        return CRS.from_epsg(epsg)
    if frame in {"ITRF2008", "ITRF08", "GRS80"}:
        if hemi != "N" or out.zone not in MEXICO_ITRF2008_UTM_EPSG:
            # Generic transverse Mercator on GRS80 for non-Mexico zones.
            south = " +south" if hemi == "S" else ""
            return CRS.from_proj4(
                f"+proj=utm +zone={out.zone}{south} +ellps=GRS80 +units=m +no_defs +type=crs"
            )
        return CRS.from_epsg(MEXICO_ITRF2008_UTM_EPSG[out.zone])
    raise CRSConfigurationError(f"Marco de salida no compatible: {out.frame}")


def source_crs_definition(md: SourceMetadata) -> CRS:
    ctype = (md.crs_type or "").upper().replace("_CANDIDATE", "")
    datum = (md.datum or "WGS84").upper()

    if ctype == "EPSG":
        if not md.epsg:
            raise CRSConfigurationError("Se requiere un código EPSG.")
        return CRS.from_epsg(md.epsg)

    if ctype == "GEOGRAPHIC":
        if datum in {"WGS84", "WGS 84"}:
            return CRS.from_epsg(4326)
        if datum in {"ITRF2008", "ITRF08", "GRS80"}:
            return CRS.from_epsg(6365)  # Mexico ITRF2008 geographic 2D
        raise CRSConfigurationError(f"Datum geográfico no compatible en v0.1: {md.datum}")

    if ctype == "UTM":
        if md.zone is None:
            raise CRSConfigurationError("Para UTM se requiere la zona.")
        hemi = (md.hemisphere or "N").upper()
        if datum in {"WGS84", "WGS 84"}:
            epsg = (32600 if hemi == "N" else 32700) + md.zone
            return CRS.from_epsg(epsg)
        if datum in {"ITRF2008", "ITRF08", "GRS80"}:
            if hemi == "N" and md.zone in MEXICO_ITRF2008_UTM_EPSG:
                return CRS.from_epsg(MEXICO_ITRF2008_UTM_EPSG[md.zone])
            south = " +south" if hemi == "S" else ""
            return CRS.from_proj4(
                f"+proj=utm +zone={md.zone}{south} +ellps=GRS80 +units=m +no_defs +type=crs"
            )
        raise CRSConfigurationError(f"Datum UTM no compatible en v0.1: {md.datum}")

    if ctype == "TME":
        if md.central_meridian is None:
            raise CRSConfigurationError("TME requiere el meridiano central ejidal.")
        # INEGI TME: Transverse Mercator, k0=1, lat0=0, false E=500000, false N=0.
        ellps = "WGS84" if datum in {"WGS84", "WGS 84"} else "GRS80"
        return CRS.from_proj4(
            f"+proj=tmerc +lat_0=0 +lon_0={md.central_meridian} +k=1 "
            f"+x_0=500000 +y_0=0 +ellps={ellps} +units=m +no_defs +type=crs"
        )

    raise CRSConfigurationError(
        "Sistema de origen no definido. Seleccione Geográficas, UTM, TME o EPSG antes de convertir."
    )


def geographic_crs_for_source(md: SourceMetadata) -> CRS:
    datum = (md.datum or "WGS84").upper()
    if datum in {"ITRF2008", "ITRF08", "GRS80"}:
        return CRS.from_epsg(6365)
    return CRS.from_epsg(4326)


def suggest_output_utm(points: list[TopoPoint], md: SourceMetadata, frame: str = "WGS84") -> OutputCRS:
    if not points:
        raise CRSConfigurationError("No hay puntos para determinar la zona UTM.")
    src = source_crs_definition(md)
    geo = geographic_crs_for_source(md)
    transformer = Transformer.from_crs(src, geo, always_xy=True)
    xs = [p.x_original for p in points]
    ys = [p.y_original for p in points]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    lon, lat = transformer.transform(cx, cy)
    zone = utm_zone_from_longitude(lon)
    hemi = "N" if lat >= 0 else "S"
    return OutputCRS(zone=zone, hemisphere=hemi, frame=frame)


def transform_points(points: list[TopoPoint], md: SourceMetadata, out: OutputCRS) -> list[TopoPoint]:
    src = source_crs_definition(md)
    dst = output_crs_definition(out)
    transformer = Transformer.from_crs(src, dst, always_xy=True)

    transformed: list[TopoPoint] = []
    for p in points:
        x, y = transformer.transform(p.x_original, p.y_original)
        if not (math.isfinite(x) and math.isfinite(y)):
            raise CRSConfigurationError(f"Transformación inválida en el punto {p.id}.")
        transformed.append(
            TopoPoint(
                id=p.id,
                x_original=p.x_original,
                y_original=p.y_original,
                z_original=p.z_original,
                x=float(x),
                y=float(y),
                z=p.z_original,
                z_source="SURVEY" if p.z_original is not None else p.z_source,
                kind=p.kind,
            )
        )
    return transformed


def describe_crs(crs: CRS) -> str:
    try:
        return crs.to_string()
    except Exception:
        return crs.name
