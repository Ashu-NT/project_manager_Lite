# UI Admin Module

`ui/admin/` provides administrative control surfaces for user management and
audit observability.

## Files

- `users_tab.py`: user and role lifecycle management UI
- `user_dialog.py`: create, edit, and reset dialogs
- `audit_tab.py`: filtered audit-log explorer

## User Administration (`UserAdminTab`)

Main capabilities:

- list users with role aggregation
- create user with role assignment
- edit profile (username, display name, email)
- assign and revoke role
- reset password
- toggle active status

Security model:

- all mutating actions require `auth.manage`
- unavailable actions are disabled with permission hint tooltips
- typed service exceptions are surfaced in contextual dialogs

## Dialog Layer (`user_dialog.py`)

Dialogs:

- `UserCreateDialog`
- `UserEditDialog`
- `PasswordResetDialog`

Technical behavior:

- password visibility toggle and strength feedback
- validation loop keeps dialog open on recoverable errors
- uses `AuthService` rules for password policy and email format

## Audit Explorer (`AuditLogTab`)

Capabilities:

- reads recent audit entries (`limit=1000`)
- filters by project, entity type, action text, actor text, and date mode
- date modes: all, single date, date range
- resolves IDs into labels where reference maps exist

Reference maps include:

- projects
- tasks
- resources
- cost items
- baselines

Event-driven behavior:

- subscribes to domain events and reloads automatically

## Notes

- table-heavy views use shared style helpers
- filtering is mostly UI-side after a bulk fetch for responsive interaction
