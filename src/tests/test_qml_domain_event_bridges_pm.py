from PySide6.QtWidgets import QApplication

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_pm_tasks_workspace_queues_domain_refresh_while_busy(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller._set_is_busy(True)
    domain_events.tasks_changed.emit("proj-1")
    domain_events.collaboration_changed.emit("task-1")
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]


# P18B retired test_pm_resources_workspace_refreshes_on_resource_events: `resources_changed`
# is deleted -- the Resources workspace now reacts via
# `ResourceViewInvalidationAdapter.resourceListStale`, which needs the real
# ViewInvalidationChannel wiring this lightweight no-registry harness cannot construct (see the
# `test_platform_settings_workspace_refreshes_on_runtime_events` retirement comment below for the
# same constraint). Proved instead, end to end with real services, by
# test_p7b_dead_signal_cleanup.py::test_pm_resources_workspace_still_reacts_to_resources and
# test_p18b_resource_view_invalidation.py.


def test_pm_collaboration_workspace_refreshes_on_collaboration_workflow_events(monkeypatch) -> None:
    """Approval-P3: `approvals_changed` is no longer emitted here -- the approvals panel's
    dependency now flows through `ApprovalViewInvalidationAdapter`, tested separately in
    `test_approval_view_invalidation.py`."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.collaborationWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.collaboration_changed.emit("task-1")
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events(
    monkeypatch, qapp
) -> None:
    """P7A: direct-wired -- `portfolio_changed`/`project_changed` are the actual specific signals
    Portfolio's own debounced `_request_domain_refresh()` override coalesces into one refresh,
    no generic `domain_changed` bridge involved."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.portfolio_changed.emit("portfolio-1")
    domain_events.project_changed.emit("proj-1")
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_timesheets_workspace_refreshes_on_timesheet_workflow_events(monkeypatch) -> None:
    """`resources_changed` removed from this binder's subscriptions (P18B) -- the review-queue's
    resource picker now reacts via `ResourceViewInvalidationAdapter.resourceListStale`, proved
    with real services in test_p18b_resource_view_invalidation.py."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.timesheetsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == ["refresh"]


def test_platform_control_workspace_refreshes_on_control_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.register_changed.emit("proj-1")

    assert refresh_calls == ["refresh"]


# test_platform_settings_workspace_refreshes_on_runtime_events retired (P10D): `modules_changed`
# was retired in P5B-3 -- module-entitlement-triggered refresh flows through
# `ModuleEntitlementViewInvalidationAdapter`, tested in
# `test_module_entitlement_view_invalidation_qt_cutover.py`. `organizations_changed` was
# Settings' last remaining legacy subscription; P10D deleted it entirely -- organization
# profile/enable/disable now flow through the typed `organization_list` ViewInvalidation target
# (`OrganizationViewInvalidationAdapter`), proved end to end in
# `test_organization_view_invalidation_qt_cutover.py
# ::test_update_and_enable_now_also_use_the_typed_view_invalidation_path`, not this lightweight
# no-registry harness (which cannot construct the real ViewInvalidationChannel wiring
# `PlatformWorkspaceCatalog()` needs a `desktop_api_registry` for). Settings therefore has no
# remaining legacy-signal-driven refresh behavior left to test here at all.


def test_platform_admin_access_workspace_reacts_to_auth_changed_narrowly(monkeypatch) -> None:

    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminAccessWorkspace
    controller.ensureLoaded()
    narrow_calls: list[str] = []
    full_refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_refresh_after_security_change", lambda: narrow_calls.append("security"))
    monkeypatch.setattr(controller, "refresh", lambda: full_refresh_calls.append("refresh"))

    domain_events.auth_changed.emit("user-1")

    assert narrow_calls == ["security"]
    assert full_refresh_calls == []
    assert not hasattr(domain_events, "access_changed")


# P16D superseded `test_platform_admin_workspace_refreshes_on_master_data_events`:
# `organizations_changed` removed (P10D), `employees_changed`/`departments_changed`/
# `sites_changed` removed (P12B/P13B/P14B), `parties_changed` removed (P15B),
# `documents_changed` removed (P16D) -- admin console's composite domain-event binder now
# subscribes to `auth_changed` only, and every master-data capability's refresh flows through
# its own typed ViewInvalidation target instead of this composite Signal list. See
# test_p7b_dead_signal_cleanup.py's `test_admin_console_still_reacts_to_its_remaining_signal`
# for the current proof.
