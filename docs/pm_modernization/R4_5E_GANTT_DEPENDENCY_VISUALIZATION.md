# R4.5E Gantt Dependency Visualization

**Status:** COMPLETE - DPR/coordinate follow-up verified
**Next phase:** none started by this follow-up
**Commit:** no E commit created

## Boundary

R4.5E adds dependency visualization only. Authoritative dependency IDs,
endpoints, relation types, labels, and signed lag continue to come from the
existing project-wide R4.5B projection. The scheduling domain remains the sole
owner of dependency semantics, cycle rules, working-day lag effects, CPM,
criticality, and infeasibility.

No dependency CRUD, baseline overlay, final critical-path styling, scheduling
calculation, resource lane, or R5 behavior was added.

## Architecture

`SchedulingGanttDependencyLayer.qml` is the only dependency renderer. It owns
one logical-coordinate `Canvas`, a compact display-route cache, bounded repaint
handling, and truthful render status. It does not own dependency facts.

The existing `GanttListModel` now exposes one bounded `dependencyWindow(...)`
slot. The slot uses the R4.5B indexes:

```text
rendered/overscan task IDs
  -> task-to-incident-edge adjacency
  -> deduplicated edge IDs
  -> keep only edges whose two endpoints are in the bounded row window
  -> discard only edges whose endpoint bars have no dates, with visible count
  -> apply measured density policy
  -> serialize compact immutable display facts
```

The complexity is `O(V + E_visible)` plus deterministic edge-ID ordering. It
does not scan all project edges for every row and does not scan rows for every
edge. The cache is cleared synchronously on `modelAboutToBeReset` and project
projection changes, then rebuilt on the next coalesced frame. It is disposable
and never becomes dependency truth.

`SchedulingGanttRowsViewport` exposes fixed-height visible and four-row
overscan bounds derived from its single vertical `ListView`. The dependency
layer consumes those bounds, the same row height/contentY, and the same
timeline `contentX`, range start, and pixels/day used by bars and the header.

## Geometry And Routing

`GanttGeometry.js` is the one shared date-to-pixel primitive for header cells,
normal bars, minimum-width bars, milestones, Today, non-working shading, and
dependency anchors.

Anchor rules are:

| Relation | Predecessor | Successor |
|---|---|---|
| FS | finish/right | start/left |
| SS | start/left | start/left |
| FF | finish/right | finish/right |
| SF | start/left | finish/right |

A normal finish anchor uses the actual rendered bar width, including the
12-pixel minimum at low density. A milestone start/finish anchor uses the left
or right side of the existing 14-pixel milestone bounds. Arrowheads always sit
on the successor endpoint and point inward from the successor's anchor side.

Routes are deterministic orthogonal polylines with source lead-out, one
vertical channel, target lead-in, and successor arrowhead. The channel chooses
a midpoint for ordinary forward FS links and an outside gutter for backward,
same-side, near, or negative-lag visual arrangements. It does not calculate
lag geometry or move task dates.

Signed lag remains unchanged in every route fact. Negative, zero, and positive
values are available as metadata with authoritative task names and relation
labels. Unsupported relation values fail visibly and produce no mislabelled
route.

## Visibility And Interaction

An edge is drawn only when both endpoints are inside the current rendered plus
bounded overscan task set and both bars are positionable. Filtering, hierarchy
collapse, flat sorting, and vertical scrolling therefore update complete edges
without half-lines or synthetic summary links. Horizontal clipping is handled
by the timeline-body layer and is independent of vertical endpoint visibility.

The controller-owned `showDependencyLines` session state defaults on. Turning
it off clears routes, resets paint diagnostics, and short-circuits
`dependencyWindow(...)`; it performs no dependency read or CPM work. Rendering
errors, unpositioned visible edges, and density suppression all produce visible
status text.

Selection intersects the visible candidate IDs with the existing O(1)
task-to-incident-edge index. Only complete visible incident routes are
emphasized. Selection, scrolling, horizontal panning, zoom, timescale changes,
and view-mode changes perform display work only. Route facts already retain
endpoint critical/infeasible flags for R4.5F, but E does not style them.

## Density Policy

The normal-render threshold is 500 complete visible routes. This is based on
real offscreen `QQuickView` measurements in `pmenv`, not an arbitrary project
edge count. The threshold applies after vertical endpoint culling.

| Visible routes | Route preparation | Canvas paint | Approx. total |
|---:|---:|---:|---:|
| 100 | 2 ms | <1 ms | about 2 ms |
| 500 | 11 ms | 1 ms | about 12 ms |
| 1,000 | 23 ms | 4 ms | about 27 ms |
| 5,000 | 125 ms | 22 ms | about 147 ms |
| 9,800 | 253 ms | 42 ms | about 295 ms |

Five hundred remains below the 16.7 ms target on this environment; 1,000 does
not. Above 500, normal routes are suppressed visibly and complete selected-task
incident routes remain available. In the 9,800-edge dense fixture, the fallback
prepared and painted all 392 visible selected incident routes in approximately
26 ms plus 1 ms, with the warning visible. No edge is silently dropped.

Project-size lookup remains bounded by the row window:

| Project rows | Project chain edges | Visible complete edges | Lookup |
|---:|---:|---:|---:|
| 100 | 99 | 29 | 0.304 ms |
| 1,000 | 999 | 29 | 0.123 ms |
| 5,000 | 4,999 | 29 | 0.198 ms |

These measurements are characterization results, not a cross-device guarantee.
R4.5G may tune/persist display preferences, but any threshold change must remain
measurement-backed and truthful.

## High DPI And Repaint Policy

The dependency Canvas uses its logical QML item dimensions and all route paint
coordinates remain logical. It does not manually multiply `canvasSize` by
`Screen.devicePixelRatio` and does not call `context.scale(DPR, DPR)`. Qt Quick
therefore performs exactly one logical-to-physical mapping, matching normal QML
task bars at DPR `1`, `1.25`, `1.5`, and `2`. Logical line widths and arrowhead
dimensions are retained so Qt renders them crisply without manual DPR inflation.

The route cache remains stable content-space geometry. Horizontal rendering
subtracts `timelineContentX`; vertical rendering subtracts the generalized
ListView offset `contentY - originY`. Scroll changes request Canvas paint
directly so the bitmap follows the rendered frame without rebuilding routes.
Width/height and route rebuild work retain the existing bounded coalescing.

The painted regression fixture verifies `144 -> 168` at `contentX=0`,
`44 -> 68` at `contentX=100`, and natural clipping at `contentX=250`. It also
verifies row centers `18 -> 54`, their exact `-12` vertical translation, and
equivalent output for non-zero `originY`.

## Files

Created:

```text
docs/pm_modernization/R4_5E_GANTT_DEPENDENCY_VISUALIZATION.md
src/tests/project_management/test_r4_5e_gantt_dependencies.py
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/GanttGeometry.js
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttDependencyLayer.qml
```

Modified:

```text
docs/pm_modernization/R4_5D_GANTT_TIME_AXIS_IMPLEMENTATION.md
docs/pm_modernization/R4_5_GANTT_ENGINEERING_AUDIT.md
src/tests/project_management/test_qml_scheduling_planning_ia_contract.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_list_model.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py
src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers/typeinfo/plugins.qmltypes
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttBar.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttHeader.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttRowsViewport.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/SchedulingGanttSurface.qml
src/ui_qml/modules/project_management/qml/workspaces/scheduling/components/gantt/qmldir
src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingGanttPanel.qml
```

Deleted: none.

No temporary adapter, compatibility shim, second dependency cache, or legacy
renderer was introduced.

## Verification

- 33 focused R4.5E tests passed;
- 100 combined targeted R4.5B/C/D/E/F and Planning IA tests passed;
- real offscreen `QQuickView` pixel tests pass at DPR `1`, `1.25`, `1.5`, and `2`;
- painted output covers exact horizontal/vertical translation, non-zero
  `originY`, first/middle/last effective-row centers, and natural clipping;
- every discrete zoom multiplier and Day/Week/Month/Quarter density shares the
  same authoritative bar/dependency anchor geometry;
- integrated surface tests cover vertical scroll, horizontal pan, zoom, every
  timescale, Grid/Timeline mode changes, and project reset;
- 120 continuous horizontal/vertical frame updates completed in approximately
  `2.1 ms` of dispatch work without any route rebuild;
- direct `pyside6-qmllint` over changed Gantt QML with application import roots
  is silent;
- targeted Python compilation passes;
- no full test suite was run;
- no commit was created.

## R4.5F Handoff

R4.5F may add the explicit selected-baseline overlay and final semantic visual
precedence for baseline, milestone, selected/focused, critical, and infeasible
states. It may style a dependency route as critical only from authoritative
endpoint/path facts; the E route representation already carries endpoint
critical/infeasible flags so the renderer does not need replacement.

R4.5F must retain the single Canvas, adjacency-window algorithm, complete-edge
visibility rule, 500-edge truthful fallback, one axis/row coordinate system,
and no-CPM/no-query display interactions. It must not add dependency CRUD,
infer infeasibility from geometry, redesign scheduling semantics, or begin R5.
