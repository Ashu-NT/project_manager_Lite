from __future__ import annotations

from datetime import date

from src.core.application.global_overview.contracts import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
    AttentionSummaryDto,
    GlobalOverviewContextDto,
    ModuleSummaryDto,
)


def test_action_center_item_dto_supports_optional_priority_and_due_at():
    item = ActionCenterItemDto(
        id="item-1",
        kind="pm_task",
        title="Review project estimates",
        module="Project Management",
        subject_type="task",
        subject_id="task-1",
        subject_display="Facility Upgrade",
        action_state="todo",
        route_id="project_management.tasks",
    )
    assert item.priority is None
    assert item.due_at is None

    dated = ActionCenterItemDto(
        id="item-2",
        kind="pm_task",
        title="Review project estimates",
        module="Project Management",
        subject_type="task",
        subject_id="task-2",
        subject_display="Facility Upgrade",
        action_state="todo",
        route_id="project_management.tasks",
        priority="high",
        due_at=date(2026, 9, 12),
    )
    assert dated.priority == "high"
    assert dated.due_at == date(2026, 9, 12)


def test_action_center_summary_and_attention_summary_are_the_same_type():
    """Locks the architectural guarantee that attention KPI counts and
    Action Center summary counts can never structurally drift apart."""
    assert AttentionSummaryDto is ActionCenterSummaryDto


def test_action_center_contribution_holds_a_bounded_preview_and_an_exact_summary():
    contribution = ActionCenterContribution(
        items=(
            ActionCenterItemDto(
                id="item-1",
                kind="approval",
                title="Review organization request",
                module="Platform",
                subject_type="approval",
                subject_id="approval-1",
                subject_display="Organization request",
                action_state="awaiting_decision",
                route_id="control_approvals",
            ),
        ),
        summary=ActionCenterSummaryDto(
            all_action_items=42,
            reviews_and_approvals=42,
            assigned_work=0,
            submissions=0,
        ),
    )
    assert len(contribution.items) == 1
    assert contribution.summary.all_action_items == 42


def test_a_fake_contributor_satisfies_the_action_center_contributor_protocol():
    class _FakeContributor:
        def collect(
            self, context: ActionCenterContext, preview_limit: int
        ) -> ActionCenterContribution:
            return ActionCenterContribution(
                items=(),
                summary=ActionCenterSummaryDto(0, 0, 0, 0),
            )

    result = _FakeContributor().collect(
        ActionCenterContext(user_id="u1", tenant_id="t1", organization_id="o1"),
        preview_limit=5,
    )
    assert result.summary.all_action_items == 0


def test_a_fake_contributor_satisfies_the_module_summary_contributor_protocol():
    class _FakeModuleSummaryContributor:
        def build_summary(self, context: ActionCenterContext) -> ModuleSummaryDto:
            return ModuleSummaryDto(
                module_code="project_management",
                title="Project Management",
                description=(
                    "Plan and monitor projects, tasks, resources, schedules, "
                    "and delivery."
                ),
                summary_text="12 active projects",
                route_id="project_management",
            )

    summary = _FakeModuleSummaryContributor().build_summary(
        ActionCenterContext(user_id="u1", tenant_id="t1", organization_id="o1")
    )
    assert summary.module_code == "project_management"


def test_global_overview_context_role_label_is_optional():
    context = GlobalOverviewContextDto(
        tenant_name="TECHASH Enterprise", organization_name="Shell"
    )
    assert context.role_label is None

    with_role = GlobalOverviewContextDto(
        tenant_name="TECHASH Enterprise",
        organization_name="Shell",
        role_label="Administrator",
    )
    assert with_role.role_label == "Administrator"
