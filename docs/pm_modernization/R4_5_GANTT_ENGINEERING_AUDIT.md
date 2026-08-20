# R4.5 Gantt Modernization: Engineering Audit and Implementation Design

**Status:** R4.5A and R4.5B complete; locked architecture/product decisions; R4.5C not started  
**Scope:** Project Management > Planning > Gantt  
**Evidence basis:** production QML, controller, presenter, desktop API, scheduling application/domain, persistence, shared QML primitives, and current targeted tests  
**R4.5A non-goals honored:** its audit was read-only; R4.5B subsequently changed Python and the clean pre-release schema baseline, but made no visual QML, scheduling-semantic, R5, or commit changes

R4.5B closure supersedes the original read-only status line above for implementation tracking: the typed read contract, indexed model, baseline milestone snapshot fact, selection seam, and local-view/CPM separation are implemented. No visual R4.5C work has started.

## 1. Executive Summary

The current Gantt is a truthful but shallow schedule viewer. It combines a server-intent `DataTable` with a separate proportional `ListView` timeline. The schedule dates, total float, criticality, infeasibility, constraints, actuals, and dependency semantics ultimately come from the established scheduling domain. The chart does not fabricate baseline or dependency data. However, it is not yet an enterprise Gantt surface:

- the chart renders only the current 25-row page and derives its date range from that page;
- grid and timeline have independent vertical scroll owners and different row geometry;
- the timeline has no horizontal calendar canvas, multi-band header, zoom, timescale, dependency layer, or baseline overlay;
- hierarchy is reduced to a WBS string because Scheduling deliberately selects leaf tasks;
- explicit `Task.is_milestone` is lost by the Scheduling DTO and the presenter incorrectly infers a milestone from equal dates;
- project-wide dependencies and per-task baseline snapshots exist below the UI boundary but are not projected into the Gantt model;
- selection is only partly coherent: row/bar clicks update `selectedActivityId`, while the Inspector consumes a separately built detail object that is not rebuilt by `selectActivity()`;
- every search/filter/sort/page refresh rebuilds the whole scheduling workspace and reruns non-persisting CPM before applying in-memory filtering, sorting, and paging.

The recommended target is a specialized, integrated Gantt surface rather than two independently scrolling generic views. A single virtualized row viewport should own vertical position and row geometry; a frozen grid region and horizontally scrollable timeline region should render inside each logical row. A centralized viewport-aware `Canvas` should render dependency connectors, while lightweight QML delegates render task, milestone, progress, selection, critical/infeasible, and baseline shapes. Python must expose a disposable, immutable Gantt read projection containing authoritative facts and stable row order; QML must own only viewport and date-to-pixel display geometry.

R4.5 does not introduce a second schedule engine. R4.5B now supplies the authoritative disposable read projection and selection/local-view seam; R4.5C-H add chart capabilities incrementally behind the documented gates.

## 2. R4.5 Boundary

R4.5 owns the deep engineering of the already-approved Planning > Gantt destination:

- one integrated WBS/grid and timeline surface;
- vertical and horizontal scroll authority;
- selection synchronization;
- deterministic date range and multi-band timeline headers;
- Day, Week, Month, and Quarter semantic timescales;
- discrete density zoom within each timescale;
- project-wide dependency visualization for FS, SS, FF, and SF links with lag metadata;
- truthful selected-baseline overlays;
- critical, infeasible, milestone, progress, actual, hover, focus, and selection presentation;
- read-only hierarchy display and expansion state;
- responsive Grid, Timeline, and Split behavior;
- Gantt-essential keyboard behavior;
- measured rendering behavior through 5,000 schedule rows.

R4.5 does not own scheduling-engine redesign, new dependency/constraint/lag semantics, resource-leveling policy, task CRUD or WBS mutation redesign, workload/resource histograms, Finance, broad accessibility cleanup, or Planning information-architecture changes. Existing CPM, calendar, constraint, dependency, actual-date, resource-leveling, and Schedule Impact behavior remains authoritative. When rendering needs more data, R4.5 extends read contracts; it does not duplicate domain calculations.

## 3. Current Gantt Architecture

The current runtime path is:

```text
SchedulingWorkspacePage.qml
  -> SchedulingWorkspaceState.qml
  -> SchedulingGanttPanel.qml
       -> AppWidgets.DataTable (grid)
       -> SchedulingTimelinePanel.qml (timeline)
       -> InspectorPanel / SlideOverPanel
  -> ProjectManagementSchedulingWorkspaceController
  -> scheduling_state_loader.load_workspace_state()
  -> ProjectSchedulingWorkspacePresenter.build_workspace_state()
  -> workspace_builder.build_workspace_state()
  -> ProjectManagementSchedulingDesktopApi
       -> SchedulingEngine / TaskService / BaselineService / ReportingService
  -> tenant/org-scoped repositories and canonical domain models
```

`workspace_builder` calls `list_schedule(project_id)`, obtains the complete selected-project leaf schedule, filters and sorts it in Python, slices one page, and creates two parallel collections from that page: `schedule` for the grid and `timeline` for bars. The controller serializes both collections and copies flattened grid rows into a `DynamicTableModel`. The Gantt therefore duplicates each visible task into a table row and a timeline record.

Production composition injects the real `SchedulingEngine`, so normal desktop reads call `recalculate_project_schedule(project_id, persist=False)`. The API retains a task-only fallback for unconnected/test compositions; that fallback has raw persisted task dates and deliberately has no CPM float/criticality.

## 4. Current QML Tree

The production QML tree is:

```text
SchedulingWorkspace.qml
`-- SchedulingWorkspacePage.qml
    |-- LoadingOverlay / InlineMessage
    |-- SchedulingPlanningContextHeader.qml
    |   `-- SchedulingActionBar.qml
    |       |-- Project ComboBox
    |       |-- Refresh
    |       `-- Run CPM
    |-- Planning navigation Flow + NavOverflowMenu
    `-- StackLayout
        `-- SchedulingGanttPanel.qml
            `-- SchedulingPanelFrame.qml
                `-- ColumnLayout
                    |-- TableToolbar (search/filter/customize)
                    |-- filter + Grid/Timeline/Split controls
                    `-- RowLayout
                        |-- SplitView
                        |   |-- grid Item
                        |   |   |-- AppWidgets.DataTable
                        |   |   |-- TablePaginationBar
                        |   |   `-- CenteredDialog filter popup
                        |   `-- SchedulingTimelinePanel.qml
                        |       `-- SchedulingPanelFrame
                        |           `-- ColumnLayout
                        |               |-- range-label header
                        |               `-- ListView
                        |                   `-- row delegate
                        |                       |-- title
                        |                       |-- 8 grid-line Rectangles
                        |                       |-- today-marker Rectangle
                        |                       |-- task/progress Rectangle
                        |                       `-- status
                        `-- Loader -> InspectorPanel (wide)
            `-- SlideOverPanel -> InspectorPanel (compact)
```

There is no distinct timeline-header component, row component, timescale model, dependency layer, baseline layer, or shared scroll coordinator. `SchedulingTimelinePanel.qml` currently owns the row delegate and all bar geometry.

Relevant shared primitives are `DataTable.qml`, `DynamicTableModel`, `TableToolbar.qml`, `TablePaginationBar.qml`, `InspectorPanel.qml`, `SlideOverPanel.qml`, `SchedulingPanelFrame.qml`, and `AppTheme.qml`. `DataTable` uses a reusable Qt 6 `TableView`; `InspectorPanel` has a fixed header and scrollable body.

## 5. Current User Capabilities

| Capability | Status | Current behavior |
|---|---|---|
| Activity grid | LIVE | Query-state filter/sort/page controls display schedule rows in `DataTable`. |
| Timeline bars | PARTIAL | Current page only; proportional to pane width; no calendar scroll or time header. |
| Task selection | PARTIAL | Grid and timeline share `selectedActivityId`, but selected detail is stale after a click. |
| Inspector | PARTIAL | Real schedule facts and lazy Schedule Impact exist; selected detail ownership is defective. |
| Critical-only filter | LIVE | Uses backend `is_critical`; resets page and refreshes. |
| Delayed-only filter | LIVE | Uses backend `late_by_days`; available in filter dialog. |
| Grid/Timeline/Split modes | LIVE | Local, non-persisted QML state; Split is suppressed when compact or inspector width does not fit. |
| Horizontal timeline scrolling | NOT IMPLEMENTED | Timeline width always equals its pane width. |
| Vertical grid/timeline synchronization | NOT IMPLEMENTED | `TableView` and `ListView` scroll independently. |
| Timeline date header | PARTIAL | Only left/right date labels and text saying "Today marker"; no ticks/bands. |
| Today marker | PARTIAL | Repeated inside every row; visible only when today falls in the current page-derived range. |
| Baseline rendering | NOT IMPLEMENTED | Historical fake outline was removed; no live overlay exists. |
| Dependency lines | NOT IMPLEMENTED | Backend edges exist, but no Gantt projection or renderer exists. |
| Milestones | PARTIAL/INCORRECT | A rounded small rectangle is shown when start equals finish; explicit milestone fact is lost. |
| Critical-path styling | PARTIAL | Critical bars are red, but this is task criticality, not a connected-path layer; infeasible is not visually distinct. |
| Zoom | NOT IMPLEMENTED | No control or model. |
| Timescale | NOT IMPLEMENTED | No semantic scale or tick model. |
| Expand/collapse | NOT IMPLEMENTED | No hierarchy rows or expansion state. |
| Hierarchy/WBS | PARTIAL | WBS text is shown; only execution leaves reach Scheduling. |
| Keyboard interaction | PARTIAL | Grid has Up/Down/Enter; timeline bars/rows are not keyboard-focusable. |
| Hover/tooltips | NOT IMPLEMENTED | Timeline has a row click area but no bar hover details or tooltip. |
| Row highlighting | LIVE | Timeline row and grid cell selection styles exist for the bound ID. |
| Bar highlighting | PARTIAL | Selection highlights the whole timeline row, not the bar/focus/dependency neighborhood. |
| Pagination | LIVE BUT UNSUITABLE FOR GANTT | Keeps UI small, but fragments range, hierarchy, dependencies, and chart truth by page. |

No production Gantt QML file is dead. The old Activity Timeline, Delays, Detail, and Resources panels are deleted and guarded by tests.

## 6. Fake / Placeholder State

The production Gantt paths contain no live `baselinePlaceholder`, `baseline_placeholder`, mock, dummy, sample, synthetic, or fake chart state. The only `baselinePlaceholder` occurrence is an explanatory comment stating that R4.4 removed it. The current no-baseline behavior is truthful: no baseline shape is rendered.

The current controls are also truthful: Dependency Lines, Zoom, and Timescale controls do not exist because their implementations do not exist. The IA contract test explicitly protects this.

The two non-authoritative presentation values identified by the audit were removed in R4.5B:

- activity code now comes from authoritative `Task.code`;
- milestone identity now comes from explicit `Task.is_milestone`, so a same-day normal task remains distinct from a milestone.

The timeline subtitle "baseline-ready planner lane" is aspirational wording, not fake rendered data, but should be changed when R4.5 implementation begins so UI language describes shipped behavior only.

## 7. Current Data Contract

The desktop DTO is `SchedulingTaskDto`; the presenter maps it into generic `SchedulingRecordViewModel.state`; the controller serializes that state to QML.

| Required fact | Classification | Current path / issue |
|---|---|---|
| task ID | AVAILABLE AND AUTHORITATIVE | `Task.id -> SchedulingTaskDto.id -> record.id/state.activityId`. |
| parent ID | MISSING | Exists on `Task.parent_task_id`, omitted from Scheduling DTO. |
| WBS code | AVAILABLE AND AUTHORITATIVE | `Task.wbs_code -> dto.wbs_code -> state.wbs`. |
| stable WBS order | MISSING | `Task.sort_order` and hierarchy order are omitted; default schedule order is start/critical/name. |
| activity code | INCORRECT/LEGACY | Presenter creates `A-###`; authoritative `Task.code` is omitted. |
| name | AVAILABLE AND AUTHORITATIVE | `Task.name`. |
| start/finish | AVAILABLE AND AUTHORITATIVE | CPM early dates in production; task dates only in fallback composition. |
| duration | AVAILABLE AND AUTHORITATIVE | `Task.duration_days`; timeline uses inclusive start/finish span instead. |
| status | AVAILABLE AND AUTHORITATIVE | `Task.status`; formatted label is display-derived. |
| percent complete | AVAILABLE AND AUTHORITATIVE | `Task.percent_complete`; progress label/ratio is display-derived. |
| is milestone | MISSING / INCORRECTLY DERIVED | Exists on `Task.is_milestone`; omitted and inferred from equal dates. |
| is critical | AVAILABLE AND AUTHORITATIVE | CPM `is_critical`; QML does not derive it. |
| is infeasible | AVAILABLE AND AUTHORITATIVE, PARTIALLY PROJECTED | DTO has it; table label uses it, timeline does not expose a distinct state/style. |
| total float | AVAILABLE AND AUTHORITATIVE | CPM working-day total float. |
| free float | MISSING | Not modeled by current CPM result; correctly not fabricated. |
| constraint type/date | AVAILABLE AND AUTHORITATIVE | DTO includes both; grid receives a display label, timeline does not use them. |
| baseline start/finish/duration | MISSING FROM GANTT | Persisted on `BaselineTask`; no list projection reaches Gantt. |
| baseline milestone state | MISSING | Not persisted in `BaselineTask`; duration zero is not an equivalent explicit fact. |
| dependency IDs/endpoints/type/lag | AVAILABLE BELOW GANTT | `SchedulingProjectDependencyDto` is complete; workspace does not expose it to Gantt. |
| resource information | MISSING FROM GANTT | Resource load exists at project level but no per-row assignment projection exists. |
| actual start/finish | AVAILABLE AND AUTHORITATIVE, NOT CHARTED | DTO and schedule-record state contain labels; timeline records omit them. |
| early/latest dates | AVAILABLE AND AUTHORITATIVE | CPM dates are present; timeline uses early dates only. |
| calendar identity | AVAILABLE AS SELECTED CONTEXT | A display label is copied to all rows; no per-task calendar ID is projected. |
| date ordinals/epoch days | AVAILABLE BUT DERIVED FOR DISPLAY | Current presenter emits offsets rather than raw numeric dates. |

`SchedulingCollectionViewModel` is too generic for the target chart. R4.5 should introduce a typed Gantt read projection rather than adding many opaque keys to `state`.

## 8. Schedule Authority

The production authority path is:

```text
tenant/org-scoped TaskRepository + DependencyRepository
  -> SchedulingEngine.recalculate_project_schedule(persist=False)
  -> CPMTaskInfo
     (ES, EF, LS, LF, total float, critical, infeasible, deadline lateness)
  -> SchedulingTaskDto
  -> Scheduling presenter projection
  -> controller serializer/model
  -> QML
```

The engine calculates the complete leaf-task graph using the project calendar, FS/SS/FF/SF links, lag, constraints, actual-date locks, and leveling floors. The Gantt therefore displays a mixture of canonical sources, not conflicting calculations: calculated early/latest/float/critical/infeasible values come from CPM, while duration, status, progress, actuals, identity, and WBS come from Task. `persist=False` prevents a read from writing schedule dates, but `CPMTaskInfo.task` is a replaced in-memory task carrying calculated dates.

The unconnected fallback (`build_schedule_from_tasks`) is deliberately degraded and must never be treated as equivalent: it emits persisted task dates, no latest dates, no float, and false critical/infeasible flags. Production wiring injects the engine. R4.5 should make degraded status explicit in the read contract or fail closed if a real Gantt is requested without scheduling authority.

The complete graph must remain the calculation input. Database pagination must not precede CPM. Rendering virtualization and query/view filtering can happen after the authoritative graph result.

## 9. Date Geometry

Current geometry is presenter-assisted calendar-day geometry:

1. `timeline_bounds(paged_schedule)` finds the minimum non-null start and maximum non-null finish on the current page.
2. For every row, the presenter computes `startOffsetDays = start - windowStart`, inclusive `spanDays = finishOffset - startOffset + 1`, `windowDays = windowFinish - windowStart + 1`, and `currentOffsetDays = today - windowStart`.
3. QML maps `x = round(startOffsetDays / windowDays * laneWidth)`.
4. QML maps `width = max(12 milestone / 18 task, round(spanDays / windowDays * laneWidth))`.

This is display geometry, not scheduling math. It uses calendar days on a continuous axis even though CPM computes working-day dates. That is appropriate for a conventional calendar Gantt: non-working days should be shaded, not removed from horizontal distance.

Current limitations:

- the inclusive denominator leaves a small unused area at the right edge for normal ranges;
- no half-open interval contract exists, making precise tick/bar alignment harder;
- no range padding exists;
- missing/invalid dates collapse to offset zero and one-day width rather than an explicit unscheduled state;
- same-day normal tasks and true milestones are conflated;
- minimum pixel widths can visually overstate very short tasks;
- `_barLeft` does not clamp a bar's right edge, so the minimum width can be clipped;
- `timeline_bounds()` is recomputed for every mapped row, O(P^2) for page size P.

Target display geometry should use integer date ordinals supplied once per row (`startDay`, `finishDay`, optional actual/baseline days) and one viewport contract (`rangeStartDay`, `pixelsPerDay`). QML then uses half-open geometry:

```text
x = (startDay - rangeStartDay) * pixelsPerDay
taskWidth = max(minTaskPixels, (finishDay - startDay + 1) * pixelsPerDay)
milestoneCenterX = (milestoneDay - rangeStartDay + 0.5) * pixelsPerDay
```

Unscheduled rows must have null geometry and an explicit grid state; they must not be drawn at day zero. Domain duration/working-day calculations remain outside QML.

## 10. Timeline Range

Current range is the min/max of only the current paged rows. Paging, filtering, or sorting can therefore rescale every bar even though the project schedule did not change. Project dates, actual dates, baseline dates, today, and unpaged tasks do not contribute. There is no padding.

The target deterministic range should be computed once from the complete visible Gantt projection:

1. Start with all scheduled current task start/finish dates in the selected project.
2. Include current actual start/finish dates when they extend outside planned dates.
3. Include selected-baseline task dates only while baseline overlay is enabled.
4. Include project start/end when available and valid, without clipping tasks outside them.
5. Apply scale-aware outer padding: 3 days for Day, 1 week for Week, 1 month for Month, and 1 quarter for Quarter.
6. Normalize a one-day/one-task range to at least one useful viewport unit around the task.
7. For no scheduled dates, show a truthful unscheduled empty state rather than an arbitrary year.

Today must not silently expand a historical or future project by years of empty space. The recommended default is to render/navigate Today only when it falls inside the padded content range. Whether "Today" should create a temporary out-of-range navigation window is a product decision in section 39.

For extremely long projects, content width is the date span times density. QML must cap numeric content dimensions safely and use coarse scales; it must not truncate authoritative dates.

## 11. Current Scrolling Architecture

The grid `DataTable` owns a Qt `TableView` with vertical and horizontal scrollbars. It virtualizes/reuses cells and fixes row height to `AppTheme.compactRowHeight` (30, 34, or 36 depending on density).

The timeline owns an independent vertical `ListView`; each row is 28px plus `spacingXs`. It has no horizontal `Flickable`, `contentWidth`, or horizontal scrollbar. Its header is not a scrolling time header; it is a fixed RowLayout containing range labels.

Consequences:

- scrolling either pane vertically does not move the other;
- row heights differ and can drift immediately;
- selection does not scroll the peer view into position;
- the chart cannot pan through time;
- there is no single content X shared by header, bars, dependency layer, today marker, or baseline layer;
- compact Inspector slide-over correctly overlays content, but wide Inspector consumes 288px and can force Split to Grid.

## 12. Grid/Timeline Synchronization

Filtering, sorting, and paging currently produce the same task order for both collections because both are mapped from `paged_schedule`. That is the only synchronization. Vertical positions are independent.

The target must have one authoritative row model and one authoritative vertical viewport. The recommended design is a specialized `GanttRowsViewport` backed by one `ListView`/`QAbstractListModel`. Each virtualized logical row renders its frozen grid cells and its timeline lane side by side. This eliminates contentY feedback loops entirely; it also gives grid, bar, baseline, milestone, selection, hover, and dependency anchors the same row Y and height.

Do not synchronize two independent Flickables by assigning each other's `contentY`; that approach needs recursion guards, accumulates rounding differences, complicates row expansion, and leaves keyboard `positionViewAtRow()` asymmetric.

The current separate `DataTable` is appropriate for ordinary paged catalogs but not the final integrated Gantt. Its column-state persistence contract can be reused, while its internal `TableView` need not be modified solely for Gantt.

## 13. Dependency Data

The established dependency model is sufficient for rendering semantics:

- `TaskDependency.id`;
- predecessor task ID;
- successor task ID;
- enum type FS, SS, FF, or SF;
- integer positive/zero/negative lag days;
- project-wide retrieval through `DependencyRepository.list_by_project()`;
- tenant/org and same-project enforcement.

`ProjectManagementSchedulingDesktopApi.list_project_dependencies()` already returns a complete `SchedulingProjectDependencyDto` for each edge, including IDs, endpoint names, type/value/label, and lag. It reads the project edge set in one dependency-repository query and sorts only for display determinism.

The presenter fetches these rows today, but uses them for diagnostics/open-end counts only. `SchedulingWorkspaceViewModel` exposes only selected-activity dependency records, not the project-wide edges. The Gantt contract therefore needs a typed `dependency_edges` collection; QML must never infer links or relation types by comparing dates.

Visibility semantics:

- toggle off: render no connectors and skip route preparation;
- filtered endpoint: hide the entire edge;
- endpoint inside a collapsed summary: hide the edge in the initial R4.5 implementation; do not imply a summary dependency that does not exist;
- one endpoint outside the rendered overscan viewport: hide the connector rather than draw an unexplained half-line;
- both endpoints outside: render nothing;
- both endpoints in the rendered/overscan row window: render the complete clipped connector;
- selected task: highlight only complete visible incident edges; Inspector may still report hidden incident-edge counts.

## 14. Dependency Rendering Options

| Option | Strengths | Risks | Verdict |
|---|---|---|---|
| One QML delegate/Shape per edge | Simple object semantics and individual hit testing | Thousands of QObject/delegate instances, binding churn, difficult viewport culling | Reject for the main edge layer. |
| `QtQuick.Shapes` with many `ShapePath`s | Vector paths and declarative styling | Still object-heavy; path rebuilds and scene graph updates scale with edge count | Accept only for small selected-edge overlays, not all edges. |
| One QML `Canvas` overlay | Centralized routing, low object count, explicit clipping and viewport filtering, proven QtQuick primitive already used in the repo | Must manage redraw regions, device pixel ratio, hit testing, and route cache carefully | Recommended. |
| Custom C++/Python `QQuickItem`/scene-graph item | Highest ceiling for huge graphs | New native rendering subsystem, deployment/test complexity, not an existing project pattern | Defer unless profiling proves Canvas insufficient. |

Use one `Canvas` over the visible timeline row viewport. Python/presenter supplies immutable edge facts and an adjacency index; QML builds row-ID-to-visible-Y and task-ID-to-bar-anchor maps for only the rendered rows. On row-window, X-scroll, zoom, scale, collapse, or selection changes, invalidate a route cache and repaint once through `requestPaint()`. Routing must be O(V + E_visible), not an edge-by-row scan.

FS/SS/FF/SF determine start/end anchor choice only; lag affects metadata and may later support a lag segment marker, but QML does not recalculate scheduling effects. Use orthogonal elbow routes with a small channel gutter and arrowhead at the successor. When edges overlap, selected/hovered edges take visual precedence; the initial phase does not promise automatic graph-layout deconfliction.

## 15. Baseline Data

The authoritative baseline chain is:

```text
ProjectBaseline / BaselineTask domain
  -> ProjectBaselineORM / BaselineTaskORM
  -> SqlAlchemyBaselineRepository
  -> BaselineService
  -> Scheduling desktop API baseline options/register/comparison
  -> presenter Baselines panel
```

`BaselineTask` and `BaselineTaskORM` persist per-task `baseline_start`, `baseline_finish`, `baseline_duration_days`, task ID/name, and planned cost. Repository reads are tenant/org scoped through the owning project/baseline. `BaselineService.get_baseline_task()` exposes one task snapshot and internally scans `list_tasks()`; there is no public bulk task-snapshot method for the Gantt.

The Gantt currently receives none of these facts. `selectedBaselineId` and baseline options exist on the controller, but only the Baselines panel consumes them. The Baselines panel also owns independent A/B comparison selectors; those are comparison concerns and must not become Gantt overlays.

R4.5B added immutable `baseline_is_milestone` identity to the domain, ORM, mapper, clean Alembic baseline, capture path, bulk read contract, and typed Gantt snapshot. It is captured from `Task.is_milestone`; duration/date equality is never used as a substitute.

## 16. Baseline Overlay Design

Gantt should visualize one explicitly selected authoritative baseline, not reproduce baseline creation, submit, approve, reject, delete, or A/B comparison governance.

- Reuse `baselineOptions` and one controller-owned `selectedBaselineId`; add a Gantt "Baseline" selector with an explicit None option.
- Default to None until the user chooses a baseline; do not silently overlay the newest draft or approved snapshot.
- Current planned bars remain the primary solid bars.
- Baseline task bars render as thin neutral bars below current bars within the same row, using baseline start/finish and the same date axis.
- Current milestones render as diamonds; baseline milestones render as smaller outlined diamonds below them.
- A task present now but absent in the baseline has no baseline shape and receives an optional "New since baseline" grid/tooltip state.
- A baseline task deleted from the current schedule cannot occupy a current row. Do not create a synthetic orphan row in the initial overlay; report deleted-task counts in a baseline summary/Inspector affordance and keep full deleted-row comparison in Baselines.
- If a task's current dates are missing but baseline dates exist, show the baseline shape and an explicit "Current unscheduled" state.
- Extend timeline range to selected baseline bounds only while the overlay is enabled.
- If baseline data fails to load, keep current bars visible, disable the overlay, and show a scoped error; never display stale baseline geometry for a newly selected ID.

The required backend addition is a bulk, permission-checked `list_baseline_task_snapshots(baseline_id)` read DTO. It should map one repository list call, not call `get_baseline_task()` per Gantt row.

## 17. Critical Path

CPM `is_critical` is authoritative and sufficient for task-level criticality. `is_infeasible` is also authoritative and must take visual precedence because current CPM marks negative-float tasks as both critical and infeasible.

R4.5 must separate two controls:

- **Critical only** is a query/view filter that removes non-critical rows. It exists and defaults off.
- **Highlight critical path** is a presentation preference that keeps all rows but emphasizes critical task bars and visible dependency links connecting critical endpoints. It should default on and be persisted as workspace preference.

Visual precedence should be: selected/focused outline over semantic fill; infeasible fill/pattern over critical fill; critical over normal; delayed as a badge/secondary marker rather than a competing fill; dependency-connected as a subtle halo; baseline always neutral and subordinate. QML reads explicit flags and never derives criticality from total float.

The existing `critical_path` top-12 collection is useful for Overview/diagnostics but is not the rendering source for the Gantt path. The full row projection is.

## 18. Milestones

`Task.is_milestone` exists, is validated, persisted, exposed by Tasks desktop DTOs, and honored by CPM date math. It is not end-to-end in Scheduling because `SchedulingTaskDto` omits it and `to_timeline_record()` infers it from equal dates.

R4.5 must thread explicit `is_milestone` through Scheduling and delete the equal-date inference. Visual states:

- normal task: horizontal bar with progress fill;
- milestone: centered diamond at its scheduled day, no progress-width fill;
- critical milestone: critical semantic fill plus diamond shape;
- infeasible milestone: infeasible fill/pattern, distinct from critical;
- selected/focused milestone: design-system selection/focus outline around the diamond;
- baseline milestone: smaller neutral outlined diamond on the baseline track.

A non-milestone same-day or zero-duration task remains a minimum-width task bar. Baseline milestone identity requires the new explicit snapshot field described in section 15.

## 19. Selection Architecture

The controller's `selectedActivityId` should remain the single selection authority, but its mutation contract must become atomic and complete.

Current defect: `selectActivity()` only sets the ID. `selectedActivity` was built during the prior full refresh, so the Inspector can show the wrong task after a grid/timeline click. `resolve_selected_activity_id()` also auto-selects the first paged row, causing an Inspector to open without user intent.

Target flow:

```text
grid row or timeline bar click
  -> controller.selectActivity(taskId)
  -> validate ID against current Gantt row index
  -> update selectedActivityId + selectedActivity projection together
  -> one row viewport positions selected row when requested
  -> Inspector renders the same projection
```

Selection must not rerun CPM. Keep the complete row/detail facts or a task-ID projection index in the disposable view model so selection can update synchronously. Schedule Impact remains explicitly lazy.

Selection survives zoom, timescale, horizontal scroll, split-ratio changes, and view-mode changes. It clears on project change, task deletion, or a filter/collapse operation that removes the row from the effective row set. Search/filter refresh may retain selection only if the ID remains visible. No first-row auto-selection. Enter/double-click continues to Open Task; single selection only opens the Inspector.

## 20. Hierarchy/WBS

The current Gantt is not hierarchical. The scheduling engine intentionally selects execution leaves; the grid only displays `wbs_code`. There is no parent ID, depth, summary flag, child count, ancestor list, indentation, expansion state, or summary bar.

The backend already has authoritative hierarchy facts:

- `Task.parent_task_id`, `sort_order`, and `wbs_code`;
- `TaskHierarchyQueryMixin.list_task_hierarchy()` with depth, summary, child count, and ancestor IDs;
- hierarchy rollups for dates, duration, progress, and status;
- Tasks desktop DTOs already expose these facts.

R4.5 required scope is read-only hierarchy presentation: stable WBS preorder, indentation, summary rows, expand/collapse, children visibility, and summary bars derived from canonical leaf schedule dates. Do not feed summary tasks into CPM and do not let summary rows become dependency endpoints unless the domain edge actually targets them (current CPM filters dependencies to leaves).

Do not reuse `list_task_hierarchy_rollups()` naively for 5,000 rows: it scans the node set for each node and is O(N^2). Build the Gantt hierarchy projection in one hierarchy traversal and merge leaf CPM results by task ID. This is display/read-model assembly, not new scheduling semantics.

Deeper WBS mutation, drag-to-reparent, reorder, and outline editing remain in Tasks/product follow-up. R4.5 may expose Open Task but must not add mutation logic to the chart.

## 21. Row Geometry

Current row authority is inconsistent:

- `DataTable`: `AppTheme.compactRowHeight`, currently 30/34/36 by density;
- timeline: fixed 28px plus `spacingXs` between delegates;
- milestone/task visual heights: 12/14px;
- headers: unrelated component heights.

The target integrated viewport should define one `rowHeight` property sourced from `AppTheme.compactRowHeight` and no inter-row spacing. Grid cells, lane background, selection, bar center, baseline track, dependency Y anchors, hover, and focus all derive from `rowIndex * rowHeight`. Summary rows use the same height in R4.5; hierarchy depth changes indentation, not height. This preserves constant-time row-to-Y mapping and reliable virtualization.

The grid header and timeline two-band header share one `headerHeight` contract, preferably two compact half-bands within a height derived from `toolbarHeight`/theme density. Milestones do not change row height. Variable-height rows and expanded inline detail are out of scope; details remain in Inspector.

## 22. Zoom

Use a combined but non-conflicting model:

- timescale selects semantic header units and a base pixels-per-day density;
- zoom selects one of five discrete density multipliers within that scale: 0.75, 0.875, 1.0, 1.25, 1.5;
- default zoom is 1.0;
- Reset restores the selected scale's 1.0 density;
- zoom keeps the date under the viewport center stable, or the cursor date when reliable pointer coordinates are available;
- zoom changes display geometry only and never schedule dates.

Discrete levels are preferable to unconstrained continuous zoom because they produce testable tick density, prevent unusable label states, and work predictably with keyboard controls. Buttons disable at minimum/maximum. Wheel/pinch support can map to the same discrete levels later; it must not create a second continuous state.

Suggested base densities are Day 40 px/day, Week 12 px/day, Month 4 px/day, and Quarter 1.5 px/day. These are starting values to validate at the five approved viewports, not new design-system tokens until measurements support them.

## 23. Timescale

The minimum viable enterprise set is Day, Week, Month, and Quarter, delivered incrementally rather than as dead controls.

| Scale | Major band | Minor band | Base density | Intended use |
|---|---|---|---:|---|
| Day | Month | Day | 40 px/day | Short detailed schedules. |
| Week | Month | Week | 12 px/day | Default project planning view. |
| Month | Year | Month | 4 px/day | Multi-quarter projects. |
| Quarter | Year | Quarter | 1.5 px/day | Multi-year overview. |

Week should be the default. Header tick models should be precomputed as immutable display facts: start/end day, label, major/minor classification, weekend/non-working shading metadata, and X/width derived in QML. Labels are elided/skipped according to available tick width; the underlying scale does not change merely because a label is hidden.

Timescale changes preserve the center date, reset zoom to neutral unless the saved state includes a valid scale/zoom pair, and recalculate only display ticks/geometry. Do not compress non-working days. Quarter can ship after Day/Week/Month foundations but remains inside R4.5.

## 24. Responsive Design

The shared compact convention is `AppTheme.compactContentBreakpoint == 1024`; current Gantt uses `width < 1024`. Current Split minimums are grid 420px and timeline 360px, with a 288px inline Inspector. R4.5 should retain shared conventions and add content-budget checks, not arbitrary window-width breakpoints.

| Target viewport | Target Gantt behavior |
|---|---|
| 1024x640 | Grid or Timeline mode only; compact toolbar overflow; Inspector as slide-over; timeline header remains usable with horizontal pan. |
| 1280x720 | Split only when actual Gantt content width satisfies grid + timeline minimums; selection may use slide-over if inline Inspector would violate those minimums. |
| 1366x768 | Split default when content budget permits, approximately 44% grid / 56% timeline; Inspector switches to overlay/slide-over if it would collapse either pane. |
| 1440x900 | Split default; inline Inspector may coexist when measured content width still satisfies both pane minimums. |
| 1920x1080 | Split default, approximately 40% grid / 60% timeline; inline Inspector; full toolbar where it fits. |

`canSplit` must be based on the Gantt root's actual available width, not `Window.width`, because shell navigation and Inspector consume space. At compact widths, changing mode does not destroy selection or horizontal time position. Toolbar controls should use an overflow menu following existing app patterns; critical filter, Today, and view mode remain highest priority, while dependency/baseline and density controls can move into More.

The current route-load test at five dimensions proves instantiation only. R4.5 needs geometry assertions and screenshots/manual verification before responsive closure.

## 25. Inspector Interaction

R4.4's Inspector architecture remains unchanged:

- one shared Inspector component;
- inline at wide widths;
- temporary right slide-over at compact/insufficient widths;
- fixed Inspector header and scrollable body;
- lazy Analyze Impact action;
- Open Task navigation;
- no automatic Schedule Impact calculation on row selection.

R4.5 must fix only the data/selection integration described in section 19. Opening the Inspector must not alter timeline X, timescale, zoom, or project context. If inline Inspector makes Split invalid, preserve the user's requested mode and render the effective mode as Grid or Timeline temporarily; closing Inspector restores Split. Slide-over must not resize the chart and its scrim must not leak pointer events to bars.

Inspector schedule facts should consume the same selected row projection as the grid/timeline. Expensive dependency detail, baseline detail, and Schedule Impact remain lazy or separately fetched; selection itself should be O(1).

## 26. Gantt Toolbar

Final truthful Gantt-local controls:

| Control | Dependency | Default | Persistence / behavior |
|---|---|---|---|
| Search / status / delayed / critical-only | Complete schedule projection | Existing values | Query/view state; changes effective rows and clears invalid selection. |
| Highlight Critical Path | authoritative critical/infeasible flags | On | Workspace preference; does not filter. |
| Dependency Lines | project-wide edge projection and renderer | On for ordinary schedules | Workspace preference; adaptive suppression may apply at measured edge thresholds. |
| Baseline | baseline options + bulk task snapshots | None | Project-scoped workspace preference; no governance actions. |
| Timescale | tick/range model | Week | Workspace preference. |
| Zoom - / reset / + | scale density model | 1.0 | Workspace preference as validated scale/zoom pair. |
| Grid / Timeline / Split | responsive content budget | Split where valid | Workspace preference; effective mode may adapt without overwriting requested mode. |
| Today | today inside range, or approved out-of-range policy | Enabled only when truthful | Ephemeral navigation action, not persisted. |
| Customize Columns | existing table-state store | Existing | Reuse organization-scoped table column state. |

No control is added before its backing data, rendering, failure state, and test gate are complete. Critical-only and critical highlighting must use distinct labels. "Baseline" must show selected baseline name/status and a clear None state.

## 27. View-State Persistence

Gantt view state is user/workspace preference, not project business truth. Use the existing `AppSettingsStore`/organization-scoped settings pattern and extend it with a dedicated Gantt state record rather than storing unrelated values in table-column JSON.

Persist, after validation:

- requested Grid/Timeline/Split mode;
- split ratio;
- timescale;
- zoom level;
- dependency-lines visibility;
- critical-path highlighting;
- baseline-overlay visibility and selected baseline per project;
- grid column order/visibility through the existing table state.

Do not persist selected task, hover/focus, contentY, transient horizontal X, loading/error state, or Schedule Impact result. Search/filter/page state can remain controller-session state unless a separately approved saved-view capability owns it. Invalid or removed baseline IDs resolve to None; invalid enum/density values fail safe to documented defaults.

## 28. Performance Risks

Current risks are masked by the 25-row page:

- `list_schedule()` recalculates the complete CPM graph on every workspace refresh, including search keystrokes, sort, filter, and page changes;
- the presenter eagerly calls projects, calendars, schedule, project dependencies, baseline register/comparison, resource load, constraint violations, selected-task dependencies, diagnostics, feed, and details in one build;
- `to_timeline_record()` calls `timeline_bounds(paged_schedule)` for every row, O(P^2);
- schedule and timeline duplicate generic dictionaries and serialization work;
- `DynamicTableModel.set_rows()` resets the table page after each refresh;
- current `ListView` virtualizes timeline rows, but a naive future Repeater/Shape per all-row/all-edge design would defeat that advantage;
- the existing hierarchy rollup helper is O(N^2) when requested for every node;
- selection currently risks a full refresh if fixed through `activateActivity()` rather than an indexed projection;
- future Canvas repaint on every binding change could cause redraw storms;
- horizontal content widths for multi-year Day scale can become very large;
- no current Gantt performance measurement covers 100, 1,000, or 5,000 tasks.

Required measured targets, excluding canonical CPM/database time and measured separately after data delivery:

- 100 rows: first usable chart projection/render <= 250ms;
- 1,000 rows: <= 500ms;
- 5,000 rows: <= 1,000ms with progress/loading feedback;
- row delegate count bounded to visible rows plus at most two viewport overscan bands, not N;
- steady scroll/pan p95 frame work <= 16.7ms where hardware supports 60fps and no individual UI stall > 50ms;
- zoom/timescale interaction acknowledgement <= 100ms, with expensive repaint coalesced;
- selection-to-highlight/Inspector update <= 50ms without DB/CPM work;
- edge routing proportional to visible endpoints/edges, never O(N x E) or O(N^2);
- no CPM rerun for pure search, selection, zoom, scale, view mode, split ratio, or scroll.

These are exit targets to profile in the project's supported desktop environment, not assumptions that current code meets them.

## 29. Large-Schedule Strategy

Do not database-page tasks before CPM. Instead:

1. Calculate/read the complete authoritative leaf schedule once per schedule revision/project refresh.
2. Merge it with one hierarchy traversal, project dependency edges, and optional selected-baseline snapshots into a disposable Gantt read model.
3. Store typed rows in a `QAbstractListModel`/indexed controller model rather than duplicate `QVariantList` collections.
4. Apply search/filter/collapse against that immutable projection without rerunning CPM.
5. Remove visual pagination from Gantt; use one virtualized vertical row viewport across the effective row set. Ordinary Tasks remains database-paginated.
6. Maintain O(1) task-ID-to-model-index and task-ID-to-detail lookup.
7. Build visible row/edge maps from the viewport plus bounded overscan.
8. Render bars/milestones as recycled delegates and dependencies through one Canvas.
9. Coalesce X-scroll/zoom/model-change repaints to one frame.
10. Keep any cache session/view scoped and invalidated by project/task/dependency/calendar/baseline domain changes. It is disposable and never a source of truth.

At 5,000 rows, the memory cost of compact typed facts is acceptable; 5,000 permanent QML row objects and potentially tens of thousands of edge objects are not. If measured edge density remains too high, automatically suppress non-selected dependency lines with a truthful "Dependency lines hidden for performance; select a task to inspect links" state. The threshold must be measurement-backed and visible, not silent.

## 30. Python vs QML Responsibility

| Layer | Owns | Must not own |
|---|---|---|
| Domain/application | CPM dates, dependency semantics/lag, constraints, actual locks, project calendars, criticality, infeasibility, float, explicit milestone, baseline capture, hierarchy invariants | Pixels, viewport, selected visual scale, QML color/shape decisions |
| Repositories/readers | Tenant/org-scoped tasks, edges, hierarchy inputs, baseline snapshots; deterministic data retrieval | Chart routing or UI state |
| Desktop API | Typed, transport-neutral Gantt rows/edges/baseline snapshot DTOs; permission-safe bulk reads | QML dictionaries or screen geometry |
| Presenter/read-model builder | Merge authoritative facts by stable ID; one-pass hierarchy projection; display labels; integer date ordinals; deterministic range/tick descriptors; adjacency/index preparation | Scheduling date/float/critical recalculation; inferred milestone semantics |
| Controller/model | Selected project/query state, immutable row model, selected ID/detail index, validated view preferences, loading/errors, model invalidation | Bar geometry loops, Canvas drawing, domain semantics |
| QML | Date-to-pixel mapping, viewport/overscan, scroll position, recycled row/bar delegates, Canvas connector drawing, visual state precedence, responsive layout, focus/keyboard intent | CPM, working-day duration, dependency effects, baseline truth, criticality derivation |

Date ordinals, range bounds, and tick intervals are display projection facts, not scheduling results. Their precomputation in Python avoids repeated parsing while preserving QML ownership of pixels.

## 31. Backend Data Gaps

| Needed fact/contract | Class | Resolution |
|---|---|---|
| `Task.code` in Scheduling | RESOLVED R4.5B | Typed row uses `Task.code`; generated `A-###` is removed. |
| parent ID, sort order, depth, summary, child count, ancestors | RESOLVED R4.5B | One-pass canonical WBS preorder projection. |
| explicit current milestone | RESOLVED R4.5B | `Task.is_milestone` is end-to-end in Scheduling/Gantt. |
| project-wide dependency edges in workspace | RESOLVED R4.5B | Typed deterministic edge collection plus adjacency index. |
| bulk selected-baseline task snapshots | RESOLVED R4.5B | One permission-checked BaselineService repository-list read. |
| current/baseline/actual numeric date ordinals | RESOLVED R4.5B | Typed dates remain and display ordinals are computed once. |
| summary row dates/progress from canonical leaf results | RESOLVED R4.5B | Linear reverse merge; summaries never enter CPM. |
| timeline range/tick descriptors | B | Derive from projected authoritative dates and selected display scale. |
| baseline explicit milestone identity | RESOLVED R4.5B | Immutable domain/persistence/capture/read snapshot fact. |
| per-task calendar identity | C if product requires row-specific labeling | Current engine may resolve resource calendars but Scheduling DTO only has selected context label. Defer until a truthful source is exposed. |
| free float | C | CPM result does not model it; do not add for visual parity. Defer. |
| per-row resources/workload lanes | C/D | Requires an approved assignment/workload projection; belongs to R5 unless only a simple read-only label is approved. |
| drag scheduling, WBS mutation, dependency editing on canvas | D | Separate product/command design; not required for R4.5 viewer modernization. |
| cross-project dependency rendering | D | Current dependency invariant is same-project; do not imply otherwise. |

No backend gap justifies changing canonical scheduling semantics.

## 32. Existing Test Coverage

Current relevant coverage:

- `test_qml_scheduling_planning_ia_contract.py`: approved navigation/header, truthful controls, no fake baseline, responsive source contract, retired files, and route loading at five viewports;
- `test_qml_project_management_presenters_scheduling.py`: controller/catalog wiring, schedule/critical/baseline presentation, sort state, and project switch;
- `test_project_management_desktop_api_scheduling.py`: schedule/calendar/baseline desktop API behavior;
- `test_scheduling_schedule_sort.py`: allowed sort behavior and deterministic IDs;
- CPM, dependency, constraint, actual-date, milestone, baseline workflow, enterprise calendar, and resource-leveling test suites protect domain authority;
- `test_dependency_query_performance.py`: one project-wide dependency read and changed-only schedule persistence behavior;
- shared `DataTable` tests protect current virtualization, sorting, keyboard, selection, and resizing behavior.

Missing R4.5 coverage:

- exact date-to-pixel and inclusive interval geometry;
- deterministic complete-project range and padding;
- Day/Week/Month/Quarter tick models and label density;
- zoom anchoring and min/max/reset;
- one vertical scroll authority and header/body horizontal synchronization;
- project-wide FS/SS/FF/SF connector anchors, visibility rules, lag labels, clipping, and selection highlighting;
- bulk baseline projection and overlay states, including added/deleted/unscheduled tasks;
- explicit milestone vs zero-duration non-milestone rendering;
- critical vs infeasible visual precedence;
- row/bar/Inspector selection consistency and no auto-selection;
- hierarchy expansion/collapse and stable preorder;
- actual responsive geometry at the five viewports;
- 100/1,000/5,000-row delegate, frame, projection, repaint, and memory measurements;
- no CPM/database call on selection, scroll, zoom, timescale, or local filter changes;
- preference validation and organization/project scoping.

No tests are added during R4.5A.

## 33. Rendering Architecture Options

### Option A: Keep DataTable and Timeline as Separate Views

Expose scroll APIs on `DataTable`, synchronize two Flickables, extend `SchedulingTimelinePanel` with a horizontal Flickable, add row delegates, and place Canvas above the timeline.

Advantages: smaller initial QML change; preserves generic DataTable column behavior. Disadvantages: two vertical authorities, feedback-loop guards, difficult hierarchy expansion, mismatched virtualization, cross-view position APIs, duplicated row delegates, and fragile selection/row geometry. It can work for a small flat chart but scales maintenance risk.

### Option B: Integrated Specialized Gantt Row Viewport

Build a typed Gantt model and one virtualized row viewport. Each recycled row contains a frozen grid region and timeline lane; one horizontal timeline Flickable controls header, lanes, overlays, and Canvas. Keep Inspector outside the surface and reuse table-column preference concepts.

Advantages: vertical synchronization by construction, one row order, constant row geometry, simple selection positioning, natural hierarchy, bounded delegates, centralized dependency rendering, and clean 5,000-row strategy. Disadvantages: requires a purpose-built grid header/cell renderer and deliberate column customization support.

### Option C: Custom Native Scene-Graph Gantt Item

Render rows, bars, headers, and dependencies in a custom `QQuickItem`/scene graph.

Advantages: highest theoretical rendering ceiling. Disadvantages: substantial new native subsystem, harder accessibility/hit testing, more complex PySide deployment/testing, and no established local primitive. It is not justified before profiling Option B.

Option B is the recommended architecture. Option C is a measured escape hatch, not a parallel implementation.

## 34. Recommended Architecture

1. **Timeline rendering:** QML-native recycled row delegates inside one specialized `GanttRowsViewport`.
2. **Dependency rendering:** one viewport-aware Canvas with cached orthogonal routes for complete visible edges.
3. **Vertical scroll authority:** the single Gantt row `ListView`; no mirrored `contentY` loop.
4. **Horizontal scroll authority:** one timeline `Flickable`; bind header, row lanes, today marker, baseline shapes, and Canvas to its content X.
5. **Row geometry authority:** one theme-derived fixed row height and one shared header-height contract.
6. **Selection authority:** controller-owned `selectedActivityId` plus O(1) indexed detail projection, updated atomically.
7. **Zoom model:** five discrete density levels within the selected semantic timescale, anchored around center/cursor date.
8. **Timescale model:** Day, Week, Month, Quarter; Week default; two-band deterministic ticks.
9. **Baseline model:** one explicit selected baseline, bulk authoritative snapshots, subordinate per-row overlay, no governance duplication.
10. **Viewport/performance:** complete authoritative schedule projection, no Gantt pagination, virtualized rows, visible-edge Canvas culling, one-pass hierarchy merge, no CPM rerun for UI-only interactions.

The Gantt read model is disposable. It can be rebuilt from authoritative services at any time and must never become schedule, dependency, hierarchy, or baseline truth.

## 35. Proposed Component Tree

Use the existing scheduling workspace structure and add a bounded Gantt subpackage:

```text
panels/
`-- SchedulingGanttPanel.qml              # orchestration, Inspector placement

components/gantt/
|-- SchedulingGanttToolbar.qml            # truthful controls and overflow
|-- SchedulingGanttSurface.qml            # responsive mode/split composition
|-- SchedulingGanttHeader.qml             # grid header + two-band time header
|-- SchedulingGanttRowsViewport.qml       # single ListView / vertical authority
|-- SchedulingGanttRow.qml                # frozen grid cells + lane delegate
|-- SchedulingGanttBar.qml                # task/progress/milestone/baseline shapes
`-- SchedulingGanttDependencyLayer.qml    # one Canvas and route cache
```

Supporting Python should be similarly bounded:

```text
api/desktop/scheduling/models/gantt.py
api/desktop/scheduling/serializers/gantt_serializer.py
api/desktop/scheduling/builders/gantt_builder.py
presenters/scheduling/gantt_projection.py
controllers/scheduling/gantt_state.py
controllers/scheduling/gantt_model.py
```

Names may be adjusted to repository conventions during implementation, but responsibilities must remain separated. Do not grow `SchedulingTimelinePanel.qml` into a monolith and do not fragment individual labels/grid lines into standalone components. Retire `SchedulingTimelinePanel.qml` only after guarded reference and qmldir verification.

## 36. Proposed R4.5 Implementation Sequence

1. **R4.5A - Engineering audit/design:** this document; no production change.
2. **R4.5B - Authoritative Gantt read contract (COMPLETE):** typed rows/edges/baseline snapshots, explicit milestone, hierarchy facts, date ordinals, stable IDs/order, one-pass merge, no generated activity codes, selection-detail index, characterization and scale tests.
3. **R4.5C - Integrated viewport and selection:** specialized single vertical row viewport, frozen grid/timeline composition, horizontal authority, atomic row/bar/Inspector selection, no first-row auto-selection, existing Inspector preserved.
4. **R4.5D - Time axis, range, timescale, and zoom:** deterministic complete-project range, two-band header, Week default, Day/Month/Quarter, discrete zoom, Today behavior, non-working shading where authoritative calendar facts permit.
5. **R4.5E - Dependency visualization:** Canvas routing, FS/SS/FF/SF anchors, viewport culling, visibility semantics, selection highlighting, lag tooltip/metadata.
6. **R4.5F - Baseline, milestone, and critical/infeasible layers:** baseline schema/read addition, selected overlay, explicit milestone shapes, critical highlight separate from filter, visual precedence tests.
7. **R4.5G - Responsive, persistence, keyboard, and performance:** toolbar overflow, five viewport layouts, validated preferences, essential focus/keyboard behavior, 100/1,000/5,000 measurements and tuning.
8. **R4.5H - Validation and cleanup:** targeted regression matrix, qmllint/offscreen checks, dead old timeline code/qmldir cleanup, documentation/exit reconciliation, no compatibility stubs left behind.

R4.5B must precede visual feature controls. A control ships in the same phase as its complete data/render/test path.

## 37. Phase Exit Gates

| Phase | Exit gate |
|---|---|
| R4.5A | All 40 audit sections complete; exact source paths and gaps reconciled; no production files changed. |
| R4.5B | COMPLETE: typed complete-project Gantt projection is tenant/org safe; explicit milestone/hierarchy/edges/baseline facts covered; generated activity code and equal-date milestone inference removed; selection lookup O(1); local view operations avoid CPM; no scheduling-semantic change. |
| R4.5C | One vertical authority; grid/timeline rows cannot drift; one horizontal authority; row/bar/Inspector selection agrees; no auto-selection; Inspector and Schedule Impact regressions green. |
| R4.5D | Deterministic range and all four scales tested; zoom min/max/reset/anchor tested; header/body X never drift; no UI action reruns CPM. |
| R4.5E | FS/SS/FF/SF anchors and visibility rules tested; Canvas processes only visible/overscan edges; no misleading partial connector; toggle is truthful. |
| R4.5F | Baseline snapshots are bulk/read-safe and explicit about milestones; added/deleted/unscheduled cases tested; critical/infeasible/milestone/selection precedence is unambiguous. |
| R4.5G | Five viewports pass geometry and offscreen load tests; preferences fail safe; keyboard essentials pass; measured 100/1,000/5,000 budgets meet section 28 or deviations are resolved, not waived silently. |
| R4.5H | Targeted PM scheduling/domain/shared-QML regressions green; qmllint green; no placeholder, duplicate renderer, unused API, stale qmldir entry, compatibility shim, or dead timeline code remains; closure docs identify any explicitly approved deferment. |

No phase may close on source-string tests alone where runtime QML behavior is material.

## 38. Exact R4.5/R5 Boundary

R4.5 delivers a professional read/inspect Gantt over existing schedule truth: hierarchy display, bars, milestones, dependencies, baseline overlay, critical/infeasible visualization, synchronized navigation, responsive behavior, and scale/performance engineering.

R5 continues to own workload management and resource-capacity experience: resource lanes/histograms, availability heatmaps, assignment balancing, My Time, Review Queue, and workload-specific navigation. R4.5 may display an already-authoritative simple task resource label only if approved and cheaply projected; it must not build resource utilization semantics into the chart.

The following also remain outside R4.5 unless separately approved: drag-to-reschedule, inline task editing, dependency creation by drawing links, WBS drag/reparent/reorder, cross-project dependencies, scenario scheduling, portfolio roadmap, probabilistic schedules, print/export redesign, and broad R8 accessibility work.

R4.5 must not reopen `run_cpm`, FS/SS/FF/SF and lag semantics, constraint-aware scheduling, negative float/infeasibility, calendar authority, resource-leveling Preview/Apply, accepted leveling convergence, or Task Detail Schedule Impact.

## 39. Open Product Decisions

**Status: CLOSED.** The following choices are locked for R4.5 implementation:

1. **Baseline default:** explicit None; never automatic latest/approved.
2. **Hierarchy default expansion:** roots visible, first-level summaries expanded, deeper summaries collapsed; expansion is session/project view state.
3. **Sorting in hierarchy mode:** canonical WBS preorder; another sort switches to explicit flat mode without indentation.
4. **Today outside project range:** unavailable with truthful explanation; never expand years of blank canvas.
5. **High-edge-density fallback:** measured adaptive suppression is allowed, visible to the user, while selected-task incident links remain available.
6. **Dependency default:** On for ordinary schedules, subject to user preference and measured density protection.
7. **Baseline-deleted tasks:** counts/link through Baselines later; no synthetic orphan Gantt rows.
8. **Quarter delivery timing:** Quarter remains in R4.5D.

None of these decisions requires changing scheduling semantics.

## 40. Final Recommendation

Option B remains approved: a specialized integrated Gantt surface with one virtualized row viewport, one horizontal timeline authority, lightweight recycled QML bar delegates, and one viewport-aware Canvas dependency layer. R4.5B is complete; R4.5C is the next phase.

R4.5B should first create a typed, disposable, complete-project Gantt projection that merges canonical CPM leaf results with existing hierarchy and dependency facts and selected-baseline snapshots. It must preserve tenant/org/project authorization, expose explicit milestone identity, add historical baseline milestone identity, remove generated activity codes, stop page-derived timeline bounds, eliminate first-row auto-selection, and make selection/detail updates atomic without rerunning CPM.

R4.5C must replace the independently scrolling grid/timeline pair and delete the explicitly temporary `gantt_legacy_adapter.py` once the specialized viewport consumes `GanttListModel` directly. R4.5C-H then continue incrementally while preserving the established enterprise scheduling engine as the sole business authority.
