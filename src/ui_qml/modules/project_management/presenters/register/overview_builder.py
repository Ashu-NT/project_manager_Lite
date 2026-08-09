from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.register import (
    RegisterMetricViewModel,
    RegisterOverviewViewModel,
)
from .utils import WorkspaceMode

def build_overview(
    *,
    entry_page,
    workspace_mode: WorkspaceMode,
) -> RegisterOverviewViewModel:
    if workspace_mode == "risk":
        return RegisterOverviewViewModel(
            title="Risk",
            subtitle="Project risk watchlist, mitigation ownership, and review focus.",
            metrics=(
                RegisterMetricViewModel("Visible risks", str(entry_page.filtered_total), f"{entry_page.scope_risk_total} total within the selected project scope."),
                RegisterMetricViewModel("Active", str(entry_page.active), "Open or in-flight risks that still need attention."),
                RegisterMetricViewModel("Critical", str(entry_page.critical), "Highest-severity delivery risks in the current filter."),
                RegisterMetricViewModel("Overdue", str(entry_page.overdue), "Active risks with due dates already missed."),
                RegisterMetricViewModel("Due soon", str(entry_page.due_soon), "Active risks due in the next seven days."),
            ),
        )
    return RegisterOverviewViewModel(
        title="Register",
        subtitle="Cross-project risks, issues, changes, and governance review queue.",
        metrics=(
            RegisterMetricViewModel("Visible entries", str(entry_page.filtered_total), f"{entry_page.scope_total} total within the selected project scope."),
            RegisterMetricViewModel("Open risks", str(entry_page.open_risks), "Risk records still open or under mitigation."),
            RegisterMetricViewModel("Open issues", str(entry_page.open_issues), "Execution blockers needing ownership."),
            RegisterMetricViewModel("Pending changes", str(entry_page.pending_changes), "Changes awaiting decision or completion."),
            RegisterMetricViewModel("Overdue", str(entry_page.overdue), "Active entries with missed due dates."),
        ),
    )
