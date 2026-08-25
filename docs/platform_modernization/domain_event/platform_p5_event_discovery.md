# Platform P5 Event Discovery

- Status: discovery only — no DomainEvent classes exist yet, no production code changed.
- Companion documents: [ADR-005](../../architecture_decisions/ADR-005-domain-events.md) (owns
  the taxonomy/semantics this discovery applies), [ADR-005 Execution
  Plan](../../architecture_decisions/ADR-005-execution-plan.md) (Phase 2B is what this document
  fills in with real evidence), [Platform Domain Event Implementation
  Plan](platform_domain_event_implementation_plan.md) (P5's own section references this
  document's slice recommendations).
- Scope: Platform only (`src/core/platform/`). PM/Inventory business vocabulary is explicitly
  out of scope except where needed to understand a Platform boundary (e.g. `ApprovalHandlerResult`
  crossing into module-owned participants).
- Method: three parallel, read-only investigations (Organization/Sites/Departments/Parties;
  Access/RBAC/Auth/Modules; Employee/Document/Calendar) plus first-hand analysis of Approval
  (already deeply inspected during P4 Steps 1-2), each tracing every real
  `domain_events.<signal>.emit(...)` call site to its enclosing method, not sampling.

## 1. Platform Mutation Inventory

Every method found to emit one of the 11 Platform-scoped legacy signals
(`organizations_changed`, `sites_changed`, `departments_changed`, `parties_changed`,
`employees_changed`, `documents_changed`, `calendars_changed`, `access_changed`, `auth_changed`,
`modules_changed`, `approvals_changed`), with its real operation, entity, scope source, and
transaction owner. All still run on the shared, process-lifetime `Session` (unmigrated — P4 only
cut over `ApprovalService`).

### Organization (`organization_service.py`, `platform_runtime_service.py`)

| Method | Real operation | Scope source | Audit | File:line |
|---|---|---|---|---|
| `create_organization` | Create a new organization | `tenant_id` from active-tenant context (correct — an org has no parent org to read scope from) | Staged atomically, `commit=False` | `organization_service.py:136-195` |
| `update_organization` | Generic multi-field update (code/name/timezone/currency/is_active) | same | Staged **after** `session.commit()` — a pre-existing, unrelated atomicity gap | `organization_service.py:197-272` |
| `set_active_organization` | Activate one org, implicitly deactivate all sibling orgs in the tenant | same | Staged atomically | `organization_service.py:274-319` |
| `PlatformRuntimeService.provision_organization` | Composite: create + provision module entitlements + optional activation, one outer commit | tenant from session context | Delegated to sub-calls | `platform_runtime_service.py:200-247` |

**Gap found:** `_deactivate_other_organizations` (`organization_service.py:327-333`) silently
flips sibling orgs' `is_active=False` without emitting anything for those siblings — only the
"winning" org's ID is signaled today.

### Site / Department / Party (`site_service.py`, `department_commands.py`, `party_service.py`)

All three: `create_*`/`update_*` only — generic CRUD, no dedicated lifecycle methods (e.g. no
`close_site`/`reopen_site`; open/closed dates are just fields on the generic update).
`organization_id` correctly comes from "currently active organization" context — **not a scope
violation** here, since these entities are only ever created/updated *within* whatever
organization is active; there is no separate "target organization" they could belong to instead.
Audit staged atomically in all cases. File:line: `site_service.py:211,326`;
`department_commands.py:106,217`; `party_service.py:204,306`.

### Employee (`employee_service.py`)

| Method | Real operation | File:line |
|---|---|---|
| `create_employee` | Create employee record | `:145` (emit), logic `73-146` |
| `update_employee` | Generic field update incl. `is_active` — no dedicated deactivate/reinstate method | `:251` (emit), logic `148-252` |

Also emits `resources_changed` (a PM-owned signal, out of scope here) for linked resources,
deliberately sequenced **after** `session.commit()` to avoid firing for rows that could still
roll back.

### Document (`document_service.py`, `document_integration_service.py`) — 9 sites, confirmed exhaustively

| File:line | Method | Real operation |
|---|---|---|
| `document_service.py:178` | `create_document_structure` | Document folder/category structure created |
| `document_service.py:271` | `update_document_structure` | Structure updated |
| `document_service.py:362` | `create_document` | Document uploaded |
| `document_service.py:492` | `update_document` | Document metadata updated |
| `document_service.py:557` | `add_link` | Document linked to an entity (direct API) |
| `document_service.py:592` | `remove_link` | Document unlinked (direct API) |
| `document_integration_service.py:164` | `register_entity_attachments` | Bulk document creation via entity-attachment registration (integration path) |
| `document_integration_service.py:270` | `link_existing_document` | Existing document linked (integration path) |
| `document_integration_service.py:328` | `unlink_existing_document` | Document unlinked (integration path) |

Confirms the earlier Platform audit's finding precisely: at minimum **4 distinct fact families**
(structure lifecycle, document lifecycle, link lifecycle, integration-attachment lifecycle), not
one coarse "documents changed."

### Calendar — **zero production emitters**

`calendars_changed` appears in exactly two places in the whole repository: its own field
definition in `domain_events.py`, and the composite QML binder that subscribes to it. Nothing
under `src/core/platform/application/time_management/calendar/` (definitions or assignment) ever
emits it. **It is wired for consumption but structurally dead.**

### Access / RBAC (`access_control_service.py`)

| Method | Real operation | Scope source | File:line |
|---|---|---|---|
| `assign_scope_grant` | Grant a scoped access role (project/site/storeroom) to a user | `tenant_id` from `_require_active_tenant_id()` — **ambient active-tenant, no organization_id captured at all** | `:153-198` (emit `:196`) |
| `remove_scope_grant` | Revoke a scoped access role | same ambient-scope issue | `:200-229` (emit `:228`) |

Payload for both is a bare `normalized_scope_id` string — no `user_id`, `scope_type`, or
`role_name` in the emitted event itself. **This ambient-scope derivation is a real ADR-005 §3
violation as it stands** (ADR-005: never derive `organization_id` from mutable active-session
state) and must be fixed as a prerequisite before this becomes a typed `DomainEvent`, not
carried forward.

### Auth (`auth_changed`) — 23 producer sites across ~12 distinct real facts, confirmed exhaustively

The widest, most over-collapsed signal in the codebase. Real distinct operations found:

| Real fact | Method(s) | File:line | Audit mechanism |
|---|---|---|---|
| Role binding assigned / revoked | `assign_role_binding` / `revoke_role_binding` | `role_governance_service.py:375,423` | `record_audit_entry`-shaped |
| Custom role updated / retired | `update_custom_role` / `retire_custom_role` | `tenant_role_administration_service.py:260,336` | present |
| Bulk role-policy reconciliation applied | `apply()` | `role_policy_reconciliation_service.py:217` | present |
| Tenant membership: invitation accepted, suspended, reactivated, removed | `_accept_membership`, `suspend_member`, `reactivate_member`, `remove_member` | `tenant_membership_service.py:273,325,347,384` | real, dedicated audit |
| Session policy changed / sessions revoked | session-policy update, `revoke_user_sessions` | `session_service.py:142,185` | **`add_atomic_security_audit`** — a separate, dedicated security-audit mechanism |
| Account activated/deactivated, profile updated, unlocked | `set_user_active`, `update_user_profile`, `unlock_user_account` | `user_admin_service.py:147,197,232` | likely security-audit pattern |
| Registration / bootstrap | `register_user`/`onboard_tenant_user`, initial admin bootstrap | `registration_service.py:316`, `bootstrap_service.py:99` | not inspected in depth |
| Password changed / force-reset / reset | `change_password`, `force_user_password_reset`, `reset_user_password` | `password_service.py:47,68,92` | `add_atomic_security_audit`, severity "high" |
| MFA enabled / disabled | (3 sites) | `mfa_service.py` | likely security-audit pattern |
| Federated identity linked | `link_federated_identity` | `federated_identity_service.py:97` | not inspected |
| Login success / failed login | `complete_successful_authentication`, `register_failed_login` | `authentication_transactions.py:245,298` | security-audit specific |

**Two independent audit mechanisms confirmed** — `record_audit_entry`/`EnterpriseAuditService`
(general Platform audit) vs. `add_atomic_security_audit` (security-specific, used throughout
`security/auth/*`). These must not be conflated into one "audit side effect" concept in the
matrix below.

### Modules / Entitlements (`module_catalog_mutation.py`)

| Method | Real operation | Scope source | File:line |
|---|---|---|---|
| `set_module_state` | License/enable/disable transition for one module, for the org implicit via `get_entitlement()` | organization ambient via "current organization" inside `get_entitlement` — **same ambient-scope concern as `access_changed`** | `:20-108` (emit `:104`) |
| `provision_organization_entitlements` | Bulk-provision licensed/enabled modules for an **explicitly specified** organization | `organization_id` is an explicit parameter — correct | `:110-203` (emit `:202`) |

**Gap found:** `provision_organization_entitlements` only emits `modules_changed` when the
provisioned org happens to be the *currently active* one — entitlement changes to any other
organization produce **no signal today** (silent under-notification, confirmed, not a false
positive). `set_module_state` shows genuine state-machine-shaped validation (license-before-enable
ordering, planned-module guards, lifecycle-status transitions) — the **strongest real
aggregate-invariant candidate** found in this whole discovery, though currently implemented as
plain service-method validation, not on a domain object.

### Approval (`approval_service.py`) — analyzed directly, not via fork (already inspected in full during P4 Steps 1-2)

| Method | Real operation | File:line |
|---|---|---|
| `request_change` | New governance request created (PENDING) | `approval_service.py:97` (transaction-owning branch) / `:159` (caller-owned branch) |
| `approve_and_apply` | Decision recorded AND module mutation applied, atomically, in one commit | `:296-330` |
| `reject` | Decision recorded (REJECTED), optional module-side reject participant runs | `:262-295` |

`ApprovalRequest` (`src/core/platform/domain/approval/approval_request.py:72`) is confirmed a
**plain, Pydantic-validated data object with no `.approve()`/`.reject()` methods** — every
transition is applied via direct field assignment inside `ApprovalService`
(`request.status = ApprovalStatus.APPROVED`, etc.), not on the domain object itself. It also
**has no `tenant_id` field** — only `organization_id`; tenant scoping is enforced entirely at the
repository/query layer via `TenantContextService`, never stored on the object. Both are real
prerequisite gaps for a properly typed, properly scoped event (§11, §13 below).

## 2. Legacy Signal Inventory (producer/consumer summary)

| Signal | Producers (real sites) | Consumers found | Timing | Tenant/org info available | Target replacement |
|---|---|---|---|---|---|
| `organizations_changed` | 4 | Composite admin binder; `settings_workspace_controller.py:124` | Post-commit (mostly) | Yes (tenant always; org = self) | DomainEvent (partial) + ViewInvalidation |
| `sites_changed` | 2 | Composite admin binder only | Post-commit | Yes (org = active-org context, correct) | ViewInvalidation only |
| `departments_changed` | 2 | Composite admin binder only | Post-commit | Yes (same) | ViewInvalidation only |
| `parties_changed` | 2 | Composite admin binder only | Post-commit | Yes (same) | ViewInvalidation only |
| `employees_changed` | 2 | Composite admin binder only | Post-commit | Yes (org = active-org context) | ViewInvalidation only (see §4) |
| `documents_changed` | 9 (4 fact families) | Composite admin binder only | Post-commit | Yes (org = active-org context) | Mixed — see §4 |
| `calendars_changed` | **0** | Composite admin binder only (dead wiring) | N/A | N/A | Obsolete — remove from bridge list at P7 |
| `access_changed` | 2 | `access_workspace_controller.py:237-240` (real, direct — **corrects the earlier Platform audit's "no confirmed subscriber" finding**) | Post-commit | **No** — ambient tenant, no org at all | Blocked on scope-derivation fix, then DomainEvent + ViewInvalidation |
| `auth_changed` | 23 (~12 facts) | `access_workspace_controller.py:237`; composite admin binder | Post-commit (mostly) | Mostly yes (per-fact varies) | Mixed — see §4 |
| `modules_changed` | 2 | `settings_workspace_controller.py:126`, `control_workspace_controller.py:200`, `access_workspace_controller.py:240` | Post-commit | Mostly yes; one ambient case | DomainEvent + ViewInvalidation |
| `approvals_changed` | 3 (request/approve/reject) | `control_workspace_controller.py:193`; **also** `project_management/controllers/collaboration/domain_event_binder.py:14` (a cross-module UI dependency on a Platform signal — noted for P6/P7, not designed here) | Post-commit | Yes (org); tenant missing from the domain object itself | DomainEvent + ViewInvalidation, gated on §13's prerequisites |

## 3. Business-Fact Classification

Legend: **A** domain event required · **B** useful but not currently required · **C** no domain
event · **D** view invalidation only · **E** notification/audit/integration concern, not a
DomainEvent.

| Candidate fact | Class | Rationale |
|---|---|---|
| `OrganizationCreated` | **A** | New organization existence is a fact other Platform behavior already reacts to (module-entitlement provisioning composes right after it); a natural creation-time application-authored event (no existing instance to record on yet). |
| `OrganizationActivated` | **B** | A real, invariant-backed transition (exactly one active org per tenant), but no current consumer needs to *react* to it beyond a UI refresh. Worth naming later once a real consumer exists; not required now. Sibling deactivation currently produces no fact at all — an open question for whoever implements this (§17). |
| Organization profile/settings update (name/timezone/currency/is_active via `update_organization`) | **D** | Generic multi-field CRUD, only ever consulted by a coarse UI refresh. Fails "does another part of the domain legitimately care" — ViewInvalidation directly, no event. |
| Site / Department / Party create & update (all 6 methods) | **D** | Same reasoning as the organization profile update — generic CRUD, single coarse UI-refresh consumer, no evidenced downstream business reaction. |
| `EmployeeHired`-shaped fact | **C** (`create_employee`) | The creation itself is *plausibly* meaningful (HR/payroll modules could care later), but nothing in Platform's own scope reacts to it today, and `payroll`/`hr_management` have zero current domain-event usage per the Execution Plan (Phase 4: "no migration needed yet"). Revisit when a real consumer exists — do not manufacture speculatively. |
| Employee generic update (incl. `is_active`) | **D** | Same as other generic-field updates; no dedicated lifecycle method exists to hang a real event on. |
| `DocumentStructureCreated` / `DocumentStructureUpdated` | **C** | Real, distinct operations, but no evidenced consumer beyond the coarse admin refresh; folder/category structure changes are not yet acted on elsewhere. |
| `DocumentUploaded` / `DocumentMetadataUpdated` | **C** | Same reasoning — distinct facts, no current downstream consumer. |
| `DocumentLinked` / `DocumentUnlinked` (direct API, `add_link`/`remove_link`) | **B** | Linking a document to an entity is a real cross-cutting fact (e.g. a future "this project has N supporting documents" indicator) — plausible future consumer, not required today. |
| `DocumentAttachmentRegistered` / integration-path link/unlink | **E** | These are the *integration* boundary's own concern (bulk attachment registration used by other modules' integration flows) — belongs with ADR-PF-011's boundary discussion if/when it durably crosses a process boundary, not a new in-process DomainEvent duplicate of the direct-API facts above. |
| Calendar (any) | **C** | No producer exists at all; nothing to classify until a real calendar-mutation code path is written. |
| `ScopeAccessGranted` / `ScopeAccessRevoked` | **A**, blocked | Genuinely meaningful (compliance/audit, permission-cache invalidation, user notification are all plausible real consumers) — but blocked on fixing the ambient-tenant/no-organization scope-derivation bug and enriching the payload (user_id, scope_type, role_name) before it can become a properly-scoped `DomainEvent`. See §17. |
| `RoleAssignmentGranted` / `RoleAssignmentRevoked` | **A** | Real, meaningful, tenant-scoped security-relevant facts with a plausible permission-cache/notification consumer. |
| `CustomRoleUpdated` / `CustomRoleRetired` | **B** | Meaningful admin action; no current consumer beyond refresh, but distinct enough to name once one exists. |
| Bulk role-policy reconciliation applied | **C** | A background/admin batch operation; the useful facts are the underlying per-binding grants/revocations (already covered above), not a synthetic "a reconciliation ran" event. |
| `TenantMembershipActivated` (from invitation accepted) / `TenantMembershipSuspended` / `TenantMembershipReactivated` / `TenantMembershipRemoved` | **A** | Real lifecycle facts — notification and access-cascade behavior plausibly depend on exactly these transitions. |
| Session policy changed / sessions revoked | **E** | Security-operational, already served by `add_atomic_security_audit` — not a general business fact other domain code reacts to. |
| `UserAccountActivated` / `UserAccountDeactivated` | **B** | Real, meaningful state, but no current consumer beyond refresh; keep named for later. |
| User profile updated | **D** | Generic field update, UI-refresh only. |
| `UserAccountUnlocked` | **E** | A security-remediation action already covered by the security-audit mechanism; not evidenced to need general-domain reaction. |
| User registration / onboarding | **B** | Plausibly useful (welcome notification, default provisioning) but not proven required by any current consumer; bootstrap (first admin) explicitly excluded — one-time startup concern, not a recurring business fact. |
| Password change/reset, MFA enable/disable, federated identity link, login success/failure | **E** (all) | Security-audit-shaped facts already served by `add_atomic_security_audit`/dedicated security recorders. Making these DomainEvents would duplicate an existing, correct mechanism and blur ADR-005 §1's Domain-Event/Audit-Record boundary. |
| `ModuleLicensed` / `ModuleEnabled` / `ModuleDisabled` (exact names pending confirmation against `set_module_state`'s real transition set — see §17) | **A** | The strongest aggregate-invariant candidate found: real state-machine validation, and other Platform behavior (feature gating elsewhere) plausibly depends on exactly this fact. |
| `ApprovalRequested` | **A** | A new governance request existing is exactly the kind of fact other application behavior (notification, UI inbox) already reacts to. |
| `ApprovalApproved` | **A** | Distinct, consequential fact — approval leads to real module-mutation application. |
| `ApprovalRejected` | **A** | Distinct, consequential fact — the opposite outcome, no module mutation applied. |
| `ApprovalApplied` | **Rejected — not a separate fact** | ADR-PF-008's design makes approval-and-apply one atomic operation; there is never a persisted "approved but not yet applied" state (a failed apply rolls back the whole transaction, including the decision). A separate `ApprovalApplied` event would be redundant UI-flavored vocabulary describing the same atomic fact `ApprovalApproved` already names. |

## 4. Proposed Minimal DomainEvent Vocabulary

Ten events, all Class A, none manufactured from a UI-signal name mechanically:

1. `OrganizationCreated`
2. `ScopeAccessGranted`
3. `ScopeAccessRevoked` (both blocked on the scope-derivation prerequisite, §17)
4. `RoleAssignmentGranted`
5. `RoleAssignmentRevoked`
6. `TenantMembershipActivated`
7. `TenantMembershipSuspended`
8. `TenantMembershipReactivated`
9. `TenantMembershipRemoved`
10. `ModuleLicensed` / `ModuleEnabled` / `ModuleDisabled` (module entitlement state transitions — exact split pending §17)
11. `ApprovalRequested`
12. `ApprovalApproved`
13. `ApprovalRejected`

(Numbered list runs to 13 individual event *types* across the "10 events" worth of business
facts — `ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled` are one fact-family with three
transition names, matching the "specific fact naming" rule rather than one generic
`ModuleStateChanged`.)

Class B candidates (`OrganizationActivated`, `CustomRoleUpdated`, `CustomRoleRetired`,
`UserAccountActivated`, `UserAccountDeactivated`, user registration, `DocumentLinked`/
`DocumentUnlinked`) are **named but deliberately deferred** — not implemented in P5's first
slices, revisited once a real consumer exists.

## 5. Rejected Event Candidates and Why

- **Every mechanical `<X>_changed` → `<X>Changed` translation** (`OrganizationsChanged`,
  `AccessChanged`, `ModulesChanged`, `ApprovalChanged`, etc.) — rejected outright per this
  document's own mandate; none of these name a business fact, all describe "a screen might be
  stale," which is exactly ViewInvalidation's job, not a DomainEvent's.
- **`ApprovalApplied`** — redundant with `ApprovalApproved` (§3).
- **Bulk role-policy reconciliation as its own event** — the real, useful facts are the
  individual grants/revocations it produces, already covered by `RoleAssignmentGranted`/`Revoked`.
- **Password/MFA/login/session-security operations as DomainEvents** — already correctly served
  by the separate, dedicated security-audit mechanism (`add_atomic_security_audit`); promoting
  them to DomainEvent status would duplicate a working mechanism and blur the Domain-Event/
  Audit-Record boundary ADR-005 §1 already draws.
- **Generic multi-field "update" methods as events** (Organization/Site/Department/Party/
  Employee/User-profile) — fail the "does another part of the domain legitimately care" test;
  classified D, served by direct ViewInvalidation with no DomainEvent at all.
- **A synthetic "DocumentAttachmentRegistered" duplicating the direct-API link/unlink facts** —
  the integration-path sites are the same underlying fact reached via a different entry point;
  do not double the vocabulary for one business fact just because it has two call paths.
- **Calendar events of any kind** — no producer exists; inventing vocabulary for code that
  doesn't run yet would be pure speculation.

## 6. Scope Model Per Event

| Event | Scope | Tenant source | Organization source |
|---|---|---|---|
| `OrganizationCreated` | Organization-scoped | Active-tenant context (correct — no parent) | The new organization's own id |
| `ScopeAccessGranted`/`Revoked` | Organization-scoped (**currently broken** — see §17) | Must be read from the grant's own target scope, never ambient active-tenant | Must be added — currently absent entirely |
| `RoleAssignmentGranted`/`Revoked` | Tenant-scoped (roles are tenant-level constructs here) | From the role binding itself | N/A — not organization-scoped by this codebase's role model |
| `TenantMembership*` (4 events) | Tenant-scoped | From the membership record | N/A |
| `Module*` (3 events) | Organization-scoped | From the entitlement record | From the entitlement record (already explicit for `provision_organization_entitlements`; `set_module_state` needs to stop reading "current organization" ambiently and take it explicitly — see §17) |
| `ApprovalRequested`/`Approved`/`Rejected` | Organization-scoped | **Missing on the domain object today** — must be resolved at construction time, not read from mutable session state (§17) | `ApprovalRequest.organization_id` (already present and already correctly non-ambient — read from the entity/command, not session state) |

Every organization-scoped event above must resolve `tenant_id`/`organization_id` from the
mutated entity/command at the point of construction — never from `TenantContextService`'s
"currently active" state, per ADR-005 §3's explicit rule. Two of the six event families
(`ScopeAccessGranted`/`Revoked`, `Module*`'s `set_module_state` half) currently violate this and
must be fixed before typing, not carried forward as-is.

## 7. Field Model Per Event

Minimal business-fact fields only — no `correlation_id`/`causation_id`/`command_id`/
`schema_version` (owned by `DomainEventContext`/ADR-PF-011's envelope, never duplicated here).

- `OrganizationCreated`: `tenant_id`, `organization_id`, `name`, `code`, `occurred_at`.
- `ScopeAccessGranted`: `tenant_id`, `organization_id`, `scope_type`, `scope_id`, `user_id`,
  `role_name`, `occurred_at`.
- `ScopeAccessRevoked`: same shape minus nothing — a full mirror of Granted.
- `RoleAssignmentGranted`/`Revoked`: `tenant_id`, `role_id`, `principal_type`, `principal_id`,
  `occurred_at`.
- `TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed`: `tenant_id`, `user_id`,
  `occurred_at` (+ `reason`/`note` only if the underlying command actually carries one — verify
  during implementation, do not invent a field the command doesn't have).
- `ModuleLicensed`/`Enabled`/`Disabled`: `tenant_id`, `organization_id`, `module_code`,
  `occurred_at`.
- `ApprovalRequested`: `tenant_id`, `organization_id`, `request_id`, `request_type`, `entity_type`,
  `entity_id`, `project_id`, `requested_by_user_id`, `occurred_at`.
- `ApprovalApproved`/`Rejected`: `tenant_id`, `organization_id`, `request_id`, `request_type`,
  `entity_type`, `entity_id`, `decided_by_user_id`, `occurred_at` (+ `decision_note` for Rejected
  only, matching the existing domain object's own field).

## 8. Recording Location Per Event

| Event | Recording mechanism | Why |
|---|---|---|
| `OrganizationCreated` | Application-authored (`uow.record_event(...)` from `OrganizationService`) | Creation facts have no prior instance to record on themselves — this is the normal, correct home for a creation event, not a workaround (ADR-005 §6's aggregate-recording rule is about *transitions on an existing entity*, not construction). |
| `ScopeAccessGranted`/`Revoked` | Application-authored, from `AccessControlService` | `ScopedAccessGrant` is a persistence-shaped record with no self-recording method; no aggregate exists to record on today (§12's honesty requirement). |
| `RoleAssignmentGranted`/`Revoked` | Application-authored, from `RoleGovernanceService` | Same — `RoleBinding` is a plain record, no aggregate methods exist. |
| `TenantMembership*` | Application-authored, from `TenantMembershipService` | Same — `UserTenantMembership` is a plain record. |
| `Module*` | Application-authored, from the module-catalog mutation mixin | Same, **despite** this being the strongest aggregate-invariant candidate found — the state-machine logic lives in the *service* today, not on a domain object; recording stays application-authored until/unless that logic is relocated onto an entity (out of this discovery's scope to decide). |
| `ApprovalRequested`/`Approved`/`Rejected` | **Blocked pending a decision** — see §17. ADR-005's preferred answer is aggregate-recorded (these are genuine transitions on an *existing* `ApprovalRequest`, not a creation), which requires `ApprovalRequest` to first gain real `.approve()`/`.reject()` methods (currently: bare field assignment inside `ApprovalService`). The pragmatic interim alternative is application-authored via `uow.record_event()`, explicitly flagged as temporary. |

**No event in this discovery uses `uow.record_event()` merely because modifying an entity would
be more work.** Every application-authored recommendation above is because the entity has no
aggregate methods to record on *at all* today (§12) — a fact, not a convenience.

## 9. Event → Invalidation Matrix

| Event / committed operation | Scope | ViewInvalidation target(s) | Legacy signal replaced | Current consumer(s) | P5 producer location | P5 mapper/handler location | P6 Qt consumer (later) | P7 removal condition |
|---|---|---|---|---|---|---|---|---|
| `OrganizationCreated` | `OrganizationScope(tenant_id, organization_id)` + `TenantWide(tenant_id)` (org list is tenant-wide) | organization list, organization details | `organizations_changed` | composite admin binder; `settings_workspace_controller.py:124` | `OrganizationService.create_organization` | `application/master_data/organization/event_handlers/view_invalidation.py` (new) | shared Qt adapter (P6) | once both consumers migrate off `organizations_changed` |
| Organization profile update (no event) | n/a | organization details | `organizations_changed` | same | `OrganizationService.update_organization` calls `ViewInvalidationChannel.notify(...)` directly, no DomainEvent | same | same | same |
| Site/Department/Party create+update (no event) | `OrganizationScope` | site/department/party list+details | `sites_changed`/`departments_changed`/`parties_changed` | composite admin binder only | direct `ViewInvalidationChannel.notify(...)` calls in each service | n/a (no mapper needed, no event) | shared Qt adapter | once binder migrates |
| `ScopeAccessGranted`/`Revoked` | `OrganizationScope` (once fixed) | access/RBAC workspace's grant list | `access_changed` | `access_workspace_controller.py:237` | `AccessControlService` | `application/access/event_handlers/view_invalidation.py` (new) | shared Qt adapter | once controller migrates |
| `RoleAssignmentGranted`/`Revoked` | `TenantScope(tenant_id)` | role/permission workspace | `auth_changed` (partial) | `access_workspace_controller.py:237`; composite binder | `RoleGovernanceService` | `application/security/authorization/event_handlers/view_invalidation.py` (new) | shared Qt adapter | once both consumers migrate |
| `TenantMembership*` (4) | `TenantScope(tenant_id)` | tenant membership/user-admin workspace | `auth_changed` (partial) | composite binder | `TenantMembershipService` | same package as above | shared Qt adapter | once binder migrates |
| `ModuleLicensed`/`Enabled`/`Disabled` | `OrganizationScope` | settings workspace, control workspace, access workspace (all three currently refresh on this) | `modules_changed` | `settings_workspace_controller.py:126`, `control_workspace_controller.py:200`, `access_workspace_controller.py:240` | module-catalog mutation mixin | `application/tenant/modules/event_handlers/view_invalidation.py` (new) | shared Qt adapter | once all three consumers migrate |
| `ApprovalRequested`/`Approved`/`Rejected` | `OrganizationScope` | approval inbox, approval details | `approvals_changed` | `control_workspace_controller.py:193`; **`project_management`'s own `domain_event_binder.py:14`** (cross-module — flag for P6/P7, do not fix now) | `ApprovalService` | `application/approval/event_handlers/view_invalidation.py` (new) | shared Qt adapter | once **both** consumers (including the PM-owned one) migrate |

One `OrganizationCreated` legitimately invalidates two targets at once (list + tenant-wide
summary); several distinct events (`TenantMembershipActivated`/`Suspended`/`Reactivated`/
`Removed`) all map to the same stale-read target (the membership list) — exactly the "not
one-to-one" relationship ADR-005 §12 anticipates.

## 10. Current QML Consumer Mapping

| Legacy signal(s) | Controller/binder | Refresh method | File:line |
|---|---|---|---|
| `organizations_changed`, `calendars_changed`, `sites_changed`, `departments_changed`, `employees_changed`, `auth_changed`, `parties_changed`, `documents_changed` | Composite admin-console binder (temporary, self-scheduled "R2" removal) | `controller._request_domain_refresh()` — one coalesced refresh regardless of which signal fired, no per-entity granularity | `src/ui_qml/platform/controllers/admin_console/domain_event_binder.py` (`bind_domain_events`, ~lines 21-36) |
| `modules_changed`, `organizations_changed` | `settings_workspace_controller.py` | same coalesced pattern | `:124-135` |
| `auth_changed`, `access_changed`, `modules_changed` | `access_workspace_controller.py` | same coalesced pattern | `:237-240` |
| `approvals_changed`, `modules_changed` (+ others) | `control_workspace_controller.py` | same coalesced pattern | `:193`, `:200` |
| `approvals_changed` | **`project_management`'s own** `collaboration/domain_event_binder.py` | PM's own refresh — a real, cross-module dependency on a Platform-owned signal | `:14` |

No consumer today reads per-signal payload content beyond "something in this bucket changed, go
re-fetch" — confirming ADR-005's own observation that every real consumer only ever decides
whether to call `refresh()`. QML itself is not modified by this discovery; P6 owns the shared
adapter design.

## 11. Integration / Audit / Notification Separation

- **Audit** stays exactly as today for every capability above — `record_audit_entry`/
  `EnterpriseAuditService` for general Platform mutations, `add_atomic_security_audit` for
  security-specific operations (login, password, MFA, session, account-lock). Neither becomes a
  DomainEvent; neither is replaced by one. `PlatformEvent` is not touched, not renamed, does not
  inherit `DomainEvent` (ADR-005 §19 already settled this as non-blocking/deferred).
- **Notification**: `ApprovalRequested`/`Approved`/`Rejected` are the clearest candidates where a
  post-commit DomainEvent handler *could* legitimately trigger `safe_dispatch_notification` (today
  it's called directly, inline, in `ApprovalService`) — noted as a future refinement, not required
  for P5 to land. No other candidate event in this discovery has an evidenced notification
  consequence worth wiring now.
- **Integration (ADR-PF-011)**: none of the 13 proposed events have a real, evidenced integration
  consumer today. `document_integration_service.py`'s two "integration path" emit sites (§1) are
  themselves just the *in-process* signal side of an integration-adjacent workflow, not an
  existing outbox producer — if a genuine cross-process need for, say, `OrganizationCreated`
  emerges later, the mapping is `DomainEvent → transactional IntegrationEvent mapping → Outbox →
  IntegrationEventEnvelope`, exactly as ADR-005 §11 already specifies; nothing here requires that
  mapping to exist yet.

## 12. Proposed P5 Capability Slices

### P5A — Organization

- Events: `OrganizationCreated` only (Activated deferred, Class B).
- Producer: `OrganizationService.create_organization`.
- Recording: application-authored (`uow.record_event`), per §8.
- Post-commit mapping: `OrganizationCreated` → `ViewInvalidationHint(scope=OrganizationScope(...))` for org details + `ViewInvalidationHint(scope=TenantScope(...))` for the org list.
- Tests: recorded exactly once per creation; no event on a rolled-back creation (e.g. duplicate-code conflict); context (`tenant_id`/`organization_id`) correct even when the acting user's "active organization" UI selector differs from the newly created org; no cross-tenant/cross-org invalidation leak (TO-1..TO-9 subset); legacy `organizations_changed` continues firing via a small bridge during this slice.
- Legacy compatibility: bridge `organizations_changed` for the 2 existing consumers until P6.
- Exit criteria: `OrganizationCreated` recorded and dispatched correctly; existing organization-creation tests unmodified and green; guardrail test green.

### P5B — Module Entitlements

- Events: `ModuleLicensed`, `ModuleEnabled`, `ModuleDisabled` (exact transition set confirmed against `set_module_state`'s real state machine during implementation — see §17).
- Producers: `set_module_state` (must stop reading organization ambiently first — a small, in-slice prerequisite fix, not a separate phase) and `provision_organization_entitlements` (already explicit).
- Recording: application-authored.
- Post-commit mapping: organization-scoped hint to settings/control/access workspaces (3 consumers).
- Tests: one event per real transition (not one per bulk-provisioned module silently skipped, per the fixed non-active-org gap); tenant/org scope correct for non-active-organization provisioning (this is the concrete regression test proving the fix); no event for a no-op state request.
- Legacy compatibility: bridge `modules_changed` for all 3 consumers until P6.
- Exit criteria: the silent non-active-org gap is closed and proven by a real cross-organization test; guardrail green.

### P5C — Access / RBAC (scope grants + role assignments)

- Events: `ScopeAccessGranted`, `ScopeAccessRevoked`, `RoleAssignmentGranted`, `RoleAssignmentRevoked`.
- **Prerequisite (in-slice, not separate):** fix `assign_scope_grant`/`remove_scope_grant`'s ambient-tenant/missing-organization scope derivation, and enrich the payload (`user_id`, `scope_type`, `role_name`) before typing the event — carrying the ambient-scope bug into a typed `DomainEvent` would enshrine an ADR-005 §3 violation.
- Recording: application-authored.
- Post-commit mapping: organization-scoped (grants) / tenant-scoped (role bindings) hints to the access workspace.
- Tests: correct organization derivation from the grant itself, not the active-session organization (this is the direct regression test for the fix); tenant-scoped role events never leak across tenants; legacy `access_changed`/`auth_changed` (partial) bridged during migration.
- Exit criteria: scope-derivation fix proven by a real cross-organization grant test; guardrail green.

### P5D — Tenant Membership

- Events: `TenantMembershipActivated`, `TenantMembershipSuspended`, `TenantMembershipReactivated`, `TenantMembershipRemoved`.
- Producer: `TenantMembershipService`.
- Recording: application-authored.
- Post-commit mapping: tenant-scoped hint to tenant-membership/user-admin workspace.
- Tests: one event per real transition; no event for `revoke_invitation` (confirmed to not emit `auth_changed` at all today — do not add one speculatively); tenant isolation proven.
- Legacy compatibility: bridge the relevant slice of `auth_changed` until P6.
- Exit criteria: all 4 transitions proven distinct and correctly scoped; guardrail green.

### Approval — explicitly NOT a P5 slice yet

Approval's events (`ApprovalRequested`/`Approved`/`Rejected`) are fully specified above (§3-§9)
but are **not** proposed as an immediate slice: `ApprovalRequest` first needs (a) a `tenant_id`
field (or an equivalent, non-ambient resolution path) and (b) an explicit decision on
aggregate-recording vs. application-authored recording (§8, §17) — both are small, well-scoped
prerequisites, but they are prerequisites, not this discovery's job to resolve. Once decided,
Approval slots in easily given P4's UoW work is already done.

## 13. Implementation Order

**P5A (Organization) → P5B (Module Entitlements) → P5C (Access/RBAC) → P5D (Tenant Membership) →
Approval (once its two prerequisites are separately resolved).**

Organization first because: clearest, cleanest business transition found (`OrganizationCreated`),
correctly exercises the multi-organization-per-tenant scope model without needing any
prerequisite bug fix first, only 2 UI consumers (small P6 blast radius), and requires no
unrelated domain refactoring. Module Entitlements second because it has the strongest real
aggregate-invariant shape found and closes a genuine, evidenced correctness gap (the
non-active-organization silent-skip). Access/RBAC third because it's real and valuable but
requires an in-slice prerequisite fix first (larger, riskier than A/B). Tenant Membership fourth
— real and clean, but its own slice rather than folding into Access/RBAC, keeping each slice
small per §27's "no big-bang P5" rule. Approval deliberately not placed in the initial sequence,
per this task's own explicit instruction not to default to it just because it was recently
touched — its prerequisites should be resolved as their own small, reviewed decision first.

## 14. Exact Files Expected Per Slice

Each slice, following the pattern ADR-005 §20/§1 and Phase P1 already established:

```text
src/core/platform/domain/<capability>/events.py          # new, typed events for that slice
src/core/platform/application/<capability>/event_handlers/
  view_invalidation.py                                    # ViewInvalidationHint construction
```

No `transactional.py` handler is expected for any of these four slices — none of the proposed
events feed a real cross-aggregate transactional reaction today (unlike the `TaskCompleted →
Project` example in ADR-005 §7); add one only if implementation reveals a genuine same-transaction
consumer, per §6's existing criteria.

## 15. Test Obligations Per Slice (per ADR-005 Test Impact / this task's §29 — no implementation now)

For every slice: event recorded exactly once per real transition; no event on rollback (a
deliberately failing variant of the mutation, e.g. a duplicate-code conflict, must produce zero
recorded events); `DomainEventContext.correlation_id` reaches the post-commit handler unchanged;
tenant-scope and organization-scope isolation (the relevant TO-1..TO-9/TO-13/TO-14 subset per
event's actual scope shape); no cross-organization or cross-tenant invalidation leak; dispatch
only after a successful commit, never after a rolled-back one; legacy-signal compatibility bridge
still fires during the slice's own transition window; no UI vocabulary anywhere in the event
class itself; no `IntegrationEvent`/outbox coupling introduced (none of these events map to one
yet, per §11).

## 16. Legacy Compatibility / Removal Gates

Per Round 8's pre-release, minimize-compatibility-lifetime principle: each slice adds a small,
explicit, dated bridge adapter translating its new event(s) into the one or two legacy signals it
replaces, removed as soon as that slice's own consumers migrate in P6 — not held open until every
other slice finishes. `calendars_changed` needs no bridge at all (nothing produces it); it can be
dropped from `DomainEvents`/the bridge spec list directly at P7 once confirmed still unused.
`documents_changed`/`auth_changed`'s *other* real facts not covered by P5A-D (document
lifecycle, password/MFA/session security, user registration) remain on the legacy mechanism,
untouched, until their own future slices are separately proposed — this document does not commit
to a timeline for those.

**P5A outcome (implemented, corrects this section's own "bridge adapter" default for
`organizations_changed` specifically):** tracing both real `organizations_changed` consumers
(admin console organization list, settings organization-profiles list) end-to-end found exactly
two, both reading a tenant-wide `list_organizations()`. Rather than the bridge-adapter default
above, both were migrated directly onto `ViewInvalidationChannel` (a Qt adapter,
`OrganizationViewInvalidationAdapter`, scoped only to the Organization slice — not a general P6
migration) since a temporary bridge would have been dead code immediately in a pre-release app
with exactly two, already-identified consumers. `organizations_changed` itself is **not**
removed — `update_organization`/`set_active_organization` still emit it directly and remain on
the legacy mechanism until their own event slice (not part of P5A) is proposed.

## 17. Unresolved / Blocking Questions

1. **`ApprovalRequest` has no `tenant_id` field.** Must be resolved (add the field, or a
   documented non-ambient resolution path) before any Approval event work begins.
2. **`ApprovalRequest` has no `.approve()`/`.reject()` methods** — a decision is needed on
   whether to add them (enabling proper aggregate-recording, ADR-005's preferred shape) or accept
   application-authored recording as a documented, permanent-until-refactored choice.
3. **`OrganizationActivated`'s sibling-deactivation gap** — should deactivating siblings produce
   its own fact/hint, or is "the active organization changed" sufficiently captured by a single
   event naming only the newly-activated organization? Needs a business-owner decision, not an
   engineering guess.
4. **`set_module_state`'s exact transition set** was not read method-by-method in this discovery
   (time-boxed); the `ModuleLicensed`/`Enabled`/`Disabled` split is provisional and must be
   confirmed against the real state machine before P5B starts.
   **Resolved (2026-08-25, P5B prerequisite pass): confirmed a real mismatch, not just a naming
   detail.** `set_module_state`'s real state model has three independent fields
   (`licensed`/`enabled`/`lifecycle_status`, the last a 5-value enum: inactive/active/trial/
   suspended/expired) that can all change in ONE call, plus a real, reachable UI action
   (`toggle_module_license`) that flips `licensed` in EITHER direction via the identical control
   -- there is no dedicated "revoke license" event name in the 3-name vocabulary, and
   `lifecycle_status` transitions (e.g. active→suspended, active→trial, active→expired) are real,
   distinct business facts the 3-name vocabulary does not address at all. Whether a license
   revocation that cascades into forcing `enabled=False` and `lifecycle_status=inactive` is one
   compound fact or up to three is a genuine business-owner decision, not an engineering guess --
   P5B's own transaction/scope prerequisites were completed (see the P5B report), but typed event
   implementation remains blocked on this vocabulary question.
5. **The `platform/access` vs. `platform/domain/security/authorization` package-ownership
   question** (already flagged as open in ADR-005 itself) still needs resolving before deciding
   which package owns `ScopeAccessGranted`/`Revoked`'s domain module.
6. **Whether `DocumentLinked`/`DocumentUnlinked` (Class B) ever gets promoted to Class A** depends
   on a future, currently-nonexistent consumer — not a blocker, just explicitly deferred.

No factual contradiction was found in ADR-005/the Execution Plan/the Implementation Plan requiring
a correction, **except one**: the Execution Plan's Phase 2B discovery table stated `access_changed`
has "no confirmed subscriber for this signal at all" — this discovery found a real, direct
consumer (`access_workspace_controller.py:237-240`). See the one-line correction applied to that
document.
