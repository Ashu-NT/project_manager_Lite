# Controller And Settings Follow-Up Round 1

Date: 2026-06-13

## Scope completed

This tranche closes the first live controller/settings gaps left after the
repository hardening rounds:

- runtime organization switching through `PlatformRuntimeApplicationService`
- project-management QML runtime-context lookup for organization-aware settings
- PM task saved-view persistence fallback keying
- PM table-column state keying through the shared app settings store

## Enterprise hardening applied

- `PlatformRuntimeApplicationService.set_active_organization(...)` now requires
  `settings.manage` before changing the session-scoped organization context.
- The runtime-service resolver and composition roots now carry `user_session`
  so permission enforcement stays active even when the desktop API registry
  reconstructs the runtime service seam.
- PM QML controllers no longer call a nonexistent `platformRuntimeApi.snapshot()`
  path to discover the active organization.
- Added a shared PM runtime-context helper that prefers
  `platformRuntimeApi.get_runtime_context()` and only falls back to `snapshot()`
  for compatibility.
- `ProjectManagementTaskViewStore` now reuses the shared app-settings tenant key
  format, including the `tenant/__no_organization__/...` fallback namespace.
- PM table-column state now resolves the active organization from the same live
  runtime API contract used by the shell.

## Coverage added

- `src/tests/platform/test_platform_runtime_application_service.py`
  - runtime org switching still works for active organizations
  - runtime org switching now rejects users missing `settings.manage`
- `src/tests/platform/test_platform_runtime_desktop_api.py`
  - desktop API maps runtime org-switch permission denials to API errors
- `src/tests/project_management/test_qml_project_management_presenters.py`
  - PM task saved views are written under the active-organization tenant key
- `src/tests/test_ui_settings_persistence.py`
  - PM task-view store uses `tenant/__no_organization__/...` instead of bare keys
  - PM workspace table-column state follows `platformRuntimeApi.get_runtime_context()`

## Verification

- Focused runtime, PM QML, and settings verification:
  - `conda run -n pmenv python -m pytest -q src/tests/platform/test_platform_runtime_application_service.py src/tests/platform/test_platform_runtime_desktop_api.py src/tests/project_management/test_qml_project_management_presenters.py src/tests/test_ui_settings_persistence.py`
  - result: `40 passed`

## Next step

- Continue with contract cleanup for remaining transitional repository APIs and
  constructor-time tenant-context requirements that still rely on post-build
  wiring.
