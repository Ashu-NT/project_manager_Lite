from __future__ import annotations

from src.core.modules.project_management.contracts.approval import (
    PM_APPROVAL_REVIEW_PERMISSIONS,
)


def test_pm_approval_handlers_are_registered_on_the_shared_approval_service(services) -> None:
    approval = services["approval_service"]
    expected = set(PM_APPROVAL_REVIEW_PERMISSIONS)

    assert expected <= approval._apply_handlers.keys()
    assert {
        "budget.approve",
        "forecast.approve",
        "project_cost.approve",
        "financial_change.apply",
        "project_billing_preparation.approve",
    } <= approval._reject_handlers.keys()
    assert all(approval._apply_handlers[key][1] is not None for key in expected)
