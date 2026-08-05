"""Application runtime orchestration."""

from src.application.runtime.desktop_api_registry import (
    DesktopApiRegistry,
    build_desktop_api_registry,
)

__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]
