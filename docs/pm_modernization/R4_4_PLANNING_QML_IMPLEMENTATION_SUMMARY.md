# R4.4 Planning / Scheduling QML IA — Final Implementation Summary

Companion document to `R4_4_PLANNING_SCHEDULING_IMPLEMENTATION_SUMMARY.md`
(which covers the Resource Leveling migration/`ResourceLevelingPlanner`
work). This document covers the **QML tab-consolidation / information
architecture pass** driven by `R4_4_PLANNING_SCHEDULING_QML_IA_AUDIT.md`,
and closes out R4.4X (validation) / R4.4Y (cleanup) / R4.4Z (documentation).

Status at time of writing: implementation complete, validated, **not
committed** (working-tree change on `refactor/safe-start`).

---

## 1. Final Planning navigation

Two-tier tab set inside the single "Planning" (route `scheduling`)
workspace — no new PM Level-1 navigation item was added.

**Primary (always-visible chips):** Overview · Gantt · Resource Leveling ·
Diagnostics

**Secondary (behind a "More" `NavOverflowMenu`):** Baselines · Calendars ·
Activity Feed

Source of truth: `SchedulingWorkspaceState.qml` (`primaryPanelTabs` /
`secondaryPanelTabs`), rendered by `SchedulingWorkspacePage.qml`'s tab strip
+ `AppWidgets.NavOverflowMenu`. The overflow menu receives `activeId` so a
secondary tab's current-location indication (highlighting) is truthful when
one of its items is active, not just when a primary tab is active.

There is no standalone "Delays" destination and no standalone "Planning
Resources" destination — both were folded into Gantt filtering and Resource
Leveling respectively (see §4, §6). The pre-existing, separate "Resources"
PM Level-1 nav item (`pm_workspace_navigation_controller.py`, Workload
Management group) is an unrelated module and was not touched.

## 2. Minimal persistent header

`SchedulingPlanningContextHeader.qml` is the only always-visible chrome
above the tab strip (besides loading/error/success banners). It exposes
exactly:

- Project selector
- Refresh
- Run CPM / Recalculate

There is exactly one live implementation of each action
(`workspaceController.refresh()` / `workspaceController.recalculateSchedule()`),
called from exactly one place. The calendar selector lives in the Calendars
tab (`SchedulingCalendarsPanel.qml`, `selectedCalendarId`); baseline-specific
controls live in the Baselines tab. Neither is duplicated in the header or
elsewhere.

## 3. Overview

`SchedulingOverviewPanel.qml` is the new landing tab. It surfaces:

- A KPI strip driven by authoritative backend metrics (Activities, Critical,
  Delayed, Open Ends, Infeasible, Resource Overloads) via
  `workspaceController.overview.metrics`.
- A single "What needs attention" feed built directly from
  `scheduleRows` / `delayedActivityRows` / `resourceLoadingRows` — i.e. the
  same authoritative rows the Gantt/Diagnostics/Resource Leveling tabs
  render, not a second parallel computation.

It does **not** duplicate the Diagnostics tab's aggregate table — Diagnostics
now shows only what Overview does not (deadline-breach count, per-constraint
overrun rows); see §8.

## 4. Gantt — first-class Planning destination

`SchedulingGanttPanel.qml` replaces the old `SchedulingActivityTimelinePanel.qml`
+ `SchedulingDetailPanel.qml` pairing with one integrated console:

- WBS/task `DataTable` + `SchedulingTimelinePanel` timeline lane in a
  `SplitView`, togglable Grid / Timeline / Split (Split unavailable at
  compact widths).
- "Critical Path" checkbox filter bound to `showCriticalOnly` (authoritative
  backend flag, not a client-side recompute).
- "Delayed only" is now a filter checkbox inside the activity filter popup,
  not a separate destination (§1) — this is the migration of the old
  standalone Delays tab's functionality.
- Row selection (`onRowSelected` → `selectActivity`) drives a contextual
  `InspectorPanel` (inline at wide widths, `SlideOverPanel` at compact
  widths) — see §5. There is no full-page activity-detail production path
  left; `SchedulingDetailPanel.qml` has been deleted and has zero remaining
  references anywhere in `src/` (confirmed by repo-wide search — only
  historical mentions remain in audit/planning docs under `docs/`).
- **No fake controls**: no Dependency Lines toggle, no Zoom control, no
  Timescale control exist anywhere in the Gantt panel or timeline panel.
  These are explicit R4.5 scope (§ "R4.5 handoff" below) and were
  deliberately not stubbed.

## 5. Activity Inspector

Rendered once (`_inspectorComponent`) and reused inline/slide-over. Fields,
sourced from `detail_builder.build_detail_view_model`:

- Task identity (Activity ID, WBS, title)
- Start / Finish (with latest-start/latest-finish supporting text)
- Duration (with remaining-duration supporting text)
- Total float (`total_float_days`) — free float is not currently modeled as
  an authoritative backend value on the schedule item and is correctly
  omitted rather than fabricated
- Status precedence **Infeasible → Critical → raw status label**
  (`detail_builder.py:104-107`), regression-tested by
  `test_scheduling_detail_builder_infeasible_status.py` (4 tests, all
  precedence combinations)
- Constraint summary (deadline + `constraint_label_for_activity`)
- Dependency summary (active predecessor/successor count)
- Resource summary (top resource pressure + utilization)
- "Open Task" action (routes to the Tasks workspace)
- Schedule Impact summary

**Schedule Impact stays lazy**: selecting a task never triggers impact
analysis. Only the explicit "Analyze Impact" `SecondaryButton` calls
`workspaceController.computeScheduleImpact({taskId})`. The result is keyed
by `taskId` (`_scheduleImpactAvailable` checks
`_scheduleImpact.taskId === selectedActivityModel.id`), so switching the
selection invalidates the display without a stale result leaking onto a
different task.

## 6. Resource Leveling — Resource Load integrated

`SchedulingResourceLevelingPanel.qml` combines, in one tab:

- Current Resource Load table (was the standalone `SchedulingResourcesPanel.qml`
  — now deleted, zero remaining references)
- Preview action → conflicts-before/after + project-finish shift summary
- Unresolved-conflict `InlineMessage` list (never silently dropped)
- Proposed-moves table + move `InspectorPanel`
- `ConfirmationDialog`-gated "Apply Leveling Plan"

Leveling invariants (Preview is pure/non-persisting, Apply is atomic,
Apply → reload → run_cpm preserves accepted dates) are unchanged
backend-side and re-verified by the existing `src/tests/project_management/dependency`
suite plus `test_qml_scheduling_leveling_controller.py` /
`test_qml_scheduling_leveling_presenter.py` — all green (see §Test Evidence).
This QML pass did not touch `ResourceLevelingPlanner` or the apply pipeline.

## 7. Performance — R4.4W.1 benchmark re-run

Re-ran `test_resource_leveling_planner_performance.py` (real DB + real
calendar, `MemoizingCalendarWindow` preview-scoped cache active) on
2026-08-20:

| Tasks | Elapsed (post-W.1 fix) | Elapsed (pre-fix, for reference) |
|---|---|---|
| 100 | 0.032 s | 0.06 s |
| 1,000 | 0.343 s | 3.3 s |
| 5,000 | 1.840 s | 111.2 s |

The 5,000-task case is ~60x faster than the pre-remediation baseline and
remains well within interactive-Preview budget. No new optimization pass
was started; the cache remains scoped to `ResourceLevelingPlanner.build_proposal`
only, per its original charter.

## 8. Diagnostics — deduplicated

`SchedulingDiagnosticsPanel.qml` now shows exactly two tables, neither of
which repeats Overview's KPI numbers:

1. A diagnostic-messages table (network logic / float pressure / stability
   checks) whose only KPI-adjacent row is deadline-breach count, explicitly
   comment-documented (`diagnostics_builder.py:16-22`) as the one fact the
   Overview KPI strip does not carry, and explicitly labeled "Deadline
   control" — not conflated with the separate per-constraint-type
   "Constraint Overruns" table below it. Deadline lateness is never
   mislabeled as a scheduling constraint.
2. "Constraint Overruns" — per-activity constraint-type violations
   (required vs. computed date, overrun days, severity).

Infeasibility reporting here is sourced from the same authoritative
`is_infeasible`/CPM state as Overview and the Inspector — no separate
recomputation.

## 9. Baselines

Unchanged governance surface (Save/Submit/Approve/Reject/Delete), now its
own secondary tab. No Gantt baseline visualization exists here or anywhere
else — real baseline bar/overlay rendering is explicit R4.5 scope.

## 10. Calendars

`SchedulingCalendarsPanel.qml` is the sole location of the calendar
selector (`selectedCalendarId`). Grep of the entire scheduling QML tree
confirms no second/duplicate calendar selector exists in the header, Gantt,
or Baselines panels.

## 11. Activity Feed

One project-level `AppWidgets.ActivityFeed` remains
(`SchedulingActivityFeedPanel.qml`), wired to `activityFeedModel` with local
search filtering. The Gantt panel's per-activity Inspector does not render
a second Activity Feed — it renders the Schedule Impact block instead (§5).
Per prior investigation (see project memory), this feed's data is ephemeral
with no actor/author data, so it was intentionally left as `AppWidgets.ActivityFeed`
rather than opportunistically swapped for `ActivityLogSection` — that swap
remains out of scope.

## 12. Removed duplication / dead QML (R4.4Y cleanup audit)

Read-only repo-wide search performed before any deletion; all items below
were already clean (no further deletions were required this pass beyond
what was already removed as part of the consolidation itself):

| Category | Result |
|---|---|
| Old 8-tab definitions | Clean — `SchedulingWorkspaceState.qml` only defines the new 7-tab (4 primary + 3 secondary) set |
| Old "Delays" nav/state | Clean — no `Delays`/`delays` identifier anywhere in scheduling QML |
| Standalone "Planning Resources" nav/state | Clean — no such destination; the unrelated top-level "Resources" PM module is untouched and out of scope |
| `SchedulingDetailPanel` production references | Clean — zero references in `src/`; only historical mentions remain in `docs/pm_modernization/*` audit/planning documents, correctly framed as history |
| Duplicate Refresh/Run CPM handlers | Clean — one implementation each, in `SchedulingPlanningContextHeader.qml`; other panels' unrelated actions ("Calculate Days", "Preview", "Clear") separately reuse the `refresh` icon glyph but call distinct controller methods |
| Dead detail-section bindings | Clean — `qmldir` under `panels/` lists only the 8 live panel files; no leftover imports/Loader sources point at deleted panels |
| `baselinePlaceholder` presentation | Removed — `SchedulingTimelinePanel.qml:190-202` renders no baseline overlay; only an explanatory comment remains, no live QML binding or Python field named `baselinePlaceholder`/`baseline_placeholder` exists anywhere in the repo (verified pre-existing state; the fake ghost outline had already been removed, not merely hidden, and no change was required this pass) |
| Obsolete "Activity Detail" section models | Clean — `detail_builder.build_constraints_collection` / `build_detail_view_model` are both live, called from `workspace_builder.py`, and test-covered — not dead code |
| Imports used solely by deleted QML | Clean — no remaining imports/registrations reference `SchedulingActivityTimelinePanel`, `SchedulingDelaysPanel`, `SchedulingDetailPanel`, or `SchedulingResourcesPanel` |
| Dead tests asserting removed IA | Clean — no test references any deleted panel name or the old 8-tab structure |
| Stale docs describing prior architecture | Clean — `R4_4_PLANNING_SCHEDULING_QML_IA_AUDIT.md`'s 8-tab description is correctly framed as the historical "before" finding, not current-state documentation |

No backend/service-layer functionality was removed or flagged for removal
by this pass.

## 13. Responsive behavior

Structural mechanisms confirmed by code review (not runtime-rendered at
each resolution in this pass — see caveat in the exit gate):

- `NavOverflowMenu` demotes secondary tabs behind "More" instead of wrapping
  the primary tab strip, keeping the header compact at narrow widths.
- Gantt panel's `_compact` breakpoint (`Theme.AppTheme.compactContentBreakpoint`)
  forces `ganttViewMode` away from `"split"` to `"grid"` or `"timeline"`,
  avoiding an unusable forced wide split at 1024×640.
- The Activity Inspector renders inline (consuming a fixed
  `Theme.AppTheme.inspectorWidth` column) only above the compact breakpoint;
  below it, it becomes an `AppWidgets.SlideOverPanel` overlay sized to
  `min(360, width-80)` — it does not permanently steal Gantt width at
  narrow sizes.
- Resource Leveling and all other secondary panels use `ScrollView` +
  `ColumnLayout` (vertical stacking), which degrades to scrolling rather
  than clipping at narrow widths.

## 14. Leveling architecture

Unchanged from `R4_4_PLANNING_SCHEDULING_IMPLEMENTATION_SUMMARY.md` §1–2:
`ResourceLevelingPlanner` remains the single authoritative, pure
implementation; this QML pass only changed where its UI lives (folded into
one Resource Leveling tab alongside Current Resource Load).

## 15. R4.4W.1 calendar-cache performance fix

See §7 above and `R4_4_PLANNING_SCHEDULING_IMPLEMENTATION_SUMMARY.md` §4 for
the full root-cause/fix writeup (`MemoizingCalendarWindow`, scoped to
`ResourceLevelingPlanner.build_proposal` only).

## 16. Test evidence (2026-08-20 validation pass)

- `src/tests/project_management -k "scheduling or leveling"` — **118
  passed**, 0 failed
- `src/tests/project_management/dependency/test_resource_leveling_planner_performance.py`
  — **3 passed** (benchmark, see §7)
- `src/tests/architecture/test_qml_architecture_guardrails_runtime.py`,
  `test_qml_architecture_guardrails_layers.py`,
  `test_qml_architecture_guardrails_workspaces.py`,
  `src/tests/test_qml_offscreen_loading.py` — **35 passed, 2 failed**
  (both pre-existing/unrelated — see §17)
- `pyside6-qmllint` over every changed/added scheduling QML file — **0
  errors, 0 warnings blocking**; 2 `Info`-level unused-import notices
  (`SchedulingWorkspacePage.qml`, `SchedulingTimelinePanel.qml`) and 1
  `Warning`-level unqualified-`modelData`-access notice
  (`SchedulingCalendarsPanel.qml:160`) — cosmetic, non-blocking, left as
  minor cleanup opportunities rather than in-scope fixes for this pass
- Full `src/tests/project_management/` regression suite — run in progress
  at time of writing; see follow-up note if not yet complete when this
  document is read

## 17. Known unrelated failures

Two pre-existing architecture-guardrail failures, confirmed unrelated to
the Planning/Scheduling QML IA change (neither file was touched by this
pass):

1. `test_qml_architecture_guardrails_layers.py::test_qml_files_do_not_use_parent_relative_imports`
   — `src/ui_qml/modules/project_management/qml/workspaces/portfolio/tabs/ScenariosTab.qml:8`
   uses a parent-relative `import "../..."`.
2. `test_qml_architecture_guardrails_workspaces.py::test_platform_admin_workspace_controller_uses_split_entrypoint`
   — stale `src/ui_qml/platform/controllers/admin` directory still exists.

Both are Portfolio/Platform-module issues outside R4.4 Planning scope and
were not introduced by this work.

## 18. Exact R4.5 boundary

Deliberately **not implemented** in R4.4, and no placeholder/stub controls
were added for any of them:

- Dependency-line rendering
- Real baseline-bar/overlay rendering
- Zoom
- Variable timescale
- Deeper Gantt timeline interaction/synchronization/polish
- Any other Gantt-specific polish already identified by the QML IA audit

R4.5 work has not started. R5 work has not started.
