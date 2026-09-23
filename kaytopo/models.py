# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class TopoPoint:
    """A point with immutable source coordinates and optional transformed coordinates."""

    id: str
    x_original: float
    y_original: float
    z_original: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    z_source: str = "NONE"  # SURVEY | DEM | NONE
    kind: str = "VERTEX"  # VERTEX | RELIEF | CONTROL

    def final_xyz(self) -> tuple[float, float, Optional[float]]:
        x = self.x if self.x is not None else self.x_original
        y = self.y if self.y is not None else self.y_original
        z = self.z if self.z is not None else self.z_original
        return x, y, z


@dataclass(slots=True)
class SourceMetadata:
    crs_type: Optional[str] = None  # GEOGRAPHIC | UTM | TME | EPSG | LOCAL
    datum: Optional[str] = None
    zone: Optional[int] = None
    hemisphere: Optional[str] = None
    central_meridian: Optional[float] = None
    epsg: Optional[int] = None
    columns: list[str] = field(default_factory=list)
    units: str = "m"
    source_file: Optional[str] = None
    source_format: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OutputCRS:
    zone: int
    hemisphere: str = "N"
    frame: str = "WGS84"  # WGS84 | GRS80

    @property
    def label(self) -> str:
        return f"UTM {self.zone}{self.hemisphere.upper()} / {self.frame}"


@dataclass(slots=True)
class ImportResult:
    points: list[TopoPoint]
    metadata: SourceMetadata
    boundary_closed: bool = False
    warnings: list[str] = field(default_factory=list)
