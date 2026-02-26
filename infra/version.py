from __future__ import annotations

import os


def get_app_version() -> str:
    raw = (os.getenv("PM_APP_VERSION") or "").strip()
    return raw or "2.1.0"


__all__ = ["get_app_version"]
