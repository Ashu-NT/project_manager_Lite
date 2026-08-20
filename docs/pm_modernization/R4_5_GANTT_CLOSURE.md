# R4.5 Gantt Closure

## 1. Status

**R4.5 GANTT MODERNIZATION - CLOSED**

R4.5A through R4.5H are complete. Final cleanup, runtime verification,
architecture guardrails, broad relevant PM regression, and documentation
reconciliation passed. No R5 capability was implemented and no commit was
created by Codex during R4.5H.

## 2. Scope Delivered

The Planning workspace now has one complete-project, disposable Gantt read
model; Grid, Timeline, and Split modes; WBS hierarchy; coherent selection;
Day/Week/Month/Quarter scales; discrete zoom; Today navigation; authoritative
milestones, baseline, critical and infeasible facts; FS/SS/FF/SF connectors;
responsive Inspector and toolbar behavior; durable view preferences; keyboard
essentials; and bounded large-project rendering.

## 3. Final Architecture

The final design has one typed projection, one `GanttListModel`, one
`GanttTimeAxisController`, one recycled vertical `ListView`, one horizontal
timeline authority, one shared date geometry utility, one selection authority,
and one viewport-aware dependency `Canvas`. The projection is disposable and is
never persisted as schedule truth.

Inventory classification:

| Class | Final result |
|---|---|
| KEEP | Typed DTOs/builder, desktop API, list model, axis controller, Gantt panel and seven registered QML components, geometry helper, settings contract, B-H tests/docs |
| DELETE | Legacy adapter/timeline/pagination from C; duplicate Scheduling detail/dependency side-channel and obsolete tests from H |
| RENAME | None required |
| LEGACY | None in the production Gantt path |
| UNUSED | None found in the final registered component tree |
| TEST-ONLY | Runtime probes, timing/route telemetry, architecture guardrails, fake projection builders |

The dependency layer retains one component-owned zero-delay `Timer` solely to
coalesce paint requests. It does not poll, rebuild the model, query data, or
outlive its component.

## 4. Final Component Tree

```text
SchedulingGanttPanel.qml
`-- SchedulingGanttSurface.qml
    |-- SchedulingGanttHeader.qml
    |-- SchedulingGanttRowsViewport.qml
    |   `-- SchedulingGanttRow.qml (recycled)
    |       |-- SchedulingGanttBar.qml
    |       `-- SchedulingGanttBaseline.qml
    `-- SchedulingGanttDependencyLayer.qml (one Canvas)

GanttGeometry.js (shared date/bar/milestone geometry)
qmldir (exactly the seven QML components above)
```

Every registration has a live consumer. There is no `SchedulingTimelinePanel`,
second row viewport, second header, Shape-per-edge renderer, baseline viewport,
or visual Gantt pagination.

## 5. Read/Data Flow

```text
Planning route / selected project
-> Scheduling workspace controller/presenter
-> ProjectManagementSchedulingDesktopApi.build_gantt_projection()
-> active tenant + organization and authorized project checks
-> canonical hierarchy + SchedulingEngine/run_cpm + project dependencies
-> optional authorized bulk baseline snapshot read
-> typed GanttProjectionDto builder
-> GanttListModel + GanttTimeAxisController
-> one integrated QML surface + Inspector
```

Project, authoritative domain, and baseline changes rebuild the projection.
Selection, scrolling, local filters/sort, hierarchy expansion, view mode, split
resize, zoom, timescale, Today, critical highlight, and dependency visibility do
not query the database or rerun CPM. Baseline selection performs only its
authorized bulk snapshot read and does not run CPM.

## 6. Scheduling Authority

`SchedulingEngine` and `run_cpm` remain the only schedule authority. QML and
presenters do not calculate dependency effects, lag shifts, working-day dates,
constraints, criticality, infeasibility, or leveling. Summary rows are display
rollups and never enter CPM. Schedule Impact remains lazy.

## 7. Hierarchy

Hierarchy mode preserves canonical WBS preorder and explicit depth/ancestor
facts. Expansion is local and indexed. Flat sorting removes tree indentation so
it cannot imply a false hierarchy. Summary rows are read-only, receive no
synthetic dependency, and do not become schedule inputs.

## 8. Selection

`controller.selectedActivityId` is the sole logical selection authority. Grid,
bar, milestone, keyboard, and Inspector remain coherent. Initial load and
project switch do not auto-select the first row. Filtering/collapse clears or
resolves selection through the indexed model without a competing QML current
task.

## 9. Timeline Axis

`GanttTimeAxisController` owns the deterministic padded project range, visible
ticks, pixels per day, and viewport state. Header, bars, milestones, baseline,
Today marker, non-working shading, and dependency anchors use the same logical
axis. The internal `timelineContentX` property is retained because it drives the
surface's center-preservation and axis-viewport synchronization signal.

## 10. Timescale / Zoom

Day, Week, Month, and Quarter pass runtime geometry tests. Zoom accepts the five
discrete multipliers `0.75`, `0.875`, `1.0`, `1.25`, and `1.5`; min/max/reset and
center preservation pass. Today navigation is truthful and does not fabricate
or expand the project range.

## 11. Dependency Rendering

One central Canvas renders complete visible/overscan routes from indexed
adjacency. FS is finish-to-start, SS start-to-start, FF finish-to-finish, and SF
start-to-finish. Lag is metadata only; the renderer does not shift dates.
Arrows point to successors. Selected incident routes are emphasized, and the
high-density fallback reports truthful suppression instead of drawing a
misleading partial graph.

## 12. Dependency DPR Fix

Bars, milestones, baselines, row centers, and connector routes remain in logical
QML coordinates; the Canvas does not manually multiply coordinates by DPR.
Painted runtime probes pass at DPR 1.0, 1.25, 1.5, and 2.0 across horizontal and
vertical scrolling, all four relationships, all scales, every zoom, hierarchy,
flat sort, and first/middle/last visible row positions.

## 13. Baseline

The Gantt baseline defaults to None. Selection is organization/project scoped
and accepted only after authorized options load. One bulk snapshot read feeds an
indexed overlay; there is no per-row query or second viewport. Current-only and
baseline-only tasks are not fabricated. Missing, deleted, unauthorized, or
wrong-project baseline IDs fail safely. Snapshot data remains authoritative and
disposable.

## 14. Milestones

Current milestone truth comes only from `Task.is_milestone`; historical truth
comes only from `baseline_is_milestone`. Same-day non-milestones remain bars.
No `start == finish` or zero-duration presentation heuristic determines
milestone identity.

## 15. Critical / Infeasible Semantics

Critical and infeasible flags come from canonical backend facts. Infeasible
visual precedence remains above critical, while selection/focus does not erase
either state. The UI says critical-task highlighting, not a fabricated critical
path, and the critical-only filter remains separate from visual highlighting.

## 16. Responsive Behavior

| Viewport | Inspector | Controls | Requested Split result |
|---|---|---|---|
| 1024 x 640 | Slide-over | Overflow | Grid fallback; Timeline remains selectable |
| 1280 x 720 | Slide-over | Overflow | Split |
| 1366 x 768 | Inline | Direct | Split when the 1024 px Gantt budget remains |
| 1440 x 900 | Inline | Direct | Split |
| 1920 x 1080 | Inline | Direct | Split |

Grid stays at least 420 px, Timeline at least 360 px, and the splitter is 6 px.
Fallback never overwrites the requested mode. Inspector close/resize restores
the requested Split where feasible; essential controls remain reachable.

## 17. View-State Persistence

Organization-scoped settings persist requested mode, split ratio, timescale,
zoom, dependency visibility, critical highlighting, and existing grid-column
state. Baseline ID preference is additionally project scoped. Malformed modes,
ratios, scales, zoom values, booleans, and JSON fail safely to validated
defaults. Settings never mutate Project, Task, Baseline, Dependency, or schedule
facts.

Selected task, focus, hover, Inspector state, scroll positions, hierarchy
expansion, routes, snapshot arrays, loading/errors, and Schedule Impact remain
transient.

## 18. Keyboard Behavior

The single row viewport owns Up, Down, Home, End, Enter/Return, and implemented
Left/Right hierarchy behavior. Offscreen rows use indexed lookup and
`positionViewAtIndex`; focus remains visible and selection stays coherent across
Grid, Timeline, and Split. Keyboard actions perform no schedule mutation,
database read, or CPM run.

## 19. Performance

Final Windows `pmenv` offscreen measurements are regression
characterizations, not universal hardware guarantees.

| Rows | Core model attach | Core first viewport | Delegates | Selection | Scroll | Filter | Mode |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3.886 ms | 29.675 ms | 20 | 0.050 ms | 7.103 ms | 2.559 ms | 0.404 ms |
| 1,000 | 30.334 ms | 28.316 ms | 20 | 0.041 ms | 7.451 ms | 3.792 ms | 0.096 ms |
| 5,000 | 140.908 ms | 29.810 ms | 20 | 0.041 ms | 7.560 ms | 13.433 ms | 0.101 ms |

Axis interaction for 100/1,000/5,000 rows was 0.373/0.345/0.661 ms with two
major and eight minor visible ticks. Rendering remains bounded by viewport plus
small overscan, not N.

## 20. 5,000-Row Combined Scenario

The final scenario contains 5,000 hierarchy rows, 4,900 baseline snapshots,
4,899 mixed FS/SS/FF/SF dependencies with signed lag, explicit milestone mix,
critical and infeasible facts, Month scale, 0.875 zoom, selection, horizontal and
vertical scroll, and the inline Inspector.

| Rows | Projection | Model | Full-panel first viewport | Delegates | Scroll | Zoom | Visible edges | Peak memory |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 10.624 ms | 0.290 ms | 305.869 ms | 27 | 22.819 ms | 6.953 ms | 30 | 0.435 MiB |
| 1,000 | 53.900 ms | 2.256 ms | 259.471 ms | 27 | 28.777 ms | 9.372 ms | 31 | 4.243 MiB |
| 5,000 | 378.675 ms | 10.340 ms | 257.756 ms | 27 | 19.568 ms | 13.129 ms | 31 | 20.779 MiB |

No visible stall or unbounded delegate/edge object growth was observed in the
offscreen harness. A-B-C-A switching with distinct 5,000/100/1,000-row project
IDs replaces rows, axis, baseline and edge indexes without stale cross-project
IDs; delegates and visible edge candidates remain below 100.

## 21. Security / Scope

The desktop API requires active tenant and organization IDs, an authorized
project lookup, canonical complete-project schedule input, scoped project
dependencies, and permission-checked baseline reads. Mixed scope, duplicate,
foreign-project, incomplete canonical, stale baseline, and unauthorized inputs
fail closed. The QML surface does not broaden access or merge cross-scope data.

## 22. Tests Run

- Focused final Gantt/presenter B-H runtime and architecture matrix: 116 passed;
  the final focused semantic-fixture-inclusive matrix: 119 passed.
- Broad relevant PM matrix after all production and test cleanup: 454 passed in
  242.01 seconds.
- Coverage included CPM, constraints, dependencies, baseline, milestones,
  resource leveling, Scheduling desktop API, controllers/presenters, routes,
  settings, Inspector, runtime QML, DPR, responsive geometry, keyboard,
  performance, and tenant/organization/project isolation.
- Final combined measurement/stress selection: 13 passed.
- All Scheduling QML passed direct `pyside6-qmllint` silently.
- Targeted Python `compileall` passed.
- `git diff --check` passed; only Git line-ending notices were emitted.
- `ruff` was not installed in `pmenv`; this optional tool was unavailable.
- A full repository suite was not run because the broad PM-focused set is the
  relevant R4.5 gate and avoids unrelated module runtime.
- No unexplained, unrelated, flaky, or environment failure remains.

## 23. Deleted Legacy Code

Earlier R4.5 phases deleted `gantt_legacy_adapter.py`,
`SchedulingTimelinePanel.qml`, the paginated Gantt DataTable, and duplicate
timeline collections. R4.5H deleted:

- `presenters/scheduling/detail_builder.py`;
- duplicate Scheduling dependency create/update/delete presenter/controller
  paths (Tasks remains the canonical dependency-editing workspace);
- selected dependency/constraint collections, table models, serializers,
  options, and old selected-activity detail side-channel;
- stale activity pagination/controller type metadata;
- unused selection activation, axis/model aliases, and geometry helper;
- dead Gantt DTO `id`/`actual_end` compatibility aliases;
- two tests that only protected the removed legacy detail/constraint panel.

`test_r4_5h_gantt_closure.py` now prevents those surfaces and registrations from
returning. No production compatibility shim or dead Gantt renderer remains.

## 24. Explicit Deferred Scope

R5 owns workload management, capacity views, utilization heatmaps, assignment
balancing, and resource-specific workload UX. R8 owns broad accessibility and
broader visual cleanup. Future product scope owns drag scheduling, canvas
dependency creation/editing, WBS drag/reparent, cross-project dependencies,
scenario planning, and portfolio roadmap. These are not R4.5 defects.

## 25. R4.5 Exit Gate

All 81 requested exit conditions pass: documentation is reconciled; legacy,
placeholder, duplicate, paginated, and compatibility paths are absent; one
projection/model/viewport/axis/geometry/selection/dependency/baseline path
remains; schedule and semantic facts are truthful; responsive, settings,
keyboard, DPR, security, runtime, performance, source-cleanliness, and broad PM
regression gates are green. No R4.5 correctness blocker remains.

## 26. R5 Handoff

Gantt provides R5 with authorized project/task schedule identity and a stable
visual Planning boundary only. Authoritative `TaskAssignment` facts remain
outside Gantt visualization. R5 owns the Resource -> ProjectResource ->
TaskAssignment -> TimeEntry workload experience. Gantt must not become a
workload heatmap, and no R5 implementation was started during closure.
