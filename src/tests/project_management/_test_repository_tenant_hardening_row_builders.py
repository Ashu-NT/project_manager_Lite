from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.domain.scheduling.baseline import BaselineStatus
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    BaselineVarianceRecordORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import (
    CalendarEventORM,
    CostItemORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
)


def _build_priority_detail_rows(now, today, project_a, project_b, resource_a, resource_b, task_a1, task_b1, task_a2, task_b2):
    """Build assignments, deps, comments, presence, costs, events, registers, baselines."""
    assignment_a = TaskAssignmentORM(
        id="assignment-a",
        task_id=task_a1.id,
        resource_id=resource_a.id,
        allocation_percent=100.0,
        hours_logged=0.0,
    )
    assignment_b = TaskAssignmentORM(
        id="assignment-b",
        task_id=task_b1.id,
        resource_id=resource_b.id,
        allocation_percent=100.0,
        hours_logged=0.0,
    )
    dependency_a = TaskDependencyORM(
        id="dependency-a",
        predecessor_task_id=task_a1.id,
        successor_task_id=task_a2.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
    )
    dependency_b = TaskDependencyORM(
        id="dependency-b",
        predecessor_task_id=task_b1.id,
        successor_task_id=task_b2.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
    )
    comment_a = TaskCommentORM(
        id="comment-a",
        task_id=task_a1.id,
        author_user_id="user-a",
        author_username="alice",
        body="Comment A",
        mentions_json="[]",
        mentioned_user_ids_json="[]",
        attachments_json="[]",
        read_by_json="[]",
        read_by_user_ids_json="[]",
        created_at=now,
    )
    comment_b = TaskCommentORM(
        id="comment-b",
        task_id=task_b1.id,
        author_user_id="user-b",
        author_username="bob",
        body="Comment B",
        mentions_json="[]",
        mentioned_user_ids_json="[]",
        attachments_json="[]",
        read_by_json="[]",
        read_by_user_ids_json="[]",
        created_at=now,
    )
    presence_a = TaskPresenceORM(
        id="presence-a",
        task_id=task_a1.id,
        user_id="user-a",
        username="alice",
        display_name="Alice",
        activity="reviewing",
        started_at=now,
        last_seen_at=now,
    )
    presence_b = TaskPresenceORM(
        id="presence-b",
        task_id=task_b1.id,
        user_id="user-b",
        username="bob",
        display_name="Bob",
        activity="reviewing",
        started_at=now,
        last_seen_at=now,
    )
    cost_a = CostItemORM(
        id="cost-a",
        project_id=project_a.id,
        task_id=task_a1.id,
        description="Cost A",
        cost_type=CostType.OVERHEAD.value,
        planned_amount=100.0,
        committed_amount=0.0,
        actual_amount=0.0,
        version=1,
    )
    cost_b = CostItemORM(
        id="cost-b",
        project_id=project_b.id,
        task_id=task_b1.id,
        description="Cost B",
        cost_type=CostType.OVERHEAD.value,
        planned_amount=200.0,
        committed_amount=0.0,
        actual_amount=0.0,
        version=1,
    )
    event_a = CalendarEventORM(
        id="event-a",
        title="Event A",
        start_date=today,
        end_date=today,
        project_id=project_a.id,
        task_id=task_a1.id,
        all_day=True,
        description="",
    )
    event_b = CalendarEventORM(
        id="event-b",
        title="Event B",
        start_date=today,
        end_date=today,
        project_id=project_b.id,
        task_id=task_b1.id,
        all_day=True,
        description="",
    )
    register_a = RegisterEntryORM(
        id="register-a",
        project_id=project_a.id,
        entry_type=RegisterEntryType.RISK,
        title="Register A",
        description="",
        severity=RegisterEntrySeverity.MEDIUM,
        status=RegisterEntryStatus.OPEN,
        impact_summary="",
        response_plan="",
        created_at=now,
        updated_at=now,
        version=1,
    )
    register_b = RegisterEntryORM(
        id="register-b",
        project_id=project_b.id,
        entry_type=RegisterEntryType.RISK,
        title="Register B",
        description="",
        severity=RegisterEntrySeverity.MEDIUM,
        status=RegisterEntryStatus.OPEN,
        impact_summary="",
        response_plan="",
        created_at=now,
        updated_at=now,
        version=1,
    )
    baseline_a = ProjectBaselineORM(
        id="baseline-a",
        project_id=project_a.id,
        name="Baseline A",
        created_at=now,
        status=BaselineStatus.DRAFT.value,
        version=1,
    )
    baseline_b = ProjectBaselineORM(
        id="baseline-b",
        project_id=project_b.id,
        name="Baseline B",
        created_at=now,
        status=BaselineStatus.DRAFT.value,
        version=1,
    )
    baseline_task_a = BaselineTaskORM(
        id="baseline-task-a",
        baseline_id=baseline_a.id,
        task_id=task_a1.id,
        task_name="Task A1",
        baseline_start=today,
        baseline_finish=today,
        baseline_duration_days=1,
        baseline_planned_cost=100.0,
    )
    baseline_task_b = BaselineTaskORM(
        id="baseline-task-b",
        baseline_id=baseline_b.id,
        task_id=task_b1.id,
        task_name="Task B1",
        baseline_start=today,
        baseline_finish=today,
        baseline_duration_days=1,
        baseline_planned_cost=200.0,
    )
    variance_a = BaselineVarianceRecordORM(
        id="variance-a",
        project_id=project_a.id,
        new_baseline_id=baseline_a.id,
        superseded_baseline_id=baseline_a.id,
        task_id=task_a1.id,
        task_name="Task A1",
        start_variance_days=0,
        finish_variance_days=0,
        cost_variance=0.0,
        created_at=today,
    )
    variance_b = BaselineVarianceRecordORM(
        id="variance-b",
        project_id=project_b.id,
        new_baseline_id=baseline_b.id,
        superseded_baseline_id=baseline_b.id,
        task_id=task_b1.id,
        task_name="Task B1",
        start_variance_days=0,
        finish_variance_days=0,
        cost_variance=0.0,
        created_at=today,
    )
    return (
        assignment_a, assignment_b, dependency_a, dependency_b,
        comment_a, comment_b, presence_a, presence_b,
        cost_a, cost_b, event_a, event_b,
        register_a, register_b, baseline_a, baseline_b,
        baseline_task_a, baseline_task_b, variance_a, variance_b,
    )
