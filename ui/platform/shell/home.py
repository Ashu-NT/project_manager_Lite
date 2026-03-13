from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from core.platform.modules.service import ModuleCatalogService
from core.platform.auth import UserSessionContext
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PlatformHomeTab(QWidget):
    def __init__(
        self,
        *,
        module_catalog_service: ModuleCatalogService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._module_catalog_service = module_catalog_service
        self._user_session = user_session
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)
        root.setSpacing(CFG.SPACING_MD)

        title = QLabel("Platform Home")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        root.addWidget(title)

        principal = self._user_session.principal if self._user_session else None
        display_name = getattr(principal, "display_name", None) or getattr(principal, "username", "team")
        subtitle = QLabel(
            f"Shared enterprise services stay available here for {display_name}. Use the tree to move between platform tools and business modules."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(subtitle)

        card_grid = QGridLayout()
        card_grid.setHorizontalSpacing(CFG.SPACING_SM)
        card_grid.setVerticalSpacing(CFG.SPACING_SM)
        root.addLayout(card_grid)

        shared_services = self._summary_values()
        cards = (
            ("Shared Services", shared_services["shared"]),
            ("Enabled Modules", shared_services["enabled"]),
            ("Planned Modules", shared_services["planned"]),
            ("Navigation Model", "Platform on the left, module workspaces below each enabled domain."),
        )
        for idx, (heading, text) in enumerate(cards):
            card_grid.addWidget(self._build_card(heading, text), idx // 2, idx % 2)

        footer = QLabel(
            "Shared tools belong in Platform. Module-specific work belongs under each module root."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(footer)
        root.addStretch(1)

    def _summary_values(self) -> dict[str, str]:
        if self._module_catalog_service is None:
            return {
                "shared": "Home, audit, access, users, and support.",
                "enabled": "Project Management",
                "planned": "Maintenance Management, QHSE, Payroll",
            }
        enabled = ", ".join(module.label for module in self._module_catalog_service.list_enabled_modules()) or "None"
        planned = ", ".join(module.label for module in self._module_catalog_service.list_planned_modules()) or "None"
        return {
            "shared": "Home, audit, access, users, and support.",
            "enabled": enabled,
            "planned": planned,
        }

    def _build_card(self, heading: str, text: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 14px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_XS)
        title = QLabel(heading)
        title.setStyleSheet(
            f"font-size: 10pt; font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY};"
        )
        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(title)
        layout.addWidget(body)
        return card


__all__ = ["PlatformHomeTab"]
