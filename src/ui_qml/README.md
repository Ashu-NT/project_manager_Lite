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

## UX modernization plan

Source of truth:

- `docs/ux_design.md`

Current implementation assessment:

- The QML architecture is already in the right shape and should be preserved.
- The strongest reusable base already exists in `shared/qml/App/*`, `shell/*`, and the typed workspace/controller catalogs.
- The main UX gap is visual, not architectural: too many bordered rectangles, too many nested white panels, and not enough surface hierarchy.
- The table-first direction is already started through `App.Widgets.DataTable`, but the surrounding shell and shared primitives still read as migration-era UI rather than a finished enterprise product.

Execution rules:

- Keep the current controller, presenter, desktop API, route, dialog-host, and named-module structure.
- Keep QML render-focused. Do not move workflow logic into QML.
- Prefer shared-component upgrades over per-page one-off styling.
- Delete QML only when it is clearly obsolete or replaced by a better shared primitive.

Planned phases:

1. Shared design-system hardening
   - Expand `App.Theme` with density-aware sizing and clearer surface hierarchy.
   - Keep existing tokens working while adding missing aliases and reusable surface tokens.
   - Reduce border-heavy defaults in shared controls and layout primitives.

2. Shell modernization
   - Refresh `App.qml`, `MainWindow.qml`, `ShellHeader.qml`, and `ShellDrawer.qml`.
   - Emphasize compact enterprise density, cleaner grouping, and stronger navigation hierarchy.
   - Keep the current route loader and shell context wiring intact.

3. Shared workspace primitive refresh
   - Upgrade `WorkspaceFrame`, `PageHeader`, `MetricCard`, `KpiStrip`, `SectionCard`, `TableToolbar`, `FilterBar`, `DataTable`, `RecordDetailPage`, `SectionDetailPage`, and shared banners/detail surfaces.
   - Replace heavy nested boxes with spacing, dividers, restrained elevation, and selected-state accents.

4. Representative workspace alignment
   - Apply the refreshed primitives to one strong workspace group per module first:
     - Platform admin/control/settings
     - Project management dashboard/projects/tasks
     - Maintenance preventive/planner/assets
     - Inventory catalog/inventory/procurement
   - Reuse the same patterns across the remaining workspaces after the representative pass is stable.

5. Validation and cleanup
   - Run `qmllint`, offscreen loading checks, and architecture guardrails after each major slice.
   - Remove duplicate or obsolete QML only after replacement is verified.

Immediate execution order:

1. Theme + density tokens
2. Shell header/drawer/frame cleanup
3. Shared table/detail/section primitives
4. Representative workspace restyling
5. Validation and follow-up cleanup

Execution progress:

- Completed:
  - README planning pass from `docs/ux_design.md`
  - theme token expansion for density and surface hierarchy
  - shell header/drawer/main-window refresh
  - shared primitive refresh for buttons, headers, cards, inline messages, table toolbar/filter bar, detail pages, table styling, and overlays
  - QML guardrail/test alignment for the QML-only repo state
  - representative workspace polish for the live platform admin document/support flow and PM projects/tasks flow
  - representative workspace polish for maintenance assets/preventive and inventory storeroom/balance/procurement detail flows
  - removal of obsolete PM workspace helper QML files after their behavior was consolidated into the active page-level compositions
- Next:
  - finish the remaining representative pages still carrying local boxed detail treatments and raw dialog buttons
  - module-by-module removal of remaining overly boxed local section treatments
