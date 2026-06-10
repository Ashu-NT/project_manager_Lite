from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryType,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterMetricViewModel,
    RegisterOverviewViewModel,
)

from .utils import is_active


def build_risk_overview(*, scope_entries, filtered_entries) -> RegisterOverviewViewModel:
    risk_entries = tuple(
        entry for entry in scope_entries if entry.entry_type == RegisterEntryType.RISK.value
    )
    visible_risks = tuple(
        entry for entry in filtered_entries if entry.entry_type == RegisterEntryType.RISK.value
    )
    today = date.today()
    due_soon_date = today + timedelta(days=7)
    return RegisterOverviewViewModel(
        title="Risk",
        subtitle="Project risk watchlist, mitigation ownership, and review focus.",
        metrics=(
            RegisterMetricViewModel(
                label="Visible risks",
                value=str(len(visible_risks)),
                supporting_text=f"{len(risk_entries)} total within the selected project scope.",
            ),
            RegisterMetricViewModel(
                label="Active",
                value=str(sum(1 for entry in visible_risks if is_active(entry.status))),
                supporting_text="Open or in-flight risks that still need attention.",
            ),
            RegisterMetricViewModel(
                label="Critical",
                value=str(
                    sum(
                        1
                        for entry in visible_risks
                        if entry.severity == RegisterEntrySeverity.CRITICAL.value
                    )
                ),
                supporting_text="Highest-severity delivery risks in the current filter.",
            ),
            RegisterMetricViewModel(
                label="Overdue",
                value=str(sum(1 for entry in visible_risks if entry.is_overdue)),
                supporting_text="Active risks with due dates already missed.",
            ),
            RegisterMetricViewModel(
                label="Due soon",
                value=str(
                    sum(
                        1
                        for entry in visible_risks
                        if entry.due_date is not None
                        and today <= entry.due_date <= due_soon_date
                        and is_active(entry.status)
                    )
                ),
                supporting_text="Active risks due in the next seven days.",
            ),
        ),
    )
