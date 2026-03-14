# UI Admin Module

`ui/platform/admin/` provides shared administrative control surfaces for the platform layer.

## Current Workspaces

- `access/`
  - project memberships, scoped permissions, and security-aware access administration
- `users/`
  - user, role, password reset, and account lifecycle management
- `employees/`
  - employee directory management for staffing and future payroll use
- `organizations/`
  - active organization switching and new-organization provisioning with initial module mix
- `modules/`
  - module licensing, runtime enablement, and lifecycle status management
- `support/`
  - diagnostics, update flow, and product support tooling

Audit now lives under `ui/platform/control/audit/` because it is a cross-platform oversight surface rather than a pure admin tool.

## User Administration (`UserAdminTab`)

Main capabilities:

- list users with role aggregation
- create user with role assignment
- edit profile (username, display name, email)
- assign and revoke role
- reset password
- toggle active status

Security model:

- read-only user/role directory visibility can be exposed via `auth.read`
- all mutating actions require `auth.manage`
- unavailable actions are disabled with permission hint tooltips
- typed service exceptions are surfaced in contextual dialogs

## Dialog Layer (`users/dialogs.py`)

Dialogs:

- `UserCreateDialog`
- `UserEditDialog`
- `PasswordResetDialog`

Technical behavior:

- password visibility toggle and strength feedback
- validation loop keeps dialog open on recoverable errors
- uses `AuthService` rules for password policy and email format

## Notes

- table-heavy views use shared style helpers
- organization and module admin screens are wired through `PlatformRuntimeApplicationService`
- filtering is mostly UI-side after a bulk fetch for responsive interaction
