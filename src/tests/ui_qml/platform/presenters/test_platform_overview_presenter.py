from __future__ import annotations

from src.tests.ui_qml.platform.presenters._platform_test_helpers import (
    build_connected_platform_registry,
)
from src.ui_qml.platform.presenters.overview.admin_overview_presenter import (
    PlatformAdminWorkspacePresenter,
)


def test_preview_mode_without_apis_reports_no_data_connected() -> None:
    overview = PlatformAdminWorkspacePresenter().build_overview()

    assert overview.status_label == "Preview"
    assert overview.title == "Platform Overview"
    assert overview.sections == ()
    assert overview.approval_actions is None
    assert overview.recent_activity == ()
    for metric in overview.metrics:
        assert metric.supporting_text == "API not connected"


def test_no_metric_or_row_carries_an_invented_trend() -> None:
    registry = build_connected_platform_registry()
    overview = PlatformAdminWorkspacePresenter(
        runtime_api=registry.platform_runtime,
        site_api=registry.platform_site,
        department_api=registry.platform_department,
        employee_api=registry.platform_employee,
        user_api=registry.platform_user,
        document_api=registry.platform_document,
        party_api=registry.platform_party,
        approval_api=registry.platform_approval,
        audit_api=registry.platform_enterprise_audit,
    ).build_overview()

    # PlatformMetricViewModel has no trend field at all -- there is nothing
    # to invent. This test exists to make that constraint explicit and
    # catch a future accidental reintroduction of a fabricated trend value.
    for metric in overview.metrics:
        assert not hasattr(metric, "trend")
        assert not hasattr(metric, "trend_label")


def test_kpi_metrics_are_real_counts_not_capped_list_lengths() -> None:
    registry = build_connected_platform_registry()
    overview = PlatformAdminWorkspacePresenter(
        runtime_api=registry.platform_runtime,
        site_api=registry.platform_site,
        department_api=registry.platform_department,
        employee_api=registry.platform_employee,
        user_api=registry.platform_user,
        document_api=registry.platform_document,
        party_api=registry.platform_party,
        approval_api=registry.platform_approval,
        audit_api=registry.platform_enterprise_audit,
    ).build_overview()

    metrics_by_label = {metric.label: metric.value for metric in overview.metrics}
    assert metrics_by_label["Organizations"] == "2"
    assert metrics_by_label["Users"] == "1"
    assert metrics_by_label["Pending approvals"] == "1"
    assert metrics_by_label["Documents"] == "1"


def test_module_tenant_status_only_lists_licensed_modules() -> None:
    registry = build_connected_platform_registry()
    overview = PlatformAdminWorkspacePresenter(
        runtime_api=registry.platform_runtime,
    ).build_overview()

    section = next(s for s in overview.sections if s.title == "Module & Tenant Status")
    labels = [row.label for row in section.rows]
    assert "Project Management" in labels
    assert "Inventory & Procurement" in labels
    # HR Management is unlicensed (planned) in the fixture -- must not appear
    # as if it were a real, governed module entitlement.
    assert "HR Management" not in labels


def test_access_security_flags_locked_accounts_only_when_present() -> None:
    registry = build_connected_platform_registry()
    overview = PlatformAdminWorkspacePresenter(
        runtime_api=registry.platform_runtime,
        user_api=registry.platform_user,
    ).build_overview()

    section = next(s for s in overview.sections if s.title == "Access & Security")
    locked_row = next(r for r in section.rows if r.label == "Locked accounts")
    assert locked_row.value == "1"
    assert locked_row.supporting_text == "Requires attention"


def test_approval_actions_never_invent_priority_or_due_date() -> None:
    registry = build_connected_platform_registry()
    overview = PlatformAdminWorkspacePresenter(
        runtime_api=registry.platform_runtime,
        approval_api=registry.platform_approval,
    ).build_overview()

    assert overview.approval_actions is not None
    for item in overview.approval_actions["items"]:
        # The canonical ActivityFeed item shape has no priority/due_at field
        # at all for this source -- nothing to accidentally populate.
        assert "priority" not in item
        assert "due_at" not in item


def test_runtime_error_reports_error_status_without_partial_metrics() -> None:
    class _FailingRuntimeApi:
        def get_runtime_context(self):
            from src.core.platform.api.desktop.models.common import (
                DesktopApiError,
                DesktopApiResult,
            )

            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(code="boom", message="Runtime unavailable.", category="domain"),
            )

    overview = PlatformAdminWorkspacePresenter(runtime_api=_FailingRuntimeApi()).build_overview()

    assert overview.status_label == "Error"
    assert overview.subtitle == "Runtime unavailable."
    assert overview.metrics == ()
