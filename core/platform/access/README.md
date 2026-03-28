# Platform Access Architecture

This package owns the reusable scoped-access model for the application.

## Platform Responsibilities

- Define and enforce scope-aware permission checks.
- Resolve access by scope type and scope id.
- Store scoped access in the authenticated session principal.
- Provide compatibility wrappers for existing project-scoped PM checks.

The shared decision seam for permission evaluation now lives under:

- `core/platform/authorization`

## Module Responsibilities

Modules define their own:

- permission vocabulary such as `task.read` or `inventory.manage`
- scope templates such as PM `viewer`, `contributor`, `lead`, `owner`
- module-specific admin UX for assigning those templates

Project Management scope templates now live in:

- `core/modules/project_management/access/policy.py`

## Current Compatibility Layer

The current implementation keeps the existing PM membership storage and APIs in place:

- `ProjectMembership`
- `ProjectMembershipRepository`
- `require_project_permission()`
- `UserSessionContext.has_project_permission()`

Under the hood, the session now also stores generic `scoped_access`, and project checks are wrappers around the generic scope-aware core.

The platform service and admin tab now also expose scope-neutral operations and UI flows:

- `AccessControlService.list_scope_grants(...)`
- `AccessControlService.assign_scope_grant(...)`
- `AccessControlService.remove_scope_grant(...)`
- `ScopedAccessGrantRepository` as the platform persistence seam for scoped grants
- a scope-oriented Access admin tab that can host future non-project scope types without importing PM policy code directly

## Phase 2 Outcome

The current implementation now supports two persistence paths:

- `scope_type = "project"`
- `scope_id = project_id`
- dedicated `scoped_access_grants` rows for non-project scope types such as `storeroom`

This keeps project compatibility intact while allowing real non-project enterprise scopes to use the same platform authorization model.

The current implementation now also includes:

- a generic `ScopedAccessGrantRepository` contract in `core/platform/common/interfaces.py`
- a mixed SQLAlchemy adapter that reads project grants from `project_memberships` and non-project grants from `scoped_access_grants`
- principal-building in `AuthService` that hydrates `scoped_access` from the generic grant repository when available
- compatibility wrappers that still preserve `project_access` and PM membership APIs for the current runtime
- first live non-project scope policy registration for `storeroom`
- scope-aware inventory filtering for storeroom administration and stock ledger queries
- split `Access` and `Security` shell workspaces while keeping `AccessTab` as a reusable shared surface
- a platform-owned authorization engine seam that `auth.authorization` and `access.authorization` now delegate through before future ABAC/web adapters are introduced
- scope existence validation through injected resolver callbacks so the access core no longer imports module repositories directly

## Suggested Next Steps

1. Add more module-owned scope policies such as asset and maintenance-area access through the same platform seam.
2. Keep pushing scope-aware enforcement deeper into inventory/procurement and future maintenance services.
3. Route richer contextual policy inputs through the shared authorization engine so future ABAC-style checks do not expand ad hoc across services.
4. Evolve the access admin UX from project-first labels to a broader multi-scope management console as more scope types come online.
