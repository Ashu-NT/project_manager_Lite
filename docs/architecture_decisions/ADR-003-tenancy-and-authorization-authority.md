# ADR-003: Tenancy and Authorization Authority

- Status: accepted; implementation in progress
- Date: 2026-07-29

## Context

The application supports a hosted SaaS mode and a local single-tenant desktop mode. It also has
legacy global role assignments, tenant memberships, resource grants, and an additive canonical
role-binding foundation. These mechanisms cannot safely remain implicit or become competing
sources of authority.

The codebase currently enforces several containment controls, but Phases 0, 1, and 2 of the
hardening program remain in progress. In particular,
`PM_AUTHORIZATION_MIGRATION_MODE` is parsed but only legacy authorization decisions are
implemented. Selecting another value does not yet activate canonical behavior.

This ADR freezes deployment mode, administrative boundaries, canonical scope semantics,
migration gates, evidence ownership, and rollback rules. Detailed findings and implementation
progress remain in
[Tenancy and RBAC Hardening](../tenancy_rbac_hardening/README.md).

## Decision

### Deployment Modes

- Hosted production runs only with `PM_TENANCY_MODE=saas`.
- Production must set `PM_TENANCY_MODE` explicitly; it is never inferred from a database URL,
  request, tenant record, or startup data.
- `local_single_tenant` is a separately configured product mode for trusted local use. It is
  not selectable by a user, request, database row, or runtime context switch.
- SaaS mode has no default-tenant fallback. Missing or invalid tenant context denies access.
- Local compatibility behavior remains behind `LocalSingleTenantContextPolicy`; business
  services must not introduce independent local-mode exceptions.

### Authority Boundaries

- A platform operator is platform authority, not a customer tenant administrator.
- Platform roles are not assignable or visible through customer role, membership, API, or UI
  paths.
- A platform operator receives no customer membership merely by provisioning a tenant.
- Customer access by platform support requires a future explicit, reasoned, expiring, and
  audited support session. Permanent or silent impersonation is prohibited.
- Tenant membership establishes eligibility to enter a tenant. It does not grant role
  authority.
- `RoleBinding` is the target persisted grant of role authority. Legacy `user_roles`,
  membership `tenant_role`, scoped grants, and project memberships remain transitional until
  migrated and retired.

Existing `admin` bindings are not automatically promoted to the target platform role. Every
such binding requires operator review. A user holding platform authority and customer
membership is a review case, not automatically an incident and not automatically valid.

### Canonical Scope Model

- `platform`: `tenant_id` and `actual_scope_id` are null.
- `tenant`: `tenant_id` is required and `actual_scope_id` is null.
- `organization` or another registered resource scope: `tenant_id` and `actual_scope_id` are
  required, and a tenant-aware resolver must prove ownership.
- A platform-managed role definition is a reusable template, not a global grant.
- A tenant-owned role definition can be used only in its owning tenant.
- A binding scope must equal the role definition's allowed scope type.
- Missing tenant context, membership infrastructure, or scope resolver denies. Absence of
  scoped rows never implies tenant-wide authority.

Polymorphic resource ownership is enforced through one tenant-aware resolver registry until a
future ADR adopts a database-backed authorization-scope registry.

### Authorization Migration Modes

Only `LEGACY_AUTHORITATIVE` is operationally permitted today.

| Mode | Decision authority | Required behavior |
| --- | --- | --- |
| `LEGACY_AUTHORITATIVE` | Legacy | Canonical writes may be shadowed only after dual-write is implemented; canonical data cannot affect decisions. |
| `CANONICAL_SHADOW` | Legacy | Both engines decide; every mismatch is durably classified; canonical denial or absence cannot alter the legacy result. |
| `CANONICAL_AUTHORITATIVE` | Canonical | Legacy is comparison-only and can never turn a canonical denial into an allow. |
| `CANONICAL_ONLY` | Canonical | Legacy authorization reads and writes are disabled and monitored as errors. |

An environment variable alone must never claim a mode that the runtime does not implement.
Startup must eventually reject unsupported transitions. No service may implement private
fallback behavior outside the central migration-mode authority.

### Transition Gates

Before `CANONICAL_SHADOW`:

- migrations are applied and verified against the deployed database engine
- a read-only before-inventory and immutable database backup are archived
- every legacy binding is mapped, revoked, or quarantined without guessing
- dual-write is transactional and idempotent for every production assignment path
- mismatch telemetry and rollback replay are tested

Before `CANONICAL_AUTHORITATIVE`:

- the approved shadow observation window has completed
- no unresolved critical mismatch remains
- expected policy differences have named Security and Platform approval
- restore and mode-rollback rehearsals have succeeded
- affected sessions can be invalidated or rebuilt

Before `CANONICAL_ONLY`:

- legacy reads and writes have remained unused for the approved observation window
- rollback no longer depends on stale legacy rows
- retention and deletion approval is recorded
- the post-cutover inventory and authorization test matrix pass

Each promotion is a reviewed deployment change. Application startup, ordinary login, and
database migration scripts must never promote a mode automatically.

### Backup, Rollback, and Evidence

Platform Operations owns database backup and restore execution. Security owns binding
classification, quarantine decisions, mismatch acceptance, and audit-retention approval.
Application Engineering owns migration tooling, deterministic reports, rollback replay, and
test evidence. Two-person approval from Operations and Security is required for authority-mode
promotion.

For every environment and transition:

- create an encrypted, access-controlled, immutable database backup
- record database revision, application version, configuration mode, inventory hash, policy
  hash, approvers, and change ticket
- store inventory and reconciliation artifacts outside source control
- prove restoration in a non-production environment before production promotion
- retain the prior authority path until its rollback window and parity gates close

A mode rollback is permitted only when the older authority data was kept transactionally
current. Restoring stale legacy authority is prohibited. After legacy writes stop, rollback
requires approved replay or database restoration, not only changing an environment variable.

### Audit Retention

Authorization mutations, membership lifecycle events, platform provisioning, support access,
context switches, policy reconciliation, migration decisions, and denied privileged operations
must produce durable security evidence.

- The business mutation and successful security audit intent commit atomically.
- A denial remains denied if its audit write fails and must trigger operational alerting.
- Retention is configurable by deployment policy and legal requirements.
- Platform-owner changes, support access, policy reconciliation, migration promotion, and
  quarantine decisions have a seven-year default retention.
- Other authorization and membership security events have a minimum 400-day default retention.
- Secrets, password material, recovery codes, tokens, and unnecessary personal data are never
  stored in inventory or audit payloads.

## Current Implementation Status

- `[x]` deployment and tenancy modes are parsed centrally
- `[x]` production rejects an omitted tenancy mode
- `[x]` SaaS and local tenant-context policies are separated
- `[x]` SaaS startup avoids legacy administrator and customer-context bootstrap
- `[x]` platform-owner provisioning is explicit and one-time
- `[x]` canonical role metadata and role-binding foundation are additive
- `[x]` legacy scoped-grant operations fail closed on context, membership, and ownership
- `[x]` schema-aware read-only inventory tooling is available
- `[x]` strict offline operational-evidence manifest and artifact-integrity verification tooling
  is available for backup, restore, rollback, retention, approval, inventory, and policy
  evidence
- `[~]` environment evidence execution, archival, inventory review, and policy reconciliation
  are operationally pending
- `[x]` unsupported authorization migration modes are rejected at configuration and composition
- `[~]` additive membership lifecycle, one-time token issuance, authenticated internal
  acceptance, targeted session invalidation, atomic membership audit, and fixed `viewer`
  orchestration are implemented; external delivery, public adapters, custom-role delegation,
  and legacy-column retirement remain pending
- `[~]` constrained quarantine and rollback-snapshot persistence is implemented additively;
  classifier execution, dual-write, shadow comparison, and promotion gates remain pending
- `[ ]` canonical authorization is decision authority
- `[ ]` successful privileged audit intent is atomic with each mutation
- `[ ]` hosted PostgreSQL migration and isolation evidence is in CI

## Consequences

- Phases 0, 1, and 2 remain in progress despite the accepted target architecture.
- Direct legacy writes may remain only when explicitly inventoried and assigned a migration
  owner.
- Canonical backfill cannot infer tenant or scope from a global role name alone.
- A canonical denial never falls back to a legacy allow.
- Customer custom roles, support impersonation, and legacy deletion cannot ship before their
  respective gates.
- Future HTTP adapters must establish request-scoped identity and tenant context; shared
  mutable desktop session state is not a hosted API security boundary.
