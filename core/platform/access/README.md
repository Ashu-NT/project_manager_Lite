# Platform Access Architecture

This package owns the reusable authorization engine for the application.

## Platform Responsibilities

- Define and enforce permission checks.
- Resolve access by scope type and scope id.
- Store scoped access in the authenticated session principal.
- Provide compatibility wrappers for existing project-scoped PM checks.

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

## Phase 1 Outcome

Phase 1 intentionally does not change the database schema. Existing `project_memberships` rows are projected into generic scoped access with:

- `scope_type = "project"`
- `scope_id = project_id`

This keeps the migration low-risk while enabling future modules to adopt the same platform authorization model.

The current implementation now also includes:

- a generic `ScopedAccessGrantRepository` contract in `core/platform/common/interfaces.py`
- a compatibility SQLAlchemy adapter that projects project-membership storage into scoped grants
- principal-building in `AuthService` that hydrates `scoped_access` from the generic grant repository when available
- compatibility wrappers that still preserve `project_access` and PM membership APIs for the current runtime

## Suggested Next Steps

1. Add dedicated persistence for non-project scope types when another module needs real scoped grants.
2. Register and ship module-owned scope policies such as storeroom, asset, or maintenance-area access through the same platform seam.
3. Evolve the access admin UX from project-first labels to a broader multi-scope management console as new scope types come online.
