# Tenancy and RBAC Hardening

Date: 2026-07-27

Status: Approved target architecture; Phase 1 immediate containment is in progress.
Configuration, replacement provisioning, explicit-context principal rebuilding, atomic context
switching, and sensitive target-user boundaries are implemented. Registration, customer-role,
SaaS startup-fallback, canonical-authority, and legacy-startup cutovers remain pending.

Owners: Platform, Security, Persistence, API, Desktop UI, and module teams.

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

No legacy authorization table or path should be deleted until its replacement has been
backfilled, verified, cut over, and covered by tenant-isolation tests.

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

## Authorization Migration Modes

Canonical migration must use one explicit authority mode. Empty canonical results or canonical
denials must never fall back to a legacy allow.

| Mode | Decision authority | Comparison behavior |
| --- | --- | --- |
| `LEGACY_AUTHORITATIVE` | legacy model | canonical data may be written, but does not affect decisions |
| `CANONICAL_SHADOW` | legacy model | canonical decision is calculated and mismatch is recorded |
| `CANONICAL_AUTHORITATIVE` | canonical model | legacy decision is comparison only and can never override |
| `CANONICAL_ONLY` | canonical model | legacy reads and writes are disabled |

Every shadow comparison is categorized:

- `legacy_allow_canonical_deny`: security-critical legacy excess
- `legacy_deny_canonical_allow`: potential canonical migration omission or intended policy change
- `both_allow`
- `both_deny`

Mode changes are deployment operations with audit evidence, health checks, rollback criteria,
and a minimum observation period. A rollback changes the explicit authority mode; it does not
perform per-request fallback. Dual-write failure must be visible and must block security
mutations when the authoritative and migration stores cannot be kept consistent.

## System Role Policy Reconciliation

System-role changes must not be silently applied during ordinary startup. Replace additive
seeding with a deliberate, versioned deployment command:

```text
role_policy_reconcile --dry-run
role_policy_reconcile --apply --expected-version=3
```

The preview must report removed and added permissions, affected bindings, affected active
users, SoD consequences, and sessions that require invalidation. Applying the change records:

- previous and new policy versions
- deterministic change-set hash
- executing principal and deployment trace
- execution timestamp and outcome
- rollback artifact or inverse change set

The command must abort on version mismatch or unexpected drift. Removing overpowered
`tenant_admin` permissions is a reviewed security migration, not a side effect of application
startup.

## Migration and Retirement Matrix

| Legacy item | Target | Retirement gate |
| --- | --- | --- |
| `RegistrationService.assign_roles_for_user()` | checked membership plus role-binding workflow | all callers migrated and registration tests prove no bypass |
| public `bypass_permission` flag | dedicated one-time platform provisioning | bootstrap command and invitation flows operational |
| recurring startup admin promotion | explicit platform-owner provisioning command | verified owner exists and bootstrap audit complete |
| `_PRIVILEGE_RANK` as authority | delegation policy and permission-subset check | assignment/revoke/bulk tests pass |
| `user_tenants.tenant_role` | role bindings only | data migrated and no reads/writes remain |
| legacy `user_roles` | canonical `role_bindings` | backfill parity, explicit-mode shadow comparison, and rollback snapshot complete |
| `scoped_access_grants.permission_codes_json` | role permissions resolved from canonical roles | scoped grants migrated and access parity verified |
| project membership as authorization source | canonical binding with optional projection/facade | PM behavior and reporting tests pass |
| implicit default tenant fallback | explicit SaaS context or configured local mode | every SaaS entry point supplies context |
| startup user-to-default-tenant backfill | migration/onboarding command | existing installations reconciled |
| `_deactivate_other_organizations()` on selection | session-only organization selection | organization lifecycle migration complete |
| duplicate scope helpers | `TenantScopedRepositorySupport` or one typed equivalent | module repositories and contracts migrated |
| role aliases `finance`, `maintenance_admin` | canonical role names | data alias migration and compatibility window complete |
| additive startup role-permission seeding | versioned preview/apply reconciliation command | dry run, expected-version guard, rollback artifact, and session invalidation pass |
| per-request canonical-deny fallback to legacy | explicit migration authority modes | mode transition tests prove legacy cannot override canonical |
| tenant-unqualified runtime executions and artifacts | tenant-qualified execution and storage metadata | worker revalidation and cross-tenant artifact tests pass |
| best-effort swallowed security audit | transactional audit/outbox | failure and recovery tests pass |
| ambiguous `platform_events` | durable integration outbox or removal | ownership and consumers documented, data retained as required |
| insecure tests that expect tenant admin to create/list tenants | scoped admin matrix tests | new policy active and old assertions removed |

Deletion must occur in a later migration after observability confirms the old path is unused.
Do not combine data deletion with initial cutover.

## Implementation Plan

### Phase 0: Safety net and decisions

Status: In progress.

- Freeze new role names and direct role-assignment paths.
- Add an architecture decision record for application mode, platform authority, and canonical
  binding scope types.
- Inventory existing users, memberships, roles, user-role rows, and scoped grants.
- Detect users with global privileged roles but no active membership.
- Detect duplicate/null-scope bindings and cross-tenant scope references.
- Add characterization tests around current login, restore, switch, assignment, and access
  behavior.
- Define and test `PM_AUTHORIZATION_MIGRATION_MODE` with the four explicit authority modes.
- Define `PM_DEPLOYMENT_ENV`, `PM_TENANCY_MODE`, and the tenant-context policy boundary.
- Define backup, rollback, and audit retention requirements.

Exit criteria:

- production data can be classified deterministically
- every direct role write has an owner and migration path
- no destructive migration is scheduled without a rollback artifact

### Phase 1: Immediate containment

Status: In progress. Replacement provisioning, the tenant-context policy foundation,
explicit-context session authority, atomic tenant/organization switching, legacy customer-admin
containment, and sensitive target-user boundaries are implemented. Registration, customer-role,
authority, and startup cutovers remain pending.

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

Status: Not started.

- Extend membership lifecycle fields and remove role authority from membership.
- Add tenant-aware role metadata.
- Add canonical role-binding table and constraints.
- Backfill platform, tenant, organization, and resource bindings.
- Quarantine ambiguous global role rows for operator review.
- Enter `LEGACY_AUTHORITATIVE`, then dual-write new assignments while legacy reads remain
  authoritative.
- Enter `CANONICAL_SHADOW` and classify every decision mismatch.
- Enter `CANONICAL_AUTHORITATIVE` only after reviewed parity and rollback rehearsal.
- Enter `CANONICAL_ONLY` only after the observation window and legacy-write shutdown.

Exit criteria:

- every effective customer grant has an explicit tenant and scope
- ambiguous rows have been reviewed rather than guessed
- canonical and expected legacy decisions match for approved cases
- canonical denial never falls back to a legacy allow

### Phase 3: Principal and authorization-engine cutover

Status: Not started.

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

Status: Not started.

- Replace containment target-user guards with canonical authorization-engine decisions.
- Migrate scoped access and project membership authority.
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

Status: Not started.

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
| Security characterization/regression tests | Implemented for the current containment tranche; broader matrix ongoing | `test_tenancy_rbac_immediate_containment.py` covers cross-tenant account operations, missing context, self-service targeting, grant replacement, and failed-switch atomicity. |
| One-time platform-owner provisioning | Implemented; startup cutover pending | `src/core/platform/auth/application/platform_owner_provisioning_service.py` and `tools/provision_platform_owner.py` |
| Deployment/tenancy/migration configuration | Implemented | `src/infra/platform/security_config.py` |
| Single tenant-context policy boundary | Implemented; broader consumers pending | `src/core/platform/tenancy/context_policy.py` and `TenantContextService` |
| Explicit login/restoration context and atomic principal rebuild | Implemented | `principal_builder.py`, `authentication_service.py`, `session_service.py`, and `TenantContextService` |
| SaaS missing-context denial and fallback removal | Policy denial implemented; startup fallback removal pending | Login/restoration now supplies validated explicit context; composition bootstrap still requires mode-specific cutover. |
| Registration bypass removal and membership onboarding | Pending | Depends on containment tests |
| Sensitive target-user boundary | Implemented | Password, MFA, federated identity, session, user-admin, and role-assignment paths use `target_user_authorization.py`. |
| Platform-role removal from customer paths | Pending | Follows target-user and registration containment |
| Versioned system-role reconciliation | Pending | Design approved; command not implemented |
| Recurring startup-promotion removal | Pending | Replacement command proven; composition cutover still required |

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
- Self-service password change can target only the authenticated user.
- Verified the CLI twice against an isolated migrated database: create followed by idempotent
  no-op.
- Verified 108 focused tests for the current containment package.
- The complete platform suite has 491 passing tests and three unrelated failures in untouched
  code: two site date-time normalization failures and one stale QML route expectation for the
  existing `platform.tenants` route.
- Legacy bootstrap remains enabled deliberately until the next cutover package.

Next containment work package:

1. Remove role selection and the public permission bypass from customer registration.
2. Require explicit active tenant membership through a dedicated invitation/onboarding path.
3. Tenant-scope user and role catalogs and remove platform roles from customer API/UI choices.
4. Remove tenant creation/global tenant listing from `tenant_admin` and implement reviewed
   versioned policy reconciliation.
5. Remove SaaS startup default-tenant/user-membership fallback, then disable recurring legacy
   administrator promotion after rollback and deployment checks pass.

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
| End-to-end tenancy/RBAC source scan and targeted re-audit | Complete |
| Target model and security invariants | Complete |
| Migration and retirement plan | Complete |
| Phase 0 safety net | In progress |
| Phase 1 immediate containment | In progress |
| Canonical role-binding schema | Not started |
| Principal/authorization-engine cutover | Not started |
| Repository/audit/background hardening | Not started |
| Custom roles and enterprise identity | Not started |
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
