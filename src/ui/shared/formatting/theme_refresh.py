from __future__ import annotations

import re

from PySide6.QtWidgets import QWidget

from src.ui.shared.formatting.theme_tokens import DARK_THEME, LIGHT_THEME

_DECLARATION_RE = re.compile(
    r"(?P<prefix>(?:^|[;{]\s*)(?P<prop>[-A-Za-z]+)\s*:\s*)(?P<value>[^;{}]+)"
)
_TEXT_COLOR_PROPERTIES = {"color", "selection-color"}


def _palette_for_mode(mode: str) -> dict[str, str]:
    normalized = (mode or "light").strip().lower()
    return dict(DARK_THEME if normalized == "dark" else LIGHT_THEME)


def _retarget_stylesheet_colors(stylesheet: str, *, previous_mode: str, next_mode: str) -> str:
    if not stylesheet:
        return stylesheet

    previous_palette = _palette_for_mode(previous_mode)
    next_palette = _palette_for_mode(next_mode)
    previous_surface = previous_palette.get("COLOR_BG_SURFACE")
    next_surface = next_palette.get("COLOR_BG_SURFACE")
    replacements = {
        old_value: next_palette[name]
        for name, old_value in previous_palette.items()
        if name in next_palette and old_value != next_palette[name]
    }

    def _replace_declaration(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        prop = match.group("prop").strip().lower()
        value = match.group("value")
        refreshed = value

        for old_value, new_value in replacements.items():
            if old_value == previous_surface and prop in _TEXT_COLOR_PROPERTIES:
                continue
            refreshed = refreshed.replace(old_value, new_value)

        if (
            previous_surface
            and next_surface
            and prop not in _TEXT_COLOR_PROPERTIES
            and previous_surface in refreshed
        ):
            refreshed = refreshed.replace(previous_surface, next_surface)

        return f"{prefix}{refreshed}"

    return _DECLARATION_RE.sub(_replace_declaration, stylesheet)


def refresh_widget_theme(root: QWidget, *, previous_mode: str, next_mode: str) -> None:
    widgets = [root, *root.findChildren(QWidget)]

    for widget in widgets:
        refresh_theme = getattr(widget, "refresh_theme", None)
        if callable(refresh_theme):
            refresh_theme()

    for widget in widgets:
        stylesheet = widget.styleSheet()
        if stylesheet:
            refreshed = _retarget_stylesheet_colors(
                stylesheet,
                previous_mode=previous_mode,
                next_mode=next_mode,
            )
            if refreshed != stylesheet:
                widget.setStyleSheet(refreshed)
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()


__all__ = ["refresh_widget_theme"]
