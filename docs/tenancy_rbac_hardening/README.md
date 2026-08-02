# Tenancy and RBAC Hardening

Date: 2026-07-27

Status (verified 2026-08-02): The canonical authority direct-cutover is complete, but the full
tenancy/RBAC hardening program is not. Every identified resource and organization scope
(organization, project, site, storeroom, maintenance) resolves authority exclusively through
canonical `role_bindings`; the legacy authority tables, repositories, migration mode, evidence
tooling, and transition markers are removed. The local development database was reset and the
cleanup migration was applied. Environment-specific policy/delegation provisioning remains an
operator action. The remaining program work is explicit: remove the non-authoritative
`user_tenants.tenant_role` and duplicate membership `is_active` compatibility columns, expose a
reviewed customer-facing invitation/account-onboarding adapter if required by the product, and
complete the repository/background/audit and hosted PostgreSQL defense-in-depth phases. The
2026-08-02 audit also removed stale legacy constructor arguments from all three security operator
tools and added an architecture guard against their return.

Owners: Platform, Security, Persistence, API, Desktop UI, and module teams.

Governing decision:
[ADR-003: Tenancy and Authorization Authority](../architecture_decisions/ADR-003-tenancy-and-authorization-authority.md).
The operational evidence runbook for the superseded staged legacy-to-canonical migration
tooling was deleted on 2026-08-01 along with that tooling (see the 2026-08-01 ledger entry
below) — this program used a direct prelaunch cutover instead, so no such evidence exists to
document.

## Executive Decision

The team review identifies the correct strategic risks. The current application has useful
tenancy and authorization foundations, but those parts do not yet form one fail-closed SaaS
security boundary.

The professional target for this codebase is:

- one global identity per user
- explicit, lifecycle-managed membership in every tenant the user may enter
- fixed permission codes owned by the platform
- role definitions with an explicit assignable scope
- one canonical tenant-aware role-binding model
- authorization decisions that always include tenant and resource context
- tenant-scoped repositories that fail closed when context is missing
- separate platform, tenant, and organization administration
- explicit delegation rules instead of role-name or numeric-rank assumptions
- session revalidation and principal rebuilding when tenant or organization context changes
- durable, security-grade audit records for privileged actions and denials
- entitlements kept separate from RBAC

This is an evolution of the existing architecture, not a second authorization subsystem. In
particular, `AuthorizationEngine` is the correct central seam and must be expanded rather than
replaced by a parallel `AuthorizationService`.

No legacy authorization path may survive the first release. Its permanent canonical replacement
must be implemented and covered by tenant-isolation tests before the legacy path and all
transition-only support code are deleted in the same prelaunch cutover program.

### Prelaunch direct-cutover decision, 2026-07-31

This application is still under development. No customer or production data needs to be
preserved. That materially changes the safe and professional migration approach:

- canonical RBAC is cut over directly in complete authority slices; a slice changes all of its
  reads, writes, bootstrap/provisioning paths, session rebuilding, audit, adapters, and tests
- runtime dual-write, shadow comparison, customer-data backfill, observation windows, and
  per-row rollback evidence will not be implemented
- existing development databases are disposable and must be reset/reseeded after the canonical
  code and schema are ready; reset remains an explicit operator action and is never performed by
  application startup
- fixtures and seed paths create canonical memberships and bindings directly; they do not seed
  legacy rows for compatibility
- every `RBAC-TRANSITION-ONLY` component and every legacy authority adapter is a release blocker
  and must be deleted before the first release; no dead transition code is retained "just in
  case"
- applied Alembic revision files remain immutable migration history, but a cleanup revision may
  drop prelaunch-only runtime tables and legacy columns once no runtime code references them

This decision does not weaken tenant isolation, RBAC, session invalidation, audit, or test
requirements. It removes migration machinery whose only purpose was preserving live customer
authority during a gradual production rollout.

## Security Invariants

The implementation is complete only when all of these invariants hold:

1. A user cannot access a tenant without an active membership, except through an explicitly
   separated platform-support path.
2. A customer role binding always has a non-null `tenant_id`.
3. An organization, site, department, project, storeroom, or other scoped binding belongs to
   the same tenant as the binding.
4. Platform roles are not assignable through customer administration screens or APIs.
5. A tenant administrator can administer only the current tenant.
6. An organization administrator can administer only the bound organization and its permitted
   descendants.
7. Tenant or organization switching validates access and rebuilds the effective principal.
8. Missing tenant context denies tenant-owned reads and writes in SaaS mode.
9. UI visibility is only a convenience. Every service mutation and sensitive read authorizes
   again.
10. A repository cannot silently broaden a query because tenant context is absent.
11. Entitlement checks answer whether a module is licensed or enabled; RBAC answers whether the
   principal may perform an action.
12. Privileged changes and denied cross-tenant attempts produce durable audit evidence.
13. No cache key, search entry, queued job, export artifact, temporary file, or generated report
   containing tenant-owned information is addressable without tenant identity.

## Review Scope

The review traced QML, presenter, desktop API, application service, authorization, repository,
ORM, migration, bootstrap, runtime-session, and test paths across:

- authentication, users, roles, permissions, sessions, passwords, MFA, and federated identity
- tenants, organizations, tenant memberships, and context switching
- scoped access grants and project memberships
- module entitlements
- activity and runtime execution tracking
- PM, inventory/procurement, maintenance, and platform repositories
- application composition and startup seeding
- authorization and tenancy tests

This document is the controlling plan for tenancy and RBAC hardening. Older tenancy repository
documents remain useful implementation evidence, but any conflicting target statement should
be resolved in favor of this document.

## Team Review Reconciliation

| Team proposal | Decision | Codebase-specific interpretation |
| --- | --- | --- |
| Global identity plus tenant memberships | Accept | `users` remains global. `user_tenants` becomes the authoritative tenant-admission lifecycle, without embedded role authority. |
| Fixed permission catalog | Accept | Keep permission codes in `src/core/platform/auth/policy.py`. Do not allow tenants to invent arbitrary permission keys. |
| Scoped role bindings | Accept | Introduce one canonical binding model with tenant and scope columns. Migrate global `user_roles` and scoped grants into it. |
| Central authorization service | Adapt | Expand the existing `AuthorizationEngine`; do not create a competing service or decorator framework. |
| Platform, tenant, and organization admin separation | Accept | Replace implicit `admin` semantics with explicit platform authority and truly scoped customer-admin bindings. |
| Delegation policies | Accept | Replace `_PRIVILEGE_RANK` as a security authority with assignable-role and permission-subset rules. |
| Invitations and first-owner provisioning | Accept | Add dedicated tenant provisioning and membership invitation workflows. Remove registration bypasses. |
| Explicit tenant context and scoped repositories | Accept | Make SaaS mode fail closed. Keep a separately configured local/single-tenant mode if required. |
| PostgreSQL row-level security | Defer as defense in depth | First make application scoping and migrations portable. Add RLS to the hosted PostgreSQL deployment profile after the canonical schema is stable. |
| Server-side sessions with revalidation | Accept | Preserve the current session design, but validate membership and rebuild the principal on restore and context switch. |
| Security audit trail | Accept | Make security audit durable and stop swallowing failed audit writes. Clarify or retire overlapping event stores. |
| Entitlements separate from RBAC | Already present; harden | Preserve the module-entitlement subsystem, add mandatory tenant scope, and remove fail-open behavior. |
| API keys and service accounts | Defer | Add non-human principals only after human role bindings and tenant context are canonical. |
| External policy engine such as OPA | Reject for this phase | The current complexity does not justify a second policy runtime. Reassess only if policies must be shared across independently deployed services. |
| Numeric role hierarchy as delegation | Reject | Ranking can remain display metadata, but it cannot decide what authority may be delegated. |
| Default tenant fallback in SaaS | Reject | Implicit fallback is incompatible with strict multi-tenant isolation. |

## Current Architecture Worth Preserving

The following components are sound foundations and should be evolved:

- `src/core/platform/authorization/domain/authorization_engine.py`
- `src/core/platform/authorization/application/session_authorization_engine.py`
- `src/core/platform/auth/domain/session.py`
- `src/core/platform/tenancy/domain/user_tenant_membership.py`
- `src/core/platform/tenancy/tenant_context.py`
- `src/core/platform/infrastructure/persistence/repositories/_tenant_scope.py`
- the fixed permission catalog in `src/core/platform/auth/policy.py`
- module entitlements under `src/core/platform/modules`
- existing tenant-scoped repository work in PM, inventory/procurement, and maintenance
- runtime session revalidation and security revision support

The issue is not a total absence of architecture. The issue is that several older global and
fail-open paths bypass these foundations.

## Verified Findings

### P0-1: User creation can produce a global privileged user without tenant membership

Evidence:

- `src/core/platform/auth/application/registration_service.py`
- `src/api/desktop/platform/user.py`
- `src/api/desktop/platform/models/user.py`
- `src/ui_qml/platform/presenters/user_catalog_presenter.py`

`RegistrationService.assign_roles_for_user()` writes `UserRoleBinding` directly instead of using
the checked assignment workflow. `register_user()` exposes a `bypass_permission` flag. The
desktop create-user command carries role names but no required tenant identifier, and defaults
to `viewer` when roles are omitted.

The resulting user may have a global role and no `user_tenants` membership. Because the tenant
context can fall back to a default tenant, that user may still enter tenant-owned workflows.
This chain is a likely root cause of the reported "multiple admin" behavior.

Required correction:

- make ordinary registration identity-only or invitation-token driven
- require an explicit tenant for customer-user onboarding
- create membership and role binding in one transaction
- remove the public bypass flag and direct role write
- make platform-owner provisioning a separate command

### P0-2: `user_roles` cannot represent tenant-local authority

Evidence:

- `src/core/platform/infrastructure/persistence/orm/auth.py`
- `src/core/platform/auth/domain/user.py`
- `src/core/platform/infrastructure/persistence/repositories/auth.py`

`RoleORM` is global. `UserRoleORM` contains an optional `organization_id` but no `tenant_id` or
scope type. A role assigned while operating in Tenant A is therefore also effective in Tenant B.
The existing organization-specific query path is not used when the normal principal is built.

The `(user_id, role_id, organization_id)` uniqueness rule also does not reliably prevent
duplicate global rows when `organization_id` is `NULL`, and application-side existence checks
remain race-prone.

Required correction:

- add canonical tenant-aware role definitions and role bindings
- require non-null tenant IDs for all customer bindings
- use a normalized non-null scope key or partial indexes for reliable uniqueness
- migrate before dropping `user_roles`

### P0-3: Context switching changes IDs without rebuilding authority

Evidence:

- `src/core/platform/auth/application/principal_builder.py`
- `src/core/platform/auth/application/auth_query.py`
- `src/core/platform/auth/domain/session.py`
- `src/core/platform/tenancy/tenant_context.py`
- `src/api/desktop/platform/tenant.py`

`set_active_tenant_id()` and `set_active_organization_id()` replace identifiers on the current
principal while retaining roles, permissions, and scoped access. `switch_to_tenant()` does not
rebuild the principal. Session restoration rebuilds permissions and restores stored context in
separate steps, so the scoped grants can be loaded under the wrong context.

Required correction:

- build a principal for an explicit tenant and organization
- validate active membership, tenant status, and organization ownership first
- atomically switch, rebuild, persist, and audit
- clear the runtime session and require re-login when a stored context is no longer valid

### P0-4: Several boundary checks fail open when context is missing

Evidence:

- `src/core/platform/auth/application/role_assignment_service.py`
- `src/core/platform/auth/application/user_admin_service.py`
- `src/core/platform/infrastructure/persistence/repositories/access.py`
- `src/core/platform/tenancy/tenant_context.py`

Role-assignment and user-boundary helpers return without denial when session, principal,
membership repository, or active tenant is missing. The access repository can query or write
without a tenant. `get_active_tenant()` silently falls back to a default tenant.

Required correction:

- use one explicit application mode: `saas` or `local_single_tenant`
- make missing context an authorization error in SaaS mode
- keep platform-wide repositories separate from tenant repositories
- never interpret a missing tenant filter as "all tenants"

### P0-5: Customer admin and platform admin authority are mixed

Evidence:

- `src/core/platform/auth/policy.py`
- `src/core/platform/auth/application/bootstrap_service.py`
- `src/core/platform/auth/application/default_seed_service.py`
- `src/core/platform/auth/application/auth_service.py`

`tenant_admin` includes tenant creation and global tenant reading. `org_admin` carries broad
global permissions but is not effectively organization-scoped. `admin` is treated as a platform
administrator by hard-coded role-name checks. Startup bootstrap can create or silently promote
the configured username to `admin` on every launch.

Required correction:

- define `platform_admin` as internal platform authority
- define `tenant_admin` only at tenant scope
- define `org_admin` only at organization scope
- optionally define a narrowly controlled, audited `platform_support` role
- replace recurring startup promotion with one-time provisioning that only runs when no
  platform owner exists
- hide platform roles from all customer role selectors and APIs

Implementation status:

- Hosted `saas` startup no longer creates or promotes the configured legacy administrator.
- Hosted `saas` startup no longer creates a default tenant or organization, selects an implicit
  customer context, or backfills users into customer memberships.
- `local_single_tenant` retains its explicit desktop initialization behavior as a separate mode.
- The one-time audited platform-owner command remains the only SaaS owner-creation path.
- Canonical role naming still uses the transitional `admin` template until the binding-schema
  migration replaces legacy global role authority.

### P0-6: Sensitive user-security operations lack a mandatory target-tenant boundary

Evidence:

- `src/core/platform/auth/application/password_service.py`
- `src/core/platform/auth/application/mfa_service.py`
- `src/core/platform/auth/application/federated_identity_service.py`
- `src/core/platform/auth/application/session_service.py`

Password reset, MFA provisioning or disablement, federated identity linking, session listing,
and session revocation do not consistently verify that the target user belongs to the actor's
active tenant and administrative scope. `change_password()` also accepts a target user ID
without proving that the authenticated principal is that user. These are potential account
takeover paths, not only data-visibility defects.

Required correction:

- route all sensitive user operations through one fail-closed target-principal boundary
- separate self-service operations from administrative operations
- require actor-equals-target for self-service password/MFA operations
- require recent authentication or MFA confirmation where appropriate
- tenant-scope administrative password, MFA, identity, and session operations
- invalidate affected sessions and audit successful and denied operations

### P1-1: Role assignment uses rank instead of delegable authority

Evidence:

- `src/core/platform/auth/application/role_assignment_service.py`

`_PRIVILEGE_RANK` assumes that a role with a higher number may delegate lower roles. This does
not prove that the actor has every permission being granted, that the target role is assignable
at the requested scope, or that separation-of-duties constraints are satisfied.

Required correction:

- store role scope and assignability
- define explicit delegation rules
- calculate the actor's delegable permissions separately from effective permissions
- require requested role permissions to be a subset of the actor's delegable permissions
- enforce target membership and target-scope ownership
- apply the same checks to assign, update, revoke, and bulk operations

### P1-2: Global user and role catalog reads are tenant-ambiguous

Evidence:

- `src/core/platform/auth/application/user_admin_service.py`

`list_users()` and `list_roles()` read global repositories. Customer administrators can
therefore receive identities or role definitions outside the current tenant even when later
mutations have partial boundary checks.

Required correction:

- tenant-scope customer user catalogs through active membership
- return only system templates assignable at the current scope and tenant-owned custom roles
- keep explicitly named platform catalogs behind platform-only permissions and APIs
- apply pagination and safe search without exposing cross-tenant existence

### P1-3: Tenant membership has no complete lifecycle

Evidence:

- `src/core/platform/tenancy/domain/user_tenant_membership.py`
- `src/core/platform/tenancy/contracts.py`
- `src/core/platform/infrastructure/persistence/repositories/user_tenant.py`

Membership records are created through tenant creation, optional registration logic, and startup
backfill. There is no complete invite, accept, suspend, reactivate, remove, or transfer-owner
workflow. The `tenant_role` field duplicates RBAC authority but is ignored by principal
construction.

Required correction:

- model membership states such as invited, active, suspended, and removed
- preserve the existing unique `(user_id, tenant_id)` row and implement explicit state
  transitions instead of additional history rows
- add invitation expiry, issuer, acceptance, and revocation metadata
- make role bindings the sole source of role authority
- migrate and remove `tenant_role`
- remove startup membership backfill from SaaS mode

### P1-4: Scoped access grants are a parallel authorization model

Evidence:

- `src/core/platform/access`
- `src/core/platform/infrastructure/persistence/orm/access.py`
- `src/core/platform/infrastructure/persistence/repositories/access.py`

`scoped_access_grants` stores a scope role plus a denormalized permission-code snapshot.
Project membership adds another representation. The service checks broad `access.manage` but
does not fully enforce delegation, target membership, or tenant ownership of resolved scopes.
Some organization and site resolvers use unscoped lookups.

Required correction:

- migrate scope roles into canonical role bindings
- retain project-membership APIs only as a facade or business projection if the UI needs them
- stop treating denormalized permission snapshots as authority
- make every scope resolver tenant-aware
- reject cross-tenant scope IDs before mutation

### P1-5: Effective scope semantics are implicit and difficult to audit

Evidence:

- `src/core/platform/auth/domain/session.py`

The current logic treats a global permission with no scoped rows as authority over every scope,
but treats the same permission as restricted once any scoped row exists. "No grant" can
therefore mean "all", which is unsafe and hard to explain.

Required correction:

- represent tenant-wide authority as an explicit tenant-scoped binding
- represent restricted authority as explicit organization or resource bindings
- never infer unrestricted authority from the absence of scoped rows

### P1-6: Separation-of-duties checks use defaults instead of effective policy

Evidence:

- `src/core/platform/auth/sod.py`
- `src/core/platform/auth/application/sod_enforcer.py`

The enforcer calculates conflicts from code defaults instead of the persisted permissions of the
requested role. It is scope-blind and includes an administrator bypass. Custom or reconciled
role permissions can therefore diverge from the SoD decision.

Required correction:

- calculate conflicts from effective persisted role permissions
- evaluate conflicts at the relevant tenant and scope
- remove blanket administrator bypasses for mandatory constraints
- record exceptions through an explicit approval workflow

### P1-7: Policy seeding is additive and cannot revoke stale permissions

Evidence:

- `src/core/platform/auth/application/default_seed_service.py`
- `src/core/platform/auth/policy.py`

Changing the permission constants is not sufficient. Seeding only inserts missing bindings and
does not remove permissions that no longer belong to a system role. Existing databases would
retain overpowered `tenant_admin` permissions.

Required correction:

- version system role definitions
- reconcile additions and removals transactionally
- report drift before applying changes
- make customer custom roles separate from managed system roles

Implementation status:

- `SYSTEM_ROLE_POLICY_VERSION` and the managed policy name now version the code-owned policy.
- `RolePolicyReconciliationService` provides deterministic preview and guarded apply operations.
- `tools/reconcile_role_policy.py` is dry-run by default and requires the reviewed previous
  version, change-set hash, and a new rollback-artifact path for apply.
- `auth_policy_reconciliations` is an append-only application ledger with a unique target
  version. A successful apply updates bindings, rotates affected users' security revisions,
  revokes their persisted sessions, and writes the ledger row in the same transaction.
- Ordinary startup remains additive and never invokes the destructive reconciler.
- Existing installations still require an explicit operator dry-run and reviewed apply; changing
  the code constants alone does not remove stale database bindings.

### P1-8: Organization lifecycle and per-session selection are mixed

Evidence:

- `src/core/platform/org/application/organization_service.py`
- `src/application/runtime/platform_runtime.py`
- `src/core/platform/tenancy/tenant_context.py`

Selecting an organization can mark every other organization inactive in persistent state, while
other paths only change session context. A SaaS tenant may legitimately operate several active
organizations at once.

Required correction:

- treat organization enabled/status state as lifecycle data
- treat selected organization as session context only
- remove `_deactivate_other_organizations()` from selection behavior
- authorize selection by membership/access, not by a broad settings permission

### P1-9: Security audit is best-effort and non-atomic

Evidence:

- `src/core/shared/audit/audit_recorder.py`
- `src/core/platform/auth/application/audit_recorder.py`
- `src/core/platform/audit`
- `src/core/platform/platform_events`

Audit failures can be swallowed. Several business changes commit before their audit event is
written. Audit context itself can depend on the current tenant, which is unreliable during
cross-context or failed operations. `audit_entries`, `domain_events`, and `platform_events` have
overlapping but unclear responsibilities.

Required correction:

- define `audit_entries` as the authoritative security/compliance record
- write privileged change plus audit intent in one transaction or through a durable outbox
- include actor, target, tenant, scope, session, trace, action, outcome, and reason
- log denied cross-tenant attempts without leaking protected object data
- use `domain_events` only for in-process notifications
- either turn `platform_events` into the durable integration outbox or retire it after migration

### P1-10: Activity and runtime execution can expose cross-tenant metadata

Evidence:

- `src/core/platform/activity/application/activity_service.py`
- `src/core/platform/infrastructure/persistence/repositories/activity.py`
- `src/core/platform/runtime_tracking/application/runtime_execution_service.py`
- `src/core/platform/infrastructure/persistence/orm/runtime_tracking.py`

Activity queries can become global when context is missing. Runtime execution records have no
tenant or organization and expose job status, input paths, and output paths through global
lookups.

Required correction:

- stamp tenant, organization, principal, and correlation context into every execution
- authorize list/get/cancel/retry operations
- make background payloads carry an explicit tenant
- deny execution when tenant context cannot be reconstructed

### P1-11: ORM, migration, and test schemas do not agree

Evidence:

- tenant-owned ORM models with nullable `tenant_id`
- `src/infra/persistence/migrations/versions/r3s4t5u6v7w8_phase_c_tenant_id_not_null.py`
- `src/tests/conftest.py`

Production migrations attempt to harden many tenant columns, while ORM declarations remain
nullable. Tests create tables from ORM metadata rather than applying migrations, so they do not
exercise production constraints. The hardening migration also contains SQLite-specific
inspection even though configurable database URLs imply broader dialect support.

Required correction:

- align ORM nullability with the migrated database
- add composite tenant ownership constraints where practical
- run schema integration tests from Alembic migrations
- test SQLite and the hosted PostgreSQL profile separately
- make migrations dialect-correct before adding PostgreSQL RLS

### P1-12: Entitlements are correctly separate but not consistently tenant-safe

Evidence:

- `src/core/platform/modules`
- `src/application/runtime/entitlement_runtime.py`
- module repository construction in `src/infra/composition/platform_registry.py`

The separation between module entitlement and action authorization is correct. However,
entitlement rows and repository construction permit nullable or absent tenant context, and some
runtime checks return when the service is unavailable.

Required correction:

- keep entitlements separate
- require tenant ownership for organization entitlements
- fail closed in SaaS mode when entitlement infrastructure is unavailable
- validate that an organization belongs to the active tenant before reading or writing its plan

### P2: Remaining repository and naming debt

Verified lower-priority items include:

- dynamic and duplicated tenant-scope helpers across PM, inventory/procurement, and maintenance
- unscoped organization and site access resolvers
- tenant membership listing that does not consistently filter active memberships
- collaboration unread queries that need explicit tenant predicates
- duplicate role aliases such as `finance` versus `finance_controller`
- duplicate maintenance aliases such as `maintenance_manager` versus `maintenance_admin`

These are not substitutes for the P0 model correction, but they must be removed before the
hardening program is complete.

## Target Domain Model

### User

`User` is a global authentication identity. It contains no implicit customer authority.

Minimum security-relevant fields:

- `id`
- normalized username/email
- status
- credential and MFA state
- security revision
- created/updated metadata

### Tenant membership

`TenantMembership` is the admission boundary.

Suggested fields:

- `id`
- `tenant_id`
- `user_id`
- `status`: invited, active, suspended, removed
- `invited_by`
- `invited_at`
- `accepted_at`
- `suspended_at`
- `removed_at`
- `expires_at`
- `version`

Preserve the existing database invariant:

```text
UNIQUE (tenant_id, user_id)
```

There is exactly one lifecycle-managed row for a user in a tenant, not one row per invitation
or active period. State transitions update that row:

```text
invited -> active -> suspended -> active -> removed
```

Reinvitation or reactivation must use an explicit transition with optimistic concurrency, not
silently insert or ignore a second row. Historical state changes belong in the authoritative
audit trail or membership-history events. Membership does not carry a role name.

### Permission

Permissions remain platform-defined immutable codes such as:

- `project.read`
- `project.manage`
- `auth.user.read`
- `auth.role.assign`
- `tenant.settings.manage`

Renaming or removal requires a data migration and policy-version reconciliation.

### Role

A role is a named set of permission codes.

Suggested fields:

- `id`
- `tenant_id`, null for platform-managed system templates and non-null for tenant-owned custom
  roles
- `name`
- `display_name`
- `allowed_scope_type`: platform, tenant, organization, site, department, project, storeroom, or
  another registered resource type
- `is_system`
- `is_assignable`
- `status`
- `policy_version`
- created/updated metadata

System roles are reconciled from code. Tenant custom roles may select only known permission
codes and cannot exceed the creator's delegable authority.

`Role.tenant_id IS NULL` means the definition is platform-managed; it does not by itself grant
platform authority. Examples:

| Role definition | Role tenant | Allowed scope | Meaning |
| --- | --- | --- | --- |
| `platform_admin` | null | platform | internal platform authority template |
| `tenant_admin` | null | tenant | system template assignable inside a customer tenant |
| `org_admin` | null | organization | system template assignable to one organization |
| Tenant A custom planner | Tenant A | tenant or a supported resource type | customer-owned definition usable only in Tenant A |

### Role binding

`RoleBinding` is the sole persisted grant of role authority.

Suggested fields:

- `id`
- `principal_type`: user initially; service_account later
- `principal_id`
- `role_id`
- `tenant_id`, null only for platform scope
- `actual_scope_type`
- `actual_scope_id`, null for platform and tenant scope and required for resource scope
- `assigned_by`
- `assigned_at`
- `expires_at`
- `revoked_at`
- `version`

Required structural and authorization rules:

- `binding.actual_scope_type == role.allowed_scope_type`
- a tenant-owned custom role can be bound only inside `role.tenant_id`
- platform binding requires `tenant_id IS NULL` and a platform-scoped role
- every non-platform scope requires `tenant_id IS NOT NULL`
- organization/resource scopes require `actual_scope_id IS NOT NULL`
- active bindings are uniquely constrained for principal, role, tenant, and scope

For example, a binding of the platform-managed `tenant_admin` template in Tenant A has
`tenant_id=Tenant A`, `actual_scope_type=tenant`, and `actual_scope_id=NULL`. The role definition
remaining global does not make this a global grant.

Ordinary relational constraints can enforce the structural rules above, but a polymorphic
`actual_scope_id` cannot have a normal foreign key to every possible resource table. Scope
ownership must initially be validated by one tenant-aware resolver registry evolved from the
existing `ScopedRolePolicyRegistry` and `scope_exists_resolvers` seams:

```python
scope = scope_resolver_registry.resolve(
    tenant_id=request.tenant_id,
    scope_type=request.actual_scope_type,
    scope_id=request.actual_scope_id,
)
if scope is None:
    raise AuthorizationDenied("Scope is unavailable.")
```

Every role-binding create, update, bulk assign, and import path must use this registry. Existing
organization and site resolvers must be changed from unscoped `get(id)` calls to tenant-aware
lookups. A future `authorization_scopes` registry table with a composite foreign key may add
database enforcement, but it is deferred because synchronizing every resource lifecycle would
add substantial first-migration risk.

### Delegation policy

Delegation is not inferred from role names.

Effective permission and delegable permission are distinct sets. A user may be allowed to
perform `billing.refund` without being allowed to create a role or binding that grants it to
someone else. The initial model should use explicit delegation relations such as:

```text
DelegationPolicy(
    actor_role_id,
    assignable_role_id,
    target_scope_type
)
```

Permission metadata such as sensitivity and allowed scope types may supplement this later, but
must not infer delegation from possession alone.

A role may be assigned only when:

- the actor has `auth.role.assign` at the target scope
- the role is assignable at that scope type
- every permission in the requested role is delegable by the actor
- the actor may administer the target principal's membership
- SoD policy permits the effective combination
- the target tenant and resource match the active authorization context

### Entitlement

Entitlement remains a separate tenant-owned record answering whether a module or capacity is
available. Passing an entitlement check never implies permission to use the feature.

## Administrative Boundaries

| Authority | Scope | Allowed examples | Explicitly prohibited |
| --- | --- | --- | --- |
| `platform_admin` | Platform | provision/suspend tenants, platform policy operations, emergency support controls | appearing in customer role selectors; ordinary project operations without an audited support context |
| `platform_support` | Explicit support session | approved diagnostic access with reason, expiry, and audit | permanent customer access; role delegation; silent impersonation |
| `tenant_admin` | One tenant | memberships, tenant-scoped roles, organizations, tenant settings | creating/listing other tenants; assigning platform roles; managing another tenant |
| `org_admin` | One organization | organization users and permitted descendants | tenant-wide role assignment; other organizations; platform settings |
| Functional roles | Tenant or resource | domain actions represented by their permissions | identity or role administration unless explicitly granted |

The legacy name `admin` must not remain an ambiguous authority. Migrate it to
`platform_admin` only for verified platform operators. Do not automatically map every existing
`admin` row without review.

## Target Authorization Flow

Every protected operation must follow this order:

1. Resolve and validate the authenticated session.
2. Resolve the explicit tenant context.
3. Validate tenant status and active user membership.
4. Resolve the optional organization/resource within that tenant.
5. Build or load a principal only for that context.
6. Ask `AuthorizationEngine` for the permission, tenant, resource, and operation decision.
7. For role/user administration, apply delegation, target-boundary, and SoD rules.
8. Execute through a tenant-scoped repository and add the audit outbox record to the same unit
   of work.
9. Commit the business mutation and audit intent once.
10. Return a sanitized authorization error to API/QML when denied.

The decision input should be an explicit value object, for example:

```python
AuthorizationRequest(
    principal_id=principal.user_id,
    session_id=principal.session_id,
    tenant_id=active_tenant_id,
    organization_id=active_organization_id,
    permission="project.manage",
    resource_type="project",
    resource_id=project_id,
    action="update",
)
```

`SessionAuthorizationEngine` currently discards resource and context inputs. It must instead:

- deny missing required context
- verify the request context matches the principal context
- distinguish platform from customer operations
- evaluate tenant-wide and resource-scoped role bindings
- return a structured decision with a safe denial reason

### Audit transaction policy

The current application uses synchronous SQLAlchemy sessions, so the first implementation
should preserve that transaction model rather than introduce an asynchronous unit-of-work
abstraction.

For a successful privileged mutation:

```python
with session.begin():
    perform_change()
    audit_outbox_repo.add(success_event)
```

If the success audit/outbox row cannot be persisted, the privileged mutation must roll back.
The outbox dispatcher may publish after commit, but the durable intent is part of the business
transaction.

A denial has no business transaction to join. The authorization engine must deny first, then
attempt a separate durable security-audit write. Failure to record the denial must never turn
the decision into an allow, and the denial record must not reveal protected target details.
Operational policy must define alerting and local fallback handling for audit-store outages.

## Session and Context Rules

The existing server-side session design is acceptable with these changes:

- store selected tenant and organization as session context, not as authorization evidence
- rebuild the principal when the session is restored
- rebuild again after every successful tenant or organization switch
- reject inactive membership, tenant suspension, or invalid organization ownership
- increment or compare security revision after password, MFA, membership, and role changes
- invalidate or refresh affected sessions after security changes
- require re-login when revalidation cannot safely restore context
- never let raw membership, entitlement, or context exceptions reach QML

Context switching must be an application service operation, not direct mutation of IDs on
`UserSessionContext`.

The containment builder cannot make legacy `user_roles` tenant-aware because that table has no
tenant ID. It must re-query roles and grants rather than copy the current principal, and apply
temporary conservative handling:

- legacy `admin` is accepted only for a reviewed platform operator
- legacy `tenant_admin` is usable only when its customer tenant can be determined
  unambiguously; multiple active memberships without a migration mapping deny switching
- legacy `org_admin` requires an explicit organization grant in the requested tenant
- ambiguous privileged rows are quarantined for operator mapping or revocation
- no current principal role or scoped grant is copied into the target context

This contains stale scoped authority but does not replace the canonical binding migration.

The codebase uses `PM_*` environment names, so the target setting is
`PM_TENANCY_MODE=saas|local_single_tenant`, not a separate `APP_*` convention. Add an explicit
deployment profile such as `PM_DEPLOYMENT_ENV=development|test|production`:

- production must fail startup when `PM_TENANCY_MODE` is absent
- hosted production must explicitly set `PM_TENANCY_MODE=saas`
- local development may default to `local_single_tenant`
- no mode may be inferred from the database URL or silently changed at runtime

Mode-specific behavior must live behind one policy:

```python
class TenantContextPolicy(Protocol):
    def require_tenant(self, session: UserSessionContext) -> TenantContext: ...

class SaaSTenantContextPolicy(TenantContextPolicy): ...
class LocalSingleTenantContextPolicy(TenantContextPolicy): ...
```

Services and repositories consume the policy result and must not accumulate scattered
`if local_mode` exceptions.

## Repository and Database Rules

### Application scoping

- Tenant-owned repositories require a constructor-provided or call-provided tenant context.
- Missing context raises a typed tenant-context error in SaaS mode.
- Platform repositories are explicitly named and available only to platform application
  services.
- Reads, writes, counts, existence checks, bulk actions, exports, and background jobs use the
  same scope.
- Resource lookup verifies both ID and tenant, not ID followed by a best-effort check.
- Scope resolvers use tenant-aware repository methods.

The current platform helper already fails when its tenant-context service is unavailable. The
parallel PM, inventory/procurement, and maintenance helpers are not equivalent: their
compatibility predicates can treat missing active tenant or missing row tenant as acceptable.
Consolidation must therefore remove permissive semantics, not only duplicate code.

### Derived data and background work

Tenant identity is part of the address and authorization context for:

- cache keys and invalidation events
- search-index documents
- queued and scheduled jobs
- runtime execution records
- import staging and export artifacts
- temporary files and generated reports

Examples:

```text
Bad:  project:123
Good: tenant:{tenant_id}:project:123

Bad:  GenerateReport(report_id=42)
Good: GenerateReport(
          tenant_id=tenant_id,
          actor_id=actor_id,
          report_id=42,
          authorization_context_id=context_id
      )
```

Workers must reconstruct tenant context and revalidate current tenant status, membership, and
authority when execution begins, especially for delayed work. A context/snapshot identifier is
for traceability and reproducibility; queued payloads must not contain a trusted copy of all
user permissions. Artifact metadata and storage paths must prevent cross-tenant guessing even
when two tenants use the same business identifier or filename.

### Database constraints

- Make tenant ownership non-null for tenant-root data.
- Add tenant-aware uniqueness constraints.
- Add composite foreign keys where the relationship is not polymorphic.
- Validate polymorphic binding scope ownership through the central tenant-aware resolver.
- Use migrations, not ORM metadata creation, for production-shape integration tests.

### PostgreSQL RLS

RLS is recommended later for the hosted PostgreSQL profile as defense in depth. It is not a
replacement for application authorization or repository scoping. The database connection must
set verified tenant context per transaction, policies must default deny, table owners and
`BYPASSRLS` roles must not be used by the application, and backup/administration roles require a
separate design.

SQLite/local deployments cannot depend on RLS, so application-level isolation remains
mandatory in every profile.

## Prelaunch Authority Cutover

The former four-mode runtime migration design is no longer the target. There is no live customer
authority to compare or preserve, and introducing dual-write or shadow execution would create
temporary product behavior and dead code without reducing launch risk.

Until a complete authority slice is converted, its existing behavior remains covered by
characterization tests. Each slice then moves directly to canonical reads and writes with no
per-request fallback. Canonical absence is a denial, never a reason to read `user_roles`.

The required cutover order is:

1. Add the permanent canonical effective-authority resolver and test platform, tenant,
   organization, and resource scope semantics. Implemented.
2. Cut over platform-owner provisioning, local bootstrap, policy impact discovery, and platform
   principal reads as one package. Implemented; stale legacy platform rows grant no authority.
3. Cut over tenant onboarding, membership acceptance, customer assignment/revocation, tenant
   principal reads, and session rebuilding as one package. Implemented.
4. Cut over organization/resource bindings and replace scoped permission JSON/project membership
   authority with canonical scoped resolution. Implemented for every identified scope.
5. Reset and reseed development databases through an explicit operator command, run the complete
   isolation matrix, then remove legacy schemas and all transition-only runtime code. Implemented
   for canonical authority; membership compatibility columns are tracked separately below.

`AuthorizationMigrationMode`, its environment variable, transition evidence, preparation
records, and migration operator CLIs were temporary repository state inherited from the previous
plan. They have been deleted and are not part of the launch architecture.

## System Role Policy Reconciliation

System-role changes must not be silently applied during ordinary startup. The implemented
deployment command is dry-run by default:

```text
python -m tools.reconcile_role_policy --username <platform-operator> --output policy-preview.json
python -m tools.reconcile_role_policy --apply --username <platform-operator> \
  --expected-version <preview-version> --expected-hash <preview-sha256> \
  --rollback-output policy-rollback.json
```

The preview reports removed and added bindings, affected active users and sessions, missing
managed definitions, a deterministic change-set hash, and the inverse change set. SoD
consequence analysis remains part of the later canonical binding/delegation work. Applying the
change records:

- previous and new policy versions
- deterministic change-set hash
- executing principal and deployment trace
- execution timestamp and outcome
- rollback artifact or inverse change set

The command aborts on version mismatch, hash mismatch, missing definitions, or unexpected drift.
It writes the rollback artifact before mutation and refuses to overwrite an existing artifact.
Removing overpowered `tenant_admin` permissions is a reviewed security migration, not a side
effect of application startup. The stored inverse artifact is implemented; an automated rollback
executor remains future deployment tooling.

## Migration and Retirement Matrix

| Legacy item | Target | Retirement gate |
| --- | --- | --- |
| `registration_service._assign_roles_for_user()` | checked membership plus role-binding workflow | all callers migrated and registration tests prove no bypass |
| public `bypass_permission` flag | dedicated one-time platform provisioning | bootstrap command and invitation flows operational |
| recurring startup admin promotion | explicit platform-owner provisioning command | verified owner exists and bootstrap audit complete |
| `_PRIVILEGE_RANK` as authority | delegation policy and permission-subset check | assignment/revoke/bulk tests pass |
| `user_tenants.tenant_role` | role bindings only | canonical fixtures/seeds and runtime paths have no reads/writes; development data reset |
| legacy `user_roles` | canonical `role_bindings` | canonical tests pass, no runtime references remain, development data reset, cleanup revision applied |
| `scoped_access_grants.permission_codes_json` | role permissions resolved from canonical roles | scoped grants migrated and access parity verified |
| project membership as authorization source | canonical binding with optional projection/facade | PM behavior and reporting tests pass |
| implicit default tenant fallback | explicit SaaS context or configured local mode | every SaaS entry point supplies context |
| startup user-to-default-tenant backfill | explicit fixture/seed provisioning | development databases reset and startup contains no membership mutation |
| `_deactivate_other_organizations()` on selection | session-only organization selection | organization lifecycle migration complete |
| duplicate scope helpers | `TenantScopedRepositorySupport` or one typed equivalent | module repositories and contracts migrated |
| role aliases `finance`, `maintenance_admin` | canonical role names | data alias migration and compatibility window complete |
| additive startup role-permission seeding | versioned preview/apply reconciliation command | dry run, expected-version guard, rollback artifact, and session invalidation pass |
| per-request canonical-deny fallback to legacy | canonical fail-closed resolution | canonical absence tests prove no legacy lookup occurs |
| tenant-unqualified runtime executions and artifacts | tenant-qualified execution and storage metadata | worker revalidation and cross-tenant artifact tests pass |
| best-effort swallowed security audit | transactional audit/outbox | failure and recovery tests pass |
| ambiguous `platform_events` | durable integration outbox or removal | ownership and consumers documented, data retained as required |
| insecure tests that expect tenant admin to create/list tenants | scoped admin matrix tests | new policy active and old assertions removed |

Deletion is part of prelaunch completion, not a post-launch observation task. Runtime references
must be removed before the cleanup migration is applied. Development database deletion/reset is
an explicit operator action and is not combined with ordinary application startup.

### Transition-code decommission register

Every temporary migration implementation must carry the searchable marker
`RBAC-TRANSITION-ONLY`. Adding temporary code without both this marker and an entry below is not
allowed. Closing the migration includes a dedicated dead-code removal change; reaching
`CANONICAL_ONLY` does not by itself make cleanup complete.

**Done on 2026-08-01** (see the dated ledger entry below for the full account):

| Transition-only component | Removal gate | Outcome |
| --- | --- | --- |
| `UserRoleBinding`, `UserRoleORM`, `UserRoleRepository`, and their SQLAlchemy adapter | Canonical resource fixtures/adapters and isolation tests pass; superseded preparation tooling is deleted; no source reference remains | Deleted; `user_roles` table dropped by the cleanup migration |
| Legacy scoped-grant/project-membership projection in principal construction | Canonical bindings own organization viewer/member and resource authority as well as login, restore, tenant switch, and organization switch | Deleted; `principal_builder` now reads `canonical_authority.scoped_access` directly |
| `AccessControlService`'s legacy `ScopedAccessGrant`/`ProjectMembership` write/read branches, plus the underlying persistence layer (confirmed unreachable in production) | Desktop API/QML adapters consume canonical role names directly for every cut-over scope type | Legacy branches, `ProjectMembership` domain class, both repository ABCs, both SQLAlchemy repos, and their ORM/mapper deleted. The `ScopedAccessGrant`-shaped translation shim itself **stays** — desktop API/QML still consume that shape |
| `CollaborationSupportMixin`'s legacy `project_membership_repo` fallback in `_list_mention_candidates_for_project` | Every `CollaborationService` construction site supplies `role_repo`/`role_binding_repo` | Deleted; canonical-only, returns no candidates when those collaborators aren't wired |
| `AuthorizationMigrationBatch`, `LegacyRoleBindingMigrationRecord`, their ORM/repository adapters, and runtime tables | Direct cutover no longer imports legacy rows; cleanup revision is ready | Deleted; tables dropped by the cleanup migration |
| Legacy binding migration planner, preparation service, operator CLI, and focused tests | Canonical fixture/seed paths are complete and direct cutover tests pass | Deleted (`role_binding_migration_plan.py`, `role_binding_migration_preparation.py`, `tools/prepare_role_binding_migration.py`, their tests) |
| Transition-evidence manifest verifier, CLI, focused tests, and runbook | Prelaunch direct-cutover checks replace staged promotion evidence | Deleted (`authorization_transition_evidence.py`, `tools/verify_authorization_transition_evidence.py`, its test, `ADR-003_OPERATIONAL_EVIDENCE.md`) |
| Legacy-specific probes in the tenancy/RBAC inventory | Legacy tables are dropped and permanent tenant-isolation inventory remains | Deleted; `build_tenancy_rbac_inventory` keeps only permanent findings (canonical bindings, membership lifecycle, tenant-role duplication) |
| `AuthorizationMigrationMode`, `PM_AUTHORIZATION_MIGRATION_MODE`, and mode-gating branches/tests | Every runtime decision is canonical and configuration no longer consumes the switch | Deleted from runtime configuration, tools, shared tests, and `.env`; guarded by `test_legacy_rbac_runtime_dependencies_are_removed` |

The system-role policy reconciliation command is **not** transition-only; controlled role-policy
updates remain necessary after canonical cutover. Applied Alembic revision files are immutable
history and must never be deleted. The prelaunch cleanup revision may drop transition runtime
tables, but it must not remove revisions that created them.

## Implementation Plan

### Phase 0: Safety net and decisions

Status: Complete for the prelaunch direct authority cutover. There was no production customer
authority to preserve; permanent inventory and characterization coverage remain, while the
superseded production-preservation evidence implementation was deleted.

- Freeze new role names and direct role-assignment paths.
- Add an architecture decision record for application mode, platform authority, and canonical
  binding scope types.
- Inventory existing users, memberships, roles, user-role rows, and scoped grants.
- Detect users with global privileged roles but no active membership.
- Detect duplicate/null-scope bindings and cross-tenant scope references.
- Add characterization tests around current login, restore, switch, assignment, and access
  behavior.
- Record the superseded staged migration-mode decision, then remove the mode and all transition
  branches after the direct prelaunch cutover. Implemented.
- Define `PM_DEPLOYMENT_ENV`, `PM_TENANCY_MODE`, and the tenant-context policy boundary.
- Define backup, rollback, and audit retention requirements.

Exit criteria:

- production data can be classified deterministically
- every direct role write has an owner and migration path
- no destructive migration is scheduled without a rollback artifact

### Phase 1: Immediate containment

Status: Complete for immediate authorization containment. Replacement provisioning, the
tenant-context policy foundation,
explicit-context session authority, atomic tenant/organization switching, customer-admin
containment, sensitive target-user boundaries, direct tenant-user onboarding, customer
role/catalog containment, canonical platform/tenant and explicit organization-role authority,
and reviewed policy
reconciliation tooling are implemented. SaaS startup no longer creates/promotes a legacy admin
or creates/selects/backfills customer context; local desktop initialization remains explicitly
mode-bound. Organization/resource cutover, development reset/reseed, delegation provisioning in
the local development environment, and legacy/transition cleanup are complete. External delivery
channels and deployment-environment provisioning are operational/product rollout work.

- Add security regression tests before changing fail-open behavior.
- Implement and test one-time platform-owner provisioning before changing startup bootstrap.
- Establish explicit tenant context during login and session restoration.
- Make tenant and organization switching validate access and atomically replace both context and
  principal, initially using a target-context-aware legacy principal builder.
- Quarantine ambiguous legacy `tenant_admin` and `org_admin` rows; do not carry them across
  tenants merely because the principal was rebuilt.
- Make missing context deny through `SaaSTenantContextPolicy`.
- Remove role selection from untrusted registration paths.
- Remove or make private the registration bypass.
- Require explicit active membership for customer-user creation.
- Apply the mandatory target-user boundary to password, MFA, federated identity, and session
  operations.
- Prevent customer flows from assigning `admin` or other platform roles.
- Remove platform roles from customer APIs, presenters, and QML role selectors.
- Stop default-tenant and startup-membership fallback in SaaS mode only after login and restore
  establish explicit context.
- Make current role and user boundary helpers fail closed.
- Tenant-scope user and role catalogs.
- Remove tenant creation and global tenant listing from `tenant_admin`.
- Preview and deliberately apply the policy reconciliation that removes stale seeded
  permissions.
- Disable recurring admin promotion only after replacement provisioning is operational.
- Add audit records for assignment, revocation, membership, context switch, and denial.

Exit criteria:

- no customer API/UI can create a global administrator
- no user without active membership can enter a tenant
- Tenant A authority cannot remain cached after switching to Tenant B
- sensitive user-security operations cannot target another tenant
- existing overpowered system-role rows are reconciled

### Phase 2: Canonical membership and role-binding schema

Status: In progress only for membership compatibility-column retirement and optional public
adapters. Additive role metadata, tenant-safe role namespaces, the structurally
constrained `role_bindings` table, explicit delegation persistence and guarded mutation,
membership lifecycle, internal authorized invitation orchestration, and direct platform/tenant
plus explicit organization-role authority cutover are implemented. Internal tenant custom-role lifecycle commands are
implemented, but no external delivery or public invitation/role adapter has been enabled.
Canonical `org_viewer`/`org_member` role definitions and their direct cutover are implemented,
retiring the legacy organization scoped-grant path entirely. Canonical project-scope roles
(`project_viewer`/`project_contributor`/`project_lead`/`project_owner`) and their direct cutover
are also implemented. Canonical site-scope roles (`site_viewer`/`site_operator`/`site_manager`),
canonical storeroom-scope roles (`storeroom_viewer`/`storeroom_operator`/`storeroom_manager`),
and canonical maintenance-scope roles (`maintenance_viewer`/`maintenance_operator`/
`maintenance_scope_manager`) and their direct cutovers are all implemented too. **Every resource
scope this program identified (organization, project, site, storeroom, maintenance) is now
canonical; none remain on the legacy `ScopedAccessGrant`/`ProjectMembership` path.**
Project-, site-, storeroom-, and maintenance-role assignment remains fail-closed in any
environment until the reviewed `tools/provision_scope_delegations.py` catalog is applied. It has
been applied to the reset local development database; other environments require the same
explicit operator action. Legacy authority and transition-code deletion are complete.

- Extend membership lifecycle fields. Implemented additively with internal token issuance,
  authenticated acceptance, administrative transitions, targeted session invalidation, and
  atomic membership audit. External delivery and public adapters remain pending.
- Remove role authority from membership. Implemented for authorization; compatibility columns
  remain persisted and require a dedicated follow-up migration.
- Add tenant-aware role metadata.
- Add tenant custom-role commands with curated permission ceilings, optimistic updates,
  non-destructive retirement, targeted session invalidation, and atomic audit.
- Add canonical role-binding table and constraints.
- Treat the existing preparation/evidence implementation as superseded transition code. It was
  not executed against development data and has been deleted.
- Implement the permanent canonical resolver and direct platform, tenant, organization, and
  resource cutover packages without dual-write or fallback. Platform and tenant packages are
  complete for platform, tenant, organization, and every identified resource role.
- Reset/reseed development databases explicitly after code cutover, then drop legacy and
  transition runtime schemas before first release. Implemented for the local development
  database and represented by the cleanup migration for every environment.

Exit criteria:

- every effective customer grant has an explicit tenant and scope
- development fixtures and seeds create only valid canonical rows
- every decision and mutation uses canonical authority without a legacy fallback
- canonical denial never falls back to a legacy allow
- no `RBAC-TRANSITION-ONLY`, migration-mode, migration-evidence, or legacy-authority runtime code
  remains

Current Phase 2 foundation:

- `UserTenantMembership` now validates `invited`, `active`, `suspended`, and `removed` states,
  invitation issuer/expiry/acceptance/revocation metadata, transition legality, and positive
  optimistic versions.
- Membership reinvitation, acceptance, suspension, reactivation, revocation, and removal reuse
  the one `(user_id, tenant_id)` row. Duplicate repository `add()` now fails explicitly rather
  than silently ignoring a lifecycle conflict.
- Membership repository admission and customer user catalogs still require `status=active`
  together with the compatibility `is_active` flag. The duplicate flag and `tenant_role` remain
  persisted compatibility columns after the authority-table cleanup; `tenant_role` is not read
  as authorization. A follow-up migration must move all membership admission to `status`, remove
  both fields from domain/ORM/mappers, and drop both columns.
- Alembic revision `6f1a9c2e8d4b` adds lifecycle metadata and constraints, conservatively maps
  legacy inactive rows to `suspended`, and has migration-created upgrade, backfill,
  downgrade, and re-upgrade coverage on SQLite.
- Alembic revision `7a2b3c4d5e6f` adds unique one-time invitation-token hashes. Pre-token
  invitations are conservatively retired because they cannot be accepted securely.
- `TenantMembershipService` authorizes invitation issue/revoke and membership
  suspend/reactivate/remove against active tenant context, actor membership, target identity,
  customer/platform boundaries, and self-lockout protection.
- Invitation acceptance is authenticated-user scoped, clears the token hash, and atomically
  creates only the canonical tenant `viewer` binding. Custom invitation roles remain gated
  until reviewed delegation permission activation and an approved adapter exist.
- Suspension and removal revoke persisted sessions whose active context is the affected tenant;
  removal also revokes unrevoked canonical bindings for that tenant.
- Membership mutations and their tenant-level SOC 2 audit entries commit together. The service
  is wired internally and emits in-app notifications, but intentionally has no desktop/HTTP
  invitation adapter or external delivery channel.
- `Role` and `roles` now carry tenant ownership, display name, allowed scope type,
  assignability, lifecycle status, policy version, and timestamps.
- Existing system role metadata is deterministically classified during migration:
  `admin`/`support_admin` are platform-scoped and non-customer-assignable, `org_admin` is
  organization-scoped, and remaining managed templates are tenant-scoped.
- `RoleBinding` validates platform, tenant, and resource scope shapes before persistence.
- `role_bindings` enforces user principals, tenant/resource nullability rules, positive
  versions, foreign keys, and separate partial unique indexes for active platform, tenant, and
  resource grants.
- `RoleBindingRepository` provides exact-context active reads and filters expired/revoked rows.
- `AuthorizationMigrationBatch`, `LegacyRoleBindingMigrationRecord`, the offline planner, and
  guarded preparation service were implemented under the former production-data migration plan
  and have been deleted. Revision `9c4d5e6f7a8b` remains immutable migration history; cleanup
  revision `c1e2a3n4u5p6` drops its runtime tables.
- System role names are unique in the platform namespace; custom role names are unique per
  tenant. Explicit repository methods preserve the platform and tenant role namespaces.
- `RoleDelegationPolicy` pins actor role, assignable role, tenant, scope, role policy version,
  and permission-set hash. Permission changes require explicit policy review.
- `RoleGovernanceService` enforces `auth.role.assign`, customer/platform separation, active
  memberships, applicable canonical actor scope, explicit delegation, tenant/resource
  ownership, and SoD before canonical assignment. Expired exact-scope rows are revoked before
  reassignment, and successful mutations are atomically audited.
- `RepositoryBundle` exposes canonical binding and delegation repositories for permanent
  canonical authority paths.
- `TenantRoleAdministrationService` provides internal tenant-scope custom-role create, list,
  full-replacement update, and retirement commands. Managed system names are reserved;
  platform-only permissions and SoD conflicts are denied; changes advance `policy_version`;
  permission changes revoke affected tenant sessions; retirement revokes active canonical
  bindings; and each mutation commits with its tenant audit event.
- `PrincipalBuilder`, tenant query methods, customer tenant-role assignment/revocation, login,
  restore, tenant switching, organization switching, and runtime session revalidation now use
  canonical platform/tenant authority without legacy fallback. Explicit organization roles are
  also canonical and generic registration/role APIs reject them without an explicit scope.
  `org_viewer`/`org_member` are now canonical too, and the legacy organization scoped-grant
  path is retired. `CanonicalRoleResolver.resolve_principal_authority()` now also resolves
  project scope, `AccessControlService` writes/reads project grants through
  `RoleGovernanceService` instead of `ScopedAccessGrant`/`ProjectMembership`. The same is now
  true for site, storeroom, and maintenance scope. All five identified resource/organization
  scopes are canonical. Reviewed delegation provisioning has been applied to the reset local
  development database and remains an explicit per-environment operator action.

### Phase 3: Principal and authorization-engine cutover

Status: Complete for principal and authorization-engine authority cutover. The complete
legacy/canonical dependency map, permanent canonical
effective-authority resolver, and platform/tenant/organization-role (including
`org_viewer`/`org_member`) plus project-, site-, storeroom-, and maintenance-role authority
cutovers are all implemented. Every resource scope this program identified now resolves
principal authority exclusively from canonical `role_bindings`. Runtime migration modes,
fallbacks, transition markers, and legacy authority persistence have been deleted. Delegation
catalog application remains a deliberate per-environment deployment action.

- Replace the containment builder with principal construction over canonical bindings and
  explicit tenant and organization context.
- Validate membership, tenant status, and resource ownership during construction.
- Route login restore and context switch through the canonical builder.
- Expand `AuthorizationEngine` to evaluate tenant, resource, and delegation context.
- Replace role-name admin checks with explicit platform authority.
- Make tenant-wide versus resource-limited authority explicit.
- Revoke/refresh affected sessions after role or membership changes.

Exit criteria:

- stale authority cannot survive tenant or organization switching
- missing context denies in SaaS mode
- authorization decisions are centralized and structured

### Phase 4: Service, repository, audit, and background hardening

Status: In progress. Canonical scoped-access/project-membership authority migration and
tenant-aware authority resolvers are complete. Repository-wide scoping consolidation,
background/artifact qualification, and durable audit/outbox completion remain open.

- Replace containment target-user guards with canonical authorization-engine decisions.
- Migrate scoped access and project membership authority. Implemented.
- Harden module entitlement tenant scope.
- Consolidate repository scope support and remove dynamic helper variants.
- Scope organization/site resolvers and remaining collaboration queries.
- Add tenant and actor context to activity and runtime execution.
- Tenant-qualify cache keys, queued work, imports, exports, temporary files, and generated report
  metadata.
- Implement durable security audit/outbox semantics.
- Align ORM nullability with migrations and add migration-created schema tests.

Exit criteria:

- all service and repository paths enforce the same tenant decision
- background and reporting paths retain tenant context
- privileged changes have durable audit evidence

### Phase 5: Customer custom roles and enterprise identity

Status: In progress at internal application-service level. Tenant custom-role lifecycle,
delegation ceilings, invitation/suspension flows, MFA, and federated identity primitives exist;
customer adapters, ownership transfer/break-glass, SCIM, and service principals remain open.

- Add tenant-owned custom role management using fixed permissions.
- Add delegation policy administration with safe ceilings.
- Add invitation, suspension, ownership transfer, and break-glass workflows.
- Add SSO/SCIM integration against membership and role-binding APIs.
- Add service accounts/API keys with tenant, scope, expiry, rotation, and audit.

Exit criteria:

- custom roles cannot exceed the creator's delegable authority
- human and non-human principals share the same authorization boundary

### Phase 6: Hosted PostgreSQL defense in depth

Status: Deferred until Phases 1 through 4 are stable.

- Make all Alembic migrations PostgreSQL-compatible.
- Introduce transaction-local verified tenant context.
- Add default-deny RLS policies to tenant-owned tables.
- force RLS for the application execution role where appropriate
- test pool reset, transaction reuse, migrations, backup, support, and batch processing
- run cross-tenant penetration and concurrency tests

Exit criteria:

- application tests pass with and without RLS enforcement
- no application connection uses table-owner or `BYPASSRLS` authority

## First Implementation Tranche

The first code tranche should be intentionally narrow and reversible:

1. Add characterization and security regression tests for login, restoration, tenant switching,
   role creation/assignment, and sensitive target-user operations.
2. Implement and test the one-time audited platform-owner provisioning command.
3. Add `PM_DEPLOYMENT_ENV` and `PM_TENANCY_MODE=saas|local_single_tenant` with production
   fail-fast configuration and one `TenantContextPolicy` boundary.
4. Establish explicit tenant context during login/restoration and atomically rebuild the legacy
   principal for an authorized target tenant during tenant switching; quarantine ambiguous
   global customer-admin roles.
5. Make missing context deny in SaaS mode, then remove default-tenant and startup-membership
   fallback from that mode.
6. Remove direct registration role binding and the public permission bypass; require an explicit
   active membership for customer-user creation.
7. Tenant-scope user catalogs and password, MFA, federated identity, and session administration.
8. Remove platform roles from customer desktop APIs, presenters, QML selectors, and assignment
   validation.
9. Dry-run, review, and deliberately apply the versioned `tenant_admin` permission
   reconciliation.
10. Disable recurring startup administrator promotion after replacement provisioning and
    rollback tests pass.

This tranche contains the highest-risk paths without forcing an immediate destructive schema
cutover. Steps 1 and 2 are mandatory predecessors: fail-closed context changes must not ship
without regression coverage, default-tenant fallback must not be removed before login and
session restoration supply explicit context, and startup promotion must not be disabled before
replacement provisioning is proven.

### First tranche progress

| Step | Status | Evidence |
| --- | --- | --- |
| Security characterization/regression tests | Implemented for the current containment tranche; broader matrix ongoing | `test_tenancy_rbac_immediate_containment.py` covers cross-tenant account operations, missing context/infrastructure, self-service targeting, onboarding, customer role restrictions, tenant-scoped catalogs, grant replacement, and failed-switch atomicity. |
| One-time platform-owner provisioning | Implemented; canonical platform authority | `src/core/platform/auth/application/platform_owner_provisioning_service.py` and `tools/provision_platform_owner.py`; SaaS composition no longer creates/promotes the configured username. A fresh owner receives one canonical platform binding, while an existing owner missing bootstrap policy authority fails for operator recovery rather than being silently repaired. |
| Deployment/tenancy configuration | Implemented; migration mode removed | `src/infra/platform/security_config.py` consumes only deployment environment and tenancy mode; the obsolete authorization migration switch is absent from runtime, tools, tests, and `.env`. |
| Single tenant-context policy boundary | Implemented; broader consumers pending | `src/core/platform/tenancy/context_policy.py` and `TenantContextService` |
| Explicit login/restoration context and atomic principal rebuild | Implemented | `principal_builder.py`, `authentication_service.py`, `session_service.py`, and `TenantContextService` |
| Authorization denial/context-switch evidence | Shared and inventoried post-gate boundaries implemented | Permission, scoped-permission, resource-anchor, target membership, delegation, permission-ceiling, SoD, support-context, and tenant/organization switch denials use the typed isolated writer. Switch success commits persisted session context and audit before principal replacement; writer failure never changes deny to allow. |
| SaaS missing-context denial and fallback removal | Implemented | Login/restoration supplies validated explicit context. SaaS composition does not create/select a default tenant or organization and does not backfill user memberships; local desktop behavior is isolated by mode. |
| Registration bypass removal and membership onboarding | Implemented for direct onboarding and internal existing-user invitations; public adapter pending | `AuthService.register_user()` no longer exposes a permission bypass. `onboard_tenant_user()` creates the account, active membership, default `viewer` binding, and forced password change in one transaction. In-app notification and token-free self-acceptance services exist, but no desktop/HTTP adapter exposes the pending-invitation flow. |
| Sensitive target-user boundary | Implemented | Password, MFA, federated identity, session, user-admin, and role-assignment paths use `target_user_authorization.py`. |
| Scoped-grant containment | Canonical migration complete | Grant reads and mutations use canonical role bindings with active tenant context, target membership, and tenant-aware resource resolvers. Missing context or resolver infrastructure denies instead of broadening access. |
| Schema-aware authorization inventory | Permanent tenant-isolation inventory retained; transition evidence deleted | `python -m tools.inventory_tenancy_rbac` remains useful for schema/isolation checks. The transition manifest verifier, runbook, and evidence-only branches were removed. |
| Reversible binding migration preparation | Superseded and deleted | The classifier, review contract, preparation service/repository/tables, CLI, and focused transition tests were removed after direct cutover. |
| Membership lifecycle schema | Internal orchestration implemented; compatibility cleanup/public adapter pending | Explicit states, one-time token hashes, one-row transitions, optimistic updates, active-status admission, internal authorization, authenticated acceptance, targeted session invalidation, atomic membership audit, and canonical default `viewer` creation are implemented. `tenant_role` and duplicate `is_active` remain non-authoritative persisted compatibility fields. |
| Platform-role removal from customer paths | Implemented as containment; canonical role scope metadata pending | Customer desktop/API/QML paths exclude and reject `admin`, `support_admin`, and organization-scoped `org_admin`; customer user catalogs are active-tenant scoped. |
| Platform tenant provisioning/catalog authority | Implemented | Tenant create/global get/list and lifecycle operations require `platform.admin`; `tenant_admin` no longer receives `tenant.create`, `tenant.manage`, or `tenant.read`, and provisioning no longer creates a customer membership for the platform operator. |
| Versioned system-role reconciliation | Implemented; policy-v2 environment apply pending | Policy v2 adds reviewed `auth.role.assign` authority, while deterministic preview, guarded transactional apply, system-role version stamping, session invalidation, append-only ledger migration, rollback artifact, and operator CLI are implemented. Existing databases require reviewed dry-run/apply. |
| Recurring startup-promotion removal | Implemented for SaaS | Hosted SaaS creates immutable permission/role definitions only and never mutates reviewed role-permission bindings during startup. Local admin creation and full additive policy seeding remain solely in explicitly configured `local_single_tenant` mode, and its platform binding is canonical. |
| Canonical role metadata/binding schema | Authority cutover complete; customer adapter pending | `RoleBinding`, role scope/ownership metadata, system and per-tenant role namespaces, curated tenant custom-role commands, optimistic role policy versions, explicit version/hash-pinned delegation policy, guarded canonical assignment/revocation, exact-scope expiry materialization, ORM/mappers/repositories, database checks, and revisions `b5c6d7e8f9a0`/`8b3c4d5e6f7a` are active. Revision `9c4d5e6f7a8b` is immutable history; its runtime tables were dropped by the cleanup revision. |

Implementation ledger, 2026-07-27:

- Added centralized parsing for `PM_DEPLOYMENT_ENV`, `PM_TENANCY_MODE`, and
  `PM_AUTHORIZATION_MIGRATION_MODE`.
- Production now rejects an omitted tenancy mode at configuration load.
- Added `SaaSTenantContextPolicy` with no default-tenant fallback and
  `LocalSingleTenantContextPolicy` preserving local desktop behavior.
- Added a one-time platform-owner provisioning service and CLI that never promotes an existing
  ordinary username, rejects ambiguous owners, is idempotent for the same owner, and writes a
  platform-level audit row in the owner-creation transaction.
- Added platform audit persistence without customer tenant context specifically for platform
  provisioning.
- Added explicit-target tenant repository reads for scoped grants and project memberships;
  principal construction no longer derives authority from mutable current-session repository
  scope.
- Login and session restoration now validate saved tenant/organization ownership, select the
  single valid initial context when appropriate, clear an invalid organization gracefully, and
  reject an invalid tenant context.
- Tenant and organization switching now build target authority first and replace principal plus
  context in one session operation. A failed rebuild preserves the prior principal and context.
- Legacy `tenant_admin` is effective only for one unambiguous active membership; multiple
  memberships deny switching. Legacy `org_admin` is effective only with an explicit
  organization binding or grant in the target tenant.
- Password, MFA, federated identity, persisted-session, user-administration, and role-assignment
  target checks now deny when authentication, active tenant, actor membership, target
  membership, or authorization infrastructure is missing.
- Password, MFA, federated identity, account activation/profile, and account-unlock success
  mutations now persist explicitly scoped security audit rows in the same transaction. Audit
  infrastructure or scope failure rolls the mutation back.
- Registration, tenant onboarding, local bootstrap account/role repair, and legacy role
  assignment/revocation now persist their security audit rows inside the owning transaction.
  Idempotent role no-ops do not emit misleading mutation events.
- Login success, known-user failure counters/lockout, standalone authentication denials, session
  policy changes, and persisted-session revocation now use explicit transaction-owned security
  audit writes with denial-preserving failure behavior.
- Self-service password change can target only the authenticated user.
- Removed role selection from `UserCreateCommand`, the user presenter, and create-mode QML.
  Customer account creation now uses a dedicated active-tenant onboarding operation, assigns
  only `viewer`, creates the active membership atomically, and requires password change at first
  sign-in.
- Removed the public `bypass_permission` argument. Legacy bootstrap now calls a private,
  composition-only registration helper while the recurring bootstrap cutover remains pending.
- Added a transitional role-scope policy. Customer role catalogs and mutations exclude or reject
  platform roles (`admin`, `support_admin`) and roles requiring a narrower explicit scope
  (`org_admin`).
- Tenant-scoped customer user catalogs now use `UserRepository.list_for_tenant()`, require
  explicit context plus active actor membership, and hide legacy platform operators. Platform
  operators retain their separate global catalog behavior.
- Customer role assignment/revocation now requires both actor authorization and active target
  membership in the selected tenant. Missing `TenantContextService` or membership
  infrastructure denies instead of degrading to an unscoped operation.
- Tenant provisioning and the global tenant catalog now require `platform.admin` exclusively.
  The platform operator is no longer added as a customer tenant member merely because they
  provisioned a tenant.
- Removed `tenant.create`, `tenant.manage`, and `tenant.read` from the managed `tenant_admin`
  template. Customer tenant administrators retain tenant-local membership, organization,
  settings, user, and role administration only.
- Added policy v1 reconciliation with deterministic drift preview, optimistic version/hash
  guards, a persisted append-only ledger, inverse rollback JSON, and affected-user session
  invalidation. The CLI authenticates a platform operator and cannot apply without a separate
  rollback artifact path.
- Verified the new Alembic head `a4b5c6d7e8f9` against an isolated migrated SQLite database;
  the `auth_policy_reconciliations` table and expected columns were created.
- Added policy-reconciliation tests covering dry-run immutability, exact stale-binding
  detection, authorization, version/hash rejection, successful apply, ledger persistence,
  rollback data, session revocation, and idempotent re-preview.
- Split composition bootstrap by tenancy mode. SaaS now initializes no legacy administrator,
  default customer tenant, default organization, active customer context, or user membership.
  The local desktop mode keeps those conveniences behind `local_single_tenant`.
- Added startup regression tests proving a fresh SaaS database remains customer-context empty,
  an existing ordinary `admin` username is not promoted or backfilled, and local desktop
  initialization remains compatible.
- Added the Phase 2 canonical role-binding foundation. Role definitions now persist explicit
  scope/ownership metadata, while canonical grants persist tenant and actual resource scope
  with database constraints and duplicate-active-grant protection.
- Verified Alembic revision `b5c6d7e8f9a0` from revision zero against an isolated SQLite
  database, verified the canonical table, role columns, and partial unique indexes, and passed
  an upgrade/downgrade/re-upgrade round trip.
- Added eight canonical domain/persistence tests and verified 142 focused authentication,
  startup, tenant-authority, reconciliation, containment, and canonical-foundation tests.
- Verified the CLI twice against an isolated migrated database: create followed by idempotent
  no-op.
- Added nine onboarding/catalog/role-containment regression cases and verified 32 directly
  affected desktop, presenter, QML, and tenancy/RBAC tests.
- At the 2026-07-27 checkpoint, the complete platform suite had 516 passing tests and three
  unrelated failures in untouched code: two site date-time normalization failures and one
  stale QML route expectation for the existing `platform.tenants` route.
- Legacy administrator/default-customer bootstrap remains available only in the explicitly
  configured local single-tenant mode.

Implementation ledger, 2026-07-29:

- Re-audited tenancy and authorization authority across platform and module services,
  repositories, composition, desktop and HTTP adapters, QML, sessions, migrations, runtime
  execution, activity, entitlements, audit, and security tests. Phases 0, 1, and 2 remain in
  progress.
- Made legacy scoped-grant reads and mutations fail closed on missing tenant context, missing
  target membership, missing resolver infrastructure, and cross-tenant resource ownership.
  Organization, site, project, storeroom, and maintenance resolvers now receive and validate
  the active tenant explicitly.
- Added `python -m tools.inventory_tenancy_rbac`, a read-only, schema-aware inventory command
  with deterministic snapshot hashing, legacy-binding classification, canonical/schema
  capability reporting, scoped-grant ownership findings, guarded CI thresholds, and
  non-overwriting artifact output.
- Ran the inventory against the configured desktop database without applying migrations. It
  confirmed revision `z3a4b5c6d7e8`, no deployed canonical binding table, no critical data
  finding, and the three high-severity review findings recorded below.
- Accepted ADR-003 for deployment modes, administrative boundaries, canonical scopes,
  transition gates, evidence ownership, rollback, and audit retention. Acceptance freezes the
  target decision but does not complete the operational Phase 0 evidence.
- Restricted authorization migration configuration to the only implemented mode,
  `LEGACY_AUTHORITATIVE`. The three reserved canonical modes now fail at configuration load
  and again at service composition rather than silently behaving as legacy authority.
- Verified 38 focused security, startup, inventory, access, and desktop API tests. The complete
  platform suite now has 525 passing tests and the same three unrelated failures in untouched
  code: two site date-time normalization failures and one stale QML route expectation for the
  existing `platform.tenants` route.

Membership lifecycle foundation ledger, 2026-07-30:

- Added the additive tenant-membership lifecycle foundation while preserving legacy decision
  authority. Membership state now supports `invited`, `active`, `suspended`, and `removed`
  with issuer, expiry, acceptance, suspension, revocation, removal, and optimistic-version
  metadata.
- Added validated one-row transitions for invite acceptance, suspension, reactivation,
  invitation revocation, removal, and reinvitation. Expired invitations deny acceptance.
- Changed duplicate membership creation from a silent no-op to an explicit
  `USER_TENANT_MEMBERSHIP_EXISTS` conflict. Local single-tenant bootstrap now checks row
  existence and does not implicitly reactivate a suspended row.
- Made membership admission and tenant-scoped user catalogs require lifecycle `active` status
  as well as the transitional `is_active` flag.
- Added revision `6f1a9c2e8d4b` with lifecycle checks, invitation issuer foreign-key integrity,
  conservative legacy backfill, and indexed status/expiry queries. Verified migration creation
  from revision zero and a legacy-row upgrade/downgrade/re-upgrade round trip.
- Updated the authorization inventory to report partial lifecycle schemas accurately and to
  classify active memberships using lifecycle status when deployed.
- Verified 99 focused membership, migration, login-context, tenant-switch, containment, SaaS
  startup, and platform-owner tests. Public invitation orchestration, session invalidation,
  durable membership audit, and role-binding assignment are intentionally not claimed.
- The complete platform suite has 531 passing tests and the same three unrelated baseline
  failures: two site-domain offset-naive/offset-aware datetime comparisons and one stale QML
  route expectation that omits the existing `platform.tenants` route.

Membership orchestration ledger, 2026-07-30:

- Added unique, one-time invitation-token hashes. Only the hash is persisted; successful
  acceptance and administrative revocation clear it, and replay is denied.
- Added an internal `TenantMembershipService` for tenant-scoped issue, acceptance, revocation,
  suspension, reactivation, and removal. Administrative paths require `auth.manage`, active
  tenant context, active actor membership unless the actor is the explicit platform operator,
  target-user validation, customer/platform separation, and self-lockout protection.
- Invitations are limited to 30 days. Issuance and acceptance fail closed for users carrying
  ambiguous non-`viewer` legacy roles, preventing membership activation from reviving hidden
  global privilege, and suspension/removal protects the last effective tenant administrator.
- Acceptance is restricted to the authenticated invited user and atomically activates the
  membership, writes the canonical tenant `viewer` binding, preserves the transitional legacy
  `viewer` binding, and persists the tenant audit event.
- Suspension/removal invalidate persisted sessions currently scoped to the affected tenant.
  Removal also revokes unrevoked canonical bindings for that tenant; unrelated tenant sessions
  are not globally invalidated.
- Added revision `7a2b3c4d5e6f`, migration-created token-schema and pre-token retirement tests,
  service-graph wiring, inventory awareness, and rollback tests proving failed audit persistence
  leaves invitation activation and role bindings unchanged.
- Verified 84 focused lifecycle, migration, authorization, session, audit, containment,
  service-architecture, and SaaS-startup tests. The complete platform suite has 542 passing
  tests and the same three unrelated baseline failures documented above.
- External delivery, public desktop/HTTP adapters, account creation from invitations, custom
  invitation roles, customer custom-role administration, delegation-policy activation, and
  canonical authorization reads remain pending.

Role-governance implementation ledger, 2026-07-30:

- Added role ownership invariants: system definitions require `tenant_id IS NULL`, tenant
  custom definitions require `tenant_id IS NOT NULL`, and customer roles cannot use platform
  scope.
- Replaced global role-name uniqueness with separate system and `(tenant_id, name)`
  namespaces. Legacy `RoleRepository.get_by_name()` now resolves system definitions only;
  explicit tenant lookup/list methods prevent ambiguous cross-namespace reads.
- Tenant role catalogs now use explicit tenant-scoped repository reads. The legacy
  name-based assignment selector intentionally offers only system templates, so tenant custom
  roles cannot leak across tenants or be misrouted before the future ID-based adapter exists.
- Added `RoleDelegationPolicy` with explicit actor role, assignable role, tenant, target scope,
  reviewed role policy version, and a SHA-256 snapshot of the assignable permission set.
  Permission drift therefore invalidates the policy instead of silently widening delegation.
- Added an internal `RoleGovernanceService` that requires `auth.role.assign`, active actor and
  target memberships, applicable canonical actor scope, explicit delegation, role ownership,
  tenant-aware resource resolution, and SoD validation before canonical assignment.
- Customer role assignment rejects platform operators outside a future governed support
  context. Canonical assignment/revocation and delegation-policy mutations write security
  audit rows in the same transaction as the mutation.
- Expired exact-scope bindings are materialized as revoked before canonical reassignment, so
  the existing unrevoked-row unique indexes no longer permanently block the guarded path.
- Added revision `8b3c4d5e6f7a` and migration-created SQLite upgrade/downgrade coverage for
  role namespaces and delegation persistence.
- Added `auth.role.assign` to the immutable permission definitions and policy v2 for
  `admin`, `tenant_admin`, and `org_admin`. This is code policy only: hosted startup does not
  grant it, and every deployed environment still requires reviewed preview/apply evidence.
- Split hosted catalog initialization from additive role-permission seeding. SaaS startup now
  creates missing role and permission definitions without adding or removing any reviewed
  role-permission binding; explicit local single-tenant bootstrap retains full convenience
  seeding.
- A newly provisioned platform owner receives only `platform.admin`, which is sufficient to
  preview and apply system policy. Existing owners missing that bootstrap authority fail with
  an operator-recovery error instead of receiving a silent recurring privilege repair.
- Successful reconciliation stamps every managed system role with the target policy version in
  the same transaction as binding changes, session invalidation, and the append-only ledger.
  Existing version/hash-pinned delegation approvals therefore become stale after policy
  release.
- No delegation row, custom-role adapter, desktop action, or HTTP route is enabled by this
  preparation. The guarded service remains fail closed without an explicit reviewed
  delegation policy.
- Verified 32 focused bootstrap/provisioning/reconciliation/governance tests and 192 broader
  tenancy/RBAC tests. The complete platform suite has 559 passing tests and only the same three
  unrelated baseline failures documented above: two site naive/aware datetime failures and
  one stale QML platform-route expectation.

Tenant custom-role administration ledger, 2026-07-30:

- Added an internal `TenantRoleAdministrationService`; no QML presenter, desktop API, HTTP
  route, or public invitation adapter resolves these commands.
- Custom roles are tenant-owned and tenant-scope only in this tranche. Names are immutable,
  managed system names are reserved, and platform operators are denied from the ordinary
  customer path without a future governed support context.
- Role administrators require both `auth.manage` and policy-v2 `auth.role.assign`, active
  tenant context, an active tenant, active actor membership, and an active canonical
  tenant-scope binding whose role carries both permissions. Organization-scoped or legacy-only
  authority cannot administer tenant-wide roles. This keeps the service dormant until policy
  v2 and canonical role preparation are deliberately completed.
- The assignable permission ceiling is the reviewed union of non-platform system-role
  permissions. Unknown codes, platform-only authority, and role-level SoD conflicts are
  rejected before persistence.
- Updates use full permission-set replacement and compare-and-swap `policy_version`. Every
  accepted definition change advances the version, conservatively invalidating prior
  version/hash-pinned delegation review.
- Permission changes revoke persisted sessions currently operating in the affected tenant for
  active role holders. Retirement is non-destructive, disables assignment, advances policy
  version, and revokes all unrevoked canonical bindings for that tenant role.
- Create, update, and retirement audit events are tenant-scoped SOC 2 records in the same
  transaction as role, permission, binding, and session changes. Audit failure rolls the
  aggregate mutation back.
- No schema revision was required because the role ownership, lifecycle, policy version,
  permission binding, and canonical role-binding columns already exist at Alembic head
  `8b3c4d5e6f7a`.
- Verified 14 direct tenant custom-role tests and 206 broader tenancy/RBAC tests. The complete
  platform suite has 573 passing tests and only the same three unrelated baseline failures
  documented above. All 10 applicable service architecture guards pass; the separately
  reported PM task-lifecycle size budget (`400 > 360`) remains an unrelated baseline failure.

Credential and account-security audit ledger, 2026-07-30:

- Added an explicit `AuditRepository` dependency to `AuthService` for transaction-owned
  security audit persistence. Selected mutations no longer call the shared helper that commits
  after the business change and swallows audit failures.
- Password change, forced reset, administrative reset, MFA provision/enable/disable, federated
  identity link, account activation, profile update, and account unlock now add the audit row
  before the service transaction commits.
- Customer events require validated active tenant scope and retain the active organization
  when present. A real platform operator with no customer context writes a platform-scoped
  event; a non-platform operation with missing scope fails closed.
- Missing audit infrastructure, invalid scope, or audit persistence failure rolls back user,
  credential, MFA, federated identity, and persisted-session changes. Domain events and
  in-memory principal refresh occur only after commit.
- Events include actor, target entity, tenant/organization or platform scope, action, outcome,
  severity, and SOC 2 classification. Password material, MFA secrets, and federated subjects
  are never included in metadata.
- Registration/onboarding, legacy `user_roles` assignment, login success/failure and lockout,
  and session administration were moved to atomic writers in the following tranches. General
  authorization denials and tenant/organization context switches still have no durable
  security event and remain pending.
- No schema revision was required; the existing `audit_entries` table and explicit
  tenant/platform repository methods support the transactional path.
- Verified 8 direct atomic security-audit tests and a 170-test auth, session, tenancy,
  membership, canonical-role, custom-role, reconciliation, and owner-provisioning regression
  matrix. The complete platform suite has 581 passing tests and only the same three unrelated
  baseline failures: two site offset-naive/offset-aware datetime comparisons and the stale
  platform QML route expectation for the implemented `platform.tenants` route.
- Source compilation and diff-integrity checks are clean, Alembic still has the single head
  `8b3c4d5e6f7a`, and the combined service architecture run has 17 passing checks with only the
  previously documented PM task-lifecycle size-budget failure (`400 > 360`).

Registration, bootstrap, and legacy-role audit ledger, 2026-07-30:

- User registration now stages the user, requested legacy role bindings, optional tenant
  membership, and SOC 2 audit event in one transaction. Tenant onboarding therefore cannot
  leave an account, role, or membership behind when audit persistence fails.
- An explicit registration tenant is retained as the event tenant. A different active context
  can target that scope only for the canonical platform operator; organization scope is cleared
  rather than copied from another tenant.
- The local first-start administrator event uses an explicit `system` actor and platform scope.
  The private `commit=False` bootstrap path no longer triggers a hidden audit commit; startup
  owns the final transaction and emits the authority-change event only after commit.
- Repairing a missing local bootstrap `admin` role is also platform-scoped and atomic. Audit
  failure leaves the pre-repair state unchanged.
- Legacy `user_roles` assignment and revocation add the audit row before commit, roll back the
  binding on failure, record role old/new semantics, and emit domain events only after commit.
  Existing assignment and absent revocation are idempotent no-ops without false audit events.
- Events contain the actor, target user, canonical role names, tenant/platform scope, outcome,
  and severity. Password values and hashes, MFA material, and federated subjects are excluded.
- This closes the transaction-durability gap but does not make `user_roles` tenant-aware or
  canonical. The broad internal `register_user()` fixture/bootstrap surface also remains
  separate from the reviewed tenant onboarding adapter and must not become a hosted HTTP API.
- No schema revision was required. Verified 10 direct rollback/scope/system-actor tests and an
  expanded 180-test security matrix. The complete platform suite has 591 passing tests and only
  the same three unrelated baseline failures documented above.

Authentication and session audit ledger, 2026-07-30:

- Replaced the best-effort `record_auth_event()` path with a dedicated transaction-owned
  authentication writer. It does not require or fabricate an authenticated principal: the
  credential claimant is recorded as an `authentication_subject`.
- Successful password and federated authentication now stage user login state, persisted
  session, and `auth.login.success` together. Audit or transaction failure rolls everything
  back and returns the safe `AUTH_AUDIT_UNAVAILABLE` domain error instead of exposing a raw
  repository exception to QML.
- Known-user password and MFA failures stage the failure counter, lockout timestamp, and
  `auth.login.failed` event together. If audit persistence fails, those writes roll back but the
  original `AUTH_FAILED`, `AUTH_MFA_REQUIRED`, or `AUTH_MFA_FAILED` denial is preserved.
- Unknown-user, inactive-user, and already-locked attempts perform a separate durable denial
  write because there is no successful business transaction to join. Writer failure is logged,
  rolled back, and can never convert the denial into an authenticated session.
- Known subjects use their validated restorable tenant/organization scope. Unknown subjects are
  platform-scoped. Federated audit identity uses the normalized provider or known username and
  never records the federated subject, password, MFA secret, or submitted MFA code.
- Expired lock reset is no longer committed as a separate pre-authentication mutation; it joins
  the eventual successful-login or failed-attempt transaction.
- Session timeout-policy changes, revoke-all, and single persisted-session revocation now add
  their SOC 2 event before commit and roll back user revisions and session rows on failure.
  Repeating an already completed single-session revocation is an idempotent no-op without a
  duplicate event.
- Session context persistence and validation heartbeats remain operational state rather than
  privileged audit events. Explicit tenant/organization context-switch auditing remains a
  separate pending package.
- Authentication entry-point decisions remain in `authentication_service.py`; transaction,
  context-restoration, lockout-state, persisted-session, and audit orchestration are isolated in
  `authentication_transactions.py`. This keeps the public service API stable without returning
  to a monolithic authentication module.
- No schema revision was required. Verified 11 direct authentication/session rollback,
  denial-preservation, scope, and redaction tests; the expanded security matrix has 191 passing
  tests. The complete platform suite has 602 passing tests and only the same three unrelated
  baseline failures. Both external PM lockout/session integration tests pass; three other tests
  in that file retain their unrelated missing-tenant-membership fixture failures.
- Architecture verification has 96 passing checks. Its two open size-budget failures are outside
  this package: the 400-line PM task lifecycle exceeds its 360-line migration budget, and the
  1,388-line enterprise calendar domain exceeds the 1,200-line hard limit.

Authorization-denial and context-switch audit ledger, 2026-07-30:

- Added a typed `SecurityDenialEvent` at the shared authorization boundary.
  `require_permission()`, `require_any_permission()`, and scoped permission checks now emit
  actor, session, current tenant/organization, required permissions, operation label, reason,
  and attempted scope before preserving the existing denial code and message.
- Production composition wires those events to `DurableSecurityDenialRecorder`. It opens an
  isolated SQLAlchemy session, writes an explicitly tenant- or platform-scoped SOC 2 event,
  includes the current trace ID when available, commits independently, and closes the session.
  It never calls commit or rollback on the caller's business session.
- Denial-audit failure is logged at critical severity and never changes deny to allow. Missing
  recorder wiring is also a critical operational condition, while lightweight session adapters
  that do not implement the audit capability retain their existing fail-closed behavior.
- Tenant and organization authority rebuilds now pass through
  `AuthService.commit_context_switch()`. Persisted auth-session context and the target-scoped
  success event commit together before the in-memory principal changes. Audit/session failure
  rolls back and returns the safe `CONTEXT_SWITCH_AUDIT_UNAVAILABLE` domain error.
- Switch success records old/new tenant and organization IDs, actor, session, target scope,
  outcome, SOC 2 classification, and trace ID. Repeating the same effective context refreshes
  authority without producing a false duplicate switch event.
- Failed tenant/organization attempts use the isolated denial writer, preserve the original
  `TENANT_ACCESS_DENIED`, `PERMISSION_DENIED`, context, lifecycle, or authentication error, and
  retain the attempted scope only as denial metadata. SaaS mode refuses a successful switch
  when the audited context committer is not configured.
- This tranche covers shared permission gates, shared scoped-permission gates, and all
  `TenantContextService` tenant/organization switch outcomes. The inventoried explicit
  post-gate resource, membership, delegation, SoD, permission-ceiling, and support-context
  decisions are completed in the 2026-07-31 ledger below.
- No schema revision was required. Verified 10 direct scope, trace, redaction, durability,
  failure-preservation, idempotency, and rollback tests; the expanded security matrix has 201
  passing tests. The complete platform suite has 612 passing tests and only the same three
  unrelated baseline failures. Architecture verification remains at 96 passing checks with the
  same two unrelated size-budget failures.

Post-gate authorization-denial ledger, 2026-07-31:

- Added `authorization_denied()` as the single audit-and-raise boundary for explicit decisions
  that occur after a shared permission gate. It emits exactly one typed event and then preserves
  the existing `BusinessRuleError` message and code; `record_authorization_denial()` remains
  available where the existing contract is a `ValidationError`, including SoD.
- Migrated active-tenant actor and target-user membership checks, self-service targeting,
  scoped-grant membership/resolver infrastructure, tenant membership self-lockout and
  last-administrator safeguards, invitation target/role safety, registration membership-writer
  availability, customer/platform role ceilings, canonical role scope and delegation policy,
  custom-role permission ceilings, and legacy/canonical SoD decisions.
- Platform operators attempting ordinary customer role administration now produce explicit
  `authorization.support_access.denied` evidence. This does not introduce support impersonation
  or customer access; governed support sessions remain a later capability and the operation
  continues to fail closed.
- Added a shared maintenance resource-scope denial helper and migrated all 17 services that
  reject unanchored records or organization-wide libraries for scope-restricted principals:
  documents, preventive plans/tasks/templates, downtime, failure codes, integration sources,
  sensors/readings/mappings/exceptions, work requests, work orders/tasks/steps, and material
  requirements.
- Events identify actor/session and stored tenant/organization context, operation, reason, and
  only the opaque attempted target or scope. Invitation tokens, passwords, MFA values,
  delegation hashes, and other submitted secrets are not recorded. Isolated-writer failure is
  still logged critically and never converts a denial to an allow.
- Not-found, malformed-input, inactive-record lifecycle, concurrency, and invitation-expiry
  failures remain ordinary domain outcomes rather than authorization evidence. Principal-build
  explicit-context failures remain owned by the enclosing audited login/restoration/context
  boundaries, preventing duplicate records.
- No schema revision was required. Direct authorization, canonical governance, and membership
  verification has 36 passing tests; the expanded scoped-access/RBAC/containment matrix has 88
  passing tests. The complete platform suite has 614 passing tests and only the same three
  unrelated baseline failures: two Site naive/aware datetime comparisons and the stale QML
  route expectation that omits implemented `platform.tenants`. The maintenance suite has 168
  passing tests and one unrelated end-of-month floating-schedule assertion (`October 30`
  versus `October 31`). Architecture verification remains at 96 passing checks with the same
  two unrelated size-budget failures.

ADR-003 operational-evidence tooling ledger, 2026-07-31:

- Added a strict, immutable Pydantic manifest contract for one-step authorization transitions.
  It rejects unknown fields, sensitive keys, credential-bearing references, malformed hashes,
  naive timestamps, transition skipping, insufficient retention, same-person approvals, and
  internally inconsistent backup, restore, rollback, revision, version, or policy claims.
- Added offline artifact verification for the before/post tenancy-RBAC inventories, reviewed
  role-policy preview, rollback artifact, and apply receipt. Every local artifact is SHA-256
  checked before its embedded inventory or policy hash/version is trusted.
- Enforced ADR-003's minimum 2,555-day privileged-evidence and 400-day authorization-evidence
  retention, separate Platform Operations and Security approvers, Security ownership of
  retention approval, non-source restore rehearsal, rollback replay, and session-rebuild
  evidence.
- Enhanced `tools.reconcile_role_policy` so evidence files are never overwritten. An apply now
  requires distinct rollback and receipt paths; the post-commit receipt binds runtime security
  mode, application version, applied policy hash/version, invalidated-session count, and
  rollback-artifact digest.
- Added `tools.verify_authorization_transition_evidence` to produce an immutable
  `ready_for_review` receipt without database access or mode promotion. The verifier proves
  integrity and consistency, not external backup immutability or human truthfulness.
- Added `ADR-003_OPERATIONAL_EVIDENCE.md` with ownership, safe command order, failure handling,
  pre/post-apply boundaries, and the explicit prohibition on treating an environment-variable
  change as authority-data rollback. `.security-evidence/` is excluded from source control.
- Repository-side evidence-contract verification has 21 passing focused policy, tamper,
  retention, approval, transition, redaction, receipt, and reconciliation tests. No schema
  revision or deployed-environment operation was performed.

Reversible binding-migration foundation ledger, 2026-07-31:

- Added the searchable `RBAC-TRANSITION-ONLY` lifecycle marker to temporary legacy models,
  repositories, writes, reads, principal construction, migration controls, and evidence
  tooling. The decommission register above defines deletion gates and retained artifacts.
- Added an architecture guardrail that compares every discovered transition marker with the
  exact transition-component registry. Unregistered temporary code and stale registry entries
  both fail the suite. Final cleanup must remove the registered components, their focused tests,
  and this temporary guardrail in the same change, leaving zero transition markers outside this
  historical plan.
- Added validated migration batches and immutable per-row legacy snapshots. Source fields are
  bound to a deterministic SHA-256 digest; quarantined rows cannot claim a resolved scope or
  canonical binding, and migration-ready rows require an explicit reviewer and valid scope
  shape.
- Added constrained ORM/repository persistence and revision `9c4d5e6f7a8b`. Source identifiers
  intentionally are not foreign keys so rollback evidence survives later legacy-row retirement.
  No source row is copied, inferred, modified, or used for an authorization decision.
- Added domain, repository, migration creation, downgrade, and re-upgrade coverage. The focused
  foundation suite has 5 passing tests, including direct database rejection of an unreviewed
  migration-ready row.
- The combined role governance, membership lifecycle, runtime configuration, SaaS startup,
  inventory, policy reconciliation, transition evidence, and migration-foundation selection
  has 61 passing tests. Architecture verification is now 98 passing checks with the same
  two unrelated baseline size failures.

Superseded binding-migration preparation ledger, 2026-07-31:

- The inventory classifier, reviewed-plan format, preparation persistence, operator CLI, and
  focused tests were completed under the former assumption that live customer role rows had to
  be preserved.
- No environment migration, review, preparation apply, canonical backfill, dual-write, or
  authority cutover was performed, so no customer evidence or rollback state must be retained.
- These components are now deletion inventory, not operator procedure. They must not be run.
- Permanent inventory checks that detect tenant/scope violations may be retained only after all
  legacy-table and transition-evidence coupling is removed.

Direct canonical resolver and platform-authority ledger, 2026-07-31:

- Added `CanonicalRoleResolver` as permanent application code. It resolves active canonical
  bindings only, validates role/binding scope agreement and tenant ownership, requires an
  explicit tenant-ownership resolver for resource bindings, ignores inactive roles and
  expired/revoked bindings, and separates tenant-wide permissions from resource-limited
  permissions.
- Organization bindings contribute authority only when their organization is the active
  organization, while their scoped row remains available for validated context selection.
- Platform operators are denied ordinary customer context in SaaS. The explicit
  `local_single_tenant` composition profile retains its local administrator exception.
- Platform-owner provisioning and local bootstrap now write only canonical platform bindings.
  Platform principal/query reads and system-policy affected-user discovery read canonical
  platform bindings. Generic registration and role mutation reject every role whose persisted
  scope is `platform`.
- Legacy `admin`/`support_admin` rows are filtered from principal and query authority. A focused
  regression proves that a stale `user_roles` admin row grants neither the role name nor
  `platform.admin`.
- Focused resolver tests pass 7/7; owner/privilege platform tests pass 41/41; affected audit,
  reconciliation, membership, and startup tests pass 34/34; broader changed-boundary tests pass
  62/62. Architecture verification remains 98 passing with the two unrelated baseline size
  failures. The full platform run exceeded its five-minute limit after 88%; its last-failed set
  contains only two existing Site naive/aware datetime failures and an unrelated platform QML
  route expectation.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.

Direct tenant-authority cutover ledger, 2026-07-31:

- Added tenant-only canonical resolution that consumes active platform/tenant bindings but
  deliberately ignores organization/resource bindings until their ownership-aware cutover.
- Broad registration is identity-only by default. Direct tenant onboarding creates explicit
  membership and canonical tenant authority; invitation acceptance creates only its canonical
  `viewer` binding. Membership `tenant_role` is compatibility data, not an authorization source.
- Customer tenant-role assignment and revocation route through `RoleGovernanceService`, require
  active target membership, enforce delegation, SoD, scope, audit, and session invalidation, and
  never mutate or fall back to `user_roles` for tenant authority.
- Tenant role and permission queries, principal construction, login, restore, tenant and
  organization switching, and runtime session revalidation resolve canonical tenant authority.
  A stale or cross-tenant legacy role cannot grant tenant permission during those paths.
- Local single-tenant platform administration enters the same governed customer-role mutation
  path through an explicit composition policy. SaaS platform operators remain unable to use
  ordinary customer context or customer role administration.
- `TenantMembershipService` has no remaining transition authority dependency and was removed
  from the exact transition-component registry. Explicit organization/resource role reads and
  writes remain marked transition-only for the next tranche.
- The platform suite passes 642 tests with three known unrelated baseline tests deselected: two
  Site naive/aware datetime failures and one stale platform QML route expectation. The exact
  transition inventory guard passes separately after removal of the stale membership entry.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.

Direct organization-role cutover ledger, 2026-07-31:

- Added an organization-only canonical resolution path. It validates organization ownership,
  exposes every canonical organization scope for context selection, and activates the role and
  its permissions only when that organization is the active context. Other resource bindings
  are ignored until their dedicated resolvers and role catalogs are ready.
- Principal construction now combines canonical platform, tenant, and explicit organization
  roles. Login, restore, organization switching, and runtime revalidation therefore rebuild
  `org_admin` from canonical bindings without any `user_roles` read or fallback.
- Generic registration and role assignment/revocation now reject organization/resource roles
  with `ROLE_SCOPE_REQUIRED`. Explicit scoped assignment remains owned by
  `RoleGovernanceService`, which validates tenant ownership, target membership, delegation,
  SoD, audit, and session invalidation.
- Removed `UserRoleRepository` from `AuthService`, `AuthQueryMixin`, registration, role mutation,
  principal construction, and policy reconciliation. Reconciliation now discovers holders of
  every non-platform role through canonical bindings across tenants.
- Removed `AuthQueryMixin`, registration, and role-assignment components from the exact
  transition registry. Principal construction remains registered only because generic
  scoped-grant/project-membership projection is still transitional.
- Organization characterization passes 22 tests, including active-vs-other-organization
  authority and proof that a forged legacy organization row grants neither `org_admin` nor
  `org.manage`. The extended platform suite passes 644 tests with the three known unrelated
  baseline tests deselected and 12 SQLite datetime-adapter deprecation warnings. Architecture
  verification passes 99 checks; its two failures are the existing PM task-lifecycle 360-line
  growth budget and enterprise-calendar 1,200-line hard limit.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.

Organization viewer/member cutover ledger, 2026-07-31:

- Added canonical `org_viewer` and `org_member` role definitions (policy version bumped to 3)
  reusing the existing `viewer`/`team_member` permission sets, and generalized
  `EXPLICIT_SCOPE_ROLE_NAMES`/`system_role_scope_type` so both seed as organization-scoped
  system roles alongside `org_admin`, with no other change needed for ordinary additive
  startup seeding to pick them up.
- Retired the legacy organization `ScopedAccessGrant` policy entirely: removed the
  `organization` `ScopedRolePolicy` registration from `AccessControlService`, and deleted
  `src/core/platform/tenancy/access_policy.py` (its `ORGANIZATION_SCOPE_ROLE_CHOICES`,
  `normalize_organization_scope_role`, `resolve_organization_scope_permissions`). The desktop
  runtime never wired `"organization"` into `PlatformAccessDesktopApi`'s scope-type choices, so
  no customer-visible admin panel used this path; retiring it only changes internal/test-level
  behavior.
- `principal_builder.py` now drops any legacy `"organization"` scoped-access entry before
  merging, so a pre-existing (or forged) `scoped_access_grants` row at organization scope can
  no longer grant authority; canonical `role_bindings` are the sole organization-scope source.
- `RoleGovernanceService.assign_role`/`revoke_role_binding` (already scope-generic) are now the
  only way to grant an organization role, for all three roles (`org_admin`, `org_viewer`,
  `org_member`) alike. No delegation policy is seeded for any of them, so assignment remains
  fail-closed/dormant until an explicit reviewed delegation policy is created, matching the
  existing `org_admin` precedent; no desktop/QML adapter is wired yet either.
- Added policy-level, seeding, `build_principal`, and cross-tenant-rejection tests for
  `org_viewer`/`org_member` mirroring the existing `org_admin` characterization tests, plus a
  regression test proving a legacy organization `ScopedAccessGrant` row now grants zero
  authority. Verified 113 focused RBAC/access/bootstrap/desktop-API tests across the directly
  and indirectly affected files with no regressions.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.

Project-scope cutover ledger, 2026-07-31:

- Added canonical `project_viewer`/`project_contributor`/`project_lead`/`project_owner` role
  definitions (policy version bumped to 4), copied verbatim from the existing
  `PROJECT_SCOPE_ROLE_PERMISSIONS` sets in `src/core/modules/project_management/access/policy.py`
  so the effective permission grants are unchanged. `EXPLICIT_SCOPE_ROLE_NAMES`/
  `system_role_scope_type` now split explicitly between organization-scoped and
  project-scoped names.
- Unlike organization scope, project-scope assignment is a real, live desktop feature
  (project_service.list_projects() is wired into the Admin Console's Roles & Access screen) with
  a real downstream dependency: PM collaboration `@mention` resolution reads project membership
  directly. `RoleGovernanceService.assign_role` requires an active `RoleDelegationPolicy`, and no
  delegation policy is auto-seeded anywhere in this codebase, so a naive redirect would have
  fail-closed every existing project-assignment action.
- Added a reviewed, dry-run-by-default provisioning mechanism instead of auto-seeding:
  `ScopeDelegationProvisioningService` (preview/apply, hash-pinned against a code-owned
  `DEFAULT_SCOPE_DELEGATIONS` catalog) and `tools/provision_scope_delegations.py`, mirroring the
  existing system-role-policy reconciliation tool's discipline. The catalog currently covers
  `access_admin` (today's only customer-facing `access.manage` holder) delegating each of the
  four project roles, as global (`tenant_id=None`) policies — `RoleDelegationPolicyRepository`
  already falls back to global policies when no tenant-specific one exists, so one policy per
  role pair covers every tenant.
- Registered a `"project"` scope-tenant resolver on both `RoleGovernanceService` and
  `CanonicalRoleResolver` (via a new `register_scope_tenant_resolver`/
  `register_canonical_scope_tenant_resolver` pair, reusing the same tenant-ownership lambda
  already registered on `AccessControlService`), since only `AccessControlService` had one before.
- Cut over `AccessControlService.assign_scope_grant`/`remove_scope_grant`/`list_scope_grants`/
  `list_user_scope_grants` for `scope_type="project"` to read/write canonical `role_bindings`
  through `RoleGovernanceService`, translating results back into the legacy
  `ScopedAccessGrant` shape so the existing desktop API/QML contract keeps working unchanged
  (`_CANONICAL_SCOPE_TYPES` marks which scope types have cut over; the translation itself is
  `RBAC-TRANSITION-ONLY` and will be deleted once the adapters consume canonical role names
  directly).
- Added `CanonicalRoleResolver.resolve_principal_authority()` (platform/tenant/organization plus
  an explicit `cutover_resource_scope_types` set) and switched `principal_builder.build_principal`
  to it, dropping legacy `"project"` scoped-access rows before merging so canonical bindings are
  project scope's sole authority source. `resolve_organization_authority` is left unchanged for
  its existing callers/tests.
- Found and fixed a real regression during verification: `CollaborationSupportMixin._list_mention_
  candidates_for_project` read project membership directly from the legacy
  `ProjectMembershipRepository` (`project_memberships` table), which
  `SqlAlchemyScopedAccessGrantRepository.add()` used to keep in sync via an internal redirect for
  `scope_type="project"`. That redirect is bypassed entirely once assignment writes
  `role_bindings` instead. Added canonical `role_repo`/`role_binding_repo` reads to
  `CollaborationService`, used whenever both are wired (real composition always wires them now);
  the legacy read remains only for test-double constructions that do not.
- Added policy-level, seeding, `build_principal`, project-scope-isolation, and legacy-grant
  (`ScopedAccessGrant` and `ProjectMembership`) no-authority regression tests mirroring the
  organization-scope tranche, plus `RoleGovernanceService` project-assignment and
  unresolvable-scope tests, plus delegation-provisioning preview/apply/hash-mismatch/
  missing-role tests. Verified 109 focused tests across every directly and indirectly affected
  file (including the fixed collaboration regression) with no other regressions; the one
  remaining failure encountered (`test_no_python_module_exceeds_hard_line_limit` picking up the
  local `pmenv/` virtualenv) is a pre-existing environmental artifact unrelated to this work.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.
  Delegation policies remain unprovisioned until an operator deliberately runs
  `tools/provision_scope_delegations.py --apply`; project-role assignment stays fail-closed until
  then, matching the fail-closed-until-reviewed posture used throughout this program.

Site-scope cutover ledger, 2026-07-31:

- Added canonical `site_viewer`/`site_operator`/`site_manager` role definitions (policy version
  bumped to 5), copied verbatim from the existing `SITE_SCOPE_ROLE_PERMISSIONS` sets in
  `src/core/platform/site/access_policy.py`. `EXPLICIT_SCOPE_ROLE_NAMES`/`system_role_scope_type`
  now also recognize the three site-scoped names.
- Site scope was structurally simpler to cut over than project: research confirmed
  `SqlAlchemyScopedAccessGrantRepository` has no site-specific dual-table redirect (unlike
  project's `ProjectMembership` special case), and an exhaustive search found no downstream
  consumer reading site membership directly outside `AccessControlService`/`AuthService` — no
  hidden bypass analogous to the collaboration `@mention` regression found during the project
  cutover. Site scope is still a live desktop feature, though (unconditionally wired into
  `PlatformAccessDesktopApi`'s scope-type choices, with a real DB-backed end-to-end test already
  covering it), so the same delegation-policy blocker as project applies.
- `RoleGovernanceService`/`AccessControlService` already shared a `"site"` `scope_exists_resolvers`
  entry (`platform_registry.py`), but `CanonicalRoleResolver`'s separate
  `canonical_scope_tenant_resolvers` dict did not; added a `"site"` entry there (same
  tenant-ownership check, duplicated inline to match the existing convention already used for
  `"organization"` in that same dict).
- Extended `DEFAULT_SCOPE_DELEGATIONS` with `access_admin` → `site_viewer`/`site_operator`/
  `site_manager`, global (`tenant_id=None`) policies, provisioned the same reviewed
  dry-run/apply way as the project-scope entries.
- Added `"site"` to `AccessControlService._CANONICAL_SCOPE_TYPES` and
  `principal_builder._CUTOVER_RESOURCE_SCOPE_TYPES` — both are the generic mechanisms already
  built during the project cutover, so no new branching logic was needed in either file.
- Found and fixed one test-only regression during verification (no production bypass, matching
  the audit's finding above): `test_tenant_switch_rebuilds_only_target_tenant_grants` inserted
  raw legacy `ScopedAccessGrantORM(scope_type="site", ...)` rows to test tenant-switch
  containment: correctly, those no longer confer authority once site is canonical. Switched the
  test to `scope_type="storeroom"` (still legacy), preserving its original containment-testing
  intent.
- Added policy-level, seeding, `build_principal`, site-scope-isolation, and legacy-grant
  no-authority regression tests mirroring the project-scope tranche, plus `RoleGovernanceService`
  site-assignment and unresolvable-scope tests. Verified 141 focused tests across every directly
  and indirectly affected file (including the fixed containment test) with no other regressions;
  the same pre-existing `pmenv/` virtualenv line-count artifact noted in the project-scope ledger
  is unrelated to this work.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.
  Site-role assignment stays fail-closed pending deliberate delegation-policy provisioning, same
  as project scope.

Storeroom-scope cutover ledger, 2026-07-31:

- Added canonical `storeroom_viewer`/`storeroom_operator`/`storeroom_manager` role definitions
  (policy version bumped to 6), copied verbatim from `STOREROOM_SCOPE_ROLE_PERMISSIONS` in
  `src/core/modules/inventory_procurement/access/policy.py`. `EXPLICIT_SCOPE_ROLE_NAMES`/
  `system_role_scope_type` now also recognize the three storeroom-scoped names.
- Storeroom's `ScopedRolePolicy` is registered in `src/infra/composition/inventory_registry.py`
  (a module-specific registry, like project's, not directly in `platform_registry.py` like
  site's). That same file already registered a `"storeroom"` `scope_exists_resolver` on
  `AccessControlService` only; found and fixed the same gap the project cutover already fixed
  once for project — added the matching `role_governance_service.register_scope_exists_resolver`
  and `auth_service.register_canonical_scope_tenant_resolver` calls, reusing the existing
  `_storeroom_exists` closure for both.
- Extended `DEFAULT_SCOPE_DELEGATIONS` with `access_admin` → `storeroom_viewer`/
  `storeroom_operator`/`storeroom_manager`, global (`tenant_id=None`) policies.
- Added `"storeroom"` to `AccessControlService._CANONICAL_SCOPE_TYPES` and
  `principal_builder._CUTOVER_RESOURCE_SCOPE_TYPES` — both already generic from the project
  cutover, so no new branching logic was needed.
- An exhaustive downstream-consumer search found no hidden bypass and no dual-table trick for
  storeroom (same as site); every inventory/procurement module read goes through the shared
  `filter_scope_rows`/`SessionAuthorizationEngine` path, not a direct repository query.
- Found and fixed two test-only regressions, both self-inflicted: during the site cutover we'd
  picked `scope_type="storeroom"` as the "still-legacy" example scope for
  `test_access_scope_domain_validation.py`'s fake-harness entity-validation test and for
  `test_tenancy_rbac_immediate_containment.py`'s tenant-switch containment test (which inserts
  raw `ScopedAccessGrantORM` rows). Both needed to move once storeroom itself became canonical.
  Migrated both to `scope_type="maintenance"` — the one remaining legacy resource scope — adding
  a fake `maintenance` `ScopedRolePolicy`/resolver to the domain-validation test's harness.
- Added policy-level, seeding, `build_principal`, storeroom-scope-isolation, and legacy-grant
  no-authority regression tests mirroring the site-scope tranche, plus `RoleGovernanceService`
  storeroom-assignment and unresolvable-scope tests. Verified 157 focused tests across every
  directly and indirectly affected file with no other regressions; the same pre-existing
  `pmenv/` virtualenv line-count artifact noted in prior ledger entries is unrelated to this
  work.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.
  Storeroom-role assignment stays fail-closed pending deliberate delegation-policy provisioning,
  same as project and site scope. **Maintenance is now the only remaining legacy resource
  scope.**

Maintenance-scope cutover ledger, 2026-07-31:

- **This closes the resource-scope cutover: organization, project, site, storeroom, and
  maintenance are all now canonical.** Maintenance was the last remaining scope on the legacy
  `ScopedAccessGrant` path.
- Found a genuinely new gap this cutover's research surfaced (not present for any earlier
  scope): `RESOURCE_ROLE_SCOPE_TYPES` in `src/core/platform/auth/domain/role_binding.py` did not
  include `"maintenance"` at all — confirmed by direct grep, not just the research agent's word,
  before acting on it. Without this, `CanonicalRoleResolver._require_resource_ownership` would
  reject every maintenance role binding with `AUTH_ROLE_BINDING_SCOPE_INVALID`. Added
  `"maintenance"` to the frozenset.
- Found a second genuinely new problem: the naming convention `{scope_type}_{scope_role}` used
  to mint canonical role names for every prior scope collides for maintenance specifically —
  `"maintenance_manager"` already names a pre-existing, unrelated, tenant-wide system role (a
  broader operational role, distinct from `_MAINTENANCE_MANAGER`/`_MAINTENANCE_ADMIN`'s existing
  permission set). Renaming or touching that existing role was out of scope for this cutover.
  Instead: named the new resource-scoped roles `maintenance_viewer`/`maintenance_operator`/
  `maintenance_scope_manager` (only the top tier needed to diverge), and added a small
  `_CANONICAL_ROLE_NAME_OVERRIDES` lookup to `AccessControlService` so the external `scope_role`
  string API (`"viewer"`/`"operator"`/`"manager"`, unchanged, still validated by the untouched
  `MAINTENANCE_SCOPE_ROLE_CHOICES` policy) still maps correctly to the differently-named
  canonical role under the hood. Verified permission sets are disjoint from the pre-existing
  tenant-wide role and that it isn't customer-assignable through the generic path.
- Maintenance's module registry (`src/infra/composition/maintenance_registry.py`) had the exact
  same gap the storeroom cutover already found and fixed once: only `AccessControlService` had a
  `"maintenance"` scope-existence resolver registered, not `RoleGovernanceService` or
  `AuthService`/`CanonicalRoleResolver`. Extracted the existing inline lambda into a named
  `_maintenance_entity_exists` function and registered it on all three.
- Extended `DEFAULT_SCOPE_DELEGATIONS` with `access_admin` → `maintenance_viewer`/
  `maintenance_operator`/`maintenance_scope_manager`, global (`tenant_id=None`) policies. Added
  `"maintenance"` to `AccessControlService._CANONICAL_SCOPE_TYPES` and
  `principal_builder._CUTOVER_RESOURCE_SCOPE_TYPES` — both already generic, no new branching
  logic needed.
- An exhaustive downstream-consumer search across the (large) maintenance module — work orders,
  work requests, assets, sensors, preventive plans, downtime events — found every service
  correctly routes through the shared `filter_scope_rows`/`require_scope_permission` helpers,
  same as site and storeroom. No hidden bypass, no dual-table trick.
- Since maintenance was the last real resource scope, its two "still-legacy example scope" test
  uses (inherited from storeroom, which had itself inherited them from site) had nowhere left to
  move to. Migrated both permanently to `"department"` — a `RESOURCE_ROLE_SCOPE_TYPES` member
  with no `ScopedRolePolicy` ever registered in production composition, so it can never be
  cut over and serves as a stable, indefinite legacy-path example for
  `test_access_scope_domain_validation.py`'s fake harness and
  `test_tenancy_rbac_immediate_containment.py`'s tenant-switch containment test.
- Added policy-level, seeding, `build_principal`, maintenance-scope-isolation, legacy-grant
  no-authority, and naming-collision regression tests mirroring the storeroom-scope tranche,
  plus `RoleGovernanceService` maintenance-assignment and unresolvable-scope tests. Verified 185
  focused tests across every directly and indirectly affected file with no other regressions;
  the same pre-existing `pmenv/` virtualenv line-count artifact noted in every prior ledger
  entry in this program is unrelated to this work.
- No application database was migrated, reset, backfilled, or otherwise modified by this work.
  Maintenance-role assignment stays fail-closed pending deliberate delegation-policy
  provisioning, same as project, site, and storeroom scope.

Local dev delegation-policy provisioning ledger, 2026-07-31:

- Provisioned the reviewed `access_admin` → project/site/storeroom/maintenance delegation
  catalog (13 entries) against the local desktop development database for the first time,
  closing out the fail-closed gate in this one environment. Other environments (staging,
  production, or any teammate's separate local database) still need the same explicit,
  reviewed dry-run/apply run before their assignment stops being fail-closed — this is a
  per-environment action, not a one-time code change.
- The local database itself predated the entire canonical `role_bindings` schema (it was at
  Alembic revision `z3a4b5c6d7e8`, exactly the "six revisions behind" state this README already
  documented on 2026-07-29, and had not been touched since). Backed it up, ran the six pending
  migrations in place (preserving existing data; these migrations already have tested
  legacy-row upgrade/downgrade/re-upgrade coverage), then ran ordinary local-single-tenant
  startup composition once to additively seed every role definition added during this session's
  five scope cutovers. No new migration was required — the schema for all of this already
  existed before this session's work began; only new `roles`/`role_permissions` rows needed
  seeding.
- Found and fixed a real bug surfaced by actually running the tool end-to-end for the first
  time: `tools/provision_scope_delegations.py`'s `AuthService` construction omitted
  `security_audit_repo`, so the very first successful login failed at the mandatory
  login-audit write and rolled the whole authentication back
  (`BusinessRuleError: Authentication audit persistence is required.`). Added
  `security_audit_repo=repositories.audit_entry_repo`. Found the identical bug in the
  pre-existing `tools/reconcile_role_policy.py` (same missing parameter, same failure mode)
  and fixed it the same way; confirmed no regressions in its focused test suite.
- No production database was touched. No dev-database reset was performed — data was migrated
  in place, not recreated from scratch, per this session's choice for this specific database.

### Repository re-audit, 2026-07-29

Phases 0, 1, and 2 all remain in progress. The current snapshot was re-audited across domain
models, repositories, migrations, composition, desktop and HTTP adapters, QML callers, session
restoration, scoped access, entitlements, runtime execution, activity, audit, and security tests.
The earlier containment work is real, but it does not yet constitute canonical authorization.

| Area | Verified state | Required follow-up |
| --- | --- | --- |
| Authorization migration mode | The configuration switch remains, but canonical platform/tenant/explicit-organization-role decisions do not use it. Generic scoped-grant/resource projection remains legacy-authoritative. | Delete all migration modes after the scoped direct cutover; do not implement the reserved modes. |
| Security ADR | ADR-003 defines deployment mode, platform authority, and canonical scope types, but its production-data migration evidence sections predate the prelaunch decision. | Update the ADR during cutover to remove staged customer-data migration requirements while preserving security invariants. |
| Legacy role writes | Runtime platform, tenant, and explicit organization-role mutations are canonical; generic auth APIs have no `user_roles` mutation path. The legacy model/repository remains only for superseded migration tooling, schema history compatibility, and deletion-focused tests. | Delete the superseded tooling and runtime schema during final cleanup after resource fixtures are canonical; never dual-write. |
| Registration surface | Broad registration is identity-only by default; explicit tenant onboarding creates membership and canonical authority. Scoped roles are rejected because registration has no resource identifier. | Separate fixture/bootstrap identity creation from production adapters and keep scoped assignment in governed scope-aware commands. |
| Session context | Login, restore, tenant switching, organization switching, and runtime revalidation rebuild canonical platform/tenant/explicit-organization-role authority. Public session ID setters and a fallback organization path can still replace IDs without rebuilding authority. | Restrict raw setters to composition/context internals and remove the fallback after callers use `TenantContextService`; add canonical resource authority. |
| Local default tenant | Local mode resolves `get_default()` as the lexicographically first active tenant. Creating an earlier-sorting tenant can therefore change fallback selection even though explicit session and membership context remain intact. SaaS mode does not use this fallback. | Add an explicit immutable/default designation or deployment setting; do not infer security context from tenant code ordering. |
| Scoped grants | Legacy grant operations now require active tenant context, target membership, and tenant-aware resource ownership resolution. Repository reads and writes fail closed when tenant context is absent. | Keep this containment covered while migrating grants to canonical bindings; add delegation and durable audit semantics before legacy retirement. |
| Organization selection | Creating, updating, or selecting one active organization deactivates the tenant's other organizations. | Separate organization lifecycle from per-session selection; several organizations may remain enabled concurrently. |
| Membership lifecycle | Additive state, one-time token hashes, authenticated internal acceptance, administrative transitions, optimistic persistence, targeted session invalidation, atomic membership audit, and canonical-only fixed `viewer` binding orchestration are implemented. `is_active` and `tenant_role` remain persisted compatibility columns but are not role authority; no external delivery or public adapter exists. | Add reviewed delivery/account-onboarding adapters and remove compatibility columns in the final cleanup migration. |
| Canonical role metadata | System and per-tenant name namespaces, role ownership checks, and internal audited tenant custom-role lifecycle commands are implemented. They require canonical tenant-scope administrative authority and enforce a curated customer permission ceiling, SoD, optimistic policy versions, session invalidation, and non-destructive retirement. No adapter is exposed. | After environment policy-v2 activation, canonical role preparation, and security review, add a request-scoped adapter; keep raw repositories and unrestricted permission mutation private. |
| Canonical binding uniqueness | Partial indexes still define persisted activity as unrevoked, but the guarded canonical assignment path now revokes an expired exact-scope row before reassignment. | Add scheduled/bulk expiry maintenance and require fixtures/imports to use the same canonical orchestration before declaring this complete. |
| Principal authority | The permanent resolver and canonical platform/tenant/explicit-organization-role principal paths are implemented. Generic organization viewer/member and resource grants still enter through the scoped-grant/project-membership projection. | Define deterministic canonical scope-role catalogs, cut over each generic scope package without fallback, then delete the projection. |
| Audit | Membership, canonical role governance and customer tenant-role mutation, tenant custom roles, platform-owner provisioning, credential/account security, registration/onboarding, local bootstrap account/role repair, authentication success/failure/lockout, session administration, shared permission/scope denials, tenant/organization context switching, and inventoried post-gate resource/membership/delegation/SoD/support denials now have explicit evidence semantics. | Preserve one-event ownership at application authorization boundaries and prevent duplicate records when future desktop/HTTP transports add request-scoped middleware. |
| Entitlements/activity/runtime | Entitlement composition omits its tenant provider; activity can become global with missing context; runtime executions have no tenant/organization and global control reads. | Keep these as open isolation work and block hosted completion until tenant-qualified. |
| Transport boundary | Desktop customer role/onboarding paths are constrained. The HTTP adapter has no per-request principal/tenant extraction boundary and reuses application service state. | Require request-scoped identity and tenant context before treating HTTP as a hosted SaaS boundary. |
| Schema verification | Most tests still use `Base.metadata.create_all()`. The Alembic graph has one head, `9c4d5e6f7a8b`; membership lifecycle, token, role namespace, delegation, and reversible migration-record upgrades have migration-created SQLite coverage, but hosted PostgreSQL migration tests are absent. | Expand migration-created coverage across authorization schema profiles and add hosted PostgreSQL. |

The configured desktop database was inspected read-only both manually and with
`python -m tools.inventory_tenancy_rbac`. It was at revision `z3a4b5c6d7e8`, now six revisions
behind the current head, and contained 9 users, 9 active memberships, 9 global legacy role
bindings, 2 legacy `admin` bindings, no duplicate global bindings, no privileged user without
an active membership, and no canonical `role_bindings` table. The tool emitted no critical
data finding and three high-severity review findings: incomplete canonical schema, missing
membership lifecycle schema, and two platform-role holders that also have customer
memberships. This is evidence for that one environment only, not a production-wide result.
The `a4b5c6d7e8f9` policy ledger, `b5c6d7e8f9a0` canonical binding foundation,
`6f1a9c2e8d4b` membership lifecycle foundation, `7a2b3c4d5e6f` invitation-token revision,
`8b3c4d5e6f7a` role-governance revision, and `9c4d5e6f7a8b` reversible migration-record revision
are not a customer-data migration requirement. After canonical code and cleanup migrations are
ready, the development database should be explicitly reset and reseeded rather than backfilled.
No reset is performed automatically by this plan.

Next containment work package:

Completed in the current containment tranche:

- Closed scoped-grant tenant, membership, and ownership-resolver fail-open paths and added
  cross-tenant mutation regression tests.
- Added deterministic, schema-aware, read-only inventory tooling for memberships, legacy
  roles, canonical bindings, and scoped grants. Environment-specific archival and review remain
  operational Phase 0 work.
- Added the lifecycle domain/schema/repository foundation with explicit transitions and
  migration round-trip coverage.
- Added internal authorized token issuance/acceptance/revocation, membership administration,
  targeted session invalidation, atomic membership audit, and canonical-only fixed `viewer` binding
  orchestration. External delivery and public adapters remain disabled.
- Directly cut over tenant onboarding/membership, customer tenant-role mutation, tenant
  principal/query authority, context switching, and session revalidation without dual-write or
  legacy fallback. Broad registration now creates identity only by default.
- Directly cut over explicit organization-role authority. Runtime auth no longer reads or writes
  `user_roles`; stale legacy organization rows grant nothing, and generic APIs require a
  scope-aware governance command.
- Migrated inventoried post-gate resource, membership, delegation, SoD, permission-ceiling, and
  support-context denials to the typed isolated writer without changing their public error
  contracts.
- Defined canonical `org_viewer`/`org_member` role definitions and directly cut over
  organization scope: the legacy `ScopedAccessGrant` policy/path for organization scope is
  retired, `principal_builder` no longer merges legacy organization-scope rows, and
  `RoleGovernanceService.assign_role` is the sole assignment path for all three organization
  roles. No adapter/UI is wired yet (matching the existing `org_admin` state); the legacy
  desktop panel never exposed organization scope, so nothing customer-visible changed.
- Defined canonical `project_viewer`/`project_contributor`/`project_lead`/`project_owner` role
  definitions and directly cut over project scope, a live desktop feature unlike organization
  scope. `AccessControlService` now writes/reads project grants exclusively through
  `RoleGovernanceService`/`role_bindings`, translating results back to the legacy
  `ScopedAccessGrant` shape so the existing desktop API/QML contract is unchanged.
  `principal_builder` no longer merges legacy project-scope rows. Because project-role
  assignment is live and no delegation policy is auto-seeded, added a reviewed
  dry-run/apply provisioning tool (`tools/provision_scope_delegations.py`,
  `ScopeDelegationProvisioningService`) instead of redirecting the write path unconditionally;
  assignment stays fail-closed until an operator deliberately runs it. Found and fixed one real
  regression along the way: PM collaboration `@mention` resolution read project membership
  directly from the legacy `ProjectMembershipRepository`, bypassing the cutover entirely.

Remaining work, in order:

**Every resource scope (organization, project, site, storeroom, maintenance) is now canonical.
No scope remains on the legacy `ScopedAccessGrant`/`ProjectMembership` path.** Remaining work is
no longer per-scope; it is:

1. Provision the reviewed `access_admin` → project-, site-, storeroom-, and maintenance-role
   delegation policies (`tools/provision_scope_delegations.py --apply`) in each remaining
   deployed environment once reviewed, so assignment through the desktop API stops being
   fail-closed there. Done for the local desktop development database (13 policies applied,
   re-applied again on 2026-08-01 after the explicit reset below); still pending for every
   other environment. Check any other environment's migration state before assuming the
   delegation-provisioning tool alone is sufficient.
2. Add the reviewed customer-facing invitation/account-onboarding adapter without exposing raw
   tokens through generic transports. Partially implemented on 2026-08-01: the ports-and-adapters
   `NotificationService` (`src/core/platform/notifications/`) persists in-app notifications and
   can fan out to registered external channels (none exist today). Membership issue/revoke emits
   notifications without raw invitation tokens, while
   `accept_invitation_for_tenant(tenant_id)` and `list_my_pending_invitations()` provide a
   self-scoped token-free application flow. A desktop or HTTP adapter still must expose that flow
   before this customer-facing onboarding item is complete. The bearer-token acceptance method
   remains reserved for a future reviewed out-of-band delivery channel.
3. ~~Update fixtures and seed data, run migration-created and cross-tenant tests, explicitly
   reset development databases, then delete every transition-only and legacy-authority
   component ... and apply a cleanup migration before the first release.~~ **Done on
   2026-08-01.** Fixtures/seed data audited (no production or test-fixture code creates new
   legacy-authority rows outside of the "prove stale legacy rows grant zero authority"
   regression tests, which were removed in this same pass since the rows they proved inert can
   no longer even be constructed). Deleted every `RBAC-TRANSITION-ONLY` component: the 10
   whole-purpose-transition files (evidence runbook, `role_binding_migration.py` domain, the
   3 `infra/security` migration-preparation modules, 2 `tools/*` CLIs, 3 test files); the marked
   partial sections in `collaboration/utils/support.py`, `access_control_service.py`
   (dead legacy scope-grant branches — the canonical translation shim itself stays, since the
   desktop API/QML still consumes the `ScopedAccessGrant` shape), `principal_builder.py`
   (the whole legacy scoped-access merge collapsed to `scoped_access = canonical_authority.scoped_access`
   directly), `auth/contracts`, `auth/domain` (`RoleBindingMigrationRepository`,
   `UserRoleRepository`, `UserRoleBinding`), the `auth` mapper/ORM/repository migration-batch and
   `user_roles` adapters, `infra/composition/repositories.py`, `infra/security/__init__.py` and
   `tenancy_rbac_inventory.py` (the legacy `user_roles` classification block and its four
   findings). Additionally — since the audit proved `ScopedAccessGrant`/`ProjectMembership`
   persistence had no reachable production write path at all (every entry point requires a
   registered `ScopedRolePolicy`, and only project/site/storeroom/maintenance ever have one) —
   deleted that whole persistence layer too, on top of the originally marked registry: the
   `ProjectMembership` domain class, both repository ABCs, both concrete SQLAlchemy repositories,
   their ORM classes and mapper module, and all composition wiring. `ScopedAccessGrant` itself
   stays (still constructed in-memory by the canonical translation shim). Ran the full
   consolidated test suite across every module directory; found and fixed two real regressions
   along the way — `CollaborationSupportMixin._list_mention_candidates_for_project` crashed
   instead of falling back when a caller wired a non-`None`, non-functional
   `tenant_context_service` placeholder, and a stale `test_platform_persistence_structure.py`
   area list — plus updated roughly a dozen test files whose fixtures directly touched the
   removed repos/domain objects. All other failures across the full sweep were pre-existing and
   unrelated (confirmed via diff against this program's changes): a site-domain
   offset-naive/aware datetime bug, a stale QML route assertion, a project-management dashboard
   activity-feed bug, a module-licensing-gate ordering issue in two unrelated import-schema
   tests, the long-standing `pmenv/` vendored-file line-count artifact, one unrelated
   line-budget breach, and date-sensitive `src/tests/pm` scheduling tests unrelated to any
   authorization code. Backed up and deleted the local desktop database entirely, ran migrations
   against the empty file, confirmed zero rows existed in any legacy or canonical authority
   table (only the migration-seeded default tenant row existed), then ran one ordinary startup
   pass and the delegation-provisioning tool again — proving the system builds correct canonical
   state from nothing. Applied one cleanup migration (`b1n2o3t4i5f6` → `c1e2a3n4u5p6`) dropping
   `user_roles`, `scoped_access_grants`, `project_memberships`, `authorization_migration_batches`,
   and `legacy_role_binding_migration_records`; verified upgrade → downgrade → re-upgrade
   round-trips cleanly and applied it to the local dev database.
4. ~~Remove `AuthorizationMigrationMode`, `PM_AUTHORIZATION_MIGRATION_MODE`, mode-gating tests,
   and tool receipt coupling.~~ **Done and independently re-audited on 2026-08-02.** Runtime
   security configuration now contains only deployment environment and tenancy mode. The shared
   test fixture and reconciliation tool no longer consume an authorization migration mode, the
   stale `.env` variable was removed, and an architecture guard scans runtime/tool source for the
   deleted dependencies and transition marker.

Lessons this program's per-scope work surfaced, worth keeping in mind for any future scope
additions:
- A hidden direct-legacy-repository bypass is possible even when `AccessControlService` itself
  is fully cut over — found once, in PM collaboration mention resolution reading
  `ProjectMembershipRepository` directly. Always search the whole codebase for direct
  `scoped_access_repo`/repo-specific reads before declaring a scope's cutover complete, not just
  its `AccessControlService` call sites.
- Module registries can wire a scope-existence resolver onto `AccessControlService` alone and
  forget `RoleGovernanceService`/`CanonicalRoleResolver` — found twice (storeroom, then
  maintenance repeating the identical gap in a different registry file). Both registrations
  must be added together.
- `RESOURCE_ROLE_SCOPE_TYPES` and the canonical role-naming convention
  (`{scope_type}_{scope_role}`) are not guaranteed to already support a new scope or be
  collision-free with pre-existing tenant-wide role names — verify both directly rather than
  assume, as maintenance needed both a new frozenset entry and a role-name override.

### Independent completion audit, 2026-08-02

The re-audit confirms the canonical authority migration is complete, but it does not classify the
entire tenancy/RBAC hardening document as complete:

- Runtime, composition, API/UI, and operator-tool source contains no legacy role/scoped-grant
  repository, migration-mode, transition-marker, or legacy fallback dependency. Immutable
  Alembic history and deliberate DTO naming are excluded from this statement.
- The audit found and removed stale deleted-repository arguments from
  `provision_platform_owner.py`, `provision_scope_delegations.py`, and
  `reconcile_role_policy.py`, plus the stale migration-mode `.env` setting.
- Focused canonical binding, all resource scopes, membership, delegation, context-switch, and
  desktop access verification passed: 187 tests. The new legacy-dependency architecture guard
  and adjacent auth tests passed: 48 tests.
- The full platform suite passed 680 tests. Its three failures are unrelated existing defects:
  two Site offset-naive/offset-aware datetime comparisons and one stale platform QML route
  expectation. The architecture suite has only the existing PM task-lifecycle and enterprise
  calendar line-budget failures.
- `user_tenants.tenant_role` and the duplicate membership `is_active` flag remain in the active
  domain/ORM/mapper/repository path. They do not grant authority, but they are unfinished
  compatibility cleanup and require a migration plus status-only admission tests.
- In-app invitation notification and self-scoped acceptance exist at application-service level,
  but no desktop or HTTP adapter exposes pending-invitation acceptance. This is customer
  onboarding/product work, not a legacy authorization fallback.
- Phases 4-6 remain separate hardening work: repository/background/artifact isolation and durable
  audit completion, enterprise identity/service principals, and hosted PostgreSQL/RLS validation.

## Required Test Matrix

### Cross-tenant isolation

- Tenant A admin cannot list, read, edit, disable, reset, or revoke sessions for Tenant B users.
- Tenant A IDs cannot be used to create children under Tenant B parents.
- Missing tenant context denies list, count, create, update, delete, export, and bulk operations.
- Activity, audit, runtime execution, and entitlement rows are tenant-isolated.
- Production startup fails when tenancy mode is not explicitly configured.
- Local single-tenant policy cannot be selected by a request or database value.

### Role and delegation

- A platform role never appears in a customer role selector.
- Tenant admin cannot create/list tenants or assign a platform role.
- Organization admin authority works only in the bound organization.
- The same user can hold different roles in two tenants without leakage.
- A global `tenant_admin` template produces only a tenant-scoped binding.
- A tenant-owned custom role cannot be bound in another tenant or at a disallowed scope type.
- An actor cannot assign a role containing permissions the actor cannot delegate.
- Possessing a permission does not make that permission delegable.
- SoD checks use effective role permissions and scope.
- Concurrent assignment cannot create duplicate active bindings.
- A canonical denial is never changed to allow by a legacy fallback in any migration mode.

### Membership and session

- Registration alone grants no tenant access.
- Invitation acceptance creates active membership and intended bindings atomically.
- Reinvitation and reactivation update the one membership row rather than creating history rows.
- Suspended/removed membership invalidates current sessions.
- Tenant switch validates membership, re-queries authority, and atomically replaces the principal.
- Ambiguous legacy customer-admin roles deny switching until mapped or revoked.
- Organization switch rejects a resource owned by another tenant.
- Session restoration rejects stale, suspended, or deleted context.
- Re-login is graceful when context cannot be restored.

### Bootstrap and policy

- Platform owner provisioning works only when no owner exists.
- Startup never promotes an existing username.
- System-role reconciliation dry-run reports removals, additions, bindings, users, and session
  impact without mutating data.
- System-role apply requires the expected prior version, records a change-set hash, and can roll
  back.
- Ordinary startup never silently reconciles security policy.
- Legacy ambiguous `admin` rows require explicit review.

### Repository and schema

- ORM-created development shape does not contradict migrated production constraints.
- Migration-based tests run against SQLite and hosted PostgreSQL.
- Composite ownership constraints reject cross-tenant foreign keys.
- Scope resolvers cannot resolve another tenant's organization or site.
- Every role-binding mutation rejects a scope whose resolver cannot prove tenant ownership.
- Cache keys, runtime executions, queued jobs, exports, temporary files, and reports include
  tenant identity.
- A delayed worker rejects work when current membership or authority has been revoked.
- PostgreSQL RLS tests use a non-owner, non-`BYPASSRLS` application role.

### Audit

- Every privileged success and denial records actor, target, tenant, scope, session, outcome,
  reason, and trace.
- A privileged mutation rolls back when its audit outbox intent cannot be persisted.
- Denial-audit failure never changes deny to allow and triggers operational alerting.
- Sensitive values and credentials are never stored in audit payloads.
- Context switch and support access are independently traceable.

## Definition of Done

This program is complete when:

- all customer authority is represented by explicit tenant-aware bindings
- all tenant entry requires active membership
- no platform role is assignable through customer paths
- principal authority is rebuilt after every context change
- all tenant repositories fail closed in SaaS mode
- legacy role and grant authorities are migrated and retired
- security audit is durable and queryable by tenant and platform security operators
- all tenant-owned derived data, artifacts, and background work are tenant-qualified and
  revalidated
- migration-created schemas and cross-tenant tests run in CI
- documentation and customer-facing role terminology match actual behavior
- an independent authorization review finds no known path that relies only on UI hiding,
  default tenant fallback, global role names, or absent scope rows

## Progress Tracker

| Work item | Status |
| --- | --- |
| First team review reconciled with code | Complete |
| Second team doubts reconciled with code | Complete |
| End-to-end tenancy/RBAC source scan and targeted re-audit | Complete for canonical authority on 2026-08-02; repeat after remaining hardening tranches |
| Target model and security invariants | Complete |
| Migration and retirement plan | Complete; revised for direct prelaunch cutover on 2026-07-31 |
| Phase 0 safety net | Complete for the direct prelaunch authority cutover; permanent inventory/characterization retained and superseded evidence tooling deleted |
| Phase 1 immediate containment | Complete for authorization containment; environment provisioning and external channels are rollout concerns |
| Phase 2 canonical membership and role-binding schema | In progress only for `tenant_role`/duplicate `is_active` retirement and optional public invitation/role adapters; canonical authority, local reseed, legacy schema removal, and transition deletion are complete |
| Principal/authorization-engine cutover | Complete; platform, tenant, organization, project, site, storeroom, and maintenance authority is canonical with no legacy fallback |
| Repository/audit/background hardening | In progress; canonical scoped authority is complete, broader repository/background/artifact/audit hardening remains |
| Custom roles and enterprise identity | In progress internally; customer adapters, ownership/break-glass, SCIM, and service principals remain |
| Hosted PostgreSQL RLS | Deferred |

## Standards References

The design is aligned with:

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [AWS SaaS tenant isolation fundamentals](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/tenant-isolation.html)
- [AWS SaaS identity and isolation](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/identity-and-isolation.html)
- [AWS Prescriptive Guidance for multi-tenant API authorization](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-api-access-authorization/introduction.html)
- [PostgreSQL row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

These references support deny-by-default authorization, explicit tenant context, authorization
on every request, session revalidation, security event logging, and database isolation as
defense in depth. The implementation decisions above remain specific to this codebase.
