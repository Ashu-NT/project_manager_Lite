from __future__ import annotations

import os
from pathlib import Path


_DEFAULT_APP_VERSION = "2.1.1"
_VERSION_FILE = Path(__file__).with_name("app_version.txt")


def _read_version_from_file(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return raw or None


def get_app_version() -> str:
    env_override = (os.getenv("PM_APP_VERSION") or "").strip()
    if env_override:
        return env_override

    file_version = _read_version_from_file(_VERSION_FILE)
    if file_version:
        return file_version

    return _DEFAULT_APP_VERSION


__all__ = ["get_app_version"]
