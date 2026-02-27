# Installer Module

This module documents Windows installer behavior implemented with NSIS.

## Source File

- `installer/ProjectManagerLite.nsi`

## Build Inputs

- app payload folder:
  - default: `..\dist\ProjectManagerLite`
  - override: `APP_SOURCE_DIR` define
- app version:
  - default hardcoded fallback in script
  - CI override: `APP_VERSION` define

## Installer Behavior

Install path:

- default target: `$PROGRAMFILES\\ProjectManagerLite`
- persisted under HKLM install registry key for update discovery

Startup checks:

- detects existing installed version from uninstall registry
- prompts user for update or repair continuation
- best-effort running-app window check before continuing

Install actions:

- copies payload recursively to install directory
- refreshes shortcuts (desktop and start menu)
- writes uninstall metadata and uninstall executable
- refreshes shell icon cache

Uninstall actions:

- removes shortcuts
- removes install directory
- removes product and uninstall registry keys

## Update Semantics

The NSIS script is update-friendly:

- reinstalling over existing version is supported by design
- CI version override allows consistent installer naming:
  - `Setup_ProjectManagerLite_<version>.exe`
