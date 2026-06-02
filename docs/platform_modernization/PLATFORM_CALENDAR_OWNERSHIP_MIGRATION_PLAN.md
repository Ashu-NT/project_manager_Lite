# Platform Calendar Ownership Migration Plan

Status: `discovery complete / backend ownership slice 1 complete / API ownership slice complete / frontend ownership slice complete / PM rewiring partial`

## Goal

Move shared working-calendar ownership out of Project Management and into
Platform while preserving PM scheduling behavior.

Platform should own:

- working calendars
- working-day rules
- holidays / exceptions
- working-day calculation helpers
- calendar CRUD/admin UX

Project Management should continue to own:

- CPM and scheduling calculations
- task and project schedule logic
- baseline and variance logic
- PM-specific calendar event sync tied to tasks/projects
- read-only calendar consumption inside PM Scheduling and Resources

## Scope Boundary Confirmed From Discovery

The repo currently mixes two different calendar concerns under PM:

1. **Global working-calendar ownership**
   - `WorkingCalendar`
   - `Holiday`
   - working-day math
   - calendar CRUD
   - calendar selector / summary / exception management UI

2. **PM-specific calendar event usage**
   - `CalendarEvent`
   - task-to-calendar event sync
   - project/task event listing

Only the first category moves to Platform in this migration slice. PM-specific
calendar-event behavior stays in PM unless a later platform-wide scheduling
event model is introduced.

## Discovery Map

### Current PM calendar backend files

- `src/core/modules/project_management/domain/scheduling/calendar.py`
- `src/core/modules/project_management/application/scheduling/work_calendar_engine.py`
- `src/core/modules/project_management/application/scheduling/work_calendar_service.py`
- `src/core/modules/project_management/application/scheduling/calendar_service.py`
- `src/core/modules/project_management/contracts/repositories/cost_calendar.py`
- `src/core/modules/project_management/infrastructure/persistence/orm/cost_calendar.py`
- `src/core/modules/project_management/infrastructure/persistence/mappers/cost_calendar.py`
- `src/core/modules/project_management/infrastructure/persistence/repositories/cost_calendar.py`
- `src/core/modules/project_management/application/scheduling/__init__.py`

### Current PM API / composition ownership

- `src/core/modules/project_management/api/desktop/scheduling.py`
- `src/api/desktop/runtime.py`
- `src/infra/composition/project_registry.py`
- `src/infra/composition/repositories.py`
- `src/infra/composition/app_container.py`

### Current PM frontend ownership

- `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py`
- `src/ui_qml/modules/project_management/presenters/scheduling_workspace_presenter.py`
- `src/ui_qml/modules/project_management/view_models/scheduling.py`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingCalendarsPanel.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingDetailPanel.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/sections/SchedulingCalendarSection.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers/typeinfo/scheduling.fragment`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers/typeinfo/plugins.qmltypes`

### Current PM tests tied to calendar ownership

- `src/tests/project_management/test_calendar_flow.py`
- `src/tests/project_management/test_cpm_flow.py`
- `src/tests/project_management/test_business_rules_and_edge_cases.py`
- `src/tests/project_management/test_project_management_desktop_api.py`
- `src/tests/project_management/test_qml_project_management_presenters.py`
- `src/tests/project_management/test_resource_leveling_workflow.py`
- `src/tests/project_management/test_technical_math_reporting.py`
- `src/tests/platform/test_phase_b_session_permissions.py`
- `src/tests/architecture/test_service_architecture.py`

### Current Platform touchpoints already present

- `src/core/platform/org/domain/site.py`
- `src/core/platform/org/application/site_service.py`
- `src/api/desktop/platform/site.py`
- `src/api/desktop/platform/models/site.py`
- `src/infra/persistence/migrations/versions/9d4e7f1a2b3c_expand_shared_master_metadata.py`

These already prove Platform has a site-level `default_calendar_id` concept even
though the actual working-calendar implementation still lives in PM.

### Current PM consumers of calendar data

- scheduling desktop API snapshot / selectors / working-day calculator
- scheduling presenter + controller state:
  - `calendarOptions`
  - `selectedCalendarId`
  - `calendar`
  - `calendarSummaryRows`
  - `holidayRows`
- scheduling UI:
  - save calendar
  - add/delete holiday
  - calculate working days
- dashboard and reporting via `WorkCalendarEngine`
- task and resource availability logic via `WorkCalendarEngine`
- baseline and schedule-impact services via `WorkCalendarEngine`

## Target Ownership

### Platform owns

- `WorkingCalendar`
- `Holiday`
- `WorkingCalendarRepository`
- working-calendar ORM / mappers / repositories
- `WorkCalendarEngine`
- `WorkCalendarService`
- platform calendar API surface
- Admin Console calendar management UX

### PM keeps

- `CalendarEvent`
- `CalendarService` for PM task/project event sync
- PM scheduling, dependency, baseline, leveling, and EVM logic
- read-only calendar selectors / summary / calculation consumption

## Implementation Phases

### Phase 1 - Discovery

- [x] scan repo for backend calendar ownership
- [x] scan repo for frontend calendar ownership
- [x] map API and composition seams
- [x] map tests and migration touchpoints
- [x] confirm PM-specific vs global calendar boundary

### Phase 2 - Backend move

- [x] create `src/core/platform/calendar/` package
- [x] move shared calendar domain types into Platform
- [x] move working-calendar repository contract into Platform
- [x] move working-calendar engine/service into Platform
- [x] move working-calendar ORM/mappers/repository into Platform infrastructure
- [x] leave PM `CalendarEvent` persistence in PM
- [x] rewire PM imports to Platform calendar engine/service
- [x] keep short-term compatibility imports only where needed

### Phase 3 - API move

- [x] move shared calendar API ownership out of PM desktop API surface
- [x] add Platform calendar API surface matching current desktop conventions
- [x] keep PM scheduling desktop API consuming Platform calendar APIs/services

### Phase 4 - Frontend move

- [x] remove calendar CRUD ownership from PM Scheduling
- [x] add Platform Admin calendar management section/workspace
- [x] preserve PM calendar selector and read-only summary/impact
- [x] update routes, catalogs, imports, qmldir, and qmltypes

### Phase 5 - PM rewiring

- [x] PM Scheduling consumes Platform calendar options and summary
- [ ] PM Resources consumes Platform calendar data where needed
- [x] PM scheduling controller/presenter/QML no longer own calendar CRUD methods

### Phase 6 - Cleanup and validation

- [ ] remove stale PM calendar ownership files
- [ ] update tests
- [ ] update architecture guardrails if ownership paths changed
- [ ] run recursive stale-import scans
- [ ] run backend and QML validation

## Immediate Execution Order

1. Introduce Platform calendar package and persistence seam.
2. Rewire composition to build `WorkCalendarEngine` / `WorkCalendarService`
   from Platform.
3. Rewire PM desktop API and PM services to import Platform calendar types.
4. Move calendar CRUD API/UI ownership into Platform.
5. Remove stale PM ownership code after tests are green.

## Validation Checklist

- PM scheduling still loads calendar options and summary
- working-day calculations still return the same results
- holidays still persist in existing tables unless a migration explicitly changes
  that ownership
- PM task/resource/dashboard/reporting flows still use calendar math correctly
- Platform site default-calendar references remain valid
- no stale PM-owned calendar CRUD UI remains after the UI migration

## Risks To Watch

- `calendar_events` is mixed into the current PM `cost_calendar` persistence
  files; moving only the shared working-calendar pieces requires a clean split.
- `src/api/desktop/runtime.py` and composition services expose work-calendar
  services broadly; import rewiring must not break service graph construction.
- PM scheduling QML currently assumes CRUD-capable calendar ownership in the PM
  controller; the UI move must remove those methods gradually, not abruptly.
- existing architecture tests and path-rewrite tests reference current PM
  calendar paths and will need coordinated updates.

## Current Execution Status

- discovery and file-level mapping: complete
- platform package design boundary: complete
- backend ownership move for shared working-calendar services: complete
- compatibility import bridge for PM consumers: complete
- API ownership move: complete
- frontend ownership move into Platform Admin: complete
- PM scheduling controller/presenter/QML ownership cleanup: complete
- PM resources follow-up and desktop API compatibility cleanup: next

## Implemented In Slice 1

- added new Platform package:
  - `src/core/platform/calendar/domain/*`
  - `src/core/platform/calendar/application/*`
  - `src/core/platform/calendar/contracts.py`
- added new Platform persistence seam:
  - `src/core/platform/infrastructure/persistence/orm/calendar.py`
  - `src/core/platform/infrastructure/persistence/mappers/calendar.py`
  - `src/core/platform/infrastructure/persistence/repositories/calendar.py`
- rewired PM compatibility layers so PM now consumes Platform-owned
  `WorkCalendarEngine` / `WorkCalendarService`
- kept PM `CalendarEvent` ownership in PM persistence and service code
- updated repository/composition wiring so the service graph builds the
  working-calendar repository from the Platform infrastructure path

## Implemented In Slice 2

- added Platform desktop calendar API:
  - `src/api/desktop/platform/calendar.py`
  - `src/api/desktop/platform/models/calendar.py`
- registered Platform calendar API in the shared desktop runtime registry
- rewired PM scheduling desktop API so shared calendar CRUD and working-day
  preview operations consume the Platform calendar desktop API as a
  compatibility client
- preserved PM-specific scheduling, dependency, baseline, and constraint logic
  inside the PM desktop API

## Known Follow-up After Slice 1

- PM scheduling desktop API still owns calendar CRUD methods and DTOs
- PM resources workspace still needs a focused pass if it should surface shared
  calendar context directly
- PM scheduling desktop API still exposes shared calendar CRUD as a compatibility
  bridge to Platform; a later cleanup pass can decide whether that shim remains
  or becomes a thin redirect-only contract

## Implemented In Slice 3

- added Platform Admin calendar governance surface:
  - `src/ui_qml/platform/presenters/calendar_catalog_presenter.py`
  - `src/ui_qml/platform/controllers/admin/calendar_controller.py`
  - `src/ui_qml/platform/qml/workspaces/admin/AdminCalendarDetailPage.qml`
  - `src/ui_qml/platform/qml/Platform/Dialogs/WorkingCalendarEditorDialog.qml`
  - `src/ui_qml/platform/qml/Platform/Dialogs/WorkingCalendarHolidayDialog.qml`
- wired Platform admin context/controller/typeinfo/nav/dialog-host integration
  so shared calendars now appear as a first-class Platform admin entity
- added `calendars_changed` shared-master domain event wiring and calendar
  service emission so Platform Admin and PM Scheduling can refresh on calendar
  mutations
- downgraded PM Scheduling calendar panel to read-only/shared-consumer behavior:
  selector, summary, exception register, and working-day preview remain
  available, but calendar CRUD no longer lives in PM QML
- permission semantics for the moved platform calendar service still use the
  legacy PM task permission guard for backward compatibility and should be
  revisited when the Platform Admin API/UI move lands
