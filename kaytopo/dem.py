# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window, from_bounds
from shapely.geometry import Point, Polygon

from .crs import output_crs_definition
from .models import OutputCRS, TopoPoint


class DEMError(ValueError):
    pass


def dem_info(path: str | Path) -> dict:
    path = Path(path)
    with rasterio.open(path) as ds:
        return {
            "path": str(path),
            "crs": ds.crs.to_string() if ds.crs else None,
            "width": ds.width,
            "height": ds.height,
            "resolution": (abs(ds.transform.a), abs(ds.transform.e)),
            "nodata": ds.nodata,
            "bounds": tuple(ds.bounds),
            "dtype": ds.dtypes[0],
        }


def _valid_dem_value(value, nodata: Optional[float]) -> Optional[float]:
    if np.ma.is_masked(value):
        return None
    try:
        fv = float(value)
    except Exception:
        return None
    if not math.isfinite(fv):
        return None
    if nodata is not None and math.isclose(fv, float(nodata), rel_tol=0, abs_tol=1e-12):
        return None
    return fv


def _sample_bilinear(ds, x: float, y: float) -> Optional[float]:
    """Interpolate at x/y from the four surrounding DEM cell centers."""
    col_corner, row_corner = (~ds.transform) * (x, y)
    col_center = float(col_corner) - 0.5
    row_center = float(row_corner) - 0.5
    col0 = math.floor(col_center)
    row0 = math.floor(row_center)

    # Bilinear interpolation needs four valid neighboring cell centers.
    if row0 < 0 or col0 < 0 or row0 + 1 >= ds.height or col0 + 1 >= ds.width:
        return None

    dx = col_center - col0
    dy = row_center - row0
    data = ds.read(1, window=Window(col0, row0, 2, 2), masked=True)
    if data.shape != (2, 2):
        return None

    values = [
        _valid_dem_value(data[0, 0], ds.nodata),
        _valid_dem_value(data[0, 1], ds.nodata),
        _valid_dem_value(data[1, 0], ds.nodata),
        _valid_dem_value(data[1, 1], ds.nodata),
    ]
    if any(v is None for v in values):
        return None

    v00, v01, v10, v11 = (float(v) for v in values)
    top = v00 * (1.0 - dx) + v01 * dx
    bottom = v10 * (1.0 - dx) + v11 * dx
    return top * (1.0 - dy) + bottom * dy


def fill_missing_z_from_dem(
    points: list[TopoPoint],
    out_crs: OutputCRS,
    dem_path: str | Path,
    sampling_method: str = "nearest",
) -> tuple[list[TopoPoint], list[str]]:
    """Fill only missing Z values. Existing survey Z values are never overwritten.

    sampling_method:
      - nearest: original DEM cell value at the point location.
      - bilinear: weighted interpolation from four surrounding cell centers.
    """
    method = sampling_method.strip().lower()
    if method not in {"nearest", "bilinear"}:
        raise DEMError(f"Método de muestreo DEM no compatible: {sampling_method}")

    warnings: list[str] = []
    dst_crs = output_crs_definition(out_crs)
    with rasterio.open(dem_path) as ds:
        if ds.crs is None:
            raise DEMError("El DEM/GeoTIFF no tiene un CRS definido.")
        to_dem = Transformer.from_crs(dst_crs, CRS.from_user_input(ds.crs), always_xy=True)
        missing = [p for p in points if p.z is None]
        coords_dem = [to_dem.transform(p.x, p.y) for p in missing]  # type: ignore[arg-type]

        if method == "nearest":
            raw_samples = list(ds.sample(coords_dem, indexes=1, masked=True))
            sampled = [_valid_dem_value(sample[0], ds.nodata) for sample in raw_samples]
        else:
            sampled = [_sample_bilinear(ds, x, y) for x, y in coords_dem]

        sample_iter = iter(sampled)
        out_points: list[TopoPoint] = []
        for p in points:
            if p.z is not None:
                out_points.append(p)
                continue

            val = next(sample_iter)
            if val is None:
                suffix = (
                    " para interpolación bilineal (requiere cuatro celdas vecinas válidas)"
                    if method == "bilinear"
                    else ""
                )
                warnings.append(f"Punto {p.id}: el DEM no contiene una elevación válida en esa posición{suffix}.")
                out_points.append(p)
            else:
                out_points.append(
                    TopoPoint(
                        id=p.id,
                        x_original=p.x_original,
                        y_original=p.y_original,
                        z_original=p.z_original,
                        x=p.x,
                        y=p.y,
                        z=float(val),
                        z_source="DEM",
                        kind=p.kind,
                    )
                )
        return out_points, warnings


def generate_relief_points(
    boundary_points: list[TopoPoint],
    out_crs: OutputCRS,
    dem_path: str | Path,
    max_points: int = 100_000,
) -> tuple[list[TopoPoint], list[str]]:
    """Generate DEM pixel-center points inside the boundary, capped for CAD usability.

    Uses native DEM cell centers. If there are too many cells, a deterministic stride is applied
    and reported as a warning. This does not invent higher resolution than the raster contains.
    """
    warnings: list[str] = []
    if len(boundary_points) < 3:
        raise DEMError("Se necesitan al menos tres vértices para generar puntos interiores de relieve.")

    dst_crs = output_crs_definition(out_crs)
    with rasterio.open(dem_path) as ds:
        if ds.crs is None:
            raise DEMError("El DEM/GeoTIFF no tiene un CRS definido.")
        dem_crs = CRS.from_user_input(ds.crs)
        to_dem = Transformer.from_crs(dst_crs, dem_crs, always_xy=True)
        from_dem = Transformer.from_crs(dem_crs, dst_crs, always_xy=True)

        ring = [to_dem.transform(p.x, p.y) for p in boundary_points]  # type: ignore[arg-type]
        polygon = Polygon(ring)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty or not polygon.is_valid:
            raise DEMError("La poligonal no es válida para recortar el DEM.")

        left, bottom, right, top = polygon.bounds
        ds_left, ds_bottom, ds_right, ds_top = ds.bounds
        if right < ds_left or left > ds_right or top < ds_bottom or bottom > ds_top:
            raise DEMError("El DEM no cubre la poligonal del terreno.")

        left = max(left, ds_left)
        right = min(right, ds_right)
        bottom = max(bottom, ds_bottom)
        top = min(top, ds_top)

        window = from_bounds(left, bottom, right, top, transform=ds.transform)
        window = window.round_offsets().round_lengths()
        row0 = max(0, int(window.row_off))
        col0 = max(0, int(window.col_off))
        row1 = min(ds.height, row0 + max(1, int(window.height)))
        col1 = min(ds.width, col0 + max(1, int(window.width)))
        estimated = max(1, (row1 - row0) * (col1 - col0))
        stride = max(1, int(math.ceil(math.sqrt(estimated / max_points)))) if estimated > max_points else 1
        if stride > 1:
            warnings.append(
                f"El área contiene ~{estimated:,} celdas DEM; se aplicó muestreo cada {stride} celdas "
                f"para mantener ≤ {max_points:,} puntos de relieve."
            )

        data = ds.read(1, window=((row0, row1), (col0, col1)), masked=True)
        relief: list[TopoPoint] = []
        pid = 1
        for local_row in range(0, data.shape[0], stride):
            global_row = row0 + local_row
            for local_col in range(0, data.shape[1], stride):
                val = data[local_row, local_col]
                if np.ma.is_masked(val):
                    continue
                fv = float(val)
                if not math.isfinite(fv):
                    continue
                if ds.nodata is not None and math.isclose(fv, float(ds.nodata), rel_tol=0, abs_tol=1e-12):
                    continue
                global_col = col0 + local_col
                x_dem, y_dem = rasterio.transform.xy(ds.transform, global_row, global_col, offset="center")
                if not polygon.covers(Point(x_dem, y_dem)):
                    continue
                x_out, y_out = from_dem.transform(x_dem, y_dem)
                relief.append(
                    TopoPoint(
                        id=str(pid),
                        x_original=float(x_out),
                        y_original=float(y_out),
                        z_original=None,
                        x=float(x_out),
                        y=float(y_out),
                        z=fv,
                        z_source="DEM",
                        kind="RELIEF",
                    )
                )
                pid += 1
                if len(relief) >= max_points:
                    warnings.append(f"Se alcanzó el límite de {max_points:,} puntos de relieve.")
                    return relief, warnings
        return relief, warnings
