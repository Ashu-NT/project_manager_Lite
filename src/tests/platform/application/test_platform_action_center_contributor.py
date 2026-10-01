from __future__ import annotations

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
)
from src.core.platform.application.global_overview.platform_action_center_contributor import (
    PlatformActionCenterContributor,
)
from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)
from src.core.platform.infrastructure.persistence.read.global_overview.action_center_reader import (
    SqlAlchemyPlatformActionCenterReader,
)


def _contributor(services) -> PlatformActionCenterContributor:
    return PlatformActionCenterContributor(
        reader=SqlAlchemyPlatformActionCenterReader(session=services["session"], target_scope_predicate=ApprovalRequestORM.project_id.is_(None)),
    )


def _context(services) -> ActionCenterContext:
    principal = services["user_session"].principal
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return ActionCenterContext(
        user_id=principal.user_id, tenant_id=tenant_id, organization_id=organization.id
    )


def _become_decider(services) -> None:
    auth = services["auth_service"]
    reviewer = auth.register_user("action-reviewer", "StrongPass123", role_names=["approver"])
    services["user_session"].set_principal(auth.build_principal(reviewer))


def _become_non_decider(services) -> None:
    """Holds approval.request (so ApprovalService.list_requests/count_pending
    would still succeed if called) but not approval.decide."""
    auth = services["auth_service"]
    viewer = auth.register_user("action-viewer", "StrongPass123", role_names=["viewer"])
    services["user_session"].set_principal(auth.build_principal(viewer))


def _create_pending_approval(services, *, entity_id: str = "org-request-1"):
    return services["approval_service"].request_change(
        request_type="organization_request",
        entity_type="organization_request",
        entity_id=entity_id,
        project_id=None,
    )


def test_no_approval_decide_permission_contributes_no_items_or_count(services):
    _create_pending_approval(services)
    _become_non_decider(services)

    contribution = _contributor(services).collect(_context(services), preview_limit=10)

    assert contribution.items == ()
    assert contribution.summary.all_action_items == 0
    assert contribution.summary.reviews_and_approvals == 0


def test_approval_decide_permission_includes_pending_approvals(services):
    _create_pending_approval(services, entity_id="org-request-2")
    _become_decider(services)

    contribution = _contributor(services).collect(_context(services), preview_limit=10)

    assert contribution.summary.all_action_items == 1
    assert contribution.summary.reviews_and_approvals == 1
    assert contribution.summary.assigned_work == 0
    assert contribution.summary.submissions == 0
    assert len(contribution.items) == 1
    item = contribution.items[0]
    assert item.kind == "approval"
    assert item.module == "Platform"
    assert item.action_state == "awaiting_decision"
    assert item.route_id == "platform.workspace"
    assert item.destination_id == "control_approvals"
    assert item.subject_id == "org-request-2"


def test_no_due_at_is_ever_invented_for_approvals(services):
    _create_pending_approval(services, entity_id="org-request-3")
    _become_decider(services)

    contribution = _contributor(services).collect(_context(services), preview_limit=10)

    assert all(item.due_at is None for item in contribution.items)
    assert all(item.sort_at is not None for item in contribution.items)


def test_exact_count_matches_actual_pending_count_beyond_preview_limit(services):
    for index in range(5):
        _create_pending_approval(services, entity_id=f"org-request-count-{index}")
    _become_decider(services)

    contribution = _contributor(services).collect(_context(services), preview_limit=2)

    assert contribution.summary.reviews_and_approvals == 5
    assert len(contribution.items) == 2
