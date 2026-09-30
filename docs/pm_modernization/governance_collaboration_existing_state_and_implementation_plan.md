# Governance and Collaboration: Existing State and R7 Implementation Plan

## Status and Scope

Audit date: 2026-09-30. R7A is COMPLETE as a characterization and roadmap phase.
R7 itself is OPEN. R7B has NOT started. This is not a security certification.
R5 and R6 remain CLOSED; their historical evidence is unchanged. R8 has not started.
Only this document and three characterization test files were added in R7A.
No production implementation, schema change, operational module, or commit was made.

The baseline is the current repository, not earlier product discussions saying
notifications do not exist. In-app notifications, generic approvals, an Action
Center, task comments/mentions, presence, activity, and enterprise audit already exist.
Extend and harden these authorities; do not build parallel replacements.

Classification: **A** canonical/healthy for its stated responsibility; **B** canonical
but incomplete; **C** conflicting behavior or competing definitions; **D** scaffold;
**E** dead/obsolete candidate; **F** absent and required by an existing workflow;
**G** intentionally out of scope. A does not certify every caller or deployment.

## Evidence Index

Paths below are repository-relative. Symbols identify the inspected implementation,
not merely a filename suggesting a feature exists.

| ID | Source and important symbols |
| --- | --- |
| AP1 | `src/core/platform/application/approval/approval_service.py`: request_change, approve_and_apply, reject, _require_pending_using, _ensure_not_self_decision, _list_users_with_permission |
| AP2 | `src/core/platform/infrastructure/persistence/repositories/approval/approval.py`: _base_scope_stmt, get_for_update, list_by_status, count_by_status |
| AP3 | `src/core/platform/domain/approval/approval_state.py`; `policy.py`; `src/core/platform/infrastructure/persistence/orm/approval/approval.py` |
| AP4 | `src/infra/composition/modules/project_registry.py`: _register_project_management_approval_handlers; `src/core/platform/api/desktop/approval/approval.py` |
| AC1 | `src/core/global_overview/contract/action_center.py`; `application/action_center_service.py`; `application/ordering.py` |
| AC2 | `src/core/modules/project_management/application/global_overview/pm_action_center_contributor.py`; `src/core/platform/application/global_overview/platform_action_center_contributor.py` |
| AC3 | `src/infra/composition/global_overview_registry.py`; `src/ui_qml/shell/controllers/global_overview/global_overview_controller.py`: selectRoute, row serialization |
| NO1 | `src/core/platform/application/notifications/notification_service.py`; `src/core/shared/notifications/safe_dispatch.py` |
| NO2 | `src/core/platform/infrastructure/persistence/repositories/events/notifications/notification.py`; corresponding ORM; `src/core/platform/contract/port/events/notifications/notification_channel.py` |
| NO3 | `src/ui_qml/shell/controllers/notifications/notifications_controller.py`; presenter; `src/ui_qml/shell/qml/NotificationsPanel.qml` |
| CO1 | `src/core/modules/project_management/application/collaboration/commands/collaboration_comments.py`; queries/collaboration_comments.py; queries/collaboration_inbox.py; utils/support.py |
| CO2 | `src/core/modules/project_management/infrastructure/persistence/reads/collaboration/sqlalchemy_workspace_reader.py`; `contracts/reads/collaboration/models/workspace_facts.py` |
| CO3 | `src/core/modules/project_management/infrastructure/persistence/orm/collaboration.py`; repositories/collaboration/collaboration.py; `infrastructure/collaboration_attachments.py` |
| CO4 | `src/ui_qml/modules/project_management/presenters/collaboration/approvals_builder.py`; workspace_builder.py; `controllers/collaboration`; `presenters/tasks/collaboration_builder.py` |
| HI1 | `src/core/platform/application/history/activity/activity_service.py`; `history/audit/enterprise_audit_service.py`; respective ORM and repositories |
| TS1 | `src/core/platform/application/time_management/time/timesheet_periods.py`; timesheet_financial_events.py; `src/core/modules/project_management/application/timesheets/services/service.py` |
| BL1 | `src/core/modules/project_management/application/scheduling/baselines/baseline_service.py`; domain/scheduling/baseline.py; infrastructure/persistence/repositories/scheduling/baseline.py |
| DB1 | `src/infra/persistence/migrations/helpers/rls_classification.py`; `src/tests/integration/postgresql/conftest.py` |
| ID1 | `src/core/shared/resource_identity/contracts.py`; `src/core/platform/infrastructure/persistence/repositories/security/auth/auth.py`: list_active_for_role_across_tenants |
| GU1 | `src/tests/architecture/test_platform_does_not_import_business_modules.py`; `docs/architecture_decisions/ADR-005-domain-events.md` |

## Findings Ordered by Risk

### GOV-01: Approval notification recipient scope is unsafe (B, first priority)

AP1 collects role bindings through `list_active_for_role_across_tenants` and also
the active tenant. ID1 confirms the first method returns non-null tenant bindings
across tenants, not just global administrators. Recipient selection does not check
the request organization/project or target decision eligibility. Notifications
include requester, entity type, and request identifiers. NO2 subsequently scopes
reads by recipient, not by request tenant, so a tenant field on the notification
does not repair incorrect targeting.

New unit characterization proves a foreign-tenant role binding enters the recipient
set. This is a production code-path finding, not proof of a historical disclosure.
R7B must resolve recipients against effective target-scoped authority, excluding the
requester where SoD applies, before notification persistence. Test tenant, org,
project, expired/revoked membership and inactive users independently.

### GOV-02: Collaboration child tables lack database isolation (B)

DB1 explicitly excludes task_comments/task_presence and document_links from RLS.
Parent joins in repositories are useful but are not PostgreSQL policies. Live
app_runtime characterization can read a foreign tenant's raw comment while the
canonical Reader join returns no matching row. This is not an ORM-leak test being
misreported as RLS proof. Notifications also intentionally have no RLS, with a
recipient-owned bootstrap justification; that needs a separate recipient-security
decision, not an indiscriminate tenant/org NOT NULL migration.

R7B must implement parent-scoped child protection and scoped reference validation;
retain a deliberate bootstrap-vs-business notification distinction. Baseline and
register child exclusions must enter the same dependency review, not be silently
described as protected because projects have RLS.

### GOV-03: Deleted comment content remains in workspace read facts (C)

CO1 soft-deletes without erasing body. CO2 neither excludes deleted rows nor exposes
a tombstone field in CollaborationCommentFact, and maps the retained body directly.
Live characterization proves the deleted body's continued presence in read output.
Deletion history may be retained for audit, but ordinary inbox/mention/search/count
surfaces must not present it as a live comment. R7E must make tombstone/redaction
semantics consistent across Task Detail and Collaboration, including replies and
mentions. This does not authorize destructive audit deletion.

### GOV-04: Actionability and decision authority disagree (B/C)

Platform Action Center uses approval.decide plus all scoped pending requests, not
target-specific reviewer eligibility. It can show one's own request even though
AP1 rejects self-decisions. Approval DTOs carry payloads; queue/read authorization
must be explicitly checked against target visibility, not inferred from the generic
decide permission. AP2 checks tenant/org and an organization-or-project join;
it is not a project-grant filter. This is a read/capability gap, not a claim that
every module decision handler bypasses its business permissions.

R7C establishes one eligibility/query contract consumed by Platform approval UI,
PM Collaboration, and Action Center. No reviewer assignment table is implied by
current permission-based routing. Add one only with a concrete approved requirement.

### GOV-05: Action Center and mention preparation have unbounded work (B)

AC2 loads all accessible projects, all assigned tasks, and every project's baseline
list before slicing the preview. The new call-count characterization measures
5 and 50 baseline-service calls for 5 and 50 projects, respectively, even with no
results. This is service-call fan-out evidence, not fabricated SQL timing evidence.
Task counts are exact by full materialization, not scalable SQL counts.

CO1 `_collaboration_scope` loads all projects; mention candidates loop role bindings
and perform user lookups; task comment detail/read-marking loads all comments.
CO2 comment pages correctly use SQL COUNT + LIMIT/OFFSET and stable created_at/id
ordering, but author options and accessible-project inputs are not bounded.
R7D/R7E must bound the whole read pipeline, not just the final DTO page.

### GOV-06: Notification durability and idempotency are incomplete (B/F)

NO1 dispatch creates a new identity on every call. There is no event-recipient
uniqueness key. `safe_dispatch_notification` persists after the originating commit
and swallows errors: useful nonfatal UX, but crash/loss cannot be recovered.
NotificationService can call external channels even with commit=False, before the
caller commits. Current composition installs the in-app service without a concrete
external channel; therefore this is a port/transaction hazard, not a claim that
production email currently sends before commit.

R7F should use existing durable event/outbox/inbox mechanics for in-app delivery
intent and recipient-level deduplication. It must not create a second general event
bus, or expand into an email/SMS product. Domain success must not depend on remote
delivery. Read/unread acknowledgement is not business approval or task completion.

### GOV-07: Layering, attachment lifecycle and transaction hazards (B)

CO1 imports concrete filesystem attachment storage and SystemClock from infrastructure.
The attachment helper copies files before the comment UoW and keeps nonexistent
input paths; rollback can leave files without committed metadata. Same-name copies
can overwrite in the local comment folder. Document metadata/link creation is in
the comment UoW, but filesystem storage is not transactional.

AP2 imports PM ProjectORM from Platform infrastructure. GU1 explicitly allowlists
this ADR-005 debt; passing architecture tests does not mean it disappeared. Replace
it with a target-scope contract bound in composition, not another Platform god-service.
Platform Time's existing timesheet mixin imports concrete SqlAlchemyUnitOfWorkBase;
it is inherited debt, not an R7A regression or justification to reopen Finance.
Presence uses shared-session commits. Activity/audit support commit flags. R7 must
contain touched operations and prohibit accidental commitment of unrelated work.

### GOV-08: Request/version and identity edges need explicit contracts (B)

Generic Approval has a stable request ID and PostgreSQL row-lock decision protection,
but no request optimistic version, submission idempotency key, or unique pending
target/revision constraint. Comment update uses repository CAS; expected_revision
is optional at its command boundary, and duplicate submissions create new comments.
Presence uniqueness uses task/username instead of stable user identity.
Baseline version CAS protects a row but alone does not prove a single-approved
baseline invariant under simultaneous approvals of different rows.

R7C/R7E require concurrency tests at these boundaries. Do not claim row locks offer
the same concurrency guarantees on SQLite as PostgreSQL. Typed actors and durable
IDs must remain distinct from labels, resource IDs, or external references.

## Authority and Capability Map

| Capability / class | Owner, authority, transitions and consumers |
| --- | --- |
| Reusable Approval (B) | Platform ApprovalService / approval_requests. PENDING -> APPROVED or REJECTED; durable requester/decider IDs plus labels. Request/decision API, Control approval detail, PM Collaboration, Action Center. Fresh write UoW, locked pending row, fail-closed audit and post-commit events. No cancellation, supersession, reviewer assignment or delegation state today. |
| Finance governance (A for retained R6 responsibility) | Finance owns Budget, Forecast, financial change, Actual and Billing eligibility/effects and their versioned persisted targets. Platform supplies approval mechanics, not financial truth. Same-transaction participants are registered in AP4. Preserve the R6 authority map and regression tests. |
| Baseline lifecycle (B) | PM Scheduling owns DRAFT/SUBMITTED/APPROVED/REJECTED/SUPERSEDED baseline and snapshot/variance evidence. BL1 uses baseline.manage / baseline.approve plus project grants, row version updates, UoW/activity/events. Separate baseline.create governance requests authorize creation, not approval of an existing submitted baseline. Do not merge these different decisions. |
| Timesheet Review (A for existing boundary) | Platform Time owns OPEN/SUBMITTED/APPROVED/REJECTED/LOCKED periods and work evidence; PM supplies project review scope and Reader. Required expected_version for decisions, CAS transition, audit/activity and approved-Time durable outbox. Review Queue reviews periods, not arbitrary approvals. No universal requester != reviewer rule is present in the inspected Time path; do not silently invent it. |
| Project/task status and assignment (A, operational) | PM project/task application services own status, staffing, Resource membership and allocation response. No blanket generic approval for every status mutation. Task dependency/constraint/leveling operations can be governed under code/env policy. |
| Action Center (B) | Neutral core/global_overview aggregator + Platform/PM contributors. Derived actionable work, no independent persisted workflow state. Sources: pending generic approvals, open assigned tasks, submitted baselines, own open/rejected periods. Exact summaries must share eligibility with previews. |
| Notifications (B) | Platform recipient-owned persisted in-app messages and read state; shell bell/drawer. Optional delivery-channel Protocol is D, not implemented external delivery. Notifications do not own work completion. |
| Activity (B) | Platform ActivityService / activity_entries: user-facing meaningful changes, entity/project/resource related references and scoped pages. Shared UI reused by domain surfaces. Not compliance evidence or chat. |
| Enterprise Audit (A/B) | Platform EnterpriseAuditService / audit_entries: compliance before/after, actor_type, reason, permission, request/correlation/causation and result. audit.read, separate org-read API. Explicit-org reads require review of caller target authorization; service permission alone is not proof. No generic retention/purge workflow found. |
| Domain history (A, distinct) | Baseline variance records, Finance revisions/approval evidence, Time period decisions. Module-specific lifecycle truth; do not replace with activity text. |
| Integration history/operator exceptions (A, retained R6) | Durable inbox/outbox, Accounting handoff/delivery/outcome/quarantine/status. Service identities, bounded evidence and governed retry. Not a new generic human Approval workflow. Retain existing port/event boundaries and no Accounting operations. |
| Task comments, replies, reactions, mentions (B/C) | PM TaskComment, CollaborationService, versioned comment repository and UoW. Author edits, collaboration.manage/project-scoped deletion (moderation-like), soft delete, mention read marks. workspace Reader and Task Detail are different read projections over the same store, not two comment stores. |
| Presence (B) | PM ephemeral task_presence, scoped read and shared-session touch/clear. Activity/last_seen is not availability, attendance or audited work. Expiring display is not physical retention. |
| Notes/register fields (A, distinct) | Register description/impact/response_plan and owner_name; baseline notes; task/project descriptions and TimeEntry notes remain aggregate attributes, not separate discussions. No generic conversation store required. |
| Attachments/evidence (B) | Platform Documents metadata/link authority plus PM local file copying and comment references. Editable human content must not be conflated with immutable Finance/handoff payload evidence. |
| Watchers/subscriptions, reviewer substitute, escalation SLA (G) | No active workflow/store found for these capabilities. Event-bus subscribers are not human subscriptions. Role delegation policy is grant-administration security, not approval delegation. No approved product need warrants implementing them in R7. |
| Durable notification intent/scoped actionable queries (F) | Required hardening of existing promised messages and work queues, not new user-facing workflow families. |
| Empty collaboration subpackages (D/E candidates) | attachments/comments/mentions/notifications/presence/models/validators contain placeholder package files while active logic lives in commands/queries/utils. Verify imports before deletion in R7E; do not call active mixins dead. |

### Approval End-to-End and Policy

`Desktop API -> ApprovalService -> fresh Approval UoW -> pending row lock ->
same-session registered module participant -> target mutation + request decision +
audit + transaction events -> commit -> post-commit invalidation/notification attempt`.
Repositories do not commit in this path. Notifications are outside the atomic
decision boundary today; do not include them in an atomicity claim.

AP4 registers exactly these apply handlers:

| Request type | Module-owned decision |
| --- | --- |
| baseline.create | Create Scheduling baseline evidence |
| dependency.add / dependency.remove / dependency.update | Task dependency business mutation |
| task.constraint.update | Task scheduling constraint |
| scheduling.leveling.apply | Apply Scheduling-owned leveling plan |
| budget.approve | Govern Budget version |
| forecast.approve | Govern Forecast version |
| project_cost.approve | Govern Actual Cost |
| financial_change.apply | Apply governed financial change |
| project_billing_preparation.approve | Govern Billing Preparation |

There are eleven apply registrations and rejection participants for the five
Finance types. No administrative-configuration approval handler was found in the
registration search. Do not infer one from the generic service's existence.

Policy is code-driven plus PM_GOVERNANCE_MODE / PM_GOVERNANCE_ACTIONS environment
configuration for selected operations. Default mode is off; this is not a tenant
policy editor. Some optional operational flows exempt admin sessions. Mandatory
Finance governance has its own business eligibility: do not describe the environment
toggle as a universal Finance bypass. Generic self-decision guard checks durable
requester and decider identity; baseline/time own their own rules. No new universal
four-eyes policy is approved by this audit.

Current generic decisions are terminal through service transitions and audited,
but the request is a mutable row, not an immutable decision ledger enforced by
the database. Payload/target version validation varies by participant. R7C must
characterize each registration, including rejected requests, duplicate requests,
stale target versions and retries, without replacing domain state machines.

## Identity, Permissions, Events and Navigation

User is the authenticated human principal and recipient/comment author. Resource
is a PM staffing entity (employee or external); ProjectResource is membership and
planned-work envelope; TaskAssignment is task work/allocation, not a User account.
Employee requires department and is linked through identity contracts, not by
matching names. ID1 ResourceIdentityReader resolves the signed-in user to a resource;
TimesheetWorkspaceReader has its own Mine resolution. R7D must test both against
the same membership rules rather than introduce a third name-based resolver.
Register owner_name and baseline submitted_by/approved_by labels are not durable
reviewer assignments. Missing linked Resource means no personal assigned-work data,
not authorization to display every Resource's work.

Enterprise Audit supports user/service/system actor classification. Approval and
comment display labels must not masquerade a missing human as a service actor.
Accounting service principals and trusted connectors remain R6-owned integration
identities. No automated worker should inherit the requesting interactive session.

Permissions currently include approval.request/approval.decide; collaboration.read/
collaboration.manage; baseline.manage/baseline.approve; timesheet.submit,
timesheet.submit_on_behalf, timesheet.approve and timesheet.lock; activity.read
(or settings.manage in Activity); audit.read; module-owned Finance permissions.
No canonical approve-cancel-delegate permission family exists. Comment editing is
author restricted; deletion under manage is broader. Make moderation semantics
explicit before splitting permissions. Mention candidates currently recognize four
named project roles plus the current permitted principal, with per-user lookups;
custom/effective grants need parity tests. Server authors capabilities; QML must
not derive decision eligibility from status strings or presence of an API object.

Distinct event roles:

- Module/domain event: typed business change, owned by the business transaction.
- Committed event/invalidation: presentation refresh only after commit; preserve
  committed-operation identity distinct from correlation ID.
- Activity: meaningful user-facing history written with the business operation.
- Enterprise audit: fail-closed traceability for governed operations.
- Notification: recipient delivery derived from committed business meaning; current
  direct best-effort dispatch needs durable hardening, not another domain authority.

Global Overview's selectRoute forwards only route_id. ActionCenterItemDto contains
subject identity but the shell row serialization/navigation does not carry a full
authorized subject deep link. Notifications serialize title/body/category/time/read
state, not a navigable entity target. R7D/R7F need context-safe target routing and
stale/deleted/permission-revoked handling without silently pinning global PM project
context. Existing compatibility PM route IDs are not proof of working subject links.
Global Overview attention cards explicitly remain noninteractive where no destination
exists; do not invent a fake full Action Center page in R7A.

Control Approvals and Collaboration Approvals consume the same Platform authority;
they are overlapping views, not necessarily duplicate workflows. Their read limits
and capabilities need convergence. Review Queue stays TimesheetPeriod-specific.
Keep notifications, activity, audit and integration retry status separate from all
three queues. No additional optional-module contributor is justified now.

## Persistence, Scope and Lifecycle Inventory

RLS labels below describe the actual manifest, not the desired future security.
Parent policies are also a real fifth repository category, PARENT_SCOPED_RLS_TABLES,
although the brief listed only four. Never relabel exclusions as parent policies.
Retention means observed lifecycle, not an approved legal retention schedule.

| Table(s) / owner | Scope and relationships | Mutation, version, uniqueness, lifecycle | Actual RLS / canonical access |
| --- | --- | --- | --- |
| approval_requests / Platform | Nullable tenant FK, required org FK; project/entity IDs polymorphic, no scoped target FK | Mutable pending/decision row; PK stable ID, no version or request dedup unique; terminal through service, no cancel/purge API | TENANT_AND_ORGANIZATION; AP1/AP2. Org-or-project join fallback and no target-grant predicate require repair |
| task_comments / PM | Task FK cascade; self parent-comment FK SET NULL; author IDs/labels; no tenant/org columns | version CAS; no submission dedup; soft deletion retains content; reactions/mentions/read marks JSON text; parent FK does not enforce same task | INTENTIONAL_RLS_EXCLUSION; CollaborationService + scoped repository / CO2 |
| task_presence / PM | Task FK cascade, user_id nullable and username label | Unique task/username; no version; touch/clear and freshness window, no durable work meaning | INTENTIONAL_RLS_EXCLUSION; collaboration presence commands/queries |
| notifications / Platform | Recipient User FK cascade, nullable tenant FK, no org/project scope columns | PK only; read_at mutable, no event-recipient uniqueness/version; no retention worker found | INTENTIONAL_RLS_EXCLUSION, recipient-only repository; NO1/NO2 |
| activity_entries / Platform | Nullable tenant/org FKs; entity/related entity/project-workspace refs polymorphic | Append-style record API, no version/dedup uniqueness; no established purge policy | TENANT_AND_ORGANIZATION; ActivityService/repository pages |
| audit_entries / Platform | Nullable tenant/org, typed actor, entity/project/request/correlation refs | Append-style compliance evidence; PK, no optimistic version; do not treat row mutability as tamper-proof storage; retention unresolved | NULLABLE_TENANT_AUDIT; EnterpriseAuditService and audit.read |
| project_baselines / PM Scheduling | Project FK cascade; submitted/approved label metadata | version CAS; status lifecycle; no independent immutable decision table; do not infer unique-approved concurrency from version alone | INTENTIONAL_RLS_EXCLUSION; BaselineService/scoped repository |
| baseline_tasks / PM Scheduling | Baseline/task references; historical schedule/cost evidence | Snapshot facts; no command revision protocol independent of baseline | INTENTIONAL_RLS_EXCLUSION; baseline repository |
| baseline_variance_records / PM Scheduling | Baseline/previous baseline/task evidence | Append-style comparison history retained with baseline lifecycle | INTENTIONAL_RLS_EXCLUSION; BL1 |
| timesheet_periods / Platform Time | Tenant/org + resource period identity | Resource/period uniqueness, version CAS, status/decision metadata; lifecycle history not a generic Approval row | TENANT_AND_ORGANIZATION; TS1 + PM review Reader |
| time_entries / Platform Time | Tenant/org + work allocation/assignment and owner context | version, editable only under permitted period lifecycle; Time owns work evidence | TENANT_AND_ORGANIZATION; Time service, not an Action Center store |
| documents / document_structures / Platform | Tenant/org FKs; structure/document relationships and uploader User FK | version; organization/code unique; is_active/current/revision metadata; mutable content metadata, not automatically immutable evidence | TENANT_AND_ORGANIZATION; Document service/repositories |
| document_links / Platform | Org FK + document FK cascade; polymorphic module/entity link | Unique document/module/entity/type/role; nullable role needs duplicate semantics review; no version; target scope not enforced by polymorphic FK | INTENTIONAL_RLS_EXCLUSION; document integration helpers |
| register_entries / PM | Project FK, human owner_name, due date | version; project/code unique; status and notes remain register domain; no automatic reminder/SLA | INTENTIONAL_RLS_EXCLUSION; Register service/Reader |
| projects, tasks, resources, project_resources, task_assignments / PM | Project/resource membership and task ownership, not User assignment | Existing versioned operational aggregates; do not add quantities to Finance amounts | Projects/resources direct tenant+org; tasks/membership/assignments parent-scoped RLS; existing operational services |
| role_bindings / user_tenants / users / roles / Platform Identity | Auth bootstrap/effective scoped permissions and membership, not reviewer queue tables | Grant expiry/revocation and principal identity; retain canonical RBAC | Intentional auth-bootstrap exclusions in DB1; authorization engine/identity services |
| role_delegation_policies / Platform Authorization | Role-grant authority policy | Security administration, NOT substitute approver lifecycle | Intentional auth-bootstrap exclusion; do not reuse as workflow delegation |
| integration_outbox / integration_inbox and Finance handoff/delivery/outcome evidence | Tenant/org plus source/destination/project correlation under existing R6 contracts | Durable identities, dedup, leases/versions and immutable evidence as defined by R6; operator history, not chat | Existing direct tenant+org classifications; IntegrationOutboxService/IntegrationInboxService and operation UoWs |
| service_principals / service_principal_api_keys / Platform Security | Explicit automated tenant/org identity and credentials | Scoped principal/credential lifecycle, not requesting User impersonation | Principals tenant+org, API keys tenant-only; existing R6 integration identity boundary |

Financial version/line/approval-related tables retain their R6 inventory and
ownership in [the closed Finance plan](project_finance_existing_state_and_implementation_plan.md).
They are consumers of governance, not new R7 stores. No new audit/comment/queue
table should copy their authoritative financial amounts or statuses.

## Read / Write Architecture and Performance

Target remains Desktop API -> application query -> Reader -> bounded SQL projection
-> immutable facts -> DTO. Commands remain API -> application/domain -> contracts
-> repository/UoW -> atomic persistence. Composition alone assembles concrete PM
and Platform contributors (AC3); generic ActionCenterContributor stays neutral.
No current optional Accounting/Procurement/Inventory module is required.

| Read/operation | Observed shape | R7 action |
| --- | --- | --- |
| Action Center aggregate | Sums contributor exact counts, merges candidates with deterministic tier/date/module/kind/id ordering; no independent DB store | Retain neutral aggregation; enforce bounded contribution and eligibility contract |
| PM assigned tasks/baselines | Entire task collection and per-project baseline fan-out before preview; measured 5 -> 50 service calls | R7D scoped SQL count + top-N projection, identical global ordering and tie breakers |
| PM own timesheet contribution | SQL open count, bounded open rows and bounded rejected period page | Retain semantics; cross-page and identity parity tests, do not turn period end into deadline |
| Platform approvals | COUNT + limited list, requested_at descending without ID tie-break, unbounded caller limit | R7C hard cap/page/sort criteria and target eligibility; shared query for list/count |
| Comment workspace | COUNT + SQL page, stable created_at/id; ORM materialized internally, immutable facts returned | Retain Reader boundary; repair deletion semantics and bound project/author selectors |
| Task comment detail/read marks | Whole task list; per-comment read-mark updates | R7E bounded detail/thread reads and targeted unread update; prove rollback/CAS |
| Mention candidates | Four role scans, per-user lookups, full result sort | R7E effective-permission bounded identity Reader; no name-based authority |
| Notifications | SQL count and limit, recipient scope, created_at only, no max limit; new ID per dispatch | R7B scope decision; R7F durable dedup, bounded stable cursor/page and target routing |
| Activity | Server-filtered pages, recognized sizes 25/50/100, related entity references | Retain shared component; explicit target-org authorization and actor/detail redaction proof |
| Enterprise audit | Limited recent reads and explicit-org reads; service permission check, no general paged search contract | R7G actor/scope/boundedness, not a duplicate compliance store |
| Presence | Bounded recent display but writes commit shared session | R7E isolate ephemeral write transaction and stable identity, not durable SLA |

No EXPLAIN latency claims or new indexes are made in R7A. R7D/F/G must measure
real PostgreSQL SQL counts/plans at increased volume before index decisions.
No repositories in the inspected Approval/comment/notification paths commit;
that does not prove every legacy application service uses a fresh UoW.

## Explicit Answers to the 25 Architecture Questions

1. Canonical generic Approval is Platform ApprovalService and approval_requests (AP1-3).
2. Eleven PM apply handlers use it; five Finance rejection participants (AP4 table above).
3. Time periods, baseline lifecycle, Finance versions and integration delivery retain necessary domain state machines.
4. No second generic Approval engine was found. Baseline creation governance vs baseline approval are different decisions; queue eligibility and deleted-comment presentation currently conflict.
5. Action Center is a derived, permission-scoped actionable work preview/count, not event history.
6. Review Queue is TimesheetPeriod review only.
7. Notification is recipient awareness/read acknowledgement, not work completion.
8. Activity is user-facing meaningful change history.
9. Enterprise Audit is permission-controlled compliance/traceability evidence with typed actors and causation.
10. Task comments/replies/reactions/mentions and presence exist; descriptions/register notes are distinct attributes.
11. Reuse current comments and Documents; no product evidence warrants a universal discussion aggregate.
12. Approval delegation/substitute is absent; defer until an explicit coverage policy is approved. RBAC role delegation is not it.
13. Real task/register due dates exist; generic escalation/reminder/SLA does not. Do not fabricate deadlines or build a scheduler now.
14. Choose C: extend existing Approval minimally. No BPMN, DSL, scripting or distributed workflow engine.
15. Align target read/decision capabilities and scoped recipient targeting; clarify comment moderation and explicit-org history permissions, not blanket role consolidation.
16. Generic Approval prohibits requester self-decision. Baseline/Time do not inherit it automatically. Preserve existing Finance rules; no new universal two-person mandate.
17. Comments/presence/document links, baseline family and register are excluded; notifications need recipient/global-bootstrap design. Scope/FK and Approval org-join gaps are listed above.
18. Request submission dedup, comment submission replay, notifications, presence identity and multi-row baseline approval need hardening; existing row CAS/locks are not discarded.
19. PM Action Center, mention/user lookups, task comment lists, project/author options; limited Approval/notification/audit APIs also need maximums and stable ties.
20. CO1 filesystem/clock imports and Platform Time concrete UoW; AP2 Platform-to-PM ORM is a separately allowlisted boundary violation.
21. Control/Collaboration approval views overlap legitimately; unify query/capability truth. Do not merge them with Timesheet Review or notifications.
22. R7B first: scoped recipient/target authorization and child-table RLS, before feature expansion.
23. Retire scope fallback branches, the direct PM ORM coupling after contract migration, placeholder subpackages after import proof, obsolete local queue filtering after Reader cutover, and direct best-effort business notification paths after durable cutover.
24. R8 retains broad accessibility, keyboard/focus, visual/theme, all-product responsive certification and human visual review.
25. Delegation/SLA/watchers and external notification channels remain future unless justified; operational Accounting/Procurement/Inventory/Payroll, FX and generic workflow engines are out of scope.

## R7B+ Execution Roadmap

Each phase requires fresh targeted tests, scoped lint, compilation, relevant QML
lint and diff checks; no phase closes with parallel compatibility authorities.
Characterization tests asserting current weaknesses must be replaced with corrected
security/correctness expectations, not preserved as permanent acceptance behavior.

### R7B - Governance Scope and Isolation

- Problem/evidence: GOV-01/02/04; raw child access and foreign recipient selection are proven.
- Authority: effective Platform authorization plus module target-scope contract; PostgreSQL enforces row isolation independently.
- Scope: target-scoped recipients; pending/read target visibility; child parent policies, missing scoped relationships; bootstrap vs business notification classification; explicit-org history authorization contract.
- Non-goals: no workflow engine, new delegation, notification delivery feature or Finance redesign.
- Migration/deletion: update RLS manifest/migration with raw tests; remove organization-or-project fallback and PM ORM coupling only after equivalent target contract is wired; update GU1 exception deliberately with ADR citation.
- PostgreSQL: runtime nonowner hostile tenant/org/project/parent SELECT/INSERT/UPDATE/DELETE tests, no context, foreign reply/document link; separately test service/ORM authorization.
- Concurrency: scope change/revoked membership between read and command; no cached authorization grants.
- UI: truthful unavailable/denied actions, no foreign count/payload/recipient leaks.
- Exit: scoped recipient and target matrix green; chosen notification bootstrap contract documented; excluded sensitive child data either protected or explicitly justified and tested. No cross-scope repair via UI-only checks.
- Dependencies: R7A only. No production implementation authorized by R7A itself.

### R7C - Approval Eligibility, Lifecycle and Decision Hardening

- Problem/evidence: GOV-04/08, AP1-4; generic decision safety exists but request identity/replay and read actionability diverge.
- Authority: Platform mechanics, module eligibility/effect participants; preserve distinct baseline/Time/Finance states.
- Scope: reusable target eligibility facts, bounded count/page/sort, stale-target evidence, request idempotency, immutable decision audit; explicit handling of withdrawn/stale requests if an existing operation requires it. Do not invent unrestricted cancellation.
- Non-goals: reviewer assignment product, delegation/SLA, arbitrary approval DSL or replacing closed Finance command authorities.
- Migration/deletion: remove hasattr repository fallback once canonical contract adopted; replace limited-list local filtering consumers; one API/query path for generic approval views.
- PostgreSQL: two approvers, approve/reject race, same request retry, same target revision request race, target mutation rollback with request/audit/event; preserve Finance participants in the same fresh UoW.
- Concurrency: baseline approvals of different versions must retain one approved authority; distinguish CAS row protection from aggregate invariant.
- UI: server-authored canDecide/reason incl. own request and stale/terminal target; counts match eligibility.
- Exit: all eleven registrations characterized; same-transaction atomicity and duplicate/stale decision matrix pass; no finance recalculation authority added.
- Dependencies: R7B.

### R7D - Bounded Action Center and Authorized Deep Links

- Problem/evidence: GOV-05, AC2/AC3 and four blocked employee-fixture tests.
- Authority: neutral aggregator, business-specific Reader contracts; no persistent Action Center workflow table.
- Scope: SQL counts/top-N task and baseline contributors; effective identity parity; stable ordering across sources; context-safe subject navigation and stale-target handling.
- Non-goals: generic review queue, artificial due dates, global PM context changes, new optional-module contributors.
- Migration/deletion: replace full-list task/baseline contributor paths, superseded local sorting/filtering, undefined Global Overview ActivityRowViewModel export; repair four Action Center fixtures with required departments, not weakened Employee validation.
- PostgreSQL: query count/EXPLAIN at realistic project/task volume, hostile scope, exact summary/preview predicate parity.
- Concurrency: item disappears or permission revoked between preview and open; scope switch/late result cannot cross projects.
- UI: existing Global Overview links carry authorized target identity; keep noninteractive summary honest unless full destination is implemented deliberately.
- Exit: count and ordering equivalence, bounded service/SQL work, four existing Action Center tests green, context-switch/deep-link tests pass.
- Dependencies: R7B/C.

### R7E - Task Collaboration, Mentions and Evidence Lifecycle

- Problem/evidence: GOV-03/05/07/08, CO1-4.
- Authority: PM owns comment/thread meaning; Platform identity/Documents own recipient identity/metadata; infrastructure implements storage port.
- Scope: deleted/tombstone consistency, required stale revision where appropriate, submission replay identity, bounded thread/mention reads and author options, effective permission candidates, attachment validation/staging/rollback compensation and authorization, stable presence identity and isolated transactions.
- Non-goals: universal discussions, document management product expansion, real-time chat service or attendance tracking.
- Migration/deletion: remove concrete storage/clock imports from application through injected ports; retire redundant local list logic and unused placeholder folders only after imports/DI/tests migrate; preserve retained audit evidence.
- PostgreSQL: parent/reply scope, version races, duplicate post, reaction/read-mark contention, file/metadata failure atomicity or explicit compensation.
- Concurrency: edit/delete vs mention/read/reaction; project switch with open composer; no stale or deleted text in ordinary workspace search/count/mention projection.
- UI: consistent tombstone behavior, explicit moderation vs author edit capabilities, bounded attachment/mention pickers and validation feedback.
- Exit: raw/service isolation, deleted content visibility, replay, attachment rollback and scoped selector matrix green; no parallel old/new comment readers.
- Dependencies: R7B and identity/query contracts from R7D; notification publishing integrates with R7F rather than inventing another notifier.

### R7F - Durable In-App Notification Delivery

- Problem/evidence: GOV-01/06, NO1-3.
- Authority: Platform recipient notification store, existing event/outbox/inbox delivery; modules publish business facts.
- Scope: transactionally durable notification intent, scoped recipients, event/recipient dedup, stable bounded reads, read-state ownership, safe subject links, scope/logout invalidation and retention policy decision for existing data.
- Non-goals: email/SMS/push infrastructure, user subscriptions/watchers or another event bus.
- Migration/deletion: migrate Approval/comment sources together; remove superseded direct commit=True best-effort business dispatch; external channel port must not allow precommit external effects. Keep legitimate bootstrap notices distinct.
- PostgreSQL: duplicate/replay and wrong-recipient denial, runtime-role policy proof appropriate to chosen bootstrap contract, restart and rollback tests.
- Concurrency: simultaneous dispatch and read/mark-all-read; exact unread count, one recipient effect per committed event.
- UI: shell bell/drawer remain notification surfaces, not queues; no body/payload leak after scope change.
- Exit: no lost intent after commit/restart, dedup proof, no precommit external effect, bounded reads and safe target routing; no new external channel implementation required.
- Dependencies: R7B recipient design, R7C/E event sources; R7D routing.

### R7G - History, Actor and Cross-Surface Integration

- Problem/evidence: HI1, typed Audit vs loosely labeled Activity/comment/service actors; explicit-org read authorization and duplicated presentation risks.
- Authority: keep Audit, Activity, domain history, integration evidence and collaboration separate stores with explicit audiences.
- Scope: scoped shared activity/audit reads, actor redaction/service identity, narrow post-commit invalidation, count/history bounds, cross-surface target consistency and retention decisions; unchanged Finance effects verified as consumers.
- Non-goals: immutable-storage infrastructure/compliance product, integration redesign, broad R8 visual cleanup.
- Migration/deletion: remove touched duplicate presentation calculations/helpers, commit-owning convenience calls from composed transactions and obsolete paths after caller migration; do not erase business history.
- PostgreSQL: audit nullable-scope classification, explicit-org denial and rollback; bounded history volume plans.
- Concurrency: separate commits sharing correlation both refresh; same commit coalesces; late project results denied; automated actors never become interactive users.
- UI: functional history permissions/deep links/errors coherent; preserve existing reusable activity components.
- Exit: audience/scope/actor matrix, atomic persistence and post-commit invalidation green, no duplicate history authority.
- Dependencies: R7B-F.

### R7H - Integrated Regression and Formal R7 Closure

- Problem/evidence: cross-cutting changes must compose, not merely pass isolated unit tests.
- Authority: certify the single paths established above; do not introduce new capabilities.
- Scope: approvals, Action Center, Review Queue boundary, notifications, comments, documents, activity/audit and optional-module independence as one system.
- Non-goals: R8, Finance reopening, operational future modules, workflow engine.
- Migration/deletion: verify all marked characterization/compatibility/placeholder replacements removed or intentionally retained with current semantics.
- PostgreSQL: full relevant RLS/concurrency/rollback/replay/worker and runtime-role integration matrix from final worktree.
- Concurrency: final end-to-end approval -> effect -> committed notification/activity/queue invalidation; project/tenant switch, stale inputs, restart.
- UI: targeted affected surfaces at established five desktop viewports and light/dark, functional focus/navigation; not full-product visual certification.
- Exit: final PM + Platform relevant suites classified with exact counts; no R7-caused failure; architecture/schema/migration/QML/scoped Ruff/compile/diff gates; dependency directions enforced; final doc closure. Known unrelated baseline failures must remain explicitly classified.
- Dependencies: R7B-G. R8 starts only with separate approval.

## Cleanup Register and Non-Goals

No production file was deleted during R7A. Candidate cleanup is not automatic
permission to delete different business semantics. Track each removal in its phase:

| Candidate | Classification / disposition |
| --- | --- |
| Platform Approval's concrete ProjectORM dependency | Active architectural debt, not dead code; R7B contract cutover then remove allowlist exception |
| Approval hasattr list/count scope fallbacks | Compatibility candidates; prove repository registration parity and remove in R7C |
| Full-list PM Action Center paths | Active but superseded by R7D bounded Reader; delete only after equivalent behavior/tests |
| Comment workspace raw deleted-body projection | Conflicting active projection; repair in R7E, retain audit history |
| Empty collaboration package placeholders | D/E candidates, inspect actual imports; no speculative future hierarchy |
| Direct business notification dispatch helper usages | Active but nondurable; R7F caller migration then delete superseded paths, not all notification channels by name |
| Global Overview ActivityRowViewModel undefined annotation/export | Existing two Ruff findings relevant to R7D; future annotations explain why some runtime tests still pass |
| Baseline vs generic Approval, Time vs generic Approval | Legitimate distinct business state machines, not deletion candidates |
| Neutral Procurement/Accounting/Inventory contracts | Future-facing boundaries, not implemented operations; do not expand or delete simply because implementations are optional |

R8 owns broad accessibility, keyboard/focus sweeps, visual consistency, theme cleanup,
all-product responsive certification and human product review. Functional defects
in touched R7 screens belong to their implementation phase. Watchers, substitutes,
SLA escalation and external delivery need separate product requirements. No BPMN,
invoice/payment/GL/tax/FX or operational Procurement/Inventory/Payroll work is planned.

## Validation and Baseline Caveats

### Executed R7A Evidence

| Gate | Actual result |
| --- | --- |
| Targeted existing Approval/Action Center/notification/activity/collaboration tests across Platform, global overview, PM and QML | **277 passed, 4 failed**, 112.67s; `.r7a_characterization.log`. All four fail in PM Action Center fixture employee creation before assertions: required department absent |
| Architecture suite + authorization engine + EnterpriseAuditService tests | **178 passed**, 20.01s; `.r7a_guards.log`. GU1's declared exceptions still apply; not a clean-layering certificate |
| New Action Center fan-out and Approval recipient characterizations | **3 passed**; `.r7a_characterization_new.log`. Measured 5/50 baseline calls and foreign binding inclusion |
| Live PostgreSQL new governance characterization + existing R5H security suite | **24 passed**, 3.49s; `.r7a_postgresql.log`. Fresh Alembic schema; runtime app_runtime NOSUPERUSER/NOBYPASSRLS/nonowner with real session context |
| PostgreSQL detail | Ten new cases: runtime role, three forced-policy tables, four real exclusions, raw foreign comment vs scoped Reader, deleted comment projection. Fourteen existing role/scope/parent-bypass/CAS cases retained |
| PostgreSQL first attempt | 10 passed / 14 fixture errors due to imported module-scoped fixture seeding duplicate IDs. Fixed only the new test fixture to own r7a-prefixed records; rerun above green. No production/migration defect masked |
| QML lint | Six inspected surfaces: OverviewWorkspace, NotificationsPanel, NotificationBell, CollaborationWorkspacePage, ApprovalDecisionDialog, ControlApprovalDetailPage; exit 0 with all shared/shell/platform/PM import roots; `.r7a_qmllint.log` empty |
| Static quality | New tests scoped Ruff F/I and compilation required green before final report; final result recorded below |

Characterizations asserting unsafe current behavior are deliberately labeled as such.
Their green status proves the audit finding, not a completed remediation. Replace
their expectations in R7B/D/E; never keep insecure behavior for compatibility.
Runtime PostgreSQL evidence is not a blanket proof of approval project grants or
notification recipient RLS: those remain findings and phase exit gates.

Reproduction: pmenv Python; `PM_RUN_POSTGRES_INTEGRATION=1`; existing Docker
PostgreSQL on port 55432, dedicated project_manager_r5h test database. The existing
fixture resets only that database schema, runs migrations as migration owner, and
executes runtime evidence through app_runtime. No installation or second stack.
Ignored `.r7a_*.log` files contain local outputs; tracked tests and these counts are
the durable audit record. Do not require local log files for CI.

### Existing Whole-Product Caveats Reclassified, Not Repaired

R6's recorded final PM result remains **2548 passed / 15 failed / 2 skipped**.
R7A did not rerun the whole PM suite because production behavior is unchanged.
The historical failures remain required-department fixture failures, not evidence
that authorization should accept incomplete Employee records.

- Four PM Action Center contributor failures are now directly relevant to R7
  identity/action correctness. Reproduced here; repair fixtures in R7D and then
  execute their actual assertions.
- Two Mine-resource and five resource-Timesheet failures are adjacent identity/Time
  boundary coverage. Track with R7D identity parity; do not hide them as unrelated
  if those paths change. They were not independently rerun in this audit selection.
- Four calendar/employee failures remain inherited calendar fixture work, outside
  R7 unless an implementation actually touches that dependency.

Repository-wide Ruff baseline remains **58 F/I findings**, not clean. New R7A import
formatting finding was fixed. The Global Overview undefined ActivityRowViewModel
annotation/export (two findings) intersects R7D; the approval test's unused req1 is
test hygiene, not proof of a broken decision path. Other inherited findings are not
automatically R7 blockers. Do not reopen R6 or perform global lint cleanup here.

## R7A Exit Decision

Authority, scope, concurrency, read boundedness, identity, queue distinctions,
optional-module boundaries and cleanup candidates are mapped above. Security gaps
are recorded as gaps, not mislabeled as certification. The chosen architecture is
minimal extension of existing Approval plus canonical Readers and existing durable
events, not a generic workflow engine.

R7A COMPLETE. R7 GOVERNANCE / COLLABORATION ROADMAP ESTABLISHED.
R7B requires a subsequent instruction. R6 remains closed. R8 is not started.
