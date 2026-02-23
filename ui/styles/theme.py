from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.styles.theme_stylesheet import base_stylesheet, calendar_stylesheet, table_stylesheet
from ui.styles.theme_tokens import DARK_THEME, LIGHT_THEME, apply_theme_tokens


def set_theme_mode(mode: str = "light") -> None:
    apply_theme_tokens(mode)


def apply_app_style(app: QApplication, mode: str = "light") -> None:
    set_theme_mode(mode)
    app.setStyleSheet(base_stylesheet())


__all__ = [
    "LIGHT_THEME",
    "DARK_THEME",
    "set_theme_mode",
    "table_stylesheet",
    "calendar_stylesheet",
    "base_stylesheet",
    "apply_app_style",
]
