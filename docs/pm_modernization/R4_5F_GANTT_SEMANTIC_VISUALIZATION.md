# R4.5F Gantt Semantic Visualization

## Status

R4.5F is implemented and verified. It adds a read-only selected-baseline overlay,
explicit current and historical milestone shapes, and authoritative
critical/infeasible presentation to the integrated R4.5 Gantt. It does not add
baseline governance, scheduling mutations, resource/workload visualization, or
R4.5G/R5 work.

## Authority Boundaries

- Current dates, milestone identity, criticality, and infeasibility remain facts
  from the canonical Gantt projection.
- Baseline lifecycle and snapshot authorization remain owned by
  `BaselineService`.
- Gantt owns only a disposable local display selection and an indexed overlay.
- Baseline selection does not call the scheduling engine, mutate tasks, run CPM,
  change dependencies, or alter a baseline.
- The read model can be discarded and rebuilt; it is not a source of schedule or
  baseline truth.

## Baseline Data Path

```text
Baseline: [None | human-labelled option]
  -> selectGanttBaseline(baseline_id)
  -> clear previous model and axis overlay
  -> ProjectSchedulingWorkspacePresenter.build_gantt_baseline_overlay(...)
  -> ProjectManagementSchedulingDesktopApi.build_gantt_baseline_overlay(...)
  -> active tenant/organization/project scope check
  -> BaselineService.list_baseline_tasks(..., expected_project_id=...)
  -> one authorized bulk repository snapshot read
  -> GanttBaselineOverlayDto
  -> axis baseline bounds
  -> GanttListModel O(N) task-ID index
  -> baselineData role on recycled visible rows
```

The regular workspace Gantt projection no longer receives the Baselines-panel
governance selection. This prevents a local visualization choice from using the
full schedule rebuild path. The legacy-compatible projection builder can still
serialize baseline snapshots for direct callers, but the live Gantt uses the
bounded overlay contract.

## Selector and Failure Behavior

- Default selection is exactly `None`; no baseline is auto-selected.
- `None` performs no baseline snapshot read, renders no baseline shape, and
  contributes no baseline range.
- Options reuse authorized human labels (`name` and creation date); raw IDs are
  not shown.
- A baseline change invalidates old geometry before loading the new overlay.
- A failed load leaves the current schedule visible, removes all stale baseline
  geometry/range, exposes a scoped generic error, and supports retry or `None`.
- Project switch clears the Gantt-local baseline ID, error, indexed snapshots,
  and range contribution.
- Domain refresh invalidates the overlay and reloads it once only when the same
  option remains valid for the active project.

The Gantt selector is independent of Planning -> Baselines A/B comparison and
lifecycle state. No create, submit, approve, reject, delete, or edit action was
added to Gantt.

## Overlay and Range Geometry

Each recycled row receives at most one `baselineData` value from the indexed
model. `SchedulingGanttBaseline.qml` maps its start/finish independently through
the same `rangeStartDay` and `pixelsPerDay` used by the current bar. A thin,
neutral track sits below the primary current bar inside the unchanged fixed row
height.

`GanttTimeAxisController` now keeps current-projection and selected-baseline
bounds separately. The effective unpadded range is their minimum/maximum only
while an overlay is active; normal scale padding then applies. Removing the
overlay restores current-only bounds. Existing surface center-date restoration
handles the resulting range expansion/contraction.

## Missing-Task Semantics

- Current-only task: current row/bar remains; `baselineData` is empty and no
  zero-length baseline shape is fabricated.
- Baseline-only task: no synthetic current WBS row is created; the model exposes
  an orphan count and directs detailed history to Planning -> Baselines.
- Current unscheduled, baseline scheduled: the grid truth remains `Unscheduled`,
  the current bar is absent, and the valid baseline shape can render.
- Current scheduled, baseline unscheduled: the current bar remains and no
  baseline geometry is fabricated.
- Summary baseline bars are intentionally omitted. No authoritative summary
  snapshots or new business rollup semantics were invented.

## Milestones

- Current milestone shape is a diamond only when `Task.is_milestone` reached the
  projection as `isMilestone`.
- A same-day non-milestone remains a minimum-width bar.
- Historical milestone shape is a smaller outlined diamond only when
  `baseline_is_milestone` reached `baselineData.isMilestone`.
- Equal baseline dates and zero duration do not infer milestone identity.
- Milestones use the existing task selection ID and receive no proportional
  progress fill.

## Critical and Infeasible Presentation

The visual precedence is:

1. selected/focused outline;
2. infeasible semantic fill (`is_infeasible`);
3. critical semantic fill (`is_critical`) when highlighting is enabled;
4. normal task fill.

Selection changes the outline and does not replace semantic fill. Infeasible
therefore remains distinct even when a task is also critical and selected.
`Critical only` remains a row filter. `Highlight Critical Tasks` is a separate,
local O(1) presentation preference and performs no query or CPM work.

The backend/projection does not expose authoritative driving/critical-edge
membership. The control is therefore deliberately labelled **Highlight Critical
Tasks**. No endpoint, float, date, lag, or dependency-type heuristic was added to
claim that an edge is on the critical path.

## Dependency Integration

R4.5F keeps the single R4.5E high-DPI Canvas and its route cache unchanged. There
is no second dependency renderer. Selected incident-edge precedence and the
measured density fallback remain intact. Existing endpoint semantic facts remain
available in route payloads, but they are not misrepresented as critical-edge
membership.

## Performance Characterization

Focused offscreen measurements from the final R4.5F run:

| Snapshot rows | DTO build | Model index | 30 visible lookups |
|---:|---:|---:|---:|
| 100 | 0.442 ms | 0.103 ms | 0.043 ms |
| 1,000 | 4.601 ms | 0.275 ms | 0.032 ms |
| 5,000 | 23.901 ms | 1.438 ms | 0.052 ms |

The overlay creates no second row model and no project-sized QML object set.
Only existing virtualized row delegates host one lightweight optional baseline
shape. Highlight toggling changes one bound boolean and creates no per-task
controller work.

## Verification

- R4.5F focused semantic, scope, failure, geometry, and performance tests:
  `19 passed`.
- Combined R4.5B-F, Scheduling planning IA, and Scheduling desktop API matrix:
  `89 passed`.
- Existing R4.5B-E regression run before F tests: `61 passed`.
- Direct `qmllint` over all changed Gantt QML: silent (zero findings).
- Python `compileall` for changed PM desktop/controller/presenter packages: pass.
- No full repository test suite was run, per the targeted-test instruction.

## Historical R4.5G Handoff

R4.5G may now address only the approved responsive layouts, toolbar overflow,
validated display-preference persistence, keyboard/focus essentials, and broader
viewport performance tuning. It must preserve the R4.5F baseline authority,
single-axis geometry, explicit milestone facts, task-only critical wording,
single dependency Canvas, fixed row-height virtualization, and zero-CPM local
controls.

R4.5G and R4.5H subsequently completed within this boundary; R5 was not started.
The final semantic and regression evidence is recorded in
`R4_5_GANTT_CLOSURE.md`.
