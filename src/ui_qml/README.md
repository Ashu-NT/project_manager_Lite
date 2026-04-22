# QML UI Migration Scaffold

This package is the final desktop UI target for the PySide6 Widgets to QML migration.

Current rule:

- `src/ui/*` remains the active legacy QWidget UI until each screen is migrated.
- QML screens are added here one workspace or dialog at a time.
- Old QWidget files are deleted only after the matching QML screen, presenter, view model, route, and tests are complete.
- The QML scaffold is not wired into `main_qt.py` yet.

Final structure:

```text
src/ui_qml/
  shell/
  shared/
  platform/
  modules/
  legacy_widgets/migration_only/
```
