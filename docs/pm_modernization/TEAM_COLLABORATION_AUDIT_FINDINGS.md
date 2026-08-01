# Team Collaboration Audit — Project Management Module

Date: 2026-08-01
Status: investigation complete, no code changes made as part of this document
Relationship to `docs/pm_modernization/README.md`: that document's Workstream 8
("Portfolio, Collaboration, and Governance") and its Collaboration Workspace
section (§9 of the detailed plan) describe collaboration at an aspirational,
target-state level ("mentions trigger platform notifications," "notifications"
listed under "Existing"). This document is the ground-truth companion: exact,
verified evidence of what the collaboration stack actually does today, file by
file. Where the two disagree, trust this document — it was produced by reading
the live code, not by restating the target model.

## TL;DR

The collaboration layer has real, working infrastructure for comments,
permission-checked @mentions, presence, and mention-scoped read tracking. But
measured against enterprise expectations (Jira/Asana/MS Project-level), it has
one structural gap that undermines everything else: **nothing in Project
Management ever notifies anyone of anything.** Task assignment, @mentions,
comments, and approval requests are all silent — the only trace they leave is
an audit-log row recording who did it, not who it's for. The addressee finds
out only by manually opening the exact task or workspace tab and looking. This
is true even though a real `NotificationService` with `dispatch()`/
`list_my_notifications()`/`mark_read()` already exists in the platform module
(currently used only for tenant invitations) — Project Management simply never
calls it.

A second structural issue: the in-process `domain_events` signal bus
(`tasks_changed`, `collaboration_changed`, `approvals_changed`, etc.) only
triggers a UI refresh **within the same running process**. Since this is a
multi-user desktop app against a shared database, User A's actions never
reach User B's separate process — there is no cross-session refresh, let
alone push delivery, anywhere in the stack.

---

## 1. What's genuinely solid

### 1.1 Comments and @mentions — real validation, real permission-gating

`TaskComment` (`domain/collaboration/comments/comment.py`) is persisted with
`mentions`/`mentioned_user_ids` resolved server-side at post time via
`resolve_mentions()` (`domain/collaboration/mentions/mention.py`), matched
against a **real, permission-filtered candidate list** built from active
project-role bindings — not a free-text guess. Unresolved `@handle`s are
hard-rejected (`ValidationError`, `COLLABORATION_MENTION_UNKNOWN`). This is
solid, production-grade validation.

### 1.2 Read-tracking — real, but narrow

`mark_task_mentions_read()` genuinely mutates `read_by`/`read_by_user_ids` on
each comment mentioning the current principal, and `_comment_is_unread_for_principal()`
computes real unread state consumed by the Inbox/Mentions tabs and badge
counts. Scope is narrow: it only tracks "have I read comments that mention
me," not general comment-seen state, and it's manual (the user or UI must
call it — nothing marks things read automatically on view).

### 1.3 Presence — half-real

`touch_task_presence`/`clear_task_presence` do a genuine upsert with a
configurable TTL (`PM_TASK_PRESENCE_TTL_SECONDS`, default 900s), and the
active-presence list is real (queried and rendered, not dead code). But there
is **no heartbeat** — grep for `QTimer`/`Timer {`/`interval:` in the entire PM
QML tree returns zero matches related to presence. `last_seen_at` is set once
on a state transition (selecting a task, opening/closing the comment
composer) and then goes stale for up to 15 minutes if the user just leaves
the task open. "Who's viewing this task" is accurate immediately after
navigation and increasingly wrong the longer someone stays.

### 1.4 Assignment safety — overallocation is enforced; skills are advisory only

`_check_resource_overallocation()` runs **inside** `assign_resource`/
`assign_project_resource`/`set_assignment_allocation` — a real, unbypassable
domain-level check (warn or block, per `PM_OVERALLOCATION_POLICY`).

`AssignmentSkillValidator` (skill/certification mismatch detection) exists
and is real, but it is **not called from the assignment commands themselves**
— it's only reachable via separate `validate_assignment`/`preview_assignment`
desktop API methods that the assignment dialog calls *before* the user
clicks "assign." A caller that skips the preview step (any future API
consumer, a script, a different UI) can assign an unqualified/uncertified
resource with no server-side check at all. This is an inconsistency worth
fixing regardless of the notification gap below.

### 1.5 Document attachment on collaboration updates — works, no versioning

New files or links-to-existing-documents can be attached to a comment via
`DocumentIntegrationService` (`register_entity_attachments`/
`link_existing_document`), scoped to `entity_type="task_comment"`. This
works. There is no task-level "Documents" tab independent of a comment, and
there is no version history anywhere — `Document.version` is hardcoded to
`1` on every create, and re-uploading a file just creates an unrelated new
row. Every attachment is "latest wins."

---

## 2. The core gap: nothing notifies anyone

### 2.1 `NotificationService` exists and is real, but PM never calls it

A ports-and-adapters `NotificationService` (`dispatch()`/
`list_my_notifications()`/`mark_read()`) already exists in the platform
module. Grepping the entire repository for `notification_service.dispatch`
finds **exactly one call site**: tenant invitation issued/revoked, in
`src/core/platform/tenancy/application/tenant_membership_service.py`.
`src/infra/composition/project_registry.py` — which builds `TaskService`,
`CollaborationService`, and every PM application service — has **zero**
occurrences of "notification" in it. It is structurally impossible for any
PM service to call `NotificationService` today; the reference was never
threaded through composition.

(Separately: even the one real caller only ever writes an in-app row, since
`NotificationService` is constructed with no `channels` — `contracts.py`'s
`NotificationChannel` Protocol has zero implementations anywhere. So "wire PM
into NotificationService" gets you an in-app inbox item, not an email/push —
see the Upgrade Plan for how this interacts with sequencing.)

### 2.2 Two things that look like notifications but aren't

- **`record_activity`** (`ActivityService.record`) is a pure audit-log
  insert. `ActivityEntry` stores the *actor*, not a recipient. There is no
  `list_for_user`/addressee concept anywhere in the activity domain — it's a
  pull-based audit table, viewed on demand.
- **PM's own `list_notifications()`/`list_inbox()`** (despite the name)
  don't dispatch or persist anything "for user X." They *derive* a view at
  query time by scanning task comments for mentions of the current principal
  and relabeling audit rows into `CollaborationNotificationItem`s. It's a
  synthetic, computed-on-read feed, not a delivered notification.

### 2.3 Traced end-to-end: three collaboration events, zero addressed notifications

**Task assignment** (`TaskAssignmentMixin.assign_project_resource`): creates
the assignment → `record_activity(actor=assigner, action="assignment.add")`
→ `domain_events.tasks_changed.emit(...)`. Nothing addresses the assignee.
They find out only by opening the task/project themselves.

**@Mention / comment** (`CollaborationCommentCommandMixin.post_comment`):
resolves and stores mentions → `domain_events.collaboration_changed.emit(...)`.
No dispatch to `NotificationService`, no per-user push. The mentioned user
finds out only if they separately open the Collaboration → Mentions tab.

**Approval request** (`ApprovalService.request_change`): creates the
`ApprovalRequest` (note: it has no `approver_user_id` concept at all — it's
role/permission-gated, not addressed to a person) → audit entry →
`domain_events.approvals_changed.emit(...)`. The same pattern repeats for
`approve_and_apply`/`reject`. An approver only learns of a pending request by
opening the Approvals panel and looking through everything visible to their
role.

This same pattern (audit row + in-process signal, no addressed notification)
applies to baseline submission/approval, timesheet submit/approve/reject, and
every other governed PM action.

### 2.4 Why the in-process signal bus can't fix this even for same-tenant users

`domain_events.*` (`src/core/shared/events/domain_events.py`) is built on
`Signal` (`src/core/shared/events/signal.py`) — an in-memory Python
`list[Callable]`, explicitly documented as "framework-agnostic signal/slot"
with no queue, socket, or IPC mechanism. This is a desktop PySide6/QML app:
each user runs their **own OS process** against a shared multi-tenant
database. `emit()` only reaches subscribers living in the emitting process.
User B's separate process has no subscriber to User A's emit at all — it is
structurally incapable of cross-session delivery, not just missing a channel
implementation. Confirmed via repo-wide grep: no WebSocket, SignalR,
Server-Sent Events, or long-polling exists anywhere in the codebase, and no
`QTimer`/polling interval drives background auto-refresh in any PM QML
controller. **User B only ever sees User A's change on their own manual
refresh or re-navigation into the relevant workspace/tab.**

---

## 3. Secondary findings

### 3.1 A second, unguarded write path into the same comment table

`src/core/modules/project_management/infrastructure/collaboration_store.py`
(`TaskCollaborationStore`) duplicates comment persistence with its own ad
hoc mention regex, writing to the **same** `task_comments` table as the
properly-guarded `CollaborationService` — but with **no permission checks,
no `TaskComment` domain validation, and no mention-candidate resolution**
(it accepts any `@handle` regardless of whether the user exists or has
project access; `mentioned_user_ids_json` is always written as `[]`). It's
wired into the composition root and used directly by tests. This is a real
inconsistency: a second code path can mutate collaboration data while
bypassing every guarantee the main service enforces. Recommend either
deleting it (if genuinely unused in production paths) or merging it into
`CollaborationService` so there's one write path with one set of guarantees.

### 3.2 Dead UI affordances suggesting unbuilt features

The "Assign" quick action (Inbox/Mentions context menu) and "Delegate"
(Approvals context menu) are visible in the QML but hardcoded
`enabled: false` — chrome for a handoff/delegation feature that was never
implemented. Leaving visibly-disabled buttons in an enterprise product reads
as broken, not "coming soon."

### 3.3 Enterprise feature checklist — present vs. absent

| Feature | Status |
|---|---|
| Permission-gated @mention resolution | **Present**, solid |
| Mention-scoped read/unread tracking | **Present**, narrow scope |
| Presence (who's viewing) | **Present**, no heartbeat, TTL-decays |
| Multiple assignees per task | **Present** |
| Overallocation check at assignment | **Present**, enforced server-side |
| Document attach/link on comments | **Present**, no versioning |
| Addressed notifications (assignment/mention/approval) | **Absent** |
| Cross-session real-time refresh | **Absent** |
| Comment edit | **Absent** |
| Comment delete (soft or hard) | **Absent** |
| Comment threading / reply-to | **Absent** (flat list only) |
| Comment reactions | **Absent** |
| @everyone / @team mentions | **Absent** (individual handles only) |
| Assignee accept/decline of a handoff | **Absent** (one-directional push) |
| Skill/certification check enforced server-side | **Absent** (advisory/UI-only) |
| Task-level checklists/subtasks | **Absent** |
| Document version history | **Absent** ("latest wins") |
| Dedicated assignment/status audit trail | **Absent** (merged into generic activity log) |

---

## 4. Why this matters for an "enterprise standard" bar

An enterprise team collaboration surface is judged on one question above all
others: **when something relevant happens, does the right person find out
without having to go looking for it?** Today, the answer is no, for every
event type in Project Management. This is the single highest-leverage gap —
higher-leverage than comment threading or reactions — because it affects
whether the tool is actually used for real-time teamwork or degrades into
"a database you refresh," which is precisely the failure mode enterprise
buyers screen for. See `TEAM_COLLABORATION_UPGRADE_PLAN.md` for a phased,
evaluable plan to close it.
