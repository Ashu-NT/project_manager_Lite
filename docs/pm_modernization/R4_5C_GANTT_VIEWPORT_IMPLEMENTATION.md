# R4.5C Integrated Gantt Viewport Implementation

**Status:** COMPLETE
**Next phase:** R4.5D - Time axis, range, timescale, and zoom
**Commit:** none created

## Boundary

R4.5C replaces the paginated `DataTable` plus independently scrolling `SchedulingTimelinePanel` with one specialized, virtualized Gantt surface. It does not add dependency rendering, baseline overlays, semantic timescales, zoom, final milestone/critical styling, resource lanes, or R5 behavior.

Canonical CPM and the disposable R4.5B projection remain the only schedule authorities. QML performs display geometry only.

## Files

Created:

```text
docs/pm_modernization/R4_5C_GANTT_VIEWPORT_IMPLEMENTATION.md
src/tests/project_management/test_r4_5c_gantt_viewport.py
src/tests/project_management/test_scheduling_schedule_sort_intent.py
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttBar.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttHeader.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttRow.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttRowsViewport.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttSurface.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/qmldir
```

Deleted:

```text
src/tests/project_management/test_scheduling_schedule_sort.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_legacy_adapter.py
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingTimelinePanel.qml
```

Modified:

```text
docs/pm_modernization/R4_5B_GANTT_READ_CONTRACT_IMPLEMENTATION.md
docs/pm_modernization/R4_5_GANTT_ENGINEERING_AUDIT.md
src/tests/project_management/test_qml_project_management_presenters_scheduling.py
src/tests/project_management/test_qml_scheduling_planning_ia_contract.py
src/tests/project_management/test_scheduling_infeasible_presenters.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_list_model.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_selection.py
src/ui_qml/modules/project_management/controllers/scheduling/panel_hydrator.py
src/ui_qml/modules/project_management/controllers/scheduling/row_builders.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_property_updates.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_selection_actions.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_state_loader.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py
src/ui_qml/modules/project_management/controllers/scheduling/table_models.py
src/ui_qml/modules/project_management/presenters/scheduling/formatters.py
src/ui_qml/modules/project_management/presenters/scheduling/option_resolver.py
src/ui_qml/modules/project_management/presenters/scheduling/record_mappers.py
src/ui_qml/modules/project_management/presenters/scheduling/schedule_sort.py
src/ui_qml/modules/project_management/presenters/scheduling/scheduling_workspace_presenter.py
src/ui_qml/modules/project_management/presenters/scheduling/workspace_builder.py
src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspaceState.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingGanttPanel.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingOverviewPanel.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/qmldir
src/ui_qml/modules/project_management/view_models/scheduling.py
```

## Old Architecture

```text
SchedulingGanttPanel
|-- DataTable -> legacy paged schedule rows -> vertical owner A
|-- TablePaginationBar
`-- SchedulingTimelinePanel -> legacy timeline rows -> vertical owner B
```

The old design could drift because grid and timeline used different collections, delegates, row heights, and vertical scroll positions.

## New Component Tree

```text
SchedulingGanttPanel.qml
`-- components/gantt/SchedulingGanttSurface.qml
    |-- SchedulingGanttHeader.qml
    |-- SchedulingGanttRowsViewport.qml
    |   `-- ONE ListView -> GanttListModel
    |       `-- SchedulingGanttRow.qml
    |           |-- frozen grid cells
    |           `-- timeline lane -> SchedulingGanttBar.qml
    |-- grid horizontal authority
    `-- ONE timeline horizontal authority
```

`SchedulingGanttRow` owns both visual halves, selection/hover state, hierarchy indentation, bar center, and future dependency/baseline Y anchors. `Theme.AppTheme.compactRowHeight` is the single row-height authority and `ListView.spacing` is zero.

## Scroll Ownership

`SchedulingGanttRowsViewport` contains the only vertical `ListView`. There is no `contentY` mirroring, recursion guard, secondary row list, or permanent delegate per task.

`timelineAxis.contentX` is the sole timeline horizontal authority. The header and every recycled lane consume that exact value. Row drag and the horizontal scrollbar update the same authority. The grid has an independent horizontal column viewport so wide configured columns remain usable without moving the timeline.

## Model And Hierarchy

The production surface binds directly to `workspaceController.ganttRowsModel`. No grid/timeline arrays are serialized.

Hierarchy mode preserves canonical WBS preorder, applies depth indentation, distinguishes summaries, and shows expand/collapse only for summaries. Roots and summaries through depth one are expanded initially; deeper summaries are collapsed. Collapse clears a selected descendant if it becomes hidden. Arbitrary sorting switches to flat mode, reports display depth zero, and removes tree affordances.

`GanttListModel` now also exposes cached complete-project date bounds, O(1) effective-row indexes, indexed keyboard navigation, and projection-derived Overview attention rows. These remain disposable view facts, not schedule truth.

## Selection And Inspector

Grid clicks, timeline row/bar clicks, and keyboard navigation call `controller.selectActivity(task_id)`. The controller performs the existing O(1) indexed lookup and atomically updates `selectedActivityId` plus `selectedActivity` before signals are emitted.

There is no local grid current-row authority and no first-row auto-selection. Project switch, filtering, or hierarchy collapse clears selection only when the selected task is no longer effective. Grid/Timeline/Split changes and horizontal panning retain valid selection.

The R4.4 Inspector is unchanged: wide layouts use the inline panel; compact layouts use `SlideOverPanel`; Open Task remains available; Schedule Impact remains lazy and never runs on selection.

## Responsive Modes

Grid, Timeline, and Split render the same row viewport and model. The requested mode remains user state; `effectiveViewMode` suppresses Split when the actual Gantt content width is at or below the shared 1024 breakpoint or cannot satisfy the 960-pixel split budget.

At 1024x640, requested Split resolves to Grid and the Inspector is a slide-over. At 1280x720 with the full content budget and no inline Inspector, Split is available. If the Inspector reduces the real surface budget below the split minimum, requested Split remains stored while effective mode safely falls back to Grid.

## Truthful Minimal Bars

Bars use authoritative start/finish ordinals, percent complete, `is_milestone`, `is_critical`, and `is_infeasible`. Infeasible styling takes precedence over critical, which takes precedence over normal. A same-day non-milestone remains a bar; only `is_milestone` produces a milestone shape. Summary bars are visually distinct but use the same fixed row geometry.

No dependency, baseline, Today, timescale, or zoom control/rendering was added.

## Deleted Legacy Code

Deleted:

- `controllers/scheduling/gantt_legacy_adapter.py`;
- `panels/SchedulingTimelinePanel.qml` and its `qmldir` registration;
- Gantt `DataTable` and `TablePaginationBar` production use;
- schedule/timeline presenter collections and controller properties;
- schedule table model, row builder, pagination state, and page slots;
- legacy schedule/timeline record mappers;
- duplicate presenter-side row sorting.

The Scheduling Overview now reads critical/infeasible attention rows from the Gantt projection instead of retaining a duplicate schedule table collection.

## Measurements

Measurements use `pmenv`, offscreen Qt, 1024x640 initial attach, then 1280x720 mode validation. Projection construction and CPM/database work are excluded.

| Rows | Model attach | First viewport | Active delegates | Selection | Vertical scroll | Local filter | Mode switch |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 6.156 ms | 39.390 ms | 20 | 0.064 ms | 8.759 ms | 2.562 ms | 0.156 ms |
| 1,000 | 30.702 ms | 37.312 ms | 20 | 0.135 ms | 9.801 ms | 5.004 ms | 0.099 ms |
| 5,000 | 180.089 ms | 29.680 ms | 20 | 0.557 ms | 8.502 ms | 10.663 ms | 0.036 ms |

Delegate count remains bounded by viewport plus cache buffer, not dataset size. Selection remains below the 50 ms gate and invokes no DB, presenter refresh, or CPM execution.

## Verification

- focused viewport/model/runtime measurements: 6 passed;
- final affected Scheduling/QML/controller/domain/qmllint matrix: 69 passed;
- registered route loads passed at 1024x640, 1280x720, 1366x768, 1440x900, and 1920x1080;
- changed Scheduling QML passes `pyside6-qmllint` with no errors or warnings;
- targeted Python compilation passes;
- no full test suite was run;
- no unexplained unrelated failure remains.

## R4.5D Handoff

R4.5D may replace the isolated transitional `pixelsPerDay` and date-label geometry with:

1. deterministic complete-project padded range rules;
2. one two-band timeline header driven by the existing `timelineAxis.contentX`;
3. Week default plus Day, Month, and Quarter semantic scales;
4. discrete min/max/reset zoom anchored predictably;
5. truthful Today navigation/marker behavior that does not expand the project range;
6. non-working shading only where authoritative calendar facts support it.

R4.5D must retain the one-row viewport, one timeline horizontal authority, direct `GanttListModel` binding, selection invariant, bounded delegates, and no-CPM UI interaction rule. It must not implement dependency connectors, baseline overlays, R5 resource lanes, or a second renderer.
