from __future__ import annotations

from ui.platform.shared.styles.ui_config import UIConfig as CFG


LIGHT_THEME = {
    "COLOR_BG_APP": "#F4F7FB",
    "COLOR_BG_SURFACE": "#FFFFFF",
    "COLOR_BG_SURFACE_ALT": "#EDF2F8",
    "COLOR_BORDER": "#CCD6E3",
    "COLOR_BORDER_STRONG": "#B8C5D6",
    "COLOR_TEXT_PRIMARY": "#16202B",
    "COLOR_TEXT_SECONDARY": "#3C4A5C",
    "COLOR_TEXT_MUTED": "#5A6678",
    "COLOR_ACCENT": "#0A66A8",
    "COLOR_ACCENT_HOVER": "#09578E",
    "COLOR_ACCENT_PRESSED": "#074A78",
    "COLOR_ACCENT_SOFT": "#D6E8F7",
    "COLOR_SUCCESS": "#1E7F5A",
    "COLOR_WARNING": "#9A5A00",
    "COLOR_DANGER": "#B3282D",
    "COLOR_SCROLLBAR_TRACK": "#DFE6EF",
    "COLOR_SCROLLBAR_HANDLE": "#8EA2BA",
    "COLOR_SCROLLBAR_HANDLE_HOVER": "#6E859F",
    "COLOR_SCROLLBAR_HANDLE_ACTIVE": "#51677F",
}


DARK_THEME = {
    "COLOR_BG_APP": "#0B1220",
    "COLOR_BG_SURFACE": "#18212D",
    "COLOR_BG_SURFACE_ALT": "#212C3A",
    "COLOR_BORDER": "#314154",
    "COLOR_BORDER_STRONG": "#3E5168",
    "COLOR_TEXT_PRIMARY": "#E9F0F8",
    "COLOR_TEXT_SECONDARY": "#B8C4D4",
    "COLOR_TEXT_MUTED": "#95A5B8",
    "COLOR_ACCENT": "#7CC4FF",
    "COLOR_ACCENT_HOVER": "#5AAFF4",
    "COLOR_ACCENT_PRESSED": "#3498E9",
    "COLOR_ACCENT_SOFT": "#1E3E57",
    "COLOR_SUCCESS": "#54D39B",
    "COLOR_WARNING": "#E5A94B",
    "COLOR_DANGER": "#F08788",
    "COLOR_SCROLLBAR_TRACK": "#233141",
    "COLOR_SCROLLBAR_HANDLE": "#4C6178",
    "COLOR_SCROLLBAR_HANDLE_HOVER": "#6F879F",
    "COLOR_SCROLLBAR_HANDLE_ACTIVE": "#93ABBE",
}


def apply_theme_tokens(mode: str = "light") -> None:
    normalized = (mode or "light").strip().lower()
    palette = DARK_THEME if normalized == "dark" else LIGHT_THEME
    for attr, value in palette.items():
        setattr(CFG, attr, value)

    CFG.INFO_TEXT_STYLE = f"color: {CFG.COLOR_TEXT_SECONDARY}; font-size: 10pt;"
    CFG.NOTE_STYLE_SHEET = (
        f"color: {CFG.COLOR_TEXT_SECONDARY}; font-size: 9pt; font-style: italic;"
    )
    CFG.SECTION_BOLD_MARGIN_STYLE = (
        f"font-weight: 700; color: {CFG.COLOR_TEXT_SECONDARY}; margin-top: 8px;"
    )
    CFG.TITLE_LARGE_STYLE = (
        f"font-size: {CFG.FONT_SIZE_TITLE}px; font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY};"
    )

    CFG.DASHBOARD_SUMMARY_STYLE = f"font-size: 10pt; color: {CFG.COLOR_TEXT_SECONDARY};"
    CFG.DASHBOARD_PROJECT_LABEL_STYLE = f"font-size: 10pt; color: {CFG.COLOR_TEXT_SECONDARY};"
    CFG.DASHBOARD_PROJECT_TITLE_STYLE = (
        f"font-size: 11pt; font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY};"
    )
    CFG.DASHBOARD_PROJECT_META_STYLE = (
        f"color: {CFG.COLOR_TEXT_SECONDARY}; font-size: 9pt; padding: 0 6px;"
    )
    CFG.PROJECT_SUMMARY_BOX_STYLE = (
        f"background-color: {CFG.COLOR_BG_SURFACE}; "
        f"border: 1px solid {CFG.COLOR_BORDER}; border-radius: 10px; padding: 8px;"
    )
    CFG.DASHBOARD_KPI_TITLE_STYLE = f"font-size: 9pt; color: {CFG.COLOR_TEXT_SECONDARY};"
    CFG.DASHBOARD_KPI_SUB_STYLE = f"font-size: 9pt; color: {CFG.COLOR_TEXT_SECONDARY};"
    CFG.DASHBOARD_HIGHLIGHT_COLOR = CFG.COLOR_ACCENT
    CFG.CHART_TITLE_STYLE = (
        f"font-size: 11pt; font-weight: 700; color: {CFG.COLOR_TEXT_SECONDARY};"
    )
    CFG.EVM_METRIC_COLORS = {
        "CPI": CFG.COLOR_SUCCESS,
        "SPI": CFG.COLOR_SUCCESS,
        "PV": CFG.COLOR_ACCENT,
        "EV": CFG.COLOR_ACCENT,
        "AC": CFG.COLOR_DANGER,
        "EAC": CFG.COLOR_DANGER,
        "VAC": CFG.COLOR_WARNING,
        "TCPI": CFG.COLOR_TEXT_SECONDARY,
        "TCPI_EAC": CFG.COLOR_TEXT_SECONDARY,
    }
    CFG.EVM_DEFAULT_COLOR = CFG.DASHBOARD_HIGHLIGHT_COLOR


__all__ = ["LIGHT_THEME", "DARK_THEME", "apply_theme_tokens"]
