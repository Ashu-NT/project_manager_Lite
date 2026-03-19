
"""Domain event hub for project, auth, collaboration, and portfolio notifications."""

from dataclasses import dataclass, field, fields

from .signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)   # project_id
    tasks_changed: Signal[str] = field(default_factory=Signal)     # project_id
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)  # period_id
    costs_changed: Signal[str] = field(default_factory=Signal)     # project_id
    resources_changed: Signal[str] = field(default_factory=Signal)  # resource_id
    baseline_changed: Signal[str] = field(default_factory=Signal)  # project_id
    approvals_changed: Signal[str] = field(default_factory=Signal)  # approval_request_id
    register_changed: Signal[str] = field(default_factory=Signal)  # project_id
    auth_changed: Signal[str] = field(default_factory=Signal)  # user_id
    employees_changed: Signal[str] = field(default_factory=Signal)  # employee_id
    organizations_changed: Signal[str] = field(default_factory=Signal)  # organization_id
    sites_changed: Signal[str] = field(default_factory=Signal)  # site_id
    departments_changed: Signal[str] = field(default_factory=Signal)  # department_id
    access_changed: Signal[str] = field(default_factory=Signal)  # project_id
    collaboration_changed: Signal[str] = field(default_factory=Signal)  # task_id
    portfolio_changed: Signal[str] = field(default_factory=Signal)  # entity_id
    modules_changed: Signal[str] = field(default_factory=Signal)  # module_code

    def reset(self) -> None:
        for signal_field in fields(self):
            getattr(self, signal_field.name).clear()


# SINGLE global instance
domain_events = DomainEvents()
