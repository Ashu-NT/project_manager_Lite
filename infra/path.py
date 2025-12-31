# infra/path.py
from __future__ import annotations
import os
import sys
from pathlib import Path

APP_NAME = "ProjectManagerLite"   
COMPANY_NAME = "TECHASH"        


def user_data_dir() -> Path:
    """
    Returns a per-user data directory, e.g.:

    Windows:
        C:\\Users\\<User>\\AppData\\Roaming\\MyCompany\\ProjectManagerLite

    macOS:
        ~/Library/Application Support/MyCompany/ProjectManagerLite

    Linux:
        ~/.local/share/MyCompany/ProjectManagerLite
    """
    try:
        if sys.platform.startswith("win"):
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

        path = base / COMPANY_NAME / APP_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        # Last-resort fallback: use home directory
        fallback = Path.home() / f".{APP_NAME}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def default_db_path() -> Path:
    """
    The full path to the SQLite database file under the user data dir.
    """
    return user_data_dir() / "project_manager.db"