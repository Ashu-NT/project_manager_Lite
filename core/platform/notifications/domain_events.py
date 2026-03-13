
"""Domain event hub for project, auth, collaboration, and portfolio notifications."""

from dataclasses import dataclass, field, fields

from .signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)   # project_id
    tasks_changed: Signal[str] = field(default_factory=Signal)     # project_id
    costs_changed: Signal[str] = field(default_factory=Signal)     # project_id
    resources_changed: Signal[str] = field(default_factory=Signal)  # resource_id
    baseline_changed: Signal[str] = field(default_factory=Signal)  # project_id
    approvals_changed: Signal[str] = field(default_factory=Signal)  # approval_request_id
    register_changed: Signal[str] = field(default_factory=Signal)  # project_id
    auth_changed: Signal[str] = field(default_factory=Signal)  # user_id
    access_changed: Signal[str] = field(default_factory=Signal)  # project_id
    collaboration_changed: Signal[str] = field(default_factory=Signal)  # task_id
    portfolio_changed: Signal[str] = field(default_factory=Signal)  # entity_id

    def reset(self) -> None:
        for signal_field in fields(self):
            getattr(self, signal_field.name).clear()


# SINGLE global instance
domain_events = DomainEvents()
