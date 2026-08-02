# Team Collaboration Audit — Project Management Module

Date: 2026-08-02
Status: investigation complete and implementation in progress. Phase 0 is
complete. The task comment stack now supports permission-derived actions,
full-body rendering, deterministic threaded replies, author-only editing,
moderated soft deletion, and current-user reaction toggles from QML through
the desktop adapter to the service/repository path. Assignment response QML,
atomic comment revisions, moderation attribution, and a platform-owned
presence heartbeat were completed on 2026-08-02.

**Scope decision (2026-08-02): an app notification system is deferred.** The
existing assignment, mention, and approval dispatch calls are persistence
foundations only. They are not a shipped notification feature because no
desktop surface reads the addressed rows, no unread lifecycle is integrated
into the shell, no cross-session refresh exists, and no delivery channel is
implemented. Phase 1 through Phase 3 must therefore remain open as one future
cross-platform notification workstream. Document versioning and approval
delegation also remain open.
Relationship to `docs/pm_modernization/README.md`: that document's Workstream 8
("Portfolio, Collaboration, and Governance") and its Collaboration Workspace
section (§9 of the detailed plan) describe collaboration at an aspirational,
target-state level ("mentions trigger platform notifications," "notifications"
listed under "Existing"). This document is the ground-truth companion: exact,
verified evidence of what the collaboration stack actually does today, file by
file. Where the two disagree, trust this document — it was produced by reading
the live code, not by restating the target model.

## TL;DR

The task collaboration layer now has a complete desktop interaction path for
comments and permission-checked @mentions: full comment bodies, nested reply
context, edit/delete controls, reaction controls, attachment/document context,
presence, and mention-scoped read tracking. Action visibility is computed from
the signed-in principal and project permissions in the application/API layer,
not inferred by QML.

The major remaining collaboration gap is notification delivery. PM currently
writes addressed platform notification rows for selected assignment, mention,
and approval events, but no app notification product consumes or delivers
them. Until the later notification workstream supplies a desktop inbox, unread
lifecycle, cross-session refresh, and channel policy, users still discover
other users' work through manual refresh/navigation.

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

### 1.3 Presence - runtime-heartbeated, not real-time

`touch_task_presence`/`clear_task_presence` do a genuine upsert with a
configurable TTL (`PM_TASK_PRESENCE_TTL_SECONDS`, default 900s), and the
active-presence list is real (queried and rendered, not dead code). But there
is now also a heartbeat while the desktop application is active. The existing
`ShellRuntimeSessionController` owns the timer and emits a generic authenticated
`runtimeHeartbeat`; `PMCollaborationController` subscribes and refreshes only
the selected task's presence snapshot. No task-only timer or QML `Timer` was
introduced. The TTL remains the crash/disconnect fallback. This is periodic
database-backed presence, not cross-process push or real-time delivery.

### 1.4 Assignment safety — overallocation and skills are both enforced server-side

`_check_resource_overallocation()` runs **inside** `assign_resource`/
`assign_project_resource`/`set_assignment_allocation` — a real, unbypassable
domain-level check (warn or block, per `PM_OVERALLOCATION_POLICY`).

**Update (2026-08-01, Phase 0):** `AssignmentSkillValidator` is now also
called from inside `assign_project_resource` itself (not just the advisory
`validate_assignment`/`preview_assignment` desktop API methods) — a BLOCK-mode
violation raises `BusinessRuleError` server-side regardless of whether the
caller checked first. See `TEAM_COLLABORATION_UPGRADE_PLAN.md`'s Phase 0
implementation notes.

### 1.5 Document attachment on collaboration updates — works, no versioning

New files or links-to-existing-documents can be attached to a comment via
`DocumentIntegrationService` (`register_entity_attachments`/
`link_existing_document`), scoped to `entity_type="task_comment"`. This
works. There is no task-level "Documents" tab independent of a comment, and
there is no version history anywhere — `Document.version` is hardcoded to
`1` on every create, and re-uploading a file just creates an unrelated new
row. Every attachment is "latest wins."

---

## 2. The deferred notification system

### 2.1 Addressed persistence exists, but there is no notification product

A ports-and-adapters `NotificationService` (`dispatch()`/
`list_my_notifications()`/`mark_read()`) is composed for tenant invitations,
task assignment, @mentions, and platform approvals. The PM command paths use
best-effort dispatch so notification persistence cannot fail the business
transaction.

This is intentionally classified as foundation, not a completed feature.
`list_my_notifications()` has no desktop consumer, `NotificationChannel` has
no implementation, and the PM Collaboration workspace still displays a
synthetic computed feed rather than persisted addressed notifications.

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

### 2.3 Traced end-to-end: addressed rows without user delivery

**Task assignment** (`TaskAssignmentMixin.assign_project_resource`): creates
the assignment, records activity, emits the local process signal, and writes
`pm.task.assigned.v1` when the resource resolves to an employee-linked user.
No desktop notification consumer surfaces that row.

**@Mention / comment** (`CollaborationCommentCommandMixin.post_comment`):
resolves and stores mentions, emits the local process signal, and writes
`pm.comment.mentioned.v1` for resolved users other than the author. The task
discussion is complete, but notification delivery is not.

**Approval request** (`ApprovalService.request_change`): creates and audits
the request, emits the local process signal, and fans out an addressed row to
current `approval.decide` holders. Approval decisions write back to the
requester. Those records also have no desktop notification consumer.

Other governed PM actions such as baseline and timesheet transitions still
rely on audit rows plus in-process signals unless explicitly wired. Coverage
must be defined as part of the future notification event catalog rather than
expanded ad hoc from individual command handlers.

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

### 3.1 A second, unguarded write path into the same comment table — resolved 2026-08-01

**Update:** confirmed dead-in-production (never resolved by any real desktop
API/controller path — only its own tests read it) and deleted, along with
its composition wiring. `CollaborationService` is now the sole comment-write
path. See `TEAM_COLLABORATION_UPGRADE_PLAN.md`'s Phase 0 implementation
notes.

<details>
<summary>Original finding (for history)</summary>

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

</details>

### 3.2 Dead UI affordances suggesting unbuilt features — partially resolved

**Update (2026-08-01):** the backend concept "Assign" implicitly suggested
(hand off a mention/inbox item to a task assignment) and what "Delegate"
implicitly suggested (assignee accept/decline of a handoff) are now real:
see Phase 4's assignee accept/decline implementation. The two buttons
themselves are still `enabled: false` in QML — implementing "Assign" needs a
new resource-picker popover UI (not just backend, which now exists);
implementing "Delegate" as originally imagined (re-routing a pending
*approval* decision to another approver) needs a new domain concept on
`ApprovalRequest` that doesn't exist and wasn't part of this pass — see the
Phase 4 notes for why that was deliberately scoped out rather than rushed.

<details>
<summary>Original finding (for history)</summary>

The "Assign" quick action (Inbox/Mentions context menu) and "Delegate"
(Approvals context menu) are visible in the QML but hardcoded
`enabled: false` — chrome for a handoff/delegation feature that was never
implemented. Leaving visibly-disabled buttons in an enterprise product reads
as broken, not "coming soon."

</details>

### 3.3 Enterprise feature checklist — present vs. absent

| Feature | Status |
|---|---|
| Permission-gated @mention resolution | **Present**, solid |
| Mention-scoped read/unread tracking | **Present**, narrow scope |
| Presence (who's viewing) | **Present with platform heartbeat** (2026-08-02); database-polled, not real-time push |
| Multiple assignees per task | **Present** |
| Overallocation check at assignment | **Present**, enforced server-side |
| Document attach/link on comments | **Present**, no versioning |
| App notification system | **Deferred**; addressed persistence foundation exists, but there is no desktop consumer, cross-session refresh, or channel |
| Cross-session real-time refresh | **Absent** (Phase 2, needs a team decision) |
| Comment edit | **Present and concurrency-safe** (2026-08-02) - author-only, edited marker, persisted atomic revision |
| Comment delete (soft or hard) | **Present with moderation evidence** (2026-08-02) - soft, permission-gated, actor + optional reason |
| Comment threading / reply-to | **Present end-to-end** (2026-08-02), with deterministic thread ordering and nested QML presentation |
| Comment reactions | **Present end-to-end** (2026-08-02), including current-user toggle state and anchored picker |
| @everyone / @team mentions | **Present** (2026-08-01, Phase 4) |
| Assignee accept/decline of a handoff | **Present end-to-end** (2026-08-02), including server-derived QML actions and decline-reason dialog |
| Skill/certification check enforced server-side | **Present** (2026-08-01, Phase 0) |
| Task-level checklists/subtasks | **Absent** |
| Document version history | **Absent** ("latest wins") — platform-owned, out of this plan's scope |
| Dedicated assignment/status audit trail | **Present** (2026-08-01, Phase 4) — query-level (`action_prefix`/`parent_entity_id` filters), not a new table |

---

## 4. Why this matters for an "enterprise standard" bar

The comment interaction itself now meets a credible enterprise desktop bar:
one guarded write path, server-resolved mentions, tenant/project scoping,
server-computed action capabilities, soft deletion, thread context, and clear
ownership/moderation behavior. The app still must not claim real-time or
notification behavior. That remains a later, separately funded platform
feature described in `TEAM_COLLABORATION_UPGRADE_PLAN.md`.
