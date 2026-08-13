from __future__ import annotations

from datetime import datetime

from src.core.platform.api.desktop.approval.models.approval import ApprovalRequestDto
from src.core.platform.domain.approval import ApprovalStatus
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters.control.control_presenter import PlatformControlWorkspacePresenter
from src.ui_qml.platform.presenters.control.control_queue_presenter import PlatformControlQueuePresenter
from src.tests.platform._platform_test_helpers import (
    FakePlatformApprovalApi,
    build_connected_platform_registry,
)


def test_platform_workspace_catalog_exposes_grouped_platform_overviews() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    admin = catalog.adminOverview()
    control = catalog.controlOverview()
    settings = catalog.settingsOverview()

    assert admin["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in admin["metrics"]] == [
        ("Organizations", "2"),
        ("Sites", "1"),
        ("Departments", "1"),
        ("Employees", "1"),
        ("Users", "1"),
        ("Documents", "1"),
    ]
    assert [section["title"] for section in admin["sections"]] == [
        "Runtime Context",
        "Identity And Workforce",
        "Master Data Coverage",
    ]
    assert admin["sections"][0]["rows"][0]["value"] == "TechAsh"
    assert admin["sections"][2]["rows"][0]["supportingText"] == "Berlin Campus, Dubai Yard"

    assert control["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in control["metrics"]] == [
        ("Pending approvals", "1"),
        ("Approved", "1"),
        ("Rejected", "1"),
        ("Audit entries", "2"),
    ]
    assert control["sections"][0]["rows"][0] == {
        "label": "Change Budget",
        "value": "Pending",
        "supportingText": "Project Apollo",
    }
    assert control["sections"][1]["rows"][0]["label"] == "approve"

    assert settings["statusLabel"] == "Connected"
    assert [(metric["label"], metric["value"]) for metric in settings["metrics"]] == [
        ("Licensed modules", "2"),
        ("Enabled modules", "1"),
        ("Planned modules", "1"),
        ("Organizations", "2"),
    ]
    assert [section["title"] for section in settings["sections"]] == [
        "Organization Profiles",
        "Module Catalog",
        "Platform Capabilities",
    ]
    assert settings["sections"][0]["rows"][0]["label"] == "TechAsh"
    assert settings["sections"][1]["rows"][0]["label"] == "Project Management"
    assert settings["sections"][2]["rows"][0]["supportingText"] == "Governed approval workflows"


def test_platform_control_presenters_skip_null_approval_rows() -> None:
    approval_api = FakePlatformApprovalApi(
        (
            ApprovalRequestDto(
                id="approval-1",
                request_type="budget_change",
                entity_type="project",
                entity_id="project-1",
                project_id="project-1",
                status=ApprovalStatus.PENDING,
                module_label="Project Management",
                context_label="Project Apollo",
                display_label="Change Budget",
                requested_by_username="ada",
                requested_at=datetime(2026, 4, 24, 7, 30, 0),
            ),
            None,
        )
    )

    queue = PlatformControlQueuePresenter(approval_api=approval_api).build_approval_queue()
    overview = PlatformControlWorkspacePresenter(approval_api=approval_api).build_overview()

    assert len(queue.items) == 1
    assert queue.items[0].id == "approval-1"
    assert overview.metrics[0].value == "1"


def test_platform_workspace_catalog_exposes_control_and_settings_action_lists() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    approval_queue = catalog.approvalQueue()
    audit_feed = catalog.auditFeed()
    module_entitlements = catalog.moduleEntitlements()
    organization_profiles = catalog.organizationProfiles()

    assert approval_queue["title"] == "Approval Queue"
    assert approval_queue["items"][0]["title"] == "Change Budget"
    assert approval_queue["items"][0]["canPrimaryAction"] is True
    assert approval_queue["items"][0]["state"]["decisionNote"] == ""
    assert approval_queue["items"][1]["canPrimaryAction"] is False

    assert audit_feed["title"] == "Recent Audit Feed"
    assert audit_feed["items"][0]["statusLabel"] == "Project"

    assert module_entitlements["title"] == "Module Entitlements"
    assert module_entitlements["items"][0]["title"] == "Project Management"
    assert module_entitlements["items"][0]["canPrimaryAction"] is True
    assert module_entitlements["items"][0]["canTertiaryAction"] is True
    assert module_entitlements["items"][2]["canPrimaryAction"] is False
    assert module_entitlements["items"][2]["canTertiaryAction"] is False

    assert organization_profiles["title"] == "Organization Profiles"
    assert organization_profiles["items"][0]["title"] == "TechAsh"
    assert organization_profiles["items"][0]["statusLabel"] == "Active"


def test_platform_workspace_controllers_hold_common_state_fields() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    assert catalog.adminWorkspace.isLoading is False
    assert catalog.adminWorkspace.isBusy is False
    assert catalog.adminWorkspace.errorMessage == ""
    assert catalog.adminWorkspace.organizations["items"][0]["title"] == "TechAsh"
    assert catalog.adminWorkspace.users["items"][0]["title"] == "Ada Lovelace"
    assert catalog.adminAccessWorkspace.scopeHint.startswith("Assign scoped access")
    assert catalog.controlWorkspace.feedbackMessage == ""
    assert catalog.settingsWorkspace.emptyState == ""
    assert len(catalog.settingsWorkspace.lifecycleOptions) == 4
    assert catalog.controlWorkspace.approvalQueue["items"][0]["title"] == "Change Budget"
    assert catalog.settingsWorkspace.moduleEntitlements["items"][0]["title"] == "Project Management"


def test_platform_workspace_catalog_exposes_support_workspace() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    support_workspace = catalog.adminSupportWorkspace

    assert support_workspace.incidentId == "inc-support-1"
    assert support_workspace.supportSettings["updateChannel"] == "stable"
    assert support_workspace.supportPaths["logsDirectoryPath"] == "C:/pm/data/logs"
    assert support_workspace.updateStatus["statusLabel"] == "Ready"
    assert support_workspace.activityFeed["title"] == "Support Activity"
    assert support_workspace.bundleState["lastDiagnosticsPath"] == ""
