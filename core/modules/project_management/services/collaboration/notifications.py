from __future__ import annotations

from core.platform.auth.authorization import require_permission
from core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    CollaborationNotificationItem,
)


class CollaborationNotificationMixin:
    def list_notifications(self, *, limit: int = 200) -> list[CollaborationNotificationItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration notifications")
        tasks, project_name_by_id = self._accessible_task_context_for_collaboration()
        inbox_items = self._build_comment_items(
            limit=limit,
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            mentions_only=True,
        )
        return self._build_notifications(limit=limit, inbox_items=inbox_items)

    def _build_notifications(
        self,
        *,
        limit: int,
        inbox_items: list[CollaborationInboxItem],
    ) -> list[CollaborationNotificationItem]:
        rows: list[CollaborationNotificationItem] = [
            CollaborationNotificationItem(
                notification_type="mention",
                entity_type="task_comment",
                entity_id=item.comment_id,
                headline=f"Mention on {item.task_name}",
                body_preview=item.body_preview,
                actor_username=item.author_username,
                created_at=item.created_at,
                project_id=item.project_id,
                project_name=item.project_name,
                attention=item.unread,
            )
            for item in inbox_items
        ]
        for row in self._audit_repo.list_recent(limit=max(limit * 3, 100)):
            notification = self._notification_from_audit(row)
            if notification is not None:
                rows.append(notification)
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[:limit]

    def _notification_from_audit(self, row) -> CollaborationNotificationItem | None:
        if row.entity_type == "approval_request":
            return self._approval_notification_from_audit(row)
        if row.entity_type == "timesheet_period":
            return self._timesheet_notification_from_audit(row)
        return None

    def _approval_notification_from_audit(self, row) -> CollaborationNotificationItem | None:
        if row.action not in {"governance.request", "governance.approve", "governance.reject"}:
            return None
        if row.project_id and not self._principal_can_access_project(row.project_id):
            return None
        details = row.details or {}
        subject = (
            str(details.get("baseline_name") or "").strip()
            or str(details.get("task_name") or "").strip()
            or str(details.get("cost_description") or "").strip()
            or str(details.get("entity_type") or "").strip()
            or "governed change"
        )
        headline_map = {
            "governance.request": f"Approval requested for {subject}",
            "governance.approve": f"Approval granted for {subject}",
            "governance.reject": f"Approval rejected for {subject}",
        }
        return CollaborationNotificationItem(
            notification_type="approval",
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            headline=headline_map[row.action],
            body_preview=self._workflow_preview_from_details(details),
            actor_username=row.actor_username or "system",
            created_at=row.occurred_at,
            project_id=row.project_id,
            project_name=self._project_name(row.project_id),
            attention=row.action == "governance.request",
        )

    def _timesheet_notification_from_audit(self, row) -> CollaborationNotificationItem | None:
        if row.action not in {
            "timesheet_period.submit",
            "timesheet_period.approve",
            "timesheet_period.reject",
            "timesheet_period.lock",
            "timesheet_period.unlock",
        }:
            return None
        project_ids = self._audit_project_ids(row)
        visible_project_ids = [project_id for project_id in project_ids if self._principal_can_access_project(project_id)]
        if project_ids and not visible_project_ids:
            return None
        details = row.details or {}
        resource_name = str(details.get("resource_name") or "Resource").strip()
        period_start = str(details.get("period_start") or "").strip()
        body_parts = [
            part
            for part in [f"Period {period_start}" if period_start else "", self._workflow_preview_from_details(details)]
            if part
        ]
        headline_map = {
            "timesheet_period.submit": f"Timesheet submitted for {resource_name}",
            "timesheet_period.approve": f"Timesheet approved for {resource_name}",
            "timesheet_period.reject": f"Timesheet rejected for {resource_name}",
            "timesheet_period.lock": f"Timesheet locked for {resource_name}",
            "timesheet_period.unlock": f"Timesheet reopened for {resource_name}",
        }
        return CollaborationNotificationItem(
            notification_type="timesheet",
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            headline=headline_map[row.action],
            body_preview="; ".join(body_parts),
            actor_username=row.actor_username or "system",
            created_at=row.occurred_at,
            project_id=row.project_id if row.project_id and self._principal_can_access_project(row.project_id) else None,
            project_name=self._project_names_label(visible_project_ids),
            attention=row.action in {"timesheet_period.submit", "timesheet_period.lock", "timesheet_period.reject"},
        )


__all__ = ["CollaborationNotificationMixin"]
