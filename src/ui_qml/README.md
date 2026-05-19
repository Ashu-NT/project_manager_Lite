# QML Desktop UI

This package is now the active desktop UI runtime.

Current state:

- `main_qt.py` loads `src.ui_qml.shell.app`
- legacy `ui/*` and `src/ui/*` QWidget trees are removed
- legacy `main.py` CLI bootstrap is removed
- migration-only `src/ui_qml/legacy_widgets/*` is removed

Active structure:

```text
src/ui_qml/
  shell/
  shared/
  platform/
  modules/
```
