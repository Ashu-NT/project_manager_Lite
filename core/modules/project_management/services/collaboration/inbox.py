from __future__ import annotations

from core.platform.common.models import CollaborationInboxItem, CollaborationNotificationItem
from core.platform.auth.authorization import require_permission


class CollaborationInboxMixin:
    def list_inbox(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration inbox")
        items: list[CollaborationInboxItem] = []
        for comment in self._list_accessible_comments(limit=limit):
            if not self._comment_mentions_principal(comment):
                continue
            task = self._task_repo.get(comment.task_id)
            if task is None:
                continue
            project = self._project_repo.get(task.project_id)
            if project is None:
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=project.id,
                    project_name=project.name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=list(comment.mentions or []),
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def list_recent_activity(self, *, limit: int = 200) -> list[CollaborationInboxItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration activity")
        items: list[CollaborationInboxItem] = []
        for comment in self._list_accessible_comments(limit=limit):
            task = self._task_repo.get(comment.task_id)
            if task is None:
                continue
            project = self._project_repo.get(task.project_id)
            if project is None:
                continue
            items.append(
                CollaborationInboxItem(
                    comment_id=comment.id,
                    task_id=task.id,
                    task_name=task.name,
                    project_id=project.id,
                    project_name=project.name,
                    author_username=comment.author_username or "unknown",
                    body_preview=self._body_preview(comment.body),
                    mentions=[item.lower() for item in comment.mentions],
                    created_at=comment.created_at,
                    unread=self._comment_is_unread_for_principal(comment),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def list_notifications(self, *, limit: int = 200) -> list[CollaborationNotificationItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view collaboration notifications")
        rows: list[CollaborationNotificationItem] = []

        for item in self.list_inbox(limit=limit):
            rows.append(
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
            )

        audit_rows = self._audit_repo.list_recent(limit=max(limit * 3, 100))
        for row in audit_rows:
            notification = self._notification_from_audit(row)
            if notification is None:
                continue
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
        project_name = self._project_name(row.project_id)
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
            project_name=project_name,
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
        headline_map = {
            "timesheet_period.submit": f"Timesheet submitted for {resource_name}",
            "timesheet_period.approve": f"Timesheet approved for {resource_name}",
            "timesheet_period.reject": f"Timesheet rejected for {resource_name}",
            "timesheet_period.lock": f"Timesheet locked for {resource_name}",
            "timesheet_period.unlock": f"Timesheet reopened for {resource_name}",
        }
        body_parts = [
            part
            for part in [f"Period {period_start}" if period_start else "", self._workflow_preview_from_details(details)]
            if part
        ]
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


__all__ = ["CollaborationInboxMixin"]
