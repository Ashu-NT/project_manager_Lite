# R4.4 Planning / Scheduling Workspace Modernization & Resource-Leveling Migration — Implementation Summary

Implementation pass migrating resource leveling off the dead-end
`ResourceLevelingMixin`/`ResourceLevelingEngine` split onto one
authoritative, pure, testable `ResourceLevelingPlanner`, with a full
Preview → Apply → governance → audit pipeline and a new Resource
Leveling tab in the Scheduling workspace.

Standing constraints honored throughout: no ALAP (not implemented or
exposed anywhere), no redesign of dependency/constraint/actual-date/
calendar-authority semantics established in earlier R4.4 phases, no
R4.5 (Gantt) work, no R5 work, no commits made by the assistant.

---

## 1. Final architecture

```
ResourceLevelingPlanner (pure, in-memory, application layer)
        |  build_proposal(tasks_by_id, deps, assignments, resource_name_by_id)
        |    -> re-runs canonical run_cpm as the feasibility seam for every
        |       candidate placement (no duplicated CPM/constraint math)
        |    -> movability_policy.task_movability() gates/ceilings candidates
        |    -> compute_schedule_fingerprint() stamps the exact snapshot reasoned about
        v
LevelingProposal (frozen, typed preview result -- never persists)
   .moves: ProposedTaskMove*      (task_id, old/new start+finish, reason,
                                    float before/after, criticality,
                                    infeasibility, deadline warning)
   .unresolved_conflicts: UnresolvedConflict*  (surfaced, never dropped)
   .schedule_fingerprint: str     (R4.4L staleness token)
        |
        v  desktop API: preview_resource_leveling(project_id)
ProjectManagementSchedulingDesktopApi
   caches the raw LevelingProposal per project_id; returns a display DTO
        |
        v  desktop API: apply_resource_leveling(project_id)
TaskService.apply_resource_leveling_plan (ResourceLevelingApplyMixin)
   -- governed/ungoverned gate (mirrors TaskSchedulingConstraintMixin) --
   -- re-validates schedule_fingerprint against a FRESH DB read (TOCTOU-safe) --
   -- writes Task.resource_leveling_not_before per move, re-syncs schedule --
   -- per-task activity-log entry (old_start/new_start/reason) --
        |
        v
Task.resource_leveling_not_before: date | None
   an unconditional forward-pass floor (task_date_math.py), composing via
   max() exactly like START_NO_EARLIER_THAN -- survives every subsequent
   canonical run_cpm/recalculate_project_schedule call, unlike the old
   mixin's raw Task.start_date write (which the forward pass ignores for
   any task with an incoming dependency)
        |
        v
QML: Scheduling workspace -> "Resource Leveling" tab
   SchedulingResourceLevelingPanel.qml -- Preview button, summary strip,
   DataTable + InspectorPanel of proposed moves, unresolved-conflict
   InlineMessages, ConfirmationDialog-gated Apply button
```

## 2. Key design decisions

- **One authoritative leveling component.** `ResourceLevelingPlanner`
  (`application/scheduling/leveling/resource_leveling_planner.py`) is
  the only leveling implementation with a live caller. The old
  `ResourceLevelingMixin` (still mixed into `SchedulingEngine`, wrapped
  by `DashboardService`) has zero QML/controller/desktop-API callers
  (confirmed by audit, R4.4A) and the old `ResourceLevelingEngine` has
  zero instantiations anywhere — both scheduled for deletion (§R4.4Y).
- **The leveled-schedule model fixes the actual architectural defect.**
  The old approach wrote a resource-driven placement directly onto
  `Task.start_date`, which the forward CPM pass ignores for any task
  with an incoming dependency, so the very next recalculation silently
  erased the leveling decision. `Task.resource_leveling_not_before` is
  a new, additive domain field applied as an unconditional floor,
  composing correctly and durably.
- **The canonical feasibility seam.** Every candidate placement is
  evaluated by re-running the SAME `run_cpm` the rest of the app uses —
  no second scheduling formula to keep in sync.
- **Movability policy is the single source of truth for "can leveling
  move this task at all."** MUST_START_ON/MUST_FINISH_ON and
  actual-locked tasks are never movable; SNET/FNET need no special
  handling (floors already compose); SNLT/FNLT report a ceiling that is
  never silently exceeded; Deadline is movable but generates an
  explicit warning if exceeded.
- **Multi-resource correctness (R4.4E).** A task with two+ assigned
  resources is only accepted at a candidate date where EVERY resource
  it uses is clear, not just the one resource whose overload triggered
  the search — an early implementation gap caught and fixed with a
  dedicated regression test before shipping.
- **Staleness via schedule fingerprint, not per-task version (R4.4L).**
  A leveling plan spans many tasks; a per-task version check could pass
  for some moves while the ones that actually made the preview stale go
  unnoticed. `compute_schedule_fingerprint` hashes every involved
  Task/TaskDependency/TaskAssignment's `(id, version)` pair into one
  opaque token, recomputed and compared at Apply time.
- **Governance parity (R4.4O).** `apply_resource_leveling_plan` mirrors
  `TaskSchedulingConstraintMixin`'s exact shape: governed/ungoverned
  branch, admin bypass, and TOCTOU-safe fingerprint revalidation when a
  governed request is later approved — registered as
  `scheduling.leveling.apply` in the composition root's approval
  handlers, added to `DEFAULT_GOVERNED_ACTIONS`.
- **Per-task audit trail (R4.4P).** Apply records one activity entry
  per moved task (`entity_type="task"`), matching every other
  schedule-affecting command in this module, carrying the move's
  `reason`/old-start/new-start — not just a project-level summary a
  viewer would have to go find separately.

## 3. Test evidence (R4.4B–P)

- `test_resource_leveling_floor_survives_cpm.py` — the floor mechanism
  survives repeated `run_cpm` and repeated live `SchedulingEngine`
  recalculation.
- `test_leveling_movability_policy.py` — 10 tests, full constraint-type
  × actual-lock matrix.
- `test_resource_leveling_planner.py` — basic overload resolution,
  preview-never-persists, dependency-aware propagation, movability
  respected, unresolved-conflict surfacing, multi-resource capacity
  correctness.
- `test_schedule_fingerprint.py` — stability/order-independence,
  changes on any involved row's version bump, planner-computed
  fingerprint matches an independently recomputed one.
- `test_apply_resource_leveling_plan.py` — happy path, version bump,
  empty-proposal no-op, staleness rejection, per-task audit entry.
- `test_apply_resource_leveling_plan_governance.py` — governed request
  flow, admin bypass, TOCTOU revalidation at apply time.
- `test_leveling_preview_apply_reload_idempotence.py` — **the
  directive-flagged CRITICAL regression**: Preview → Apply → a
  genuinely disconnected reload (fresh objects, not the pre-apply
  Python instances) → repeated `run_cpm` (pure function) and repeated
  `SchedulingEngine.recalculate_project_schedule` (live path) — the
  resolved conflict must never reappear. Both pass.
- `test_scheduling_desktop_api_resource_leveling.py` /
  `test_qml_scheduling_leveling_presenter.py` /
  `test_qml_scheduling_leveling_controller.py` — desktop API, presenter
  DTO shaping, and controller Slot/Property wiring for the QML tab,
  including a real offscreen QML load of the whole Scheduling
  workspace (`test_qml_offscreen_loading.py`).

## 4. R4.4W.1 — Resource Leveling Performance Remediation

### 4.1 The problem

R4.4W's initial characterization measured `ResourceLevelingPlanner
.build_proposal` resolving a single representative resource conflict
at increasing project size, using a synthetic Mon–Fri test calendar:

| Tasks | Elapsed |
|---|---|
| 100 | 0.06 s |
| 1,000 | 3.3 s |
| 5,000 | 111.2 s |

A 5× increase in project size (1,000 → 5,000) produced a ~34×
increase in runtime — worse than quadratic, and unusable for an
interactive Preview button at real-project scale.

### 4.2 Profiling (before changing anything)

Per the remediation directive, the algorithm was profiled before any
optimization was attempted, using both the synthetic calendar and,
critically, the **real DB-backed `services` fixture with the real
`GlobalCalendarShim` calendar**, since a synthetic test calendar's
performance characteristics are not proof of anything about
production behavior.

**Call-count finding.** Wrapping `run_cpm`/`build_resource_conflicts`
as invoked from inside the planner showed only **7 total `run_cpm`
calls** even at 5,000 tasks (1 baseline + 1 per outer-loop iteration +
a handful of candidate-date evaluations + 1 final) — the planner's own
orchestration was never the problem; the leveling search converged
quickly in the representative scenario.

**Per-call cost finding.** Each `run_cpm` call's own duration exploded
super-linearly with task count (real DB + real calendar, single
`run_cpm` call, zero dependencies): a representative real-DB
`build_proposal` run measured **5.05 s at 100 tasks** and **57.67 s at
1,000 tasks** (11.4× for 10× tasks).

**Stage breakdown (real DB + real calendar, n=1,000, one `run_cpm`
call, function-level instrumentation):**

| Stage | Calls | Total time | % of run_cpm |
|---|---|---|---|
| `build_project_dependency_graph` | 1 | 0.001 s | 0.0% |
| `run_forward_pass` | 1 | 2.640 s | 30.6% |
| `run_backward_pass` | 1 | 0.890 s | 10.3% |
| `build_schedule_result` | 1 | 5.094 s | **59.0%** |

**Calendar-call breakdown inside that same run:**

| Calendar method | Calls | Total time | Mean/call |
|---|---|---|---|
| `working_days_between` | 1,000 | 5.045 s | 5.045 ms |
| `add_working_days` | 2,000 | 3.516 s | 1.758 ms |
| `is_working_day` | 3,714 | 3.499 s | 0.942 ms |

**Root cause.** `build_schedule_result` calls
`calendar.working_days_between(est, lst)` once per task to compute
float. For independent/end tasks in a flat project, `lst` gets pushed
out toward the project's overall finish, so many tasks' float windows
scale with project size — but the actual root cause was simpler and
worse: **every single calendar call re-resolved facts from scratch**
(the enterprise calendar resolver, a DB-backed dependency) with **no
caching across calls within one `run_cpm` invocation**, even though
the same project/date-range facts are re-derivable from a single bulk
query. `run_cpm` invokes these calendar methods once (or a few times)
per task; with zero memoization, that's N un-cached, non-trivial calls
regardless of how the CPM control flow itself scales (which is
O(N log N) via a proper heap-based topological sort — verified clean).

This was NOT a leveling-planner defect and NOT a CPM-algorithm defect
— it affects any `run_cpm` invocation at scale, though this migration
only fixes it for the leveling Preview path per its charter.

### 4.3 The fix

`application/scheduling/leveling/calendar_cache.py` —
`MemoizingCalendarWindow`, a `CalendarProtocol`-compatible wrapper
constructed once per `ResourceLevelingPlanner.build_proposal` call:

- Computes a generously bounded `[window_start, window_end]` covering
  every date fact any involved task could plausibly need
  (`build_memoizing_window_for_tasks`), padded for the leveling
  search's own horizon.
- Bulk-resolves working-day facts **once** via
  `working_day_dates_between` (a method the real calendar classes
  already expose) instead of once per task.
- Answers `is_working_day` from an in-memory set (O(1)) and
  `working_days_between` via a sorted-list bisect count —
  mathematically identical to summing the same set day by day, so
  there is no semantic drift.
- `add_working_days`/`next_working_day` keep the **exact same
  day-by-day loop structure** the real calendar classes
  (`GlobalCalendarShim`/`ProjectCalendarAdapter`/
  `WorkingDaySnapshotCalendar`) already use — only the underlying
  `is_working_day` lookup got faster, not the algorithm.
- **Any date outside the precomputed window, or any calendar lacking
  `working_day_dates_between`, transparently falls back to the real,
  uncached calendar.** Correctness never depends on the window
  estimate being right, or on the wrapped calendar supporting the bulk
  method — only the amount of speedup does.

Wired into `ResourceLevelingPlanner.build_proposal` only (not into
`run_cpm`, not into `SchedulingEngine`, not exposed anywhere else) —
scoped narrowly to the leveling Preview path per the remediation
directive's charter, leaving canonical CPM/scheduling semantics
untouched everywhere else in the app.

**Explicitly not done, per the directive's gating:** no second CPM
implementation, no incremental/affected-subgraph scheduling (the
profiling evidence showed the bottleneck was uncached calendar I/O,
not CPM's own control-flow complexity, so the incremental-CPM escape
hatch was never triggered), no change to candidate-search algorithm
structure, no change to dependency/constraint/actual-date/capacity
semantics.

### 4.4 Correctness verification

- `test_leveling_calendar_cache.py` (8 tests, new) — proves
  `MemoizingCalendarWindow` produces results **identical** to the real,
  uncached calendar for `is_working_day`/`working_days_between`/
  `add_working_days`/`next_working_day`, both inside and outside the
  cached window, including a deliberately narrow window that forces
  the mid-walk fallback path.
- Full `src/tests/project_management/dependency` suite (265 tests) —
  zero regressions after wiring the cache into the planner: all
  R4.4B–P leveling tests, the Preview→Apply→reload idempotence
  regression, governance tests, and the full dependency/constraint
  matrix all still pass unchanged.

### 4.5 Before / after / speedup

| Scenario | Before | After | Speedup |
|---|---|---|---|
| Real DB + real calendar, n=100 | 5.05 s | 0.023–0.036 s | ~140–220× |
| Real DB + real calendar, n=1,000 | 57.67 s | 0.198–0.326 s | ~180–290× |
| Real DB + real calendar, n=5,000 | not measured pre-fix (projected tens of minutes+ from the observed super-linear trend; impractical to run) | **1.589 s** | — |
| Synthetic calendar (bulk-method-capable), n=100 | 0.058 s | 0.032 s | ~1.8× |
| Synthetic calendar (bulk-method-capable), n=1,000 | 3.28 s | 0.341 s | ~9.6× |
| Synthetic calendar (bulk-method-capable), n=5,000 | 111.2 s | 1.737 s | **~64×** |

Post-fix scaling across 100→1,000→5,000 tasks is roughly linear on
BOTH the real DB+calendar path (0.023 s → 0.290 s → 1.589 s) and the
synthetic-calendar path (0.032 s → 0.341 s → 1.737 s), not quadratic —
consistent with the root cause (uncached per-task calendar I/O) having
been eliminated rather than merely reduced by a constant factor. The
n=5,000 real-DB run's own ORM task-creation SETUP took ~27.5 minutes
(1652.6 s, via `ts.create_task` in a loop) — an unrelated cost of
building the synthetic test dataset itself through the real
application/domain-validation/ORM stack, not part of what
`build_proposal` measures or what this remediation addresses.

### 4.6 Performance-exit classification

**INTERACTIVE.** Sub-second Preview times through 1,000 tasks and
low-single-digit-second times at 5,000 tasks, on real DB-backed data
with the real production calendar, are well within the range of an
interactive "Preview" button — no spinner-tolerant "long operation" UX
is required for the project sizes this app targets.

### 4.7 Correctness invariants preserved

Dependency, constraint, actual-date, calendar, and multi-resource
capacity semantics are byte-for-byte unchanged (same authoritative
calendar facts, only pre-fetched once instead of re-derived per task);
`ResourceLevelingPlanner.build_proposal` remains a pure, non-persisting
preview (no repository writes, confirmed by existing `TestPreviewNever
Persists` coverage, unaffected by this change); the Preview → Apply →
reload → `run_cpm` idempotence invariant (§3) was re-verified green
after the fix; determinism is preserved (the cache is a pure function
of the same authoritative source, contains no randomness, and the
existing fingerprint/proposal-shape tests — which assert exact
equality of results — continued to pass unchanged).

---

## 5. Explicitly out of scope

- **ALAP** — not implemented, not exposed, not planned.
- **R4.5 (Gantt) work, R5 work** — untouched.
- **`ResourceLevelingMixin`/`ResourceLevelingEngine` deletion** — see
  §6 for the dead-code audit and removal.
- **General CPM-wide calendar caching** (beyond the leveling Preview
  path) — the root cause found in §4.2 would also benefit any other
  `run_cpm` consumer (Dashboard, Task Detail, plain "Recalculate
  Schedule"), but fixing it everywhere was not authorized by this
  migration's charter and was deliberately left as a candidate for a
  future, separately-scoped performance pass.

## 6. R4.4Y — dead code removed

A dedicated reachability audit (grep every reference across `src/`,
classify each as definition/comment/test-only/real caller, trace
`DashboardService`'s own callers one level further to confirm nothing
in QML or the desktop API reaches it) confirmed the old resource-leveling
implementation had zero production callers anywhere, and removed it:

- **`ResourceLevelingEngine`**
  (`application/scheduling/leveling/resource_leveling_engine.py`) —
  zero instantiations anywhere; deleted along with its re-exports from
  `scheduling/__init__.py` and `scheduling/leveling/__init__.py`.
- **`ResourceLevelingMixin`**
  (`application/scheduling/leveling/leveling_mixin.py`) — mixed into
  `SchedulingEngine` but reachable only from tests and from
  `DashboardService`'s own three wrapper methods, which were
  themselves reachable from nothing but tests (no `.qml` file, no
  desktop API caller). `SchedulingEngine` no longer inherits it;
  `class SchedulingEngine:` has no base class now.
- **`DashboardService.preview_resource_conflicts` /
  `.auto_level_overallocations` / `.manually_shift_task_for_leveling`**
  — the dead wrapper methods, deleted along with their now-unused
  `ResourceConflict`/`ResourceLevelingAction`/`ResourceLevelingResult`/
  `domain_events` imports.
- **`ResourceLevelingAction`/`ResourceLevelingResult`** dataclasses
  (`models/leveling.py`) — orphaned once the mixin methods that
  returned them were deleted; removed along with their re-exports.
  `ResourceConflict`/`ResourceConflictEntry` (still used by
  `build_resource_conflicts`, actively consumed by
  `ResourceLevelingPlanner`) were kept.
- **Test files deleted outright** (tested the deleted mixin/engine
  directly, not salvageable): `test_resource_leveling_workflow.py`,
  `test_dashboard_leveling_flow.py`,
  `dependency/test_leveling_dependency_boundary.py` (the latter was a
  deliberately pinned regression proving the OLD broken interaction
  the new `resource_leveling_not_before` floor mechanism, §2, already
  fixes — its own docstring said its final assertion should flip once
  R4.4 "reconciles leveling with dependency minimum dates through one
  schedule model," which is exactly what happened).
- **Test files trimmed** (one dead test/assertion removed, rest kept):
  `test_r43_resource_capacity_upgrade.py` (a whole test function that
  only checked the deleted `preview_resource_conflicts`'s query-batching
  behavior), `test_phase_b_session_permissions.py` (two `pytest.raises`
  blocks asserting permission checks on the two deleted
  `DashboardService` methods).
- **Architecture guardrail rewritten, not deleted**:
  `test_scheduling_leveling_is_split_from_engine`
  (`test_architecture_guardrails_services.py`) previously asserted
  `scheduling_engine.py`'s source text contained the exact mixin
  import/inheritance strings — now asserts the new architecture
  instead (`ResourceLevelingPlanner` is not in `SchedulingEngine`'s
  MRO), preserving the file's general "keep orchestrator services
  thin" guardrail intent without depending on deleted code.

Verified via the full `src/tests/project_management` suite plus the
touched architecture/platform test files — zero regressions from the
deletion (one pre-existing, unrelated failure in
`test_known_large_modules_have_growth_budgets`, caused by two
untouched files exceeding their line budgets, predates this session).

## 7. R4.4 exit-gate self-assessment

This backend self-assessment is reconciled with the authoritative 35-item
R4.4X/Y/Z QML and IA exit gate in
`R4_4_PLANNING_QML_IMPLEMENTATION_SUMMARY.md` section 19.

| Area | Status |
|---|---|
| One authoritative leveling component (no duplicate implementations) | **PASS** — `ResourceLevelingPlanner` is the only leveling component with real callers; `ResourceLevelingMixin`/`ResourceLevelingEngine` deleted (§6) |
| Leveled-schedule model survives recalculation | **PASS** — `Task.resource_leveling_not_before` floor, proven via repeated `run_cpm`/`SchedulingEngine.recalculate_project_schedule` (§3) |
| Canonical feasibility seam (no duplicated CPM/constraint math) | **PASS** — every candidate re-runs the real `run_cpm` |
| Resource capacity authority incl. multi-resource tasks | **PASS** — R4.4E multi-resource gap found and fixed with regression coverage |
| Dependency-aware leveling/propagation | **PASS** — `TestDependencyAwarePropagation` |
| Constraint-aware leveling + movability policy | **PASS** — `movability_policy.py`, 10-test matrix |
| Actual-execution policy | **PASS** — actual-locked tasks never movable |
| Float/criticality/infeasibility-informed candidate priority | **PASS** — `_ordered_candidates` |
| Candidate-placement search (no `+1 day` greedy loop) | **PASS** — bounded nearest-legal-placement search |
| Pure, non-persisting Preview | **PASS** — `TestPreviewNeverPersists`, unaffected by the R4.4W.1 cache change |
| Staleness/concurrency (fingerprint) | **PASS** — `compute_schedule_fingerprint`, re-validated at Apply time |
| Apply command, atomic mutate+recalculate | **PASS** — mirrors `TaskSchedulingConstraintMixin`'s shape |
| **Preview → Apply → reload → run_cpm idempotence** | **PASS** — the directive-flagged CRITICAL regression, both via pure `run_cpm` and the live `SchedulingEngine` path |
| Governance parity (admin bypass, TOCTOU revalidation) | **PASS** — `scheduling.leveling.apply` registered, 3 dedicated tests |
| Per-task audit trail | **PASS** — `entity_type="task"` activity entries with old/new start + reason |
| Unresolved-conflict UX (never silently dropped) | **PASS** — surfaced as danger-toned banners in the QML panel |
| Resource Leveling tab in Scheduling workspace | **PASS** — real offscreen QML load of the whole workspace passes |
| Leveling inspector panel | **PASS** — DataTable + InspectorPanel, reusing established app widgets |
| Async/loading UX | **PASS** — reuses the page's existing `isBusy`/`isLoading`/error/feedback banners; Apply gated by a confirmation dialog |
| Performance at 100/1,000/5,000 tasks | **PASS (after remediation)** — real DB+calendar: 0.023 s / 0.290 s / 1.589 s; classified INTERACTIVE (§4.6) |
| Dead/duplicate leveling code removed | **PASS** — §6 |
| Documentation | **PASS** — this document |
| Full regression suite green (scheduling/leveling scope) | **PASS** — 118 focused scheduling/leveling tests, 283 dependency/constraint/impact tests, and 3 benchmark tests pass. The broad PM run reconciles to 1,161 passing and one known unrelated Finance pagination-offset failure after 36 sandbox user-data write failures passed with workspace-local `APPDATA`. |
| No ALAP / no R4.5 / no R5 / no scheduling-semantics redesign | **PASS** — none occurred |
| Final QML/IA exit gate | **PASS** — the exact 35-item table is in `R4_4_PLANNING_QML_IMPLEMENTATION_SUMMARY.md` section 19 |

**Overall: R4.4 CLOSED.**

## 8. R4.4X/Y/Z final reconciliation

The final QML/IA validation pass confirms that the backend closure above and
the Planning workspace closure agree:

- the fabricated Gantt baseline placeholder has no live field or rendering;
- all 15 live Scheduling QML files pass direct qmllint with no output;
- the registered Planning route loads offscreen at 1024x640, 1280x720,
  1366x768, 1440x900, and 1920x1080;
- the stale qmllint test targets for deleted Scheduling section files were
  replaced with discovery of every live Scheduling QML file;
- the final benchmark is 0.034 s / 0.317 s / 1.660 s for
  100 / 1,000 / 5,000 tasks;
- two unrelated architecture guardrails remain (Portfolio parent-relative
  import and stale Platform admin directory);
- one unrelated broad PM failure remains in the Finance commitment
  pagination-offset contract.

The complete test matrix, cleanup list, 35-item exit gate, and exact R4.5
handoff are maintained in
`R4_4_PLANNING_QML_IMPLEMENTATION_SUMMARY.md` sections 16-20.

This completion pass did not invoke `git commit`. HEAD advanced externally
during validation to team commits `88086a4c` and `4e5600ee`; no history was
rewritten or amended here.
