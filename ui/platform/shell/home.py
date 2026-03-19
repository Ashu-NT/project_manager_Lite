from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from application.platform import PlatformRuntimeApplicationService
from core.platform.auth import UserSessionContext
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PlatformHomeTab(QWidget):
    def __init__(
        self,
        *,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._platform_runtime_application_service = platform_runtime_application_service
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
            ("Platform Base", shared_services["platform_base"]),
            ("Licensed Modules", shared_services["licensed"]),
            ("Available Modules", shared_services["available"]),
            ("Planned Modules", shared_services["planned"]),
        )
        for idx, (heading, text) in enumerate(cards):
            card_grid.addWidget(self._build_card(heading, text), idx // 2, idx % 2)

        footer = QLabel(
            "Shared tools belong in Platform. Business modules appear by entitlement, and future hosted deployments will reuse the same module rules."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(footer)
        root.addStretch(1)

    def _summary_values(self) -> dict[str, str]:
        if self._platform_runtime_application_service is None:
            return {
                "platform_base": "Users, access, audit, approvals, employees, documents, inbox, notifications, settings.",
                "licensed": "Project Management",
                "available": "None",
                "planned": "Maintenance Management, QHSE, HR Management",
            }
        if hasattr(self._platform_runtime_application_service, "snapshot"):
            context_snapshot = self._platform_runtime_application_service.snapshot()
            snapshot = context_snapshot.module_snapshot
            platform_base = ", ".join(capability.label for capability in snapshot.platform_capabilities) or "None"
            entitlement_by_code = {
                entitlement.code: entitlement
                for entitlement in snapshot.entitlements
            }
            licensed = ", ".join(
                (
                    f"{module.label} ({entitlement_by_code[module.code].lifecycle_label})"
                    if entitlement_by_code.get(module.code) is not None
                    and entitlement_by_code[module.code].lifecycle_alert
                    else module.label
                )
                for module in snapshot.licensed_modules
            ) or "None"
            available = ", ".join(module.label for module in snapshot.available_modules) or "None"
            planned = ", ".join(module.label for module in snapshot.planned_modules) or "None"
        else:
            platform_base = ", ".join(
                capability.label for capability in self._platform_runtime_application_service.list_platform_capabilities()
            ) or "None"
            licensed = ", ".join(
                module.label for module in self._platform_runtime_application_service.list_licensed_modules()
            ) or "None"
            available = ", ".join(
                module.label for module in self._platform_runtime_application_service.list_available_modules()
            ) or "None"
            planned = ", ".join(
                module.label for module in self._platform_runtime_application_service.list_planned_modules()
            ) or "None"
        return {
            "platform_base": platform_base,
            "licensed": licensed,
            "available": available,
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
