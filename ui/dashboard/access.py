from __future__ import annotations

from dataclasses import dataclass

from core.services.auth import UserSessionContext
from ui.shared.guards import apply_permission_hint, can_execute_governed_action, has_permission


@dataclass(frozen=True)
class DashboardAccess:
    can_create_baseline: bool
    can_delete_baseline: bool
    can_level_resources: bool


def resolve_dashboard_access(user_session: UserSessionContext | None) -> DashboardAccess:
    return DashboardAccess(
        can_create_baseline=can_execute_governed_action(
            user_session=user_session,
            manage_permission="baseline.manage",
            governance_action="baseline.create",
        ),
        can_delete_baseline=has_permission(user_session, "baseline.manage"),
        can_level_resources=has_permission(user_session, "task.manage"),
    )


def apply_dashboard_permission_hints(owner: object) -> None:
    apply_permission_hint(
        owner.btn_create_baseline,
        allowed=owner._can_create_baseline,
        missing_permission="baseline.manage or approval.request",
    )
    apply_permission_hint(
        owner.btn_delete_baseline,
        allowed=owner._can_delete_baseline,
        missing_permission="baseline.manage",
    )
    apply_permission_hint(
        owner.btn_auto_level,
        allowed=owner._can_level_resources,
        missing_permission="task.manage",
    )
    apply_permission_hint(
        owner.btn_manual_shift,
        allowed=owner._can_level_resources,
        missing_permission="task.manage",
    )


def sync_dashboard_baseline_actions(owner: object) -> None:
    project_id, _ = owner._current_project_id_and_name()
    has_project = bool(project_id)
    selected_baseline = owner.baseline_combo.currentData()
    can_delete_selected = has_project and selected_baseline is not None
    owner.btn_create_baseline.setEnabled(owner._can_create_baseline and has_project)
    owner.btn_delete_baseline.setEnabled(owner._can_delete_baseline and can_delete_selected)


def configure_dashboard_access(owner: object, user_session: UserSessionContext | None) -> None:
    access = resolve_dashboard_access(user_session)
    owner._can_create_baseline = access.can_create_baseline
    owner._can_delete_baseline = access.can_delete_baseline
    owner._can_level_resources = access.can_level_resources


def wire_dashboard_access(owner: object) -> None:
    owner.project_combo.currentIndexChanged.connect(
        lambda _index: sync_dashboard_baseline_actions(owner)
    )
    owner.baseline_combo.currentIndexChanged.connect(
        lambda _index: sync_dashboard_baseline_actions(owner)
    )
    apply_dashboard_permission_hints(owner)
    sync_dashboard_baseline_actions(owner)


__all__ = [
    "DashboardAccess",
    "apply_dashboard_permission_hints",
    "configure_dashboard_access",
    "resolve_dashboard_access",
    "sync_dashboard_baseline_actions",
    "wire_dashboard_access",
]
