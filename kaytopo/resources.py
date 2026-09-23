# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Cristian Esparza Ayala

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Resolve bundled resources in development and PyInstaller builds."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / relative_path


def app_icon_path() -> Path:
    return resource_path("assets/branding/KayTopo_icon_1024.png")


def logo_path() -> Path:
    return resource_path("assets/branding/KayTopo_logo.png")
