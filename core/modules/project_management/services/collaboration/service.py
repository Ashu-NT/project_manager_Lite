from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import (
    AuditLogRepository,
    ProjectMembershipRepository,
    ProjectRepository,
    TaskCommentRepository,
    TaskRepository,
    UserRepository,
)
from core.platform.common.models import (
    CollaborationInboxItem,
    CollaborationMentionCandidate,
    CollaborationNotificationItem,
    TaskComment,
)
from core.platform.access.authorization import require_project_permission
from core.platform.auth.authorization import require_permission
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.collaboration.mentions import resolve_mentions
from infra.modules.project_management.collaboration_attachments import store_task_comment_attachments


class CollaborationService(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        session: Session,
        comment_repo: TaskCommentRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        audit_repo: AuditLogRepository,
        project_membership_repo: ProjectMembershipRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._comment_repo = comment_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._project_membership_repo = project_membership_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def list_comments(self, task_id: str) -> list[TaskComment]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view task collaboration")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view task collaboration",
        )
        return self._comment_repo.list_by_task(task_id)

    def list_mention_candidates(self, task_id: str) -> list[CollaborationMentionCandidate]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view mention candidates")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view mention candidates",
        )
        return self._list_mention_candidates_for_project(task.project_id)

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments: Iterable[str] | None = None,
    ) -> TaskComment:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.manage", operation_label="post task collaboration update")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.manage",
            operation_label="post task collaboration update",
        )
        text = (body or "").strip()
        if not text:
            raise ValidationError("Comment text is required.", code="COLLABORATION_BODY_REQUIRED")

        mention_candidates = self._list_mention_candidates_for_project(task.project_id)
        mentions, mentioned_user_ids, unresolved = resolve_mentions(
            text=text,
            candidates=mention_candidates,
        )
        if unresolved:
            preview = ", ".join(f"@{token}" for token in unresolved[:4])
            raise ValidationError(
                f"Unknown mention handle(s): {preview}. Mention project collaborators with access to this task.",
                code="COLLABORATION_MENTION_UNKNOWN",
            )

        principal = self._user_session.principal if self._user_session is not None else None
        comment = TaskComment.create(
            task_id=task_id,
            author_user_id=getattr(principal, "user_id", None),
            author_username=getattr(principal, "username", None) or "unknown",
            body=text,
            mentions=mentions,
            mentioned_user_ids=mentioned_user_ids,
            attachments=[],
        )
        comment.attachments = store_task_comment_attachments(
            task_id=task_id,
            comment_id=comment.id,
            attachments=[str(item) for item in (attachments or []) if str(item).strip()],
        )
        self._comment_repo.add(comment)
        self._session.commit()
        domain_events.collaboration_changed.emit(task_id)
        return comment

    def mark_task_mentions_read(self, task_id: str) -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="mark collaboration updates read")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="mark collaboration updates read",
        )
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        aliases = self._principal_aliases()
        if not principal_user_id and not aliases:
            return

        changed = False
        for comment in self._comment_repo.list_by_task(task_id):
            if not self._comment_mentions_principal(comment):
                continue

            user_reads = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            alias_reads = {item.lower() for item in comment.read_by}
            already_read = False
            if principal_user_id and principal_user_id in user_reads:
                already_read = True
            if not already_read and aliases and not alias_reads.isdisjoint(aliases):
                already_read = True
            if already_read:
                continue

            if principal_user_id:
                comment.read_by_user_ids = sorted(user_reads.union({principal_user_id}))
            primary_alias = self._principal_primary_alias()
            if primary_alias:
                comment.read_by = sorted(alias_reads.union({primary_alias}))
            self._comment_repo.update(comment)
            changed = True

        if changed:
            self._session.commit()
            domain_events.collaboration_changed.emit(task_id)

    def unread_mentions_count(self) -> int:
        return sum(1 for item in self.list_inbox(limit=500) if item.unread)

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

    def _list_accessible_comments(self, *, limit: int) -> list[TaskComment]:
        accessible_task_ids: list[str] = []
        for project in self._project_repo.list_all():
            if self._user_session is None:
                continue
            if not self._user_session.has_project_permission(project.id, "collaboration.read"):
                continue
            for task in self._task_repo.list_by_project(project.id):
                accessible_task_ids.append(task.id)
        return self._comment_repo.list_recent_for_tasks(accessible_task_ids, limit=limit)

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
        body_parts = [part for part in [f"Period {period_start}" if period_start else "", self._workflow_preview_from_details(details)] if part]
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

    def _list_mention_candidates_for_project(self, project_id: str) -> list[CollaborationMentionCandidate]:
        candidates: list[CollaborationMentionCandidate] = []
        seen_user_ids: set[str] = set()
        for membership in self._project_membership_repo.list_by_project(project_id):
            permissions = {str(code).strip() for code in membership.permission_codes}
            if permissions.isdisjoint({"collaboration.read", "collaboration.manage"}):
                continue
            user = self._user_repo.get(membership.user_id)
            if user is None or not user.is_active:
                continue
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            candidates.append(
                CollaborationMentionCandidate(
                    user_id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    scope_role=membership.scope_role,
                )
            )

        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id and principal_user_id not in seen_user_ids:
            if self._user_session is not None and self._user_session.has_project_permission(project_id, "collaboration.read"):
                user = self._user_repo.get(principal_user_id)
                if user is not None and user.is_active:
                    candidates.append(
                        CollaborationMentionCandidate(
                            user_id=user.id,
                            username=user.username,
                            display_name=user.display_name,
                            scope_role="direct",
                        )
                    )

        return sorted(candidates, key=lambda item: ((item.display_name or item.username).lower(), item.username.lower()))

    def _comment_mentions_principal(self, comment: TaskComment) -> bool:
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        mentioned_user_ids = {str(item).strip() for item in comment.mentioned_user_ids if str(item).strip()}
        if principal_user_id and principal_user_id in mentioned_user_ids:
            return True
        mentions = {item.lower() for item in comment.mentions}
        aliases = self._principal_aliases()
        return bool(aliases and not mentions.isdisjoint(aliases))

    def _principal_can_access_project(self, project_id: str | None) -> bool:
        if not project_id or self._user_session is None:
            return False
        return self._user_session.has_project_permission(project_id, "collaboration.read")

    def _project_name(self, project_id: str | None) -> str:
        if not project_id:
            return ""
        project = self._project_repo.get(project_id)
        return project.name if project is not None else ""

    def _project_names_label(self, project_ids: list[str]) -> str:
        names = [self._project_name(project_id) for project_id in project_ids if self._project_name(project_id)]
        if len(names) == 1:
            return names[0]
        if names:
            return ", ".join(names[:2]) + ("..." if len(names) > 2 else "")
        return ""

    @staticmethod
    def _workflow_preview_from_details(details: dict) -> str:
        parts: list[str] = []
        for key in ("project_name", "decision_note", "resource_name", "status"):
            value = str(details.get(key) or "").strip()
            if not value:
                continue
            label = key.replace("_", " ").title()
            parts.append(f"{label}: {value}")
        return "; ".join(parts)

    @staticmethod
    def _audit_project_ids(row) -> list[str]:
        details = row.details or {}
        if row.project_id:
            return [row.project_id]
        raw = details.get("project_ids")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        project_id = str(details.get("project_id") or "").strip()
        return [project_id] if project_id else []

    def _comment_is_unread_for_principal(self, comment: TaskComment) -> bool:
        if not self._comment_mentions_principal(comment):
            return False
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id:
            read_by_user_ids = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            if principal_user_id in read_by_user_ids:
                return False
        aliases = self._principal_aliases()
        read_by = {item.lower() for item in comment.read_by}
        return read_by.isdisjoint(aliases)

    def _require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def _principal_aliases(self) -> set[str]:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            return set()
        aliases: set[str] = set()
        if principal.username:
            aliases.add(principal.username.strip().lower())
        display_name = (principal.display_name or "").strip().lower()
        if display_name:
            aliases.add(display_name.strip(" @"))
            aliases.add(display_name.replace(" ", "").strip(" @"))
            aliases.add(display_name.replace(" ", ".").strip(" @"))
        return {alias for alias in aliases if alias}

    def _principal_primary_alias(self) -> str:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or not getattr(principal, "username", None):
            return ""
        return str(principal.username).strip().lower()

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationService"]
