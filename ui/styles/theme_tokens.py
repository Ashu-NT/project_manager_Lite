from __future__ import annotations

from ui.styles.ui_config import UIConfig as CFG


LIGHT_THEME = {
    "COLOR_BG_APP": "#F4F7FB",
    "COLOR_BG_SURFACE": "#FFFFFF",
    "COLOR_BG_SURFACE_ALT": "#F8FAFC",
    "COLOR_BORDER": "#D7E0EA",
    "COLOR_BORDER_STRONG": "#C7D2DE",
    "COLOR_TEXT_PRIMARY": "#1F2937",
    "COLOR_TEXT_SECONDARY": "#4B5563",
    "COLOR_TEXT_MUTED": "#6B7280",
    "COLOR_ACCENT": "#1D4ED8",
    "COLOR_ACCENT_HOVER": "#1E40AF",
    "COLOR_ACCENT_PRESSED": "#1E3A8A",
    "COLOR_ACCENT_SOFT": "#DBEAFE",
    "COLOR_SUCCESS": "#0F766E",
    "COLOR_WARNING": "#B45309",
    "COLOR_DANGER": "#B42318",
    "COLOR_SCROLLBAR_TRACK": "#E2E8F0",
    "COLOR_SCROLLBAR_HANDLE": "#94A3B8",
    "COLOR_SCROLLBAR_HANDLE_HOVER": "#64748B",
    "COLOR_SCROLLBAR_HANDLE_ACTIVE": "#475569",
}


DARK_THEME = {
    "COLOR_BG_APP": "#0B1220",
    "COLOR_BG_SURFACE": "#111A2C",
    "COLOR_BG_SURFACE_ALT": "#16243A",
    "COLOR_BORDER": "#29405C",
    "COLOR_BORDER_STRONG": "#36527A",
    "COLOR_TEXT_PRIMARY": "#E5EDF8",
    "COLOR_TEXT_SECONDARY": "#B9C7DC",
    "COLOR_TEXT_MUTED": "#91A4C2",
    "COLOR_ACCENT": "#60A5FA",
    "COLOR_ACCENT_HOVER": "#3B82F6",
    "COLOR_ACCENT_PRESSED": "#2563EB",
    "COLOR_ACCENT_SOFT": "#1E3A5F",
    "COLOR_SUCCESS": "#34D399",
    "COLOR_WARNING": "#F59E0B",
    "COLOR_DANGER": "#F87171",
    "COLOR_SCROLLBAR_TRACK": "#1F2E45",
    "COLOR_SCROLLBAR_HANDLE": "#4C678A",
    "COLOR_SCROLLBAR_HANDLE_HOVER": "#6E86A5",
    "COLOR_SCROLLBAR_HANDLE_ACTIVE": "#8FB3D9",
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
