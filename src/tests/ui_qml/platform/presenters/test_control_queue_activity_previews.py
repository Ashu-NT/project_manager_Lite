from __future__ import annotations

from datetime import datetime, timezone

from src.core.platform.api.desktop.approval.models.approval import ApprovalRequestDto
from src.core.platform.api.desktop.history.audit.models.audit_entry import AuditEntryDto
from src.core.platform.domain.approval import ApprovalStatus
from src.ui_qml.platform.presenters.control.control_queue_presenter import PlatformControlQueuePresenter
from src.tests.ui_qml.platform.presenters._platform_test_helpers import (
    FakePlatformApprovalApi,
    FakePlatformEnterpriseAuditApi,
)


def _approval(**overrides) -> ApprovalRequestDto:
    fields = dict(
        id="req-1",
        request_type="budget_change",
        entity_type="project_budget",
        entity_id="b1",
        project_id="p1",
        status=ApprovalStatus.PENDING,
        requested_by_username="ada",
        requested_at=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        module_label="Project Management",
        context_label="Project Apollo",
        display_label="Change Budget",
    )
    fields.update(overrides)
    return ApprovalRequestDto(**fields)


def _audit_entry(**overrides) -> AuditEntryDto:
    fields = dict(
        id="a1",
        timestamp=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        operation="role.update",
        entity_type="role",
        entity_id="r1",
        module="platform",
        actor_id="u1",
        actor_username="ada",
        actor_type="user",
        source="api",
        severity="low",
        category="SECURITY",
        result="SUCCESS",
    )
    fields.update(overrides)
    return AuditEntryDto(**fields)


def test_build_approval_activity_preview_produces_the_canonical_shape() -> None:
    presenter = PlatformControlQueuePresenter(approval_api=FakePlatformApprovalApi((_approval(),)))

    items = presenter.build_approval_activity_preview(status=ApprovalStatus.PENDING)

    assert len(items) == 1
    item = items[0]
    assert item.title == "Change Budget"
    assert item.actor_display == "ada"
    assert item.subject_display == "Project Apollo"
    assert item.tone == "warning"
    assert item.status_label == ""  # pending is the ordinary state -- no badge
    assert item.occurred_at == datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc)


def test_build_approval_activity_preview_tone_reflects_real_status_not_text() -> None:
    presenter = PlatformControlQueuePresenter(
        approval_api=FakePlatformApprovalApi((_approval(id="req-2", status=ApprovalStatus.APPROVED),))
    )

    items = presenter.build_approval_activity_preview()

    assert items[0].tone == "success"
    assert items[0].status_label == "Approved"


def test_build_approval_activity_preview_respects_limit() -> None:
    rows = tuple(_approval(id=f"req-{i}") for i in range(10))
    presenter = PlatformControlQueuePresenter(approval_api=FakePlatformApprovalApi(rows))

    items = presenter.build_approval_activity_preview(limit=3)

    assert len(items) == 3


def test_build_approval_activity_preview_empty_without_api() -> None:
    presenter = PlatformControlQueuePresenter(approval_api=None)
    assert presenter.build_approval_activity_preview() == ()


def test_build_audit_activity_preview_produces_the_canonical_shape() -> None:
    presenter = PlatformControlQueuePresenter(audit_api=FakePlatformEnterpriseAuditApi((_audit_entry(),)))

    items = presenter.build_audit_activity_preview()

    assert len(items) == 1
    item = items[0]
    assert item.title == "Role Update"
    assert item.actor_display == "ada"
    assert item.subject_display == "Role"
    assert item.icon_key == "history"  # "role" has no dedicated icon registry mapping
    assert item.tone == "neutral"
    assert item.status_label == ""


def test_build_audit_activity_preview_high_severity_gets_a_badge_and_danger_tone() -> None:
    presenter = PlatformControlQueuePresenter(
        audit_api=FakePlatformEnterpriseAuditApi((_audit_entry(severity="critical"),))
    )

    items = presenter.build_audit_activity_preview()

    assert items[0].tone == "danger"
    assert items[0].status_label == "Critical"


def test_build_audit_activity_preview_empty_without_api() -> None:
    presenter = PlatformControlQueuePresenter(audit_api=None)
    assert presenter.build_audit_activity_preview() == ()
