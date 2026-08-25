# QML Redesign Docs

Index and implementation notes for the PM QML redesign effort. Start with
the design docs, then use the pattern notes below when implementing.

## Design docs

- [`../R5F_REVIEW_QUEUE_REDESIGN.md`](../R5F_REVIEW_QUEUE_REDESIGN.md)
  -- completed authoritative TimesheetPeriod Review Queue workflow, read model,
  concurrency, security, QML ownership, cleanup, and R5G handoff.

- [`project_management_qml_existing_state_audit.md`](project_management_qml_existing_state_audit.md)
  -- current-state audit of the PM QML surface.
- [`project_management_qml_target_ui_ux_design.md`](project_management_qml_target_ui_ux_design.md)
  -- target IA, page patterns, wireframes, and design-system extension list
  (see `10.2 Extend shared primitives` for `InspectorPanel`).
- [`project_management_ui_repository_restructure_plan.md`](project_management_ui_repository_restructure_plan.md)
  -- file/module layout plan for the redesign.

## Implementation pattern: InspectorPanel close behavior

The target design (`10.2`) calls for `InspectorPanel` to have "responsive
optional inspector with focus return and close behavior." This section
records the concrete pattern implemented for the **Projects** workspace so
later redesign phases (and the rollout to the other `InspectorPanel`
consumers) reuse it rather than re-deriving it.

`InspectorPanel` (`src/ui_qml/shared/qml/App/Widgets/InspectorPanel.qml`) is
used side-by-side with a list/table in a `RowLayout` on 11 pages today
(Projects, Access, Documents, DocumentStructures, Users, Parties, Employees,
Calendars, Departments, Sites, Organizations). Each page composes that
`RowLayout` independently -- there is no shared "table + inspector" host
component. Selection state is either controller-backed (Projects:
`workspaceController.selectedProjectId`) or a plain local
`property string selectedRowId` (the platform pages).

**Required close triggers:**

- explicit close ("X" button, already existed via `InspectorPanel.closeRequested`)
- click on blank space *within* the list/table's own empty rows (already
  existed via `DataTable`'s `_emptySpaceCatcher`)
- click on blank space anywhere else in the workspace's own list/detail
  content area (KPI strip padding, toolbar gaps, pagination margins, etc.)
- `Escape`, but only when no popup/dialog currently owns it

**Must NOT close on:** selecting a different row (inspector stays open and
retargets), or any interaction with a real control, popup, `ComboBox`,
`DatePicker`, or dialog.

### Pieces (implemented for Projects; not yet rolled out elsewhere)

1. **`InspectorPanel.qml` -- swallow its own blank clicks (shared, safe for
   all 11 consumers today).** A page-level "click outside closes the
   inspector" catcher can only work if the panel itself never lets a click
   on its *own* blank padding fall through to whatever sits behind it.
   `InspectorPanel` now has a plain full-fill `MouseArea` as its **first**
   child (behind the divider/header/body/actions in stacking order) that
   silently consumes such clicks. Real controls (close button, edit/
   secondary buttons, the scrollable body) are declared after it and still
   claim their own clicks first. This addition changes no public contract
   and is inert for pages that don't yet add an outside-click catcher.

2. **Per-page background catcher (implemented in `ProjectsWorkspacePage.qml`
   only so far).** A low-z, full-fill `MouseArea` placed as the *first*
   child of the page's stacked list/detail `Item`, i.e. behind the
   `RowLayout` that holds the list and the `InspectorPanel`. Because it's
   behind everything, it only ever receives clicks that no other control
   (or the panel itself, per point 1) claimed -- true background clicks.
   `onPressed` clears the inspector's selection; `enabled` is gated on the
   inspector actually being open, `visible` on the detail page not being
   open. Popups reparent into `Overlay.overlay` (above everything), so
   they're naturally unaffected regardless of z-order here.

3. **`Escape` shortcut (implemented in `ProjectsWorkspacePage.qml` +
   `ProjectsDialogHost.qml`).** A `Shortcut { sequence: "Escape" }` closes
   the inspector, `enabled` only when the inspector is open **and** every
   popup/dialog the page can reach reports `.opened === false` --
   including popups (`AnchoredPopup`-based: filter popup, bulk-change
   popup) and the dialog host's own dialogs. The dialog host exposes a
   single `anyDialogOpen` readonly property (OR of its dialogs' `.opened`)
   so the page doesn't need to enumerate them itself. This guard is
   necessary because these popups/dialogs aren't guaranteed to grab
   keyboard focus, so relying on normal Escape event bubbling isn't safe.

### Rollout status

- Done: Projects.
- Not yet done: Access, Documents, DocumentStructures, Users, Parties,
  Employees, Calendars, Departments, Sites, Organizations -- apply pieces
  2 and 3 above per page once the Projects behavior has been used for a
  while and proven correct. Piece 1 already applies to all of them since
  it lives in the shared widget.

Regression coverage: `src/tests/test_qml_inspector_panel_swallows_own_clicks.py`
(piece 1, widget-level) and `src/tests/test_qml_data_table_empty_space_click_clears_selection.py`
(the `DataTable`-internal empty-space catcher this pattern complements).
