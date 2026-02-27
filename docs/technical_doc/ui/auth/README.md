# UI Auth Module

`ui/auth/` contains login-time authentication UX.

## File

- `login_dialog.py`

## `LoginDialog` Responsibilities

- capture username and password credentials
- show password toggle (show or hide)
- validate non-empty credentials before service call
- authenticate via `AuthService.authenticate(...)`
- build principal via `AuthService.build_principal(...)`
- set principal into shared `UserSessionContext`

## Runtime Flow

1. User submits credentials.
2. Dialog calls `AuthService.authenticate`.
3. On success, dialog creates principal and writes it into the session context.
4. Dialog returns `Accepted`; main window launches with permission-aware tabs.
5. On failure, dialog shows warning or error and remains open.

## Error Handling

- `ValidationError`: user-facing warning (invalid credentials)
- unexpected exceptions: critical dialog

## Security Notes

- password input uses masked echo by default
- no credential persistence in UI layer
- role and permission materialization is delegated entirely to core auth service
