
"""Domain event hub for project/task/cost/baseline change notifications."""

from dataclasses import dataclass, field

from .signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)   # project_id
    tasks_changed: Signal[str] = field(default_factory=Signal)     # project_id
    costs_changed: Signal[str] = field(default_factory=Signal)     # project_id
    resources_changed: Signal[str] = field(default_factory=Signal)  # resource_id
    baseline_changed: Signal[str] = field(default_factory=Signal)  # project_id


# SINGLE global instance
domain_events = DomainEvents()
