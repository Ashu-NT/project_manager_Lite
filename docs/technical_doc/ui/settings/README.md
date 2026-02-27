# UI Settings Module

`ui/settings/` contains persisted main-window preference storage.

## File

- `main_window_store.py`

## `MainWindowSettingsStore` Responsibilities

- persist and load:
  - theme mode
  - selected tab index
  - main-window geometry
  - governance mode
  - update channel
  - startup auto-check flag
  - update manifest source URL

Storage backend:

- `QSettings` with org/app namespace:
  - org: `TECHASH`
  - app: `ProjectManagerLite`

## Validation and Normalization

The store normalizes invalid values to safe defaults:

- theme: `light` or `dark`
- governance mode: `off` or `required`
- update channel: `stable` or `beta`
- tab index: non-negative integer
- boolean parsing for persisted checkbox-like values

## Update Manifest Defaulting

If no manifest URL is persisted, store falls back to:

- `infra.update.default_update_manifest_source()`

This allows first-run installs to auto-target the release manifest without
manual setup.

## Integration Points

- main window startup and shutdown persistence
- governance tab mode persistence
- support tab update and diagnostics settings snapshot
