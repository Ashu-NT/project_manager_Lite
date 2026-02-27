# UI Support Module

`ui/support/` is the productization and support operations panel for admins.

## File

- `tab.py`

## `SupportTab` Responsibilities

Update management:

- select update channel (`stable` or `beta`)
- persist auto-check preference
- persist and edit manifest source URL
- check updates asynchronously against manifest
- show current version and update result details
- install updates in-app (Windows):
  - download installer
  - verify SHA256
  - prepare detached handoff
  - close app
  - run installer and relaunch app

Diagnostics:

- export diagnostics bundle (metadata + logs + DB snapshot)
- open logs folder
- open app data folder

## Dependencies

- `MainWindowSettingsStore`
- `infra.update` (manifest parsing and version comparison)
- `infra.updater` (installer download/handoff)
- `infra.diagnostics` (bundle export)
- `infra.version` (runtime app version)

## Async Behavior

All potentially slow operations are async:

- update checks
- installer download and validation
- diagnostics bundle creation

Busy-state toggles and retry semantics are integrated through shared async job
infrastructure.

## Default Manifest Strategy

If user does not set a manifest source, defaults resolve to the app release
`latest` manifest URL (overrideable by `PM_UPDATE_MANIFEST_URL`).

## Operational Notes

- In-app installer handoff is currently Windows-specific.
- Non-Windows flows fall back to opening the download URL.
- Support result box acts as an admin activity log for support actions.
