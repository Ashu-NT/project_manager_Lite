from __future__ import annotations

from ui.styles.ui_config import UIConfig as CFG


def dashboard_card_style() -> str:
    return f"""
    QWidget {{
        background-color: {CFG.COLOR_BG_SURFACE};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 12px;
    }}
    """


def dashboard_summary_style() -> str:
    return f"""
    QWidget {{
        background-color: {CFG.COLOR_BG_SURFACE};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 12px;
    }}
    """


def dashboard_meta_chip_style() -> str:
    return f"""
    QLabel {{
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 8px;
        color: {CFG.COLOR_TEXT_SECONDARY};
        font-size: 9pt;
        padding: 3px 8px;
    }}
    """


def dashboard_action_button_style(variant: str) -> str:
    if variant == "primary":
        bg = CFG.COLOR_ACCENT
        border = CFG.COLOR_ACCENT_HOVER
        hover = CFG.COLOR_ACCENT_HOVER
        pressed = CFG.COLOR_ACCENT_PRESSED
        text = "#FFFFFF"
    elif variant == "danger":
        bg = CFG.COLOR_DANGER
        border = CFG.COLOR_DANGER
        hover = "#9F2D1B"
        pressed = "#7F1D1D"
        text = "#FFFFFF"
    else:
        bg = CFG.COLOR_BG_SURFACE_ALT
        border = CFG.COLOR_BORDER_STRONG
        hover = CFG.COLOR_ACCENT_SOFT
        pressed = "#C8DAF6"
        text = CFG.COLOR_TEXT_PRIMARY

    return f"""
    QPushButton {{
        background-color: {bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {hover};
    }}
    QPushButton:pressed {{
        background-color: {pressed};
    }}
    QPushButton:disabled {{
        background-color: {CFG.COLOR_BORDER};
        border-color: {CFG.COLOR_BORDER_STRONG};
        color: {CFG.COLOR_TEXT_MUTED};
    }}
    """


__all__ = [
    "dashboard_action_button_style",
    "dashboard_card_style",
    "dashboard_meta_chip_style",
    "dashboard_summary_style",
]
