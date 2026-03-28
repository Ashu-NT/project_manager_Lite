# Application Layer

`application/` is the shared orchestration seam between delivery surfaces and the business layer.

## Current Scope

The current package is intentionally focused:

- `platform/runtime/service.py`

This is enough to give the desktop app and future transport adapters one common orchestration boundary without forcing the desktop through HTTP.

## Responsibilities

`PlatformRuntimeApplicationService` currently coordinates:

- active organization lookup and switching
- module entitlement reads and updates
- runtime context snapshots for shell and admin screens
- organization creation and update
- organization provisioning with an initial module mix

## Current Consumers

- `ui/platform/shell/main_window.py`
- `ui/platform/shell/platform/home.py`
- `ui/platform/admin/modules/tab.py`
- `ui/platform/admin/organizations/tab.py`
- `api/http/platform/runtime.py`

## Design Rule

- `application/` coordinates use cases
- `core/` owns the rules
- `infra/` owns persistence and wiring
- `ui/` and `api/` are delivery adapters on top

## Status

- active and in use by the desktop runtime
- ready to be reused by a future web/server layer
