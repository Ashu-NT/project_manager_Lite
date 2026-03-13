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

## Pro Phase 2 Roadmap (Tracked 2026-03-11)

- [x] 1. Portfolio dashboard
  - cross-project executive KPIs
  - portfolio ranking and status rollups
  - resource capacity across projects
  - progress: dashboard now supports a `Portfolio Overview` mode with aggregated KPIs, project ranking, status rollup, and cross-project capacity on 2026-03-11
  - progress: project view now exposes `Milestone Health` and `Critical Path Watchlist` as selectable professional panels on 2026-03-11
- [x] 2. Timesheet approvals / lock periods
  - monthly resource timesheet periods
  - submit / approve / reject / explicit lock-unlock lifecycle
  - edit blocking for submitted, approved, and locked periods
  - progress: backend/service lifecycle shipped and covered by targeted tests on 2026-03-11
  - progress: extracted into dedicated `timesheet` core/infra/ui modules and upgraded runtime dialog to manage monthly period state on 2026-03-11
  - progress: timesheet dialog now surfaces a period review lane, approval queue summary, and faster month navigation for approvers on 2026-03-11
- [x] 3. Richer import wizard
  - preview + validation before commit
  - dry-run summaries and row-level error handling
  - broader mapping flow beyond raw CSV entrypoint
  - progress: projects workspace now opens an import wizard with column mapping, preview counts, row diagnostics, and partial-valid import execution on 2026-03-11
- [x] 4. Risk / issue / change register
  - dedicated records, ownership, status, due dates
  - audit-friendly workflow and reporting
  - progress: new persisted register aggregate shipped with dedicated UI tab, dashboard summary panel, audit coverage, and project-level refresh wiring on 2026-03-11

Execution note:
- The implementation order starts with the timesheet backend because it has the strongest existing foundation and lowest migration risk.
- Each item ships with targeted tests before being marked complete.

## Enterprise RBAC Hardening Roadmap (Tracked 2026-03-12)

- [x] 1. Deny-by-default auth/session semantics
  - anonymous sessions no longer implicitly pass permission checks
  - UI permission guards now deny unauthenticated access by default
  - `PM_SKIP_LOGIN` no longer bypasses authentication for anonymous desktop sessions
  - CLI startup now authenticates before opening the command workflow
- [x] 2. Backend read enforcement on core service surfaces
  - read/list access now enforced on project, task, assignment, dependency, resource, cost, timesheet, calendar, work-calendar, baseline, dashboard, reporting, finance, approval, and audit read paths
  - report export UI enablement now depends on authenticated `report.export`
- [x] 3. Dedicated enterprise permissions
  - split broad permissions like `auth.manage` and `project.manage` into domain-specific admin/read/export/approve capabilities
  - add explicit permissions for register, support, audit, finance, import, portfolio, and timesheet lifecycle decisions
- [x] 4. Project-scoped access control / membership model
  - move beyond global roles toward project membership, scoped roles, and row-level filtering
- [ ] 5. Enterprise identity controls
  - add SSO/MFA, session expiry, lockout/rate limiting, and safer bootstrap admin handling

Progress note:
- Focused RBAC hardening shipped on 2026-03-12 with deny-by-default sessions, CLI/desktop authentication tightening, and backend read enforcement across the main business-service surfaces.
- Enterprise role templates, canonical scoped project roles, read-only identity visibility, and payroll-ready permission boundaries were added on 2026-03-13.
