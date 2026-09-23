# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

_datas, _bins, _hidden = [], [], []
for pkg in ("pyproj", "rasterio", "ezdxf", "shapely"):
    d, b, h = collect_all(pkg)
    _datas += d; _bins += b; _hidden += h

# Official KayTopo branding bundled for the runtime UI.
_datas += [
    ("assets/branding/KayTopo_icon_1024.png", "assets/branding"),
    ("assets/branding/KayTopo_logo.png", "assets/branding"),
]

a = Analysis(
    ["kaytopo_launcher.py"],
    pathex=["."],
    binaries=_bins,
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="KayTopo",
    icon="assets/branding/KayTopo.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
