# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .crs import suggest_output_utm, transform_points
from .dem import fill_missing_z_from_dem, generate_relief_points
from .exporters import export_csv, export_dxf, export_txt, write_info_file
from .io_formats import read_input
from .models import ImportResult, OutputCRS, SourceMetadata, TopoPoint


@dataclass
class KayTopoProject:
    imported: ImportResult | None = None
    transformed: list[TopoPoint] = field(default_factory=list)
    relief: list[TopoPoint] = field(default_factory=list)
    output_crs: OutputCRS | None = None
    dem_path: str | None = None
    dem_sampling_method: str = "nearest"
    warnings: list[str] = field(default_factory=list)

    def load(self, path: str) -> ImportResult:
        self.imported = read_input(path)
        self.transformed = []
        self.relief = []
        self.output_crs = None
        self.dem_path = None
        self.dem_sampling_method = "nearest"
        self.warnings = list(self.imported.warnings)
        return self.imported

    @property
    def metadata(self) -> SourceMetadata:
        if not self.imported:
            raise ValueError("No hay archivo cargado.")
        return self.imported.metadata

    @property
    def source_points(self) -> list[TopoPoint]:
        if not self.imported:
            raise ValueError("No hay archivo cargado.")
        return self.imported.points

    def suggest_utm(self, frame: str = "WGS84") -> OutputCRS:
        return suggest_output_utm(self.source_points, self.metadata, frame=frame)

    def transform(self, out_crs: OutputCRS) -> list[TopoPoint]:
        self.output_crs = out_crs
        self.transformed = transform_points(self.source_points, self.metadata, out_crs)
        self.relief = []
        return self.transformed

    def apply_dem(
        self,
        dem_path: str,
        generate_relief: bool = False,
        max_relief: int = 100_000,
        sampling_method: str = "nearest",
    ) -> None:
        if not self.output_crs or not self.transformed:
            raise ValueError("Primero convierta las coordenadas al CRS de salida.")
        self.dem_path = dem_path
        self.dem_sampling_method = sampling_method
        self.transformed, warnings = fill_missing_z_from_dem(
            self.transformed, self.output_crs, dem_path, sampling_method=sampling_method
        )
        self.warnings.extend(warnings)
        if generate_relief:
            self.relief, warnings = generate_relief_points(self.transformed, self.output_crs, dem_path, max_points=max_relief)
            self.warnings.extend(warnings)

    def export(
        self,
        directory: str,
        basename: str,
        csv_enabled: bool = True,
        txt_enabled: bool = False,
        dxf_enabled: bool = True,
        decimals: int = 3,
        scale: int = 100,
        standard_layers: bool = True,
    ) -> list[Path]:
        if not self.output_crs or not self.transformed:
            raise ValueError("No hay datos transformados para exportar.")
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        base = basename.strip() or "KayTopo_export"
        generated: list[Path] = []

        if csv_enabled:
            generated.append(export_csv(out_dir / f"{base}_vertices.csv", self.transformed, decimals, preserve_ids=True))
            if self.relief:
                generated.append(export_csv(out_dir / f"{base}_relieve.csv", self.relief, decimals, preserve_ids=False))
        if txt_enabled:
            generated.append(export_txt(out_dir / f"{base}_vertices.txt", self.transformed, decimals, preserve_ids=True))
            if self.relief:
                generated.append(export_txt(out_dir / f"{base}_relieve.txt", self.relief, decimals, preserve_ids=False))
        if dxf_enabled:
            generated.append(export_dxf(out_dir / f"{base}.dxf", self.transformed, self.relief, scale, standard_layers))

        generated.append(
            write_info_file(
                out_dir / f"{base}_KayTopo.info.txt",
                self.metadata,
                self.output_crs,
                self.transformed,
                self.relief,
                self.dem_path,
                self.warnings,
                self.dem_sampling_method,
            )
        )
        return generated
