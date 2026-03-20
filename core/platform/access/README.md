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

## Phase 1 Outcome

Phase 1 intentionally does not change the database schema. Existing `project_memberships` rows are projected into generic scoped access with:

- `scope_type = "project"`
- `scope_id = project_id`

This keeps the migration low-risk while enabling future modules to adopt the same platform authorization model.

## Suggested Next Steps

1. Add a generic scoped grant repository abstraction.
2. Introduce non-project scope types when another module needs them.
3. Evolve the access admin UI from PM-only project memberships to a generic scope access console.
