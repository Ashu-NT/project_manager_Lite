from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from core.exceptions import BusinessRuleError


def show_cost_business_rule(parent, exc: BusinessRuleError) -> None:
    code = (getattr(exc, "code", "") or "").strip().upper()
    if code == "APPROVAL_REQUIRED":
        QMessageBox.information(parent, "Approval required", str(exc))
        return
    QMessageBox.warning(parent, "Error", str(exc))


__all__ = ["show_cost_business_rule"]
