from __future__ import annotations

from src.api.desktop.platform import (
    ApprovalDecisionCommand,
    ApprovalStatus,
    PlatformAccessDesktopApi,
    PlatformApprovalDesktopApi,
    PlatformAuditDesktopApi,
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantRemoveCommand,
)
from src.api.desktop.runtime import build_desktop_api_registry
from tests.ui_runtime_helpers import login_as


def _access_api(services) -> PlatformAccessDesktopApi:
    return PlatformAccessDesktopApi(access_service=services["access_service"])


def _approval_api(services) -> PlatformApprovalDesktopApi:
    return PlatformApprovalDesktopApi(approval_service=services["approval_service"])


def _audit_api(services) -> PlatformAuditDesktopApi:
    return PlatformAuditDesktopApi(
        audit_service=services["audit_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        cost_service=services["cost_service"],
        baseline_service=services["baseline_service"],
    )


def test_platform_access_desktop_api_manages_project_scope_grants(services):
    api = _access_api(services)
    project = services["project_service"].create_project("Desktop Access Project")
    user = services["auth_service"].register_user("desktop-access", "StrongPass123", role_names=["viewer"])

    role_choices_result = api.list_scope_role_choices("project")
    assign_result = api.assign_scope_grant(
        ScopedAccessGrantAssignCommand(
            scope_type="project",
            scope_id=project.id,
            user_id=user.id,
            scope_role="lead",
        )
    )
    list_result = api.list_scope_grants(scope_type="project", scope_id=project.id)

    assert role_choices_result.ok is True
    assert role_choices_result.data is not None
    assert "lead" in role_choices_result.data
    assert assign_result.ok is True
    assert assign_result.data is not None
    assert assign_result.data.scope_role == "lead"
    assert list_result.ok is True
    assert list_result.data is not None
    assert [row.user_id for row in list_result.data] == [user.id]

    remove_result = api.remove_scope_grant(
        ScopedAccessGrantRemoveCommand(
            scope_type="project",
            scope_id=project.id,
            user_id=user.id,
        )
    )
    refreshed_result = api.list_scope_grants(scope_type="project", scope_id=project.id)

    assert remove_result.ok is True
    assert refreshed_result.ok is True
    assert refreshed_result.data == ()


def test_platform_approval_desktop_api_lists_and_approves_requests(services):
    api = _approval_api(services)
    project = services["project_service"].create_project("Desktop Approval Project")
    services["approval_service"].register_apply_handler("baseline.create", lambda _request: None)
    services["auth_service"].register_user(
        "approval-requester-desktop",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    services["auth_service"].register_user(
        "approval-approver-desktop",
        "StrongPass123",
        role_names=["admin"],
    )

    login_as(services, "approval-requester-desktop", "StrongPass123")
    request = services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id="baseline-1",
        project_id=project.id,
        payload={"name": "Gate Baseline", "project_name": project.name},
    )

    login_as(services, "approval-approver-desktop", "StrongPass123")
    pending_result = api.list_requests(status=ApprovalStatus.PENDING)
    approve_result = api.approve_and_apply(
        ApprovalDecisionCommand(request_id=request.id, note="Approved from desktop API")
    )

    assert pending_result.ok is True
    assert pending_result.data is not None
    pending_row = next(row for row in pending_result.data if row.id == request.id)
    assert pending_row.module_label == "Project Management"
    assert pending_row.context_label == project.name
    assert "Gate Baseline" in pending_row.display_label

    assert approve_result.ok is True
    assert approve_result.data is not None
    assert approve_result.data.status == ApprovalStatus.APPROVED
    assert approve_result.data.decision_note == "Approved from desktop API"


def test_platform_audit_desktop_api_returns_resolved_labels(services):
    api = _audit_api(services)
    project = services["project_service"].create_project("Desktop Audit Project")
    task = services["task_service"].create_task(project.id, "Desktop Audit Task")
    services["audit_service"].record(
        action="task.update",
        entity_type="task",
        entity_id=task.id,
        project_id=project.id,
        details={"task_id": task.id, "project_id": project.id, "status": "IN_PROGRESS"},
        commit=True,
    )

    result = api.list_recent(limit=20)

    assert result.ok is True
    assert result.data is not None
    row = next(item for item in result.data if item.entity_id == task.id and item.action == "task.update")
    assert row.project_label == project.name
    assert row.entity_label == "Task"
    assert "task=Desktop Audit Task" in row.details_label


def test_build_desktop_api_registry_exposes_platform_control_adapters(services):
    registry = build_desktop_api_registry(services)

    assert registry.platform_access.list_scope_role_choices("project").ok is True
    assert registry.platform_approval.list_requests(status=ApprovalStatus.PENDING).ok is True
    assert registry.platform_audit.list_recent(limit=5).ok is True
