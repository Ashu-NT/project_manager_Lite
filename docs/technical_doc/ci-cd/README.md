# CI/CD Release Module

This module documents automated release packaging and publication.

## Source File

- `.github/workflows/release.yml`

## Trigger Modes

- tag push matching `v*`
- manual `workflow_dispatch` with `release_tag` input

## Pipeline Stages

1. Resolve release metadata:
   - validates tag format
   - normalizes to `vX.Y.Z`
   - derives installer name and download URL
2. Resolve project paths:
   - entry script
   - optional spec file
   - NSIS script
3. Setup Python environment.
4. Stamp runtime app version file (`infra/app_version.txt`).
5. Install dependencies.
6. Install and resolve NSIS executable path robustly.
7. Build PyInstaller bundle:
   - spec build when present
   - script fallback with explicit data and hidden imports
8. Build NSIS installer with CI-injected version define.
9. Collect installer artifact with safe same-path handling.
10. Generate SHA256 checksum and release manifest JSON.
11. Upload artifacts to workflow run.
12. Publish GitHub release assets.

## Release Assets

- `Setup_ProjectManagerLite_<version>.exe`
- `Setup_ProjectManagerLite_<version>.exe.sha256`
- `release-manifest.json`

Manifest includes channel records (`stable`, `beta`) with:

- version
- download URL
- notes
- SHA256

## Reliability Hardening Included

- release tag validation (no spaces, semver-style checks)
- NSIS executable path probing across multiple install locations
- fallback from spec to script PyInstaller build
- artifact copy guard to avoid self-copy failure
- explicit release summary output with latest-manifest URL
