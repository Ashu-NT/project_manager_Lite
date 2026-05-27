# src/infra/platform/resource.py
from __future__ import annotations
import sys
from pathlib import Path

def resource_path(relative: str) -> str:
    """
    Get path to resource, works for dev and for PyInstaller (onefile or onefolder).
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # PyInstaller temp dir
    else:
        base = Path(__file__).resolve().parents[3]  # project root
    return str(base / relative)
