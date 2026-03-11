# Pro Set Implementation Tracker

This file persists the requested instruction:

Implement the full Pro Set 1 to 7 and keep progress tracked until all items are completed.

## Scope

1. Productivity UX core:
   - bulk actions
   - advanced search/filtering
   - saved views
2. Accessibility + shortcuts
3. Undo/redo
4. Interactive Gantt with drag-and-drop
5. Custom dashboard builder
6. Collaboration baseline
7. Material Design 3 visual modernization

## Status

- [x] 1. Productivity UX core (v1 on Task workspace)
- [x] 2. Accessibility + shortcuts (v1 for Task workspace + global focus styling)
- [x] 3. Undo/redo (v1 for bulk task status updates)
- [x] 4. Interactive Gantt drag-and-drop (v1 timeline editor in Gantt dialog)
- [x] 5. Custom dashboard builder (v1 persisted layout dialog)
- [x] 6. Collaboration baseline (v1 task comments/mentions/attachments + mention badge)
- [x] 7. Material Design 3 modernization (v1 tokens/shape updates)

## Notes

- This is an initial integrated delivery (v1) across all seven areas.
- Next iterations should expand each capability beyond Task/Report/Dashboard focus.

## Resource Capacity Rollout (Phase 1-3)

- [x] 1. Resource profile expanded with `capacity_percent`, `address`, `contact`
- [x] 2. Capacity applied to assignment validation and dashboard utilization views
- [x] 3. Capacity integrated into reporting and resource leveling thresholds

## Expansion Tracker (2026-03-11)

- [x] 1. Shared collaboration foundation
  - runtime default moved from local JSON-only comments to DB-backed task comments
  - mentions/read-state preserved
  - attachments stored as app-managed references during comment post
- [x] 4. Import workflows
  - CSV import flows added for projects, resources, tasks, and costs
  - import runs through canonical service-layer validation/update rules
  - Projects tab now exposes an `Import CSV` action
- [x] 5. Real timesheets
  - `time_entries` persistence added at the assignment level
  - task assignment totals now roll up from time entries
  - task UI now opens a timesheet dialog instead of editing aggregate hours directly
  - existing aggregate `hours_logged` now seeds an opening-balance entry on first timesheet use

## Follow-ups

- Shared collaboration becomes truly multi-user when the app is pointed at a shared database via `PM_DB_URL`.
- Legacy aggregate `hours_logged` is still preserved as the reporting compatibility field, but it now syncs from timesheet rows once an assignment is initialized for timesheets.
