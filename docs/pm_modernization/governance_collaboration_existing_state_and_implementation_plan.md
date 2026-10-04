# Governance and Collaboration: Existing State and R7 Implementation Plan

## Status and Scope

Audit date: 2026-09-30. R7A is COMPLETE as a characterization and roadmap phase.
R7 itself is OPEN. R7B and R7C are COMPLETE; implementation and verification are recorded below.
The approved R7C brief supersedes the original phase numbering: R7C is Action
Center bounded reads/eligibility consistency. The original broader Approval
lifecycle proposal is deferred, not implicitly certified by this closure.
R7D is now IN PROGRESS under the approved Durable Notifications / Deduplication /
Delivery Reliability brief. R7D is not complete and R7E has not started.
The R7A findings below are historical characterization, not current acceptance behavior.
R5 and R6 remain CLOSED; their historical evidence is unchanged. R8 has not started.
Only this document and three characterization test files were added in R7A.
No production implementation, schema change, operational module, or commit was made
by the R7A audit agent. Concurrent team package moves are preserved, not reverted.

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
surfaces must not present it as a live comment. The approved R7B scope brings tombstone/redaction
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
Timesheet periods have versioned transitions but no resource/period unique index
in the inspected ORM or fresh-schema migration. Existing period lookup is not a
database uniqueness guarantee; initial-period creation races need characterization
if R7 changes that identity boundary, without reopening the closed R5 phase.

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
| timesheet_periods / Platform Time | Nullable tenant/org FKs + Resource FK and period dates | version CAS, status/decision metadata; resource/period lookup has no corresponding unique index in inspected schema; lifecycle history not a generic Approval row | TENANT_AND_ORGANIZATION; TS1 + PM review Reader |
| time_entries / Platform Time | Tenant/org + work allocation/assignment and owner context | version, editable only under permitted period lifecycle; Time owns work evidence | TENANT_AND_ORGANIZATION; Time service, not an Action Center store |
| documents / document_structures / Platform | Tenant/org FKs; structure/document relationships and uploader User FK | version; organization/code unique; is_active/current/revision metadata; mutable content metadata, not automatically immutable evidence | TENANT_AND_ORGANIZATION; Document service/repositories |
| document_links / Platform | Org FK + document FK cascade; polymorphic module/entity link | Unique document/module/entity/type/role; nullable role needs duplicate semantics review; no version; target scope not enforced by polymorphic FK | INTENTIONAL_RLS_EXCLUSION; document integration helpers |
| register_entries / PM | Project FK, human owner_name, due date | version; project/code unique; status and notes remain register domain; no automatic reminder/SLA | INTENTIONAL_RLS_EXCLUSION; Register service/Reader |
| projects, tasks, resources, project_resources, task_assignments / PM | Project/resource membership and task ownership, not User assignment | Existing versioned operational aggregates; do not add quantities to Finance amounts | Projects/resources direct tenant+org; tasks/membership/assignments parent-scoped RLS; existing operational services |
| role_bindings / user_tenants / users / roles / Platform Identity | Auth bootstrap/effective scoped permissions and membership, not reviewer queue tables | Grant expiry/revocation and principal identity; retain canonical RBAC | Intentional auth-bootstrap exclusions in DB1; authorization engine/identity services |
| role_delegation_policies / Platform Authorization | Role-grant authority policy | Security administration, NOT substitute approver lifecycle | Intentional auth-bootstrap exclusion; do not reuse as workflow delegation |
| platform_time_financial_outbox, inventory_procurement_financial_outbox, project_finance_inbox_receipts, project_accounting_outbox and Finance handoff/delivery/outcome evidence | Tenant/org plus source/destination/project correlation under existing R6 contracts; the Procurement-named table is a neutral integration boundary, not an operational module | Durable identities, dedup, leases/versions and immutable evidence as defined by R6; operator history, not chat | Existing direct tenant+org classifications; generic IntegrationOutboxService/IntegrationInboxService operate through their contracts, not separate tables named integration_outbox/integration_inbox |
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

- Approved scope supersedes the broader R7A proposal: GOV-01, comment protection in GOV-02, and GOV-03 only.
- Authority: persisted Approval request scope and effective recipient grants; task/project ancestry and active collaboration grants for comment RLS.
- Scope: scoped Approval notification recipients, comment parent integrity/RLS, and deleted-content privacy across reads and downstream presentation.
- Non-goals: no workflow engine, new delegation, notification delivery feature or Finance redesign.
- Migration/deletion: replace unscoped recipient helper and unsafe characterizations; install comment policy and same-task reply FK. Generic approval target visibility/fallbacks and the existing allowlisted Platform repository/PM ORM dependency remain R7C contract work, not closed by B.
- PostgreSQL: runtime nonowner hostile tenant/org/project/parent SELECT/INSERT/UPDATE/DELETE tests, no context and foreign replies; independently test service/ORM authorization. Broader document-link hardening remains R7E.
- Concurrency: scope change/revoked membership between read and command; no cached authorization grants.
- UI: truthful unavailable/denied actions, no foreign count/payload/recipient leaks.
- Exit: scoped recipient matrix, comment RLS, privacy, concurrency, migration and quality gates green. This is not certification of unrelated excluded child tables.
- Dependencies: R7A only. No production implementation authorized by R7A itself.

### Deferred Approval Lifecycle Proposal (Original R7C Roadmap)

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

### R7C - Bounded Action Center and Eligibility Consistency (Approved Scope)

- Problem/evidence: GOV-05, AC2/AC3 and four blocked employee-fixture tests.
- Authority: neutral aggregator, business-specific Reader contracts; no persistent Action Center workflow table.
- Scope: SQL counts/top-N task and baseline contributors; effective identity parity; stable ordering across sources; context-safe subject navigation and stale-target handling.
- Non-goals: generic review queue, artificial due dates, global PM context changes, new optional-module contributors.
- Migration/deletion: replace full-list task/baseline contributor paths, superseded local sorting/filtering, undefined Global Overview ActivityRowViewModel export; repair four Action Center fixtures with required departments, not weakened Employee validation.
- PostgreSQL: query count/EXPLAIN at realistic project/task volume, hostile scope, exact summary/preview predicate parity.
- Concurrency: item disappears or permission revoked between preview and open; scope switch/late result cannot cross projects.
- UI: existing Global Overview links carry authorized target identity; keep noninteractive summary honest unless full destination is implemented deliberately.
- Exit: count and ordering equivalence, bounded service/SQL work, four existing Action Center tests green, context-switch/deep-link tests pass.
- Dependencies: R7B. Implemented evidence and the exact navigation scope follow below.

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
| Platform Approval's concrete ProjectORM dependency | Active architectural debt, not dead code; R7C target contract cutover then remove allowlist exception; outside the approved narrow R7B scope |
| Approval hasattr list/count scope fallbacks | Compatibility candidates; prove repository registration parity and remove in R7C |
| Full-list PM Action Center paths | Active but superseded by R7D bounded Reader; delete only after equivalent behavior/tests |
| Comment workspace raw deleted-body projection | Replaced in R7B by typed redacted facts; retained persistence is not ordinary collaboration content |
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
| Final combined regression after concurrent team package/fixture edits | **459 passed, 5 failed**, 99.55s; `.r7a_final_regression.log`. Four Action Center fixture failures now report `EmployeeService.create_employee() got an unexpected keyword argument 'user_id'`; the fifth is the ORM metadata source guard expecting the retired `orm.events.notifications.notification` import. This supersedes the earlier run as the current regression state; not a green architecture-suite claim |
| New Action Center fan-out and Approval recipient characterizations | **3 passed**; `.r7a_characterization_new.log`. Measured 5/50 baseline calls and foreign binding inclusion |
| Live PostgreSQL new governance characterization + existing R5H security suite | **24 passed**, 3.49s; `.r7a_postgresql.log`. Fresh Alembic schema; runtime app_runtime NOSUPERUSER/NOBYPASSRLS/nonowner with real session context |
| PostgreSQL detail | Ten new cases: runtime role, three forced-policy tables, four real exclusions, raw foreign comment vs scoped Reader, deleted comment projection. Fourteen existing role/scope/parent-bypass/CAS cases retained |
| PostgreSQL first attempt | 10 passed / 14 fixture errors due to imported module-scoped fixture seeding duplicate IDs. Fixed only the new test fixture to own r7a-prefixed records; rerun above green. No production/migration defect masked |
| QML lint | Six inspected surfaces: OverviewWorkspace, NotificationsPanel, NotificationBell, CollaborationWorkspacePage, ApprovalDecisionDialog, ControlApprovalDetailPage; exit 0 with all shared/shell/platform/PM import roots; `.r7a_qmllint.log` empty |
| Static quality | All three new test files pass Ruff F/I and Python compilation, including after the team's Global Overview package move. Repository-wide Ruff F/I: 92 findings in the final concurrent worktree, versus 58 at audit start. `git diff --check` and new-file whitespace checks pass. No production files modified by this audit |

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
  identity/action correctness. Initially reproduced as missing-department errors.
  Concurrent team fixture edits changed the final failure to obsolete `user_id`
  passed to EmployeeService.create_employee, in `_setup_user_employee_resource`
  at line 69. Repair fixtures using the canonical identity-link path in R7D and
  then execute their actual assertions; do not continue calling the current
  failures missing-department errors.
- Two Mine-resource and five resource-Timesheet failures are adjacent identity/Time
  boundary coverage. Track with R7D identity parity; do not hide them as unrelated
  if those paths change. They were not independently rerun in this audit selection.
- Four calendar/employee failures remain inherited calendar fixture work, outside
  R7 unless an implementation actually touches that dependency.

The final combined run also finds one new characterization guard mismatch after
the concurrent notification package move:
`src/tests/architecture/test_architecture_guardrails_legacy_orm.py:187`,
`test_orm_package_root_loads_all_model_packages`, expects
`src.core.platform.infrastructure.persistence.orm.events.notifications.notification`.
The production notification package was moved by the team; its old-path source
assertion is stale. Preserve the move; update that assertion as part of the team's
restructure validation, not by restoring a compatibility module. This is recorded
as a current architecture-test failure, not concealed in the R6 baseline or fixed
incidentally during an audit-only phase.

Repository-wide Ruff was **58 F/I findings** at audit start. Following concurrent
team package moves, the final run reports **92**: 38 I001, 45 F841, 5 F401, 2 F821,
1 F811 and 1 F822. The increase is 34 import-order findings; all other code counts
are unchanged. Logs: `.r7a_ruff_repository.log` and `.r7a_ruff_repository_final.log`.
Do not describe the final repository as lint-clean. The new R7A test import
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
R7B was subsequently authorized with the narrow security/privacy scope above.
R6 remains closed. R8 is not started.

## R7B Implementation and Closure Evidence

### Approval Recipient Authority

The retired `_list_users_with_permission` combined broad user/role discovery with
insufficient target scope. One repository projection now resolves recipient IDs
from the persisted request, ambient tenant/org, a verified project ancestry, active
human identity, active/non-revoked tenant membership, and active/non-expired scoped
role bindings. Reviewer grants require `approval.decide`; requester outcome notices
require `approval.request` or `approval.decide` and the persisted requester ID.
Tenant-wide grants intentionally cover their tenant; organization/project grants
must cover the request's exact organization/project. Platform-only/global grants
are not business-recipient membership. No new reviewer assignment or approval
decision policy was invented. Pending reviewer notices exclude the requester,
matching existing separation of duties.

SQL DISTINCT plus stable user-ID seek pagination produces unique recipients in
pages capped at 100. The service uses only this repository contract; obsolete
permission/role repository constructor dependencies and the broad helper are gone.
The live query-count test proves one SQL statement per page and rechecks revoked
membership on a subsequent resolution. This is dispatch-time eligibility, not a
durable notification/revocation delivery guarantee; that remains R7F.

### Comment Scope and Privacy

`task_comments` moves from intentional exclusion to the repository's existing
**parent-scoped RLS** taxonomy: task -> project -> tenant/organization. This is
tenant-and-organization ownership inherited from the canonical parent rather than
duplicated mutable child scope columns. Policy additionally requires an active
user/member and a non-revoked/non-expired effective collaboration grant covering
the parent project. PostgreSQL ENABLE/FORCE RLS uses the real transaction-local
`app.tenant_id`, `app.organization_id`, and `app.user_id` context. No context denies
access. RLS protects row scope; application command permissions/author checks
remain authoritative for edit/delete/reaction policy.

The composite reply FK `(parent_comment_id, task_id) -> (id, task_id)` prevents
cross-task replies even within the same project. Soft deletion is retained; no
destructive content purge or restore/admin authority was introduced. Migration
`a7b19c32d405` installs the constraint/policy and redacts old mention notification
body previews and navigation metadata. Downgrade restores the old FK/policy shape
but intentionally cannot reconstruct redacted notification content.

Workspace facts carry `is_deleted`/`deleted_at`, an empty body and no mentions.
Deleted rows retain their activity position but do not match body searches,
mention/unread counts, or author options. Desktop serializers render the tombstone
label and suppress attachments, linked documents, mentions and reactions. QML
receives no deleted body to reconstruct. Task document reads skip deleted comments.
Mention notifications contain generic text and no task/project/comment metadata;
they do not retain a separate private-content preview. Authorized contextual
notification deep links remain future R7D/F work.

Audit records preserve actor/scope/entity/action/time, not comment body. Existing
Activity intents carry IDs only. The current collaboration UoW installs audit but
not an Activity writer, so R7B does not claim a persisted Activity row per comment
operation or introduce one. Collaboration recent-activity facts are redacted.
Historical command persistence retains the body; it is not exposed by ordinary
Desktop/workspace reads and is not a new audit-content API.

### Transactions, Dependencies and Migration Prerequisites

Fresh operation UoWs retain commit ownership; comment mutation, audit and events
remain atomic, and user notifications remain after commit. Existing rollback,
repeated-delete and stale-revision proofs are retained. A live two-session test
loads an old revision, commits deletion elsewhere, rejects the stale writer, then
reads only a tombstone. Edit authorization now precedes disclosure of deletion or
revision status. No repository commits were added.

Attachment storage and clock are injected from composition, removing the touched
application's concrete infrastructure imports. No new attachment lifecycle or
delivery pipeline was implemented. The existing Platform repository ProjectORM
allowlist is unchanged, pending the R7C target-contract work.

Fresh PostgreSQL bootstrap exposed pre-existing employee migrations using a SELECT
alias in HAVING and rebuilding a referenced employee table. The prerequisite fix
uses `HAVING COUNT(*)` and native PostgreSQL unique-constraint/index alterations,
preserving incoming FKs and RLS. SQLite retains its established rebuild path. No
PostgreSQL installation, production DB reset or alternative test stack was added.

### Boundedness and Remaining Roadmap

Recipient filtering is SQL-side, one statement per capped page. Existing
collaboration query measurements stay at two comment statements (count/page),
four total query-path statements at both five and twelve projects, without new
per-comment queries. Task detail/thread list boundedness and mention-candidate
optimization remain explicitly R7E, not claimed solved by this privacy patch.

R7C retains Approval eligibility/lifecycle/target contracts; R7D bounded Action
Center/identity/deep links; R7E remaining collaboration/evidence lifecycle; R7F
durable in-app delivery; R7G/H integration and closure. None was started here.
Notifications, presence and document links retain their documented RLS exclusions;
comment certification must not be misreported as their certification.

### Final Verification and Exit Decision (2026-10-01)

All commands used conda `pmenv`. Counts below are separate selections and overlap;
they must not be summed as a unique suite total.

| Selection | Final result |
| --- | --- |
| PM, Platform and PM QML tests selected by `collaboration or task_comment or approval or mention_notifications or r7b` | 253 passed, 0 failed, 0 skipped; 3960 deselected |
| Live PostgreSQL `test_r7b_governance_security.py` plus existing `test_r5h1_postgresql_security.py` | 45 passed, 0 failed, 0 skipped |
| Architecture directory, PostgreSQL context guards and retained R7A Action Center characterization | 179 passed, 0 failed, 0 skipped |
| New privacy/API/migration tests plus collaboration rollback/full-modernization and Approval UoW tests | 54 passed, 0 failed, 0 skipped; subsequently covered by the final focused selection |
| Notification service/Desktop API/QML controller, priority/no-context repositories and initial service privacy selection | 39 passed, 0 failed, 0 skipped |

PostgreSQL ran against the existing dedicated Docker test database with fresh
Alembic bootstrap. Tests used `app_runtime`, asserting LOGIN, NOSUPERUSER,
NOBYPASSRLS and no protected-table ownership. Tests assert forced policies and
independently exercise raw SQL without ORM scope predicates. Covered denied
tenant/org/project reads, inserts, updates, deletes, foreign reply parents,
context absence, inactive/revoked/expired principals, exact recipient dedup,
revocation recheck, stale-edit-after-delete, and redacted search/count behavior.
SQLite service/Reader tests independently prove scope enforcement without RLS.
SQLite upgrade/downgrade/re-upgrade preserves the irreversible preview redaction.

Scoped Ruff F/I passes for all worktree Python changes and the earlier R7B
application/contracts/Reader/API/ORM/composition/manifest changes. `compileall -q
src` passes. QML lint passes for CollaborationWorkspacePage, OverviewWorkspace,
NotificationsPanel, NotificationBell, ApprovalDecisionDialog and
ControlApprovalDetailPage with the canonical import roots. No QML production
changes or visual redesign were necessary. Architecture/schema/RLS guards and
`git diff --check` pass. Retired recipient-helper search has no production hit.

Repository-wide Ruff is **not clean**: **90 F/I findings** (45 F841, 37 I001,
4 F401, 2 F821, 1 F811, 1 F822). This is down from the recorded 92 after fixing
the touched composition import block and unused import. Unrelated findings were
not swept into R7B. R7A's four obsolete Action Center employee-fixture failures
remain historical unresolved evidence, not rerun or claimed fixed here. Its stale
notification ORM-path guard was repaired and the architecture selection passes.
The full PM suite was not required or run for this scoped phase; R6 evidence is
unchanged.

Cleanup replaces unsafe R7A PostgreSQL expectations with the R7B security matrix
and removes the retired broad-recipient characterization/helper/dependencies.
There is one Approval recipient query and one canonical workspace comment Reader;
serializers perform defensive presentation redaction rather than calculate scope.
The existing transaction model and non-durable post-commit notification dispatch
are preserved, not represented as a new durable delivery guarantee.

**R7B COMPLETE.** The approved three security/privacy findings have implementation
and regression evidence. R7 remains OPEN; R7C has not started. R6 remains CLOSED;
R8, Action Center optimization and durable notification delivery were not started.
No future operational module was implemented. Concurrent team work was preserved;
the implementation agent made no commit.

## R7C Implementation and Closure - 2026-10-01

This section supersedes the original R7A sequencing and the historical R7B
statement that Action Center work had not started. R7C is the approved bounded
Action Center/eligibility phase, not the entire deferred Approval product redesign.

### Authority and Contributor Inventory

Action Center projects current actionable work. It is not persisted workflow,
Activity, Audit, Notifications, or Timesheet Review Queue. Two module-owned
contributors implement the neutral `ActionCenterContributor` contract:

| Owner | Action | Eligibility/source authority |
| --- | --- | --- |
| PM | Assigned open task | Active linked resource, non-declined assignment, open task state, scoped project/task permission |
| PM | Submitted baseline review | Submitted baseline, scoped baseline approval and project read authority |
| PM | Own open/rejected timesheet | Canonical Mine resource resolution, own-entry read/submit authority, rejected correction permission; no reviewer queue aggregation |
| Platform | Pending approval | Pending request, active human/membership, nonexpired/nonrevoked target-covered grant, valid project parent, requester excluded |

Platform recipient selection, Action Center approval reads, and decision-time
eligibility reuse the same SQL reviewer predicate. Approve/reject recheck this
predicate inside the fresh operation UoW after locking the request, before the
participant effect. Cached principal permissions alone cannot authorize a revoked
reviewer. Existing self-decision, terminal-state, participant and audit rollback
rules remain intact. The deferred broader Approval workspace/read-product work is
not replaced or certified here.

Canonical identity is `(module, kind, authoritative object ID)`. Open timesheet
identity is resource plus period start. EXISTS predicates prevent duplicate grants
and assignments from multiplying items/counts. Duplicate ownership across
contributors fails explicitly instead of silently inflating totals. UI activation
also matches kind and ID rather than ID alone.

### Bounded Read and Pagination Architecture

Desktop API -> GlobalOverviewService -> ActionCenterService -> contributor
contract -> module SQL Reader -> immutable facts. The aggregator has no module
ORM imports. Only top-level composition assembles concrete contributors and
cross-module parent-scope SQL. Generic ordering/seek SQL lives under
`src/core/global_overview/infrastructure/persistence/reads`, as requested; it
contains no module table knowledge.

The requested page is capped at 100. Contributors supply at most page size plus
one candidates, with exact eligible SQL counts independent of the page. PM merges
four bounded source windows; aggregation never loads the full candidate set.
Counts use the same business/scope predicates as rows. Global keyset pagination
uses actual due date ascending, then undated timestamp descending, then stable
module/kind/ID ties. Microseconds, NULL timestamps, minimum timestamps and date
boundaries have SQL-versus-canonical-order regression coverage. No synthetic due
dates are introduced.

Cursors include user/tenant/org context and reject cross-context reuse. Paging is
a live query, not a frozen historical snapshot: completed actions disappear,
counts reflect current state, and explicit refresh restarts page one. The
controller owns Previous/Next cursor history. Failures remain errors, not empty
or zero-count successes. Request generations discard older reentrant/scope-switched
results, including errors and stale next-page cursors.

Timesheet open-month discovery is SQL GROUP BY with a correlated existing-period
exclusion. It no longer loads every entry date or queries each month separately.
The Action Center reuses this canonical month statement rather than recalculating
period eligibility. Baseline reads no longer enumerate projects; task reads use
assignment EXISTS rather than loading resource task collections.

### Optional Modules, Navigation and Invalidation

Composition accepts an absent PM service bundle and registers only Platform in
that case. An installed PM contributor rechecks current module accessibility
before reading. Accounting, Procurement, Inventory and Payroll are not required
contributors or operational dependencies.

Navigation uses `platform.workspace`/`control_approvals` and the canonical
`project_management.workspace` PM-local destinations. Tasks use the existing
task entity deep link. Baseline and time actions enter their owning workflow;
they do not silently change the pinned project or impersonate a resource.
There is no new direct baseline/period detail-route implementation in this phase.
Unknown retired workspace routes are not dispatched. Owning commands always
revalidate authority/state; a previously rendered row is not authorization.

A scoped adapter subscribes to committed contributor, identity, membership,
grant and entitlement invalidations. It refreshes Action Center and its attention
counts, not all Overview/Finance surfaces. Accounting transport hints do not
match. Scope replacement disposes the old subscriptions. Separate committed hints
are not discarded through a correlation-ID cache. Events trigger requery and are
never stored as Action Center truth. Durable Notifications remain deferred.

### Security, Performance and Cleanup Evidence

PostgreSQL tests use the existing dedicated integration environment and real
runtime tenant/org context. Runtime-role policy checks remain in its shared
fixture; no owner/superuser shortcut is used for tested reads or decisions.
Hostile users cover foreign tenant/org/project grants, disabled identity,
suspended membership, revoked/expired grants and missing authority. Independent
raw SQL verifies RLS hides foreign tenant/org requests. Corrupt/foreign project
parents fail closed through production composition's parent predicate.

Two concurrent reviewers use the real locking repository/eligibility predicate;
one pending outcome commits and the other loses eligibility. Application tests
prove revoked-after-read denial, completed-action removal and stale-command
rejection. Existing Approval UoW tests retain participant/audit/commit rollback
coverage.

At 10, 100 and 1,000 submitted baselines plus one Platform approval, a fixed
10-item page performs six SQL statements, and the next page performs six more.
Materialized candidates stay bounded and adjacent pages do not overlap. These
query-count figures specifically describe that fixture, not every resource/time
configuration. No speculative index or universal latency claim is made.

Removed/replaced: unbounded task/project-baseline contributor implementations,
full-date/per-month open-period discovery, unsafe R7A fan-out characterization,
obsolete employee `user_id` fixture setup, and undefined ActivityRowViewModel
annotation/export. Activity remains the shared ActivityItemViewModel contract.
Approval-related fixtures now use persisted appropriately scoped reviewers;
Finance regression fixtures preserve separation of duties rather than synthesizing
administrator identities. Distinct module summaries/activity reads are not
misclassified as duplicate Action Center authority.

### Verification and Exit

| Gate | Result |
| --- | --- |
| Action Center/API/controller/presenter/composition, Approval and Timesheet/Review Queue focused matrix | 164 passed |
| Affected cost/Finance participant, read-model and Desktop command fixtures | 47 passed |
| PostgreSQL R7C plus R7B security regression, including reviewer race | 49 passed |
| Architecture guards | 168 passed |
| Touched Overview QML lint | Passed, empty diagnostics |
| Scoped Ruff F/I | Passed |
| Python compilation | Passed |
| `git diff --check` | Passed |
| Repository-wide Ruff F/I | 80 findings; not repository-wide clean |

The repository-wide findings outside this cutover remain classified as existing
or concurrent work, not hidden by the scoped result. No schema migration was
introduced by R7C. No full PM-suite result is claimed for this targeted phase.

**R7C COMPLETE.** R7 remains OPEN. At this closure R7D required its own next-phase brief;
durable notification delivery and the remaining Approval/collaboration lifecycle
roadmap are not automatically started. R5/R6 remain CLOSED. R8 and future
operational modules were not implemented. Unrelated team work is preserved.
The implementation agent made no commit.

## R7D Current Implementation - 2026-10-03

The approved R7D brief authorizes durable in-app notification consumption, scoped
recipients, deterministic deduplication, retry/recovery, bounded reads and related
regressions. R7C remains closed. No durable Notifications closure is claimed by
the existing in-memory post-commit callbacks.

### Verified Starting Architecture (superseded by the current cutover)

- `NotificationService.dispatch` currently persists a randomly identified row and
  optionally commits a shared session. Channel fan-out is immediate; no concrete
  email/SMS/push adapter is registered in production composition.
- Approval requested/decided, task assignment and comment mention call the shared
  `safe_dispatch_notification` helper after the business transaction. Failures are
  logged/swallowed, so successful business commits can lose notifications.
- Tenant invitation issued/revoked originally used the same swallowing dispatch
  helper. Product correction: an invitee without application access cannot receive
  an in-app notification. R7D must not stage invitation bell work or open a
  cross-tenant notification visibility exception. Invitation delivery/onboarding
  is a separate out-of-app product concern; no SMTP or other transport is added here.
- `notifications` lacks organization/source-event/deduplication columns and a
  logical uniqueness constraint. Repository predicates currently scope by user
  only. These are outstanding security/schema gates, not fixed by UI generation
  checks or bounded list reads.
- R7B mention copy contains no comment body or private metadata. Preserve this;
  durable delivery must not create a deleted-content archive.
- Existing IntegrationOutbox/Inbox services provide transaction-neutral delivery,
  leases, retries and quarantine. Their current record/ORM contracts mandate
  organization scope (the record explicitly validates financial integration
  organization presence). Tenant-wide invitations cannot be forced into an
  arbitrary organization just to reuse that concrete schema. Reuse canonical
  delivery infrastructure with explicit scope support rather than introduce a
  competing business-event bus or weaken Finance scope validation.

### Implemented Hardening

- Notification list materialization is capped at 100 and ordered by
  `created_at DESC, id DESC`; zero requested rows returns none. Exact unread
  count remains SQL COUNT, independent of the bounded result size.
- Notification controller generations discard old-scope and superseded refresh
  responses before updating the badge/list. Read/read-all mutation responses from
  a previous scope cannot publish errors or refresh the new scope.
- Unexpected refresh exceptions clear loading and show a safe message rather
  than exposing a raw exception to QML.
- Regression tests cover equal-timestamp ordering, the hard cap, independent
  unread count, scope switches during count/list, reentrant refresh and stale
  mutation errors.

Initial targeted verification: 44 notification controller/service/Desktop API,
Approval notification and PM assignment/mention tests passed. Scoped Ruff F/I,
Python compilation and diff checks passed. This does not constitute durable
delivery, deduplication, migration or PostgreSQL certification.

### Current Durable Cutover And Remaining Certification

Approval and PM assignment/mention events now stage per-recipient durable work in
their source UoW. A local fresh-session worker inserts the notification and marks
work processed atomically, with database uniqueness on source event/kind/recipient,
bounded retry and poison quarantine. Direct post-commit notification helpers and
the unused channel contract were removed. Alembic installs the work table,
provenance/deduplication columns and forced PostgreSQL RLS for notifications and
work; runtime-role hostile-scope tests pass. A committed delivery emits a
recipient-only presentation hint; the shell bell subscribes for its signed-in
user and queues refresh to avoid reentrant reads. No business state is inferred
from a notification row.

Invitation events remain business facts but have no in-app notification policy.
In-app reads require an active tenant; the prior cross-tenant invitation exception
was removed from repository and RLS predicates. The existing invitation workflow
and token issuance remain intact, but actual invitation delivery outside the app
must be designed separately before customer onboarding. This is not a reason to
expose the notification bell to unauthenticated invitees.

Focused SQLite notification/controller tests, R7B/R7C security tests and the live
PostgreSQL notification RLS tests have passed during this continuation. Final
R7D certification still requires the full retry/crash/concurrency matrix,
bounded-volume/read query evidence, all relevant integration/architecture/schema
guards and the consolidated final regression run. R7D remains IN PROGRESS;
R7E/R8 have not started.

### R7D Approval Audience And Query Reconciliation - 2026-10-04

Platform Approval remains the reusable lifecycle, persistence, recipient-query,
and decision-eligibility boundary. Each Approval request persists its required
decision permission; Platform checks both that scoped permission and
`approval.decide` against current membership and role bindings. The PM module
owns the mapping of its 11 registered request types to action-specific grants:
baseline, dependency/constraint/leveling, budget, forecast, project cost,
financial change, and billing preparation. A future module must provide its own
mapping at registration, not add its approval vocabulary to Platform. A generic
`approval.decide` grant alone does not make a salesperson a baseline reviewer.

The same database eligibility predicate drives PM reviewer notification
selection, Action Center actions, decision commands, and the Control queue's
`can_decide` presentation. Delivery rechecks pending reviewer eligibility or
requester outcome authority before materializing delayed Approval work; stale
or revoked audiences are quarantined. The Control desktop page caps approval
rows at 500 and performs one set-based eligibility query for the page (not a
query per row or a first-200-only partial check). PM mention recipient lookup
likewise resolves active tenant members with current project-scoped
`collaboration.read` in one set-based query before staging per-recipient work.
Delayed mention delivery rechecks that grant and the live task/comment scope;
tenant membership alone does not authorize a mention notification.

Evidence: all 11 PM handler registrations match the PM permission map; 30
Approval view-invalidation tests and 31 PostgreSQL R7B security tests pass;
one PostgreSQL regression asserts a 300-ID approval page is checked in a
single Approval data query. A PostgreSQL mention regression covers authorized,
unauthorized and foreign-project delivery. This is audience hardening, not a claim
that the full R7D retry/concurrency/read-volume closure matrix has passed.
