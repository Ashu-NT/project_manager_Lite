# Team Collaboration Upgrade Plan — For Team Evaluation

Date: 2026-08-02
Status: **Phase 0 complete. Phase 4 comment modernization is complete
end-to-end through the task workspace QML.** The assignment-response UI,
document version history, and approval delegation remain open.

**Notification scope decision (2026-08-02): Phases 1 through 3 are deferred
as one future app notification workstream.** The addressed-row dispatch code
implemented on 2026-08-01 is retained as tested platform foundation, but it
is not a completed or shipped notification system. There is no desktop
consumer, shell unread lifecycle, cross-session refresh, or channel
implementation. This plan must not describe persisted rows alone as an
in-app notification feature.
Grounded in: `docs/pm_modernization/TEAM_COLLABORATION_AUDIT_FINDINGS.md`
(read that first — every phase below cites a specific finding).
Consistent with: `docs/pm_modernization/README.md`'s existing ownership
rules ("Notifications: PM owns mention/comment/event intent, while the
platform notification service owns delivery and channel policy") and event
architecture standards (durable event envelope, `pm.<entity>.<verb>.v1`
naming). This plan implements those already-agreed rules rather than
introducing new ones — the README stated the target; this plan is the "how"
that was missing.

## Deployment context this plan assumes

`src/infra/persistence/db/engine.py` supports `sqlite`, `postgresql`,
`mysql`, `oracle`, `mssql` via `PM_DB_URL`, defaulting to local SQLite in
dev. This is a **desktop app, multiple users each running their own
process, against one shared database** — there is no existing application
server/backend process today. That constraint shapes which real-time
delivery options are actually available (see Phase 2) and is the single
biggest open decision in this plan.

---

## Guiding principle

Every phase below is scoped so it can ship and be evaluated independently.
None of them require the others to land first, except where explicitly
noted as a dependency. The team should feel free to approve a subset, reorder,
or reject any phase without unwinding the rest.

---

## Phase 0 — Fix the two integrity gaps (small, low-risk, do first regardless of what else is approved)

These aren't collaboration *features* — they're inconsistencies found during
the audit that undermine trust in the guarantees the system claims to have.

### 0.1 Enforce skill/certification validation server-side, not just in the UI

**Finding:** §1.4 of the audit — `AssignmentSkillValidator` exists and works,
but `assign_resource`/`assign_project_resource` never call it. Only the UI
dialog calls `preview_assignment` first. Any other caller (API, script,
future integration) can assign an uncertified/unskilled resource with zero
check.

**Fix:** call `AssignmentSkillValidator` from inside the assignment command
itself, mirroring exactly how `_check_resource_overallocation()` is already
wired — same file, same pattern, same WARN/BLOCK/OVERRIDE modes that already
exist. This is a small, mechanical change (no new domain concepts).

**Effort:** small. **Risk:** low — the validator and its modes already exist
and are tested; this only changes *where* it's called from.

### 0.2 Resolve the duplicate collaboration write path

**Finding:** §3.1 — `TaskCollaborationStore` writes to the same
`task_comments` table as `CollaborationService`, with no permission check
and no mention-candidate validation.

**Decision needed from the team:** is `TaskCollaborationStore` still used by
anything in production, or is it a leftover from an earlier iteration kept
alive only by its own tests? If unused: delete it. If still needed for some
composition-root reason: merge its write path through `CollaborationService`
so there's exactly one comment-write code path with one set of guarantees.

**Effort:** small–medium (depends on the answer above). **Risk:** low once
the usage question is answered — this is aligned with the README's guardrail
"PM must not create duplicate ... systems."

### Phase 0 implementation notes (2026-08-01)

Both items shipped.

**0.1 — skill/certification enforcement:** `TaskService`/`TaskAssignmentMixin`
gained an `assignment_skill_validator` constructor param (wired at
`project_registry.py`, reusing the same `AssignmentSkillValidator` instance
already built for the advisory `validate_assignment`/`preview_assignment`
desktop API methods — no new object, just a second reference to it).
`assign_project_resource` now calls `_check_resource_skill_requirements()`
immediately after the existing overallocation check, mirroring its exact
shape: `result.is_blocked` → raises `BusinessRuleError` (code
`ASSIGNMENT_SKILL_BLOCKED`) using the first blocking violation's message;
`result.requires_approval` or non-blocking `result.warnings` → stashed in a
new `_last_skill_violation_warning` / `consume_last_skill_violation_warning()`
pair, exactly parallel to the existing overallocation-warning mechanism. No
behavior change for tasks with zero skill requirements (the validator
short-circuits to an empty, non-blocking result). Tests:
`src/tests/project_management/test_assignment_skill_enforcement.py`.

**0.2 — duplicate write path:** confirmed via full-repo trace that
`TaskCollaborationStore` was dead-in-production — constructed and placed in
the composition services dict, but never resolved by
`ProjectManagementDesktopRuntimeServices`, any desktop API factory, or any
controller; only its own unit tests and two regression tests read it
directly. Deleted the class
(`src/core/modules/project_management/infrastructure/collaboration_store.py`)
and all composition wiring (`project_registry.py`, `app_container.py`).
`CollaborationService` (backed by the tenant-scoped `TaskCommentRepository`)
is now the sole comment-persistence path, as the audit recommended. The
handful of tests that exercised the dead store directly were removed; the
regression tests they lived in (import/timesheet cascade-delete behavior)
were otherwise unaffected and remain green.

---

## Phase 1 — App notification system (deferred; persistence foundation only)

**Current decision:** do not continue notification implementation in the
comments/mentions modernization. Treat the implementation notes below as
foundation history and resume this phase only with an approved product scope
covering the desktop consumer, read lifecycle, refresh/delivery model, and
channel policy together.

**Finding:** §2 of the audit — addressed persistence exists for assignment,
mentions, and approval requests, but the `NotificationService` has no desktop
consumer or delivery channel and therefore does not yet notify an app user.

**Target outcome for the resumed phase:** an addressed, persisted notification
row (`recipient_user_id` set) for:
- task assignment → the assignee
- @mention in a comment → the mentioned user(s)
- approval requested → the specific approver(s) whose action is pending
- approval decided (approved/rejected) → the requester

**How it plugs into the existing architecture (per the README's own event
standards):**
1. Thread a `notification_service` reference through
   `src/infra/composition/project_registry.py` into `TaskService`,
   `CollaborationService`, and wherever `ApprovalService` is constructed for
   PM — the same way `NotificationService` is already threaded into
   `TenantMembershipService` today. This is composition-root wiring only, no
   new abstraction.
2. Each PM command that currently only does
   `record_activity(...) + domain_events.X.emit(...)` gains one additional,
   best-effort call: `notification_service.dispatch(recipient_user_id=..., category="pm.task.assigned", ...)`
   (or reuses `_safe_dispatch_notification`-style try/except wrapping, matching
   how `TenantMembershipService` already guards notification calls so a
   notification failure never fails the parent operation).
3. Event/category naming follows the README's existing convention
   (`pm.task.assigned.v1`, `pm.comment.mentioned.v1`, `pm.approval.requested.v1`,
   `pm.approval.decided.v1`) so this is consistent with the durable-event
   naming rules already documented, not a new pattern.
4. The Collaboration workspace's existing "Notifications"/"Inbox" tabs (today
   backed by the synthetic `list_notifications()` computed-on-read scan) get
   a second, real feed to merge in: `notification_service.list_my_notifications()`.
   The synthetic scan can stay as a fallback/legacy source during migration,
   or be retired once the real feed covers the same ground — team's call.

**What this phase does NOT do:** send email, OS toast, or any external
channel. `NotificationService` has zero `NotificationChannel` implementations
today (`contracts.py`'s Protocol, unimplemented). This phase only gets you a
reliable **in-app** "you have a notification" — which already closes most of
the gap, since it's addressed and persisted rather than a synthetic scan, and
it can be surfaced as an unread badge on app launch/workspace switch.

**Effort:** medium. Touches `project_registry.py` (composition), `TaskService`,
`CollaborationService`, PM's `ApprovalService` usage, and the four-or-so
command methods where events currently fire. **Risk:** low-medium — the
existing `_safe_dispatch_notification` pattern from tenant invitations is the
template to copy, and it's designed to never break the calling operation.

**Open question for the team:** should the "who is the approver" problem
(§2.3 — `ApprovalRequest` has no `approver_user_id`, it's role-gated) be
resolved by notifying *every user holding the deciding role/permission*, or
does this need a real assignable-approver concept first? Recommend starting
with "notify everyone who currently holds the deciding permission for that
scope" — simplest, no schema change, and correct enough for a first version.

### Phase 1 foundation notes (2026-08-01; reclassified 2026-08-02)

The persistence foundation was implemented with two decisions resolved during
implementation (both confirmed by the team before coding):

1. **Resource → user recipient gap (discovered during implementation, not
   anticipated in the original plan):** neither `Resource` nor `Employee` had
   any link to a real `UserAccount` — task-assignment notifications had no
   resolvable recipient. Rather than skip this notification, the team asked
   to close the gap: added a nullable `Employee.user_id` field (domain, ORM
   column + index, migration `4f20c1d95e8f`, mapper, repository, and
   `EmployeeService.create_employee`/`update_employee` + desktop API DTOs/
   commands all threaded through). Task-assignment notifications resolve
   `resource.employee_id → Employee.user_id` and no-op (log-free, by design)
   when that link isn't set — most existing employees won't have it set
   until someone links their account, which is expected and not a bug.
2. **Approval notification wiring location:** implemented inside the shared
   `ApprovalService` (not PM-only), per the team's choice — every module
   using platform approvals benefits immediately.

Foundation implemented:
- `src/core/shared/notifications/safe_dispatch.py` — a `safe_dispatch_notification(owner, ...)`
  helper mirroring the existing `record_activity(owner, ...)` convention,
  pulling `owner._notification_service` and swallowing/logging delivery
  failures so a notification can never break the calling operation (same
  guarantee `TenantMembershipService._safe_dispatch_notification` already
  had, generalized).
- `TaskService`/`CollaborationService`/`ApprovalService` all gained an
  optional `notification_service` constructor param, wired at the
  composition root (`project_registry.py`/`platform_registry.py`) from the
  `NotificationService` instance that already existed.
- `TaskAssignmentMixin.assign_project_resource` dispatches
  `pm.task.assigned.v1` to the resolved assignee.
- `CollaborationCommentCommandMixin.post_comment` dispatches
  `pm.comment.mentioned.v1` to every `@mentioned` user except the comment's
  own author.
- `ApprovalService.request_change` fans out `approval.requested.v1` to every
  user holding the `approval.decide` permission (tenant-scoped `approver`
  role bindings plus platform-wide `admin` bindings), excluding the
  requester. `reject`/`approve_and_apply` dispatch
  `approval.rejected.v1`/`approval.approved.v1` back to the requester
  (`ApprovalRequest.requested_by_user_id`), including the decision note when
  present.
- New tests: `src/tests/project_management/test_pm_assignment_and_mention_notifications.py`,
  `src/tests/platform/test_approval_notification_dispatch.py`, plus the
  `Employee.user_id` coverage folded into the existing employee test suite.
  Full repo test suite re-run clean (same pre-existing, unrelated baseline
  failures as before this work; zero regressions).

Not shipped as an app feature: no desktop surface calls
`list_my_notifications()`, no shell badge/read lifecycle exists, no delivery
channel exists, and no cross-session refresh exists. The persisted rows are
therefore not called "in-app notifications" in current product status. All
remaining notification work is deferred by the 2026-08-02 scope decision.

---

## Phase 2 — Cross-session delivery (the harder, architecture-level decision)

**Finding:** §2.4 of the audit — even after Phase 1, User B only sees a new
notification/comment/presence update when their own process independently
re-queries the DB. There is no mechanism today for User A's action to reach
User B's already-running process at all.

This is the one phase that genuinely requires the team to pick a direction,
because the options have real cost/complexity tradeoffs and depend on how
this app is actually deployed in practice (single shared SQLite file on a
network share? Postgres server? something else?). Presented as three tiers,
increasing in cost and capability — the team does not have to jump straight
to the top tier.

### Tier A — Timed background refresh (cheapest, works with any DB)

Add a lightweight periodic re-query (e.g. every 30–60s) for the
Collaboration workspace's unread-notification count and active-presence
list, using a `QTimer` in the relevant QML controller — the same kind of
mechanism already used nowhere in this codebase today (confirmed: zero
`QTimer`/polling in PM QML), so this would be new but simple. Gets you "you
find out within a minute" instead of "you find out never until you happen to
click into that screen." Works identically regardless of which database
backend is deployed.

**Effort:** small. **Cost:** a background query every 30-60s per connected
client — negligible at the target scale (150 concurrent users, per the
README's stated scalability targets) as long as the query is a simple
indexed `COUNT`/`SELECT ... LIMIT`.

### Tier B — Postgres `LISTEN`/`NOTIFY` (medium cost, Postgres-only)

If production deployments run Postgres (supported today via `PM_DB_URL`,
though local dev defaults to SQLite), a `NOTIFY` fired from the notification
insert trigger/service and a `LISTEN` connection per client process gives
near-real-time delivery without introducing a new server component. This
would need a small always-on listener thread per desktop client and a
documented "SQLite deployments fall back to Tier A polling" rule, since
SQLite has no equivalent primitive.

**Effort:** medium. **Cost:** one extra long-lived DB connection per client
for the LISTEN channel. **Constraint:** only helps tenants actually running
on Postgres — needs a capability/feature-flag check at startup so SQLite
tenants transparently fall back to Tier A.

### Tier C — A real push channel (WebSocket/SSE via a small notification
relay service)

The "do it properly" option: introduce a minimal server-side component
(even a lightweight one) that clients maintain a persistent connection to,
and which broadcasts `notification.created`/`presence.updated` events to
connected clients for the relevant tenant/org. This is the only tier that
gives true real-time delivery independent of the database engine, and the
only one that scales cleanly to a future web/mobile client if that's ever on
the roadmap. It's also the only tier that requires standing up genuinely new
infrastructure (a running service, not just a library) — a meaningfully
bigger commitment than Tier A/B.

**Effort:** large. **Cost:** new always-on service to build, deploy, and
operate; connection-management, reconnect/backoff, and tenant-isolation
concerns all need real design, not just a code change.

**Recommendation:** ship Tier A now (it's small and universally applicable),
evaluate Tier B if/when the team confirms Postgres is the real production
target, and treat Tier C as a separate, larger initiative the team scopes on
its own timeline rather than folding into this collaboration upgrade. Do not
block Phase 1 (addressed notifications) on this decision — Phase 1 is valuable
even under pure polling.

---

## Phase 3 — Real notification channels (email / OS-level)

**Finding:** §2.1 — `NotificationChannel` Protocol exists, zero
implementations.

Once Phase 1 exists (addressed, persisted notifications), adding a channel
is additive and low-risk: implement `NotificationChannel` for email (SMTP,
using whatever mail-sending capability the platform already has or needs to
add) and/or a native OS notification (`QSystemTrayIcon.showMessage`, which
PySide6 already supports natively — no new dependency). Register the
channel(s) in `NotificationService`'s construction in `platform_registry.py`.

**Recommendation:** OS-level toast first (zero external dependency, works
offline, matches "desktop app" nature of this product) before email (which
needs outbound SMTP configuration, deliverability concerns, and is more
naturally a "digest" — e.g. "3 things happened since you were last online" —
than a per-event channel for a desktop-first product). The team should decide
whether email is in scope at all for this product, or genuinely OS-toast-only.

**Effort:** small (OS toast) to medium (email, including a digest/throttling
policy so users aren't spammed one email per mention).

---

## Phase 4 - Collaboration depth features (implemented scope and backlog)

These are the "present vs. absent" gaps from audit §3.3 that are about
richness of interaction, not silence/visibility. None of them are
architecturally entangled with Phases 1–3 — they can be picked up in any
order, by priority, independent of the notification work above.

| Feature | Why it matters | Rough effort |
|---|---|---|
| Comment edit (with edit history or at least an "edited" marker) | Baseline expectation in any modern comment system; typo/correction currently requires a new comment | Small–medium (needs `updated_at` + edit history decision) |
| Comment soft-delete | Same — currently impossible to retract | Small (add `deleted_at`, filter on read) |
| Comment threading (reply-to) | Flat lists become unreadable past a handful of comments on an active task | Medium (needs `parent_comment_id` + UI nesting) |
| Comment reactions | Lower priority than the above; nice-to-have | Small |
| @everyone / @team mentions | Useful for project-wide announcements | Small–medium (extends `resolve_mentions` + notification fan-out — depends on Phase 1 existing first, since fan-out is only meaningful once notifications are addressed) |
| Assignee accept/decline of a handoff | Turns assignment from a pure push into a real workflow; the "Assign" quick-action stub (§3.2) suggests this was intended | Medium (new status field/enum on `TaskAssignment`, UI for the assignee side) |
| Document version history | "Latest wins" today loses prior versions silently | Medium–large (needs a supersede/version-chain model on `Document`, likely a platform-level change since Documents are platform-owned per the README's ownership rules — not purely a PM change) |
| Dedicated assignment/status audit trail separate from generic activity log | Would make "who changed what, when" easier to audit at scale | Small–medium, arguably lower priority since the generic activity log already captures it, just undifferentiated |
| Implement or remove the dead "Assign"/"Delegate" buttons (§3.2) | Currently misleading — visible but permanently disabled | Small if removed; folds into the accept/decline item above if implemented |

**Recommendation for sequencing within Phase 4:** comment edit + soft-delete
first (cheapest, most obviously expected), then threading, then the
assignee-accept/decline workflow (highest value of the remaining items,
since it turns a one-directional push into an actual collaborative
handoff). Reactions and @everyone are genuinely optional polish — defer
freely.

### Phase 4 implementation notes (2026-08-01 to 2026-08-02)

Shipped: comment edit, comment soft-delete, comment threading, comment
reactions, @everyone/@team mentions, assignee accept/decline, and the
dedicated-audit-trail query enhancement. The desktop assignment response UI,
atomic comment revision checking, moderation evidence, and platform runtime
presence heartbeat are also complete. Deferred: document version history
(unchanged from this doc's original scoping - platform-owned) and the
"Delegate" approval quick-action (see below).

**Comment edit + soft-delete + threading + reactions** (one combined pass,
since they touch the same domain/ORM/repository/DTO files): `TaskComment`
gained `parent_comment_id`, `updated_at`, `deleted_at`,
`deleted_by_user_id`, `deletion_reason`, a persisted `version`, and a
`reactions: dict[emoji, [user_id, ...]]` field (domain, ORM columns +
index, migration `7a1b2c3d4e5f`, mapper, and explicit field-copies in
`SqlAlchemyTaskCommentRepository.update()`). Migration `i7j8k9l0m1n2` adds
the revision and moderation columns. Repository updates now use a
`WHERE id = ... AND version = ...` predicate and raise `STALE_WRITE` when
another writer wins. New `CollaborationService`
methods: `edit_comment` (author-only — enforced by comparing the current
principal's `user_id` against `comment.author_user_id`, raising
`OperationNotPermittedError` otherwise; re-resolves mentions against the
edited body; sets `updated_at`), `delete_comment` (soft — sets `deleted_at`,
idempotent; open to anyone holding `collaboration.manage`, i.e. moderation-
capable, not author-restricted like edit — deleting spam/off-topic content
is a different trust decision than rewriting someone else's words),
`react_to_comment`/`remove_reaction` (toggle the current user's id into/out
of `reactions[emoji]`, gated by `collaboration.read`). `post_comment` gained
an optional `parent_comment_id` param, validated to belong to the same task.
The desktop API/DTO/serializer layer surfaces all of this
(`TaskCollaborationEditCommand`/`DeleteCommand`/`ReactionCommand`,
`is_reply`/`is_edited`/`is_deleted`/`reactions` on the comment DTO — deleted
comments render body as "This comment was deleted." at the serializer, not
by mutating the stored text, so the original remains in the DB for audit).
Controller/presenter/command-handler plumbing
(`editTaskComment`/`deleteTaskComment`/`reactToTaskComment`/
`removeTaskCommentReaction` slots, and the view-model now carries
`authorUserId`/`parentCommentId`/`isEdited`/`isDeleted`/`reactions` in each
row's `state`) is fully wired end-to-end.

**QML completion update (2026-08-02):** the task Activity section now uses a
dedicated `TaskCommentCard` instead of the generic `ActivityFeed`. It renders
full bodies, attachment/document context, edited/deleted state, reply nesting,
parent-author context, reply counts, reaction chips, and an anchored reaction
picker. The existing composer now has create/reply/edit modes and carries the
loaded revision on edit. Deletion uses a moderation dialog that carries the
revision and optional reason, and the public task workspace controller exposes
all mutations in QML type metadata. Action visibility is computed from the
current principal's global/project permissions and comment ownership in the
application/API path. Roots are newest-first and replies are chronological,
which keeps active discussions discoverable without breaking thread context.

Verification on 2026-08-02:
- focused collaboration/controller/runtime and QML architecture tests:
  **68 passed**;
- changed-file QML lint: **clean with no warnings**;
- complete in-memory Alembic upgrade: **passed**, single head
  `i7j8k9l0m1n2`;
- complete `src/tests/project_management` run: **314 passed, 3 failed**. The
  remaining failures are not collaboration regressions: two dashboard trend
  tests use fixed May 2026 timestamps against rolling current-date windows,
  and one import test expects an RBAC denial before the now-earlier module
  entitlement denial.

Comment hardening is complete for the approved scope: simultaneous stale
edits/deletes are rejected using a persisted atomic revision, and soft-delete
records the deleting principal plus an optional reason while preserving the
original body.

**@everyone / @team mentions:** `resolve_mentions()` special-cases the
literal tokens `everyone`/`team` to expand to every candidate's `user_id`
(no signature change — still returns the same 3-tuple), so existing callers
were untouched. The mention-picker option list
(`build_task_snapshot().mention_options`) now always includes an "@everyone"
entry first.

**Assignee accept/decline:** `TaskAssignment` gained `response_status`
(`pending`/`accepted`/`declined`, default `pending`) and `responded_at`
(migration `8b2c3d4e5f6a`).
`TaskAssignmentMixin.accept_assignment`/`decline_assignment` resolve the
assignment → resource → `Employee.user_id` chain (the same link Phase 1
added) and only allow the assignee's own linked user account to respond
(`OperationNotPermittedError` otherwise; `BusinessRuleError` if the resource
has no linked user at all, since there's no one to ask). Desktop API:
`ProjectManagementTasksDesktopApi.accept_assignment`/`decline_assignment`.
The task Assignments section now displays response status and server-derived
capabilities. Selecting a pending assignment shows Accept/Decline only to the
linked assignee; manager-only allocation, hours, and removal actions are shown
from the same capability context. Accept uses a confirmation dialog, decline
requires a reason, and completed responses cannot be reversed without a new
assignment handoff.

**Presence heartbeat:** `ShellRuntimeSessionController` now emits a generic
authenticated `runtimeHeartbeat` while the application is active. The PM
collaboration controller subscribes to that platform lifecycle signal, touches
the active task presence row, and refreshes only the presence collection. This
avoids a task-specific timer and keeps the TTL as the abnormal-exit fallback.
It remains polling against the shared database, not cross-session push.

**Dedicated assignment/status audit trail:** rather than a new table (the
generic `activity_entries` table + `record_activity` plumbing already had
everything needed once two small gaps closed), added `action_prefix` and
`parent_entity_id` filter params to `ActivityRepository.list_recent` /
`ActivityService.list_recent` (pushed down to SQL, not filtered in Python),
and `record_assignment_action` now accepts and forwards a `task_id` as
`parent_entity_id` (previously always `None`). A per-task assignment-history
view is now a single `activity_service.list_recent(entity_type="task_assignment",
parent_entity_id=task_id)` call instead of a synthetic client-side join.

**"Assign"/"Delegate" dead buttons — deliberately not implemented this
pass:** the audit's research confirmed these need genuinely different
amounts of work. "Assign" (mentions/inbox row → directly assign the
underlying task) is small and could reuse `assign_project_resource`
end-to-end, but still needs a new resource-picker popover and controller
slot — real UI work, not a backend gap. "Delegate" (approvals row → hand a
pending decision to someone else) needs a **brand-new domain concept from
scratch**: `ApprovalRequest` has no delegation/reassignment field or
service method today, and the platform's existing `RoleDelegationPolicy` is
an unrelated concept (who may grant which roles, not per-request handoff).
Building it means a new field/entity on the approval domain, a new
authorization rule for who may accept a delegated decision, and its own
notification wiring — a scope roughly comparable to a phase of its own, not
a button fix. Recommend the team scope "Delegate" as its own ticket with an
explicit design decision (field on `ApprovalRequest` vs. a separate
`ApprovalDelegation` entity) rather than have it implemented as a
side-effect of this backlog pass. Leaving both buttons `enabled: false` for
now remains accurate — nothing about their disabled state changed.

---

## What this plan deliberately does not touch

- Anything already covered by `docs/pm_modernization/README.md`'s other
  workstreams (scheduling, financials, portfolio, baselines) — this plan is
  scoped strictly to the collaboration surface.
- Document versioning is flagged (Phase 4) but is really a platform-module
  concern per the README's ownership rules ("Documents: PM owns business
  linkage and context, while the platform document library owns storage,
  versioning...") — recommend raising it as its own cross-module ticket
  rather than a PM-only change.
- No decision is made here about Tier B/C real-time delivery — that's
  explicitly left for the team, since it depends on production deployment
  facts (which DB engine tenants actually run) that aren't visible from the
  codebase alone.
- The notification persistence foundation is not expanded during comment UI
  modernization. Desktop notification UX, background refresh, delivery
  channels, retention, and operational monitoring belong to the deferred
  notification workstream.

## Suggested evaluation order for the team

1. Verify the completed Phase 4 task comment UX with real seeded users and
   project-scoped roles.
2. Verify assignment accept/decline with linked employee user accounts and
   project-scoped roles; the desktop action path is now complete.
3. Keep Phases 1 through 3 deferred until the team approves one complete app
   notification scope; do not ship only another partial delivery mechanism.
4. Track document versioning as a separate platform-owned initiative.
