from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_project_domain_events(controller) -> None:
    """direct-wired to the specific legacy signals this workspace actually reads -- no
    generic `domain_changed` bridge. Budget's own summary reaction is wired separately, in
    `context.py`, through `BudgetViewInvalidationAdapter.budgetProjectSummaryStale` -- see
    `on_budget_project_summary_stale` below -- now that `budgets_changed` is retired (P38B)."""

    def _on_domain_event(_payload: object) -> None:
        controller._request_domain_refresh()

    for signal in (
        domain_events.project_changed,
        domain_events.portfolio_changed,
    ):
        controller._subscribe_domain_signal(signal, _on_domain_event)


def on_budget_project_summary_stale(controller, project_id: str) -> None:
    """P38B: project-scoped precision replacing the old blanket `budgets_changed` reaction, which
    refreshed the whole workspace for every project's budget change regardless of selection."""
    if str(project_id or "") == controller._selected_project_id:
        controller._request_domain_refresh()


__all__ = ["bind_project_domain_events", "on_budget_project_summary_stale"]
