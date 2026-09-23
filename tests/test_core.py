# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from pathlib import Path

import ezdxf
import pytest

from kaytopo.crs import source_crs_definition, transform_points
from kaytopo.exporters import export_csv, export_dxf, export_txt
from kaytopo.io_formats import read_delimited, read_kml
from kaytopo.models import OutputCRS, SourceMetadata, TopoPoint


def test_csv_with_metadata(tmp_path: Path):
    p = tmp_path / "utm.csv"
    p.write_text(
        "# KAYTOPO_FORMAT=1\n"
        "# CRS_TYPE=UTM\n"
        "# DATUM=WGS84\n"
        "# ZONE=14\n"
        "# HEMISPHERE=N\n"
        "# COLUMNS=ID,X,Y,Z\n"
        "1,498235.421,2224185.672,2413.586\n"
        "2,498247.183,2224197.348,2413.912\n",
        encoding="utf-8",
    )
    r = read_delimited(p)
    assert r.metadata.crs_type == "UTM"
    assert r.metadata.zone == 14
    assert r.metadata.hemisphere == "N"
    assert len(r.points) == 2
    assert r.points[0].z_original == pytest.approx(2413.586)


def test_kml_wgs84_and_closed_ring(tmp_path: Path):
    p = tmp_path / "poly.kml"
    p.write_text(
        """<?xml version='1.0' encoding='UTF-8'?>
        <kml xmlns='http://www.opengis.net/kml/2.2'><Document><Placemark><Polygon>
        <outerBoundaryIs><LinearRing><coordinates>
        -98.879,20.112,0 -98.878,20.112,0 -98.878,20.113,0 -98.879,20.112,0
        </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>""",
        encoding="utf-8",
    )
    r = read_kml(p)
    assert r.metadata.crs_type == "GEOGRAPHIC"
    assert r.metadata.datum == "WGS84"
    assert r.boundary_closed is True
    assert len(r.points) == 3


def test_wgs84_to_utm14_known_coordinate():
    md = SourceMetadata(crs_type="GEOGRAPHIC", datum="WGS84")
    pt = TopoPoint("1", -99.1332, 19.4326)
    out = transform_points([pt], md, OutputCRS(14, "N", "WGS84"))[0]
    assert out.x == pytest.approx(486017.3309, abs=0.002)
    assert out.y == pytest.approx(2148700.2198, abs=0.002)


def test_tme_matches_inegi_reference_example():
    """INEGI Guía de Proyecciones Cartográficas, TME example, GRS80.

    Geographic input:
      lat 23°15'34.75620" N
      lon 111°12'32.62310" W
      central meridian 112°30' W
    Published TME result: E=632103.481, N=2573880.995 m.
    """
    from pyproj import CRS, Transformer

    lat = 23 + 15 / 60 + 34.75620 / 3600
    lon = -(111 + 12 / 60 + 32.62310 / 3600)
    md = SourceMetadata(crs_type="TME", datum="ITRF2008", central_meridian=-112.5)
    tme = source_crs_definition(md)
    tr = Transformer.from_crs(CRS.from_epsg(6365), tme, always_xy=True)
    e, n = tr.transform(lon, lat)
    assert e == pytest.approx(632103.481, abs=0.002)
    assert n == pytest.approx(2573880.995, abs=0.002)


def test_clean_2d_exports(tmp_path: Path):
    pts = [TopoPoint("1", 1, 2, x=498000.1234, y=2224000.5678), TopoPoint("2", 3, 4, x=498010, y=2224010)]
    csvp = export_csv(tmp_path / "a.csv", pts, decimals=3)
    txtp = export_txt(tmp_path / "a.txt", pts, decimals=3)
    assert csvp.read_text().splitlines()[0] == "1,498000.123,2224000.568"
    assert txtp.read_text().splitlines()[0] == "1\t498000.123\t2224000.568"
    assert "Copyright" not in csvp.read_text()
    assert "Copyright" not in txtp.read_text()


def test_dxf_layers_point_style_and_hidden_authorship(tmp_path: Path):
    pts = [
        TopoPoint("1", 1, 2, z_original=100, x=498000, y=2224000, z=100, z_source="SURVEY"),
        TopoPoint("2", 3, 4, z_original=101, x=498010, y=2224010, z=101, z_source="SURVEY"),
        TopoPoint("3", 5, 6, z_original=102, x=498020, y=2223990, z=102, z_source="SURVEY"),
    ]
    p = export_dxf(tmp_path / "a.dxf", pts, scale=100)
    raw = p.read_text(encoding="utf-8")
    assert "Cristian Esparza Ayala" in raw
    doc = ezdxf.readfile(p)
    assert doc.header["$PDMODE"] == 34
    assert doc.header["$PDSIZE"] == pytest.approx(0.5)
    assert "KTOPO_LIMITE" in doc.layers
    assert "KTOPO_VERTICES" in doc.layers
    assert "KTOPO_NUMEROS" in doc.layers
    assert "KAYTOPO_METADATA" in doc.rootdict
    meta = [tag.value for tag in doc.rootdict["KAYTOPO_METADATA"].tags]
    assert any("Cristian Esparza Ayala" in str(v) for v in meta)


def test_dem_fills_missing_z_and_generates_relief(tmp_path: Path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from kaytopo.dem import fill_missing_z_from_dem, generate_relief_points

    dem = tmp_path / "dem.tif"
    # 10x10 raster, EPSG:32614, cells of 10 m. Elevation = row/col sequence.
    data = np.arange(100, dtype="float32").reshape(10, 10) + 2000.0
    transform = from_origin(500000, 2200100, 10, 10)
    with rasterio.open(
        dem, "w", driver="GTiff", height=10, width=10, count=1,
        dtype="float32", crs="EPSG:32614", transform=transform, nodata=-9999,
    ) as ds:
        ds.write(data, 1)

    boundary = [
        TopoPoint("1", 0, 0, x=500010, y=2200090),
        TopoPoint("2", 0, 0, x=500070, y=2200090),
        TopoPoint("3", 0, 0, x=500070, y=2200030),
        TopoPoint("4", 0, 0, x=500010, y=2200030),
    ]
    out_crs = OutputCRS(14, "N", "WGS84")
    filled, warnings = fill_missing_z_from_dem(boundary, out_crs, dem)
    assert not warnings
    assert all(p.z is not None for p in filled)
    assert all(p.z_source == "DEM" for p in filled)

    relief, warnings = generate_relief_points(filled, out_crs, dem, max_points=1000)
    assert len(relief) > 0
    assert all(p.kind == "RELIEF" and p.z_source == "DEM" for p in relief)


def test_service_separates_vertices_and_relief_point_files(tmp_path: Path):
    from kaytopo.models import ImportResult
    from kaytopo.service import KayTopoProject

    vertices = [
        TopoPoint("10", 0, 0, x=498000.0, y=2224000.0, z=100.0, z_source="SURVEY"),
        TopoPoint("20", 0, 0, x=498010.0, y=2224010.0, z=101.0, z_source="SURVEY"),
    ]
    relief = [
        TopoPoint("R50", 0, 0, x=498002.0, y=2224002.0, z=100.2, z_source="DEM", kind="RELIEF"),
        TopoPoint("R51", 0, 0, x=498004.0, y=2224004.0, z=100.4, z_source="DEM", kind="RELIEF"),
    ]
    md = SourceMetadata(crs_type="UTM", datum="WGS84", zone=14, hemisphere="N", source_file="test.csv", source_format="CSV")
    project = KayTopoProject(imported=ImportResult(points=vertices, metadata=md), transformed=vertices, relief=relief, output_crs=OutputCRS(14, "N", "WGS84"))

    files = project.export(str(tmp_path), "terreno", csv_enabled=True, txt_enabled=True, dxf_enabled=False)
    names = {p.name for p in files}
    assert "terreno_vertices.csv" in names
    assert "terreno_relieve.csv" in names
    assert "terreno_vertices.txt" in names
    assert "terreno_relieve.txt" in names
    assert "terreno.csv" not in names
    assert (tmp_path / "terreno_vertices.csv").read_text().splitlines()[0].startswith("10,")
    assert (tmp_path / "terreno_relieve.csv").read_text().splitlines()[0].startswith("1,")
    assert (tmp_path / "terreno_relieve.csv").read_text().splitlines()[1].startswith("2,")


def test_dem_bilinear_sampling_and_info(tmp_path: Path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from kaytopo.dem import dem_info, fill_missing_z_from_dem

    dem = tmp_path / "bilinear.tif"
    data = np.array(
        [
            [0.0, 10.0, 20.0],
            [20.0, 30.0, 40.0],
            [40.0, 50.0, 60.0],
        ],
        dtype="float32",
    )
    transform = from_origin(0, 30, 10, 10)
    with rasterio.open(
        dem, "w", driver="GTiff", height=3, width=3, count=1,
        dtype="float32", crs="EPSG:32614", transform=transform, nodata=-9999,
    ) as ds:
        ds.write(data, 1)

    info = dem_info(dem)
    assert info["crs"] == "EPSG:32614"
    assert info["resolution"] == pytest.approx((10.0, 10.0))
    assert info["width"] == 3
    assert info["height"] == 3

    # (10,20) lies exactly halfway between the centers of the four top-left cells:
    # 0, 10, 20 and 30 -> bilinear result = 15.
    pt = TopoPoint("1", 10, 20, x=10, y=20)
    filled, warnings = fill_missing_z_from_dem(
        [pt], OutputCRS(14, "N", "WGS84"), dem, sampling_method="bilinear"
    )
    assert not warnings
    assert filled[0].z == pytest.approx(15.0, abs=1e-9)
    assert filled[0].z_source == "DEM"


def test_dem_bilinear_never_overwrites_existing_z(tmp_path: Path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from kaytopo.dem import fill_missing_z_from_dem

    dem = tmp_path / "preserve_z.tif"
    data = np.full((3, 3), 123.0, dtype="float32")
    with rasterio.open(
        dem, "w", driver="GTiff", height=3, width=3, count=1,
        dtype="float32", crs="EPSG:32614", transform=from_origin(0, 30, 10, 10), nodata=-9999,
    ) as ds:
        ds.write(data, 1)

    pt = TopoPoint("1", 10, 20, z_original=999.5, x=10, y=20, z=999.5, z_source="SURVEY")
    filled, warnings = fill_missing_z_from_dem(
        [pt], OutputCRS(14, "N", "WGS84"), dem, sampling_method="bilinear"
    )
    assert not warnings
    assert filled[0].z == pytest.approx(999.5)
    assert filled[0].z_source == "SURVEY"



def test_official_branding_resources_exist():
    from kaytopo.resources import app_icon_path, logo_path

    icon = app_icon_path()
    logo = logo_path()
    assert icon.exists()
    assert icon.name == "KayTopo_icon_1024.png"
    assert logo.exists()
    assert logo.name == "KayTopo_logo.png"
    assert (icon.parent / "KayTopo.ico").exists()



def test_runtime_smoke_test():
    from kaytopo.app import _frozen_smoke_test

    _frozen_smoke_test()
