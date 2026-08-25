from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError


def require_financial_decision_actor(user_session) -> str:
    """Shared by every PM financial approval participant (`budget.approve`,
    `project_cost.approve`, `financial_change.apply`, `project_billing_preparation.approve`) --
    ported verbatim from the identical closure the four financial approval registrations shared
    in `project_registry.py` """
    principal = user_session.principal if user_session else None
    if principal is None:
        raise BusinessRuleError(
            "An authenticated principal is required to decide a financial approval.",
            code="PROJECT_FINANCIAL_APPROVAL_ACTOR_REQUIRED",
        )
    return principal.user_id


__all__ = ["require_financial_decision_actor"]
