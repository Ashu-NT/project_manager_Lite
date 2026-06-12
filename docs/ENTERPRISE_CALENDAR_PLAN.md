# Enterprise Calendar Engine — Implementation Plan

**Date:** 2026-06-02  
**Branch:** `refactor/safe-start`  
**Status:** Phase 1 (Discovery) COMPLETE — Plan ready for execution

---

## 1. Discovery Results — Existing Structure

### 1.1 Platform Calendar — Current State

| Artifact | Location | Status |
|---|---|---|
| `WorkingCalendar` domain | `src/core/platform/calendar/domain/calendar.py` | Minimal: id, name, working_days (set[int]), hours_per_day |
| `Holiday` domain | same file | id, calendar_id, date, name |
| `WorkingCalendarORM` | `src/core/platform/infrastructure/persistence/orm/calendar.py` | `working_calendars` table |
| `HolidayORM` | same file | `holidays` table |
| `WorkCalendarService` | `src/core/platform/calendar/application/work_calendar_service.py` | get/set/list/add/delete |
| `WorkCalendarEngine` | `src/core/platform/calendar/application/work_calendar_engine.py` | is_working_day, next_working_day, add_working_days, working_days_between |
| `WorkingCalendarRepository` (ABC) | `src/core/platform/calendar/contracts.py` | get, get_default, upsert, list_holidays, add_holiday, delete_holiday |
| `SqlAlchemyWorkingCalendarRepository` | `src/core/platform/infrastructure/persistence/repositories/calendar.py` | Full implementation |
| `AdminCalendarDetailPage.qml` | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminCalendarDetailPage.qml` | Sections: Overview, Holidays, Calculator, Audit |
| `WorkingCalendarEditorDialog.qml` | `src/ui_qml/platform/qml/Platform/Dialogs/WorkingCalendarEditorDialog.qml` | Exists |
| `WorkingCalendarHolidayDialog.qml` | `src/ui_qml/platform/qml/Platform/Dialogs/WorkingCalendarHolidayDialog.qml` | Exists |

**Gap:** Single flat `working_calendars` table. No type, scope, hierarchy, rules, exceptions, shift patterns, or assignment tables. No `organization_id`.

### 1.2 Site

| Artifact | Location | Notes |
|---|---|---|
| `Site` domain | `src/core/platform/org/domain/site.py` | Has `default_calendar_id` (FK to `working_calendars.id`) |
| `SiteORM` | `src/core/platform/infrastructure/persistence/orm/org.py` | `sites` table |
| `SiteService` | `src/core/platform/org/application/site_service.py` | Full CRUD |
| `SqlAlchemySiteRepository` | `src/core/platform/infrastructure/persistence/repositories/org.py` | Full implementation |
| `PlatformSiteDesktopApi` | `src/api/desktop/platform/site.py` | list, create, update |
| `AdminSiteDetailPage.qml` | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminSiteDetailPage.qml` | Sections: Overview, Departments, Structures, Warehouses, Projects, Assets, Documents, Audit — NO Calendar section |

**Gap:** Site has `default_calendar_id` but no Calendar section in detail page, no enterprise calendar assignment table, no exception or recurring event management.

### 1.3 Department

| Artifact | Location | Notes |
|---|---|---|
| `Department` domain | `src/core/platform/org/domain/department.py` | No calendar_id |
| `DepartmentORM` | `src/core/platform/infrastructure/persistence/orm/org.py` | `departments` table |
| `DepartmentService` | `src/core/platform/org/application/department_service.py` | Full CRUD |
| `AdminDepartmentDetailPage.qml` | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDepartmentDetailPage.qml` | No Calendar section |

**Gap:** No calendar linkage at all. No recurring meeting/training management.

### 1.4 Employee

| Artifact | Location | Notes |
|---|---|---|
| `Employee` domain | `src/core/platform/org/domain/employee.py` | No calendar_id |
| `EmployeeORM` | `src/core/platform/infrastructure/persistence/orm/org.py` | `employees` table |
| `EmployeeService` | `src/core/platform/org/application/employee_service.py` | Full CRUD |
| `AdminEmployeeDetailPage.qml` | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEmployeeDetailPage.qml` | No Calendar section |

**Gap:** No employee-level calendar assignment, vacation/sick leave/exception management.

### 1.5 Organization

| Artifact | Location | Notes |
|---|---|---|
| `Organization` domain | `src/core/platform/org/domain/organization.py` | id, organization_code, display_name, timezone_name, base_currency |
| `OrganizationORM` | `src/core/platform/infrastructure/persistence/orm/org.py` | `organizations` table |
| `OrganizationService` | `src/core/platform/org/application/organization_service.py` | Full CRUD |

**Action:** `platform_calendars` must have `organization_id → organizations.id`.

### 1.6 PM Project

| Artifact | Location | Notes |
|---|---|---|
| `Project` domain | `src/core/modules/project_management/domain/projects/project.py` | Has `organization_id`, `site_id` — no `calendar_id` |
| `ProjectORM` | `src/core/modules/project_management/infrastructure/persistence/orm/project.py` | `projects` table |
| `ProjectService` | `src/core/modules/project_management/application/projects/service.py` | Full orchestrator |

**Gap:** No project calendar assignment table. PM scheduling references calendar via `WorkCalendarEngine` but not via a structured project-calendar relationship.

### 1.7 PM Resource

| Artifact | Location | Notes |
|---|---|---|
| `Resource` domain | `src/core/modules/project_management/domain/resources/resource.py` | id, name, code, role, hourly_rate, `capacity_percent` (static!), `worker_type` (EMPLOYEE/EXTERNAL), `employee_id` (nullable) |
| `ResourceORM` | `src/core/modules/project_management/infrastructure/persistence/orm/resource.py` | `resources` table, FK `employee_id → employees.id` |
| `ResourceService` | `src/core/modules/project_management/application/resources/resource_service.py` | Orchestrator with mixins |

**Critical gap:** `capacity_percent` is stored as a static field. Must become derived from calendar rules. No resource calendar assignment table.

### 1.8 PM Scheduling — Calendar Integration

| Artifact | Location | Notes |
|---|---|---|
| `CalendarContext` | `src/core/modules/project_management/application/scheduling/calendar_resolver.py` | resource > project > site > organization > default |
| `CalendarResolver` | same file | resolve(), resolve_for_resource(), resolve_for_project() |
| `WorkCalendarEngine` (PM copy) | `src/core/modules/project_management/application/scheduling/work_calendar_engine.py` | Duplicate of Platform engine |
| `SchedulingEngine` | `src/core/modules/project_management/application/scheduling/engine.py` | CPM, leveling |

**Gaps:** CalendarResolver exists but uses `WorkCalendarEngine` wrappers only. No department-level or employee-level calendar in the chain. PM has its own `work_calendar_engine.py` — duplication to eliminate. No structured calendar context exposed to QML.

### 1.9 Repository Bundle (current)

`src/infra/composition/repositories.py` — `RepositoryBundle` has:
- `work_calendar_repo: SqlAlchemyWorkingCalendarRepository`
- `calendar_repo: SqlAlchemyCalendarEventRepository` (PM scheduling events, not the platform calendar)

### 1.10 No Migration System

No Alembic. Tables created by SQLAlchemy `create_all(Base.metadata)`. New ORM classes in files that import `Base` are auto-included when the engine bootstraps.

### 1.11 Admin QML Patterns (confirmed)

- `SectionDetailPage` — tabbed detail shell
- `LazySectionLoader` — lazy-load section content
- `AdminDetailTableSection` — reusable table section component
- `AdminInformationalDetailSection` — informational/placeholder section
- `ContextualActionToolbar` — section-level action bar
- Pattern: all sections use `activeSectionIndex` or `_activeSectionLabel` switching
- All data flows as `property var` objects from controller → page

---

## 2. Architecture Decisions

### 2.1 New vs. Extend Existing Tables

Keep `working_calendars` + `holidays` intact. PM scheduling's `WorkCalendarEngine` references them directly. Introduce new `platform_calendars` table as the enterprise model. Migration bridge: on bootstrap, create a default `GLOBAL` platform calendar and link it to the existing `working_calendars.id = "default"`.

### 2.2 Organization ID on Platform Calendars

`platform_calendars.organization_id → organizations.id NOT NULL`. All calendar queries filter by active organization. This follows the existing `sites`, `departments`, `employees` pattern.

### 2.3 Capacity Is Derived

`Resource.capacity_percent` stays on the ORM for backward compatibility with existing queries. It becomes a presentational field populated by `ResourceCapacityCalculator.compute()` on demand. It must NOT be the source of truth for scheduling. New derived capacity is returned by the `WorkingTimeCalculator` and exposed via API without being persisted.

### 2.4 PM Does Not Duplicate Calendar Logic

- Platform owns: calendar definitions, working rules, exceptions, recurring events, shift patterns, resolver, calculator.
- PM owns: project-calendar assignment, resource-calendar assignment, project calendar adapter (calls Platform), resource availability service (calls Platform resolver).
- The existing PM `work_calendar_engine.py` and PM `work_calendar_service.py` are PM-local wrappers that will be refactored to delegate to Platform.

### 2.5 Employee vs. PM Resource Calendar

- If `Resource.worker_type == EMPLOYEE` and `Resource.employee_id` is set → inherit employee calendar automatically. PM must not store duplicate rules.
- If `Resource.worker_type == EXTERNAL` → `resource_calendar_assignments` is the source. PM resource calendar is authoritative for externals.

---

## 3. New File Map — Complete List

### 3.1 Backend — Platform Domain

```
src/core/platform/calendar/
├── domain/
│   ├── calendar.py                          ← EXISTING (keep)
│   └── enterprise_calendar.py              ← NEW: PlatformCalendar, CalendarWorkingRule,
│                                                   CalendarException, CalendarRecurringEvent,
│                                                   ShiftPattern, ShiftPatternDay,
│                                                   SiteCalendarAssignment, DeptCalendarAssignment,
│                                                   EmployeeCalendarAssignment, enums
├── application/
│   ├── work_calendar_service.py             ← EXISTING (keep)
│   ├── work_calendar_engine.py              ← EXISTING (keep)
│   ├── enterprise_calendar_service.py       ← NEW: CalendarService (CRUD for platform_calendars)
│   ├── working_rule_service.py             ← NEW: WorkingRuleService (CRUD for calendar_working_rules)
│   ├── calendar_exception_service.py       ← NEW: CalendarExceptionService (CRUD for calendar_exceptions)
│   ├── recurring_event_service.py          ← NEW: RecurringEventService (CRUD for calendar_recurring_events)
│   ├── shift_pattern_service.py            ← NEW: ShiftPatternService (CRUD for shift_patterns)
│   ├── calendar_assignment_service.py      ← NEW: CalendarAssignmentService (assign/unassign all entity types)
│   ├── enterprise_calendar_resolver.py     ← NEW: EnterpriseCalendarResolver (full hierarchy resolution)
│   └── working_time_calculator.py          ← NEW: WorkingTimeCalculator (derived hours, capacity, utilization)
└── contracts.py                             ← EXISTING + new ABC methods
```

### 3.2 Backend — Platform ORM

```
src/core/platform/infrastructure/persistence/orm/
├── calendar.py                              ← EXISTING (keep working_calendars + holidays)
└── enterprise_calendar.py                  ← NEW: PlatformCalendarORM, CalendarWorkingRuleORM,
                                                    CalendarExceptionORM, CalendarRecurringEventORM,
                                                    ShiftPatternORM, ShiftPatternDayORM,
                                                    SiteCalendarAssignmentORM,
                                                    DepartmentCalendarAssignmentORM,
                                                    EmployeeCalendarAssignmentORM
```

### 3.3 Backend — Platform Repositories

```
src/core/platform/infrastructure/persistence/repositories/
├── calendar.py                              ← EXISTING (keep)
└── enterprise_calendar.py                  ← NEW: SqlAlchemyPlatformCalendarRepository,
                                                    SqlAlchemyCalendarWorkingRuleRepository,
                                                    SqlAlchemyCalendarExceptionRepository,
                                                    SqlAlchemyCalendarRecurringEventRepository,
                                                    SqlAlchemyShiftPatternRepository,
                                                    SqlAlchemyCalendarAssignmentRepository
```

### 3.4 Backend — Platform Contracts

```
src/core/platform/calendar/contracts.py     ← EXISTING + add new ABCs:
                                               PlatformCalendarRepository
                                               CalendarWorkingRuleRepository
                                               CalendarExceptionRepository
                                               CalendarRecurringEventRepository
                                               ShiftPatternRepository
                                               CalendarAssignmentRepository
```

### 3.5 Backend — PM Module ORM

```
src/core/modules/project_management/infrastructure/persistence/orm/
└── calendar_assignment.py                  ← NEW: ProjectCalendarAssignmentORM,
                                                    ResourceCalendarAssignmentORM
```

### 3.6 Backend — PM Module Domain

```
src/core/modules/project_management/domain/
└── calendar/
    ├── __init__.py
    └── assignment.py                       ← NEW: ProjectCalendarAssignment, ResourceCalendarAssignment
```

### 3.7 Backend — PM Module Repositories

```
src/core/modules/project_management/infrastructure/persistence/repositories/
└── calendar_assignment.py                  ← NEW: SqlAlchemyProjectCalendarAssignmentRepository,
                                                    SqlAlchemyResourceCalendarAssignmentRepository
```

### 3.8 Backend — PM Module Services (adapters/consumers)

```
src/core/modules/project_management/application/
├── scheduling/
│   └── project_calendar_adapter.py         ← NEW: ProjectCalendarAdapter
│                                               wraps EnterpriseCalendarResolver for project scope
└── resources/
    ├── resource_availability_service.py    ← NEW: ResourceAvailabilityService
    │                                           resolves resource calendar context, returns available slots
    └── resource_capacity_calculator.py     ← NEW: ResourceCapacityCalculator
                                                compute(resource_id, date_range) → derived capacity dict
```

### 3.9 Backend — Platform Desktop API

```
src/api/desktop/platform/
├── enterprise_calendar.py                  ← NEW: EnterpriseCalendarDesktopApi
└── models/
    └── enterprise_calendar.py              ← NEW: DTOs + Commands for all calendar entities
```

### 3.10 Backend — PM Desktop API Extensions

```
src/api/desktop/project_management/ (or equivalent)
└── resource_availability.py               ← NEW: ResourceAvailabilityDesktopApi
```

### 3.11 Infra Composition Updates

```
src/infra/composition/
├── repositories.py                         ← EXTEND: add enterprise calendar repos + PM calendar assignment repos
├── platform_registry.py                    ← EXTEND: add calendar services to PlatformServiceBundle
└── project_registry.py                     ← EXTEND: add PM calendar adapter + availability/capacity services
```

### 3.12 Frontend — Platform QML

```
src/ui_qml/platform/qml/
├── workspaces/admin/detail/
│   ├── AdminCalendarDetailPage.qml         ← EXTEND: add sections Working Rules, Shift Pattern, Assignments, Usage
│   ├── AdminSiteDetailPage.qml             ← EXTEND: add Calendar section
│   ├── AdminDepartmentDetailPage.qml       ← EXTEND: add Calendar section
│   └── AdminEmployeeDetailPage.qml         ← EXTEND: add Calendar section
├── workspaces/admin/dialogs/
│   └── AdminDialogHost.qml                 ← EXTEND: add all new calendar dialogs
└── Platform/Dialogs/
    ├── CalendarEditorDialog.qml            ← NEW: enterprise calendar create/edit (type, scope, timezone, etc.)
    ├── CalendarWorkingRuleDialog.qml       ← NEW: working rule create/edit per weekday
    ├── CalendarExceptionDialog.qml         ← NEW: exception create/edit (holiday, shutdown, vacation, etc.)
    ├── CalendarRecurringEventDialog.qml    ← NEW: recurring event create/edit
    ├── ShiftPatternEditorDialog.qml        ← NEW: shift pattern create/edit
    └── CalendarAssignmentDialog.qml        ← NEW: assign calendar to entity (site/dept/employee/project/resource)
```

### 3.13 Frontend — PM QML Extensions

```
src/ui_qml/modules/project_management/qml/
├── resources/
│   ├── sections/
│   │   └── ResourceCalendarSection.qml     ← NEW: resource calendar view (source, rules, exceptions, capacity)
│   └── panels/
│       └── ResourcesDetailPanel.qml        ← EXTEND: add Calendar section tab
└── scheduling/
    └── sections/
        └── SchedulingCalendarSection.qml   ← NEW: project calendar context viewer (read-only summary + chain)
```

### 3.14 Tests

```
src/tests/platform/
└── test_enterprise_calendar_foundation.py  ← NEW: full platform calendar test suite

src/tests/project_management/
└── test_enterprise_calendar_pm_integration.py  ← NEW: PM integration tests
```

---

## 4. Data Models — Detailed Schema

### 4.1 `platform_calendars` (new table)

```python
class PlatformCalendarORM(Base):
    __tablename__ = "platform_calendars"

    id: str (PK)
    organization_id: str (FK → organizations.id, NOT NULL)
    code: str (UNIQUE per org, NOT NULL)
    name: str (NOT NULL)
    description: str (nullable)
    calendar_type: str  # GLOBAL | SITE | DEPARTMENT | EMPLOYEE | PROJECT | RESOURCE
    base_calendar_id: str (FK → platform_calendars.id, nullable, self-referential)
    scope_type: str (nullable)   # site | department | employee | project | resource
    scope_id: str (nullable)     # FK to the scoped entity id
    timezone: str (NOT NULL, default "UTC")
    locale: str (nullable)
    is_default: bool (default False)
    is_active: bool (default True)
    effective_from: date (nullable)
    effective_to: date (nullable)
    priority: int (default 0)
    version: int (default 1)
    created_by: str (nullable)
    created_at: datetime
    updated_by: str (nullable)
    updated_at: datetime

Indexes:
    idx_platform_calendars_org (organization_id)
    idx_platform_calendars_type (calendar_type)
    idx_platform_calendars_scope (scope_type, scope_id)
    ux_platform_calendars_org_code (organization_id, code) UNIQUE
```

### 4.2 `calendar_working_rules` (new table)

```python
class CalendarWorkingRuleORM(Base):
    __tablename__ = "calendar_working_rules"

    id: str (PK)
    calendar_id: str (FK → platform_calendars.id, CASCADE DELETE)
    weekday: int  # 0=Monday … 6=Sunday
    is_working_day: bool (default True)
    start_time: time (nullable)       # e.g. 08:00
    end_time: time (nullable)         # e.g. 17:00
    break_start_time: time (nullable)
    break_end_time: time (nullable)
    break_minutes: int (default 0)
    hours_override: float (nullable)  # if set, overrides computed hours
    shift_code: str (nullable)        # reference to shift_patterns.code
    effective_from: date (nullable)
    effective_to: date (nullable)
    priority: int (default 0)

Indexes:
    idx_cal_working_rules_calendar (calendar_id)
    ux_cal_working_rules_cal_day (calendar_id, weekday) UNIQUE
```

### 4.3 `calendar_exceptions` (new table)

```python
class CalendarExceptionORM(Base):
    __tablename__ = "calendar_exceptions"

    id: str (PK)
    calendar_id: str (FK → platform_calendars.id, CASCADE DELETE)
    scope_type: str (nullable)     # additional scope override (resource, employee, etc.)
    scope_id: str (nullable)
    exception_date: date (NOT NULL)
    exception_type: str            # HOLIDAY | SHUTDOWN | VACATION | SICK_LEAVE | TRAINING |
                                   # MEETING | NON_WORKING | EXTRA_WORKING | REDUCED_HOURS |
                                   # OVERTIME | MAINTENANCE_WINDOW | SITE_CLOSED
    name: str (NOT NULL)
    description: str (nullable)
    start_time: time (nullable)
    end_time: time (nullable)
    hours_override: float (nullable)
    impact_type: str               # UNAVAILABLE | REDUCED_CAPACITY | EXTRA_CAPACITY |
                                   # WORKING | INFORMATION_ONLY
    priority: int (default 0)
    approval_status: str (default "APPROVED")   # PENDING | APPROVED | REJECTED
    approved_by: str (nullable)
    created_by: str (nullable)
    created_at: datetime
    updated_by: str (nullable)
    updated_at: datetime

Indexes:
    idx_cal_exceptions_calendar (calendar_id)
    idx_cal_exceptions_date (exception_date)
    idx_cal_exceptions_scope (scope_type, scope_id)
    idx_cal_exceptions_cal_date (calendar_id, exception_date)
```

### 4.4 `calendar_recurring_events` (new table)

```python
class CalendarRecurringEventORM(Base):
    __tablename__ = "calendar_recurring_events"

    id: str (PK)
    calendar_id: str (FK → platform_calendars.id, CASCADE DELETE)
    scope_type: str (nullable)
    scope_id: str (nullable)
    title: str (NOT NULL)
    event_type: str    # MEETING | TRAINING | ADMIN | MAINTENANCE | UNAVAILABLE |
                       # ON_CALL | OVERTIME_WINDOW | SHIFT_BLOCK
    recurrence_rule: str (NOT NULL)  # RFC 5545 RRULE string e.g. FREQ=WEEKLY;BYDAY=MO,WE
    start_time: time (NOT NULL)
    end_time: time (NOT NULL)
    impact_type: str   # UNAVAILABLE | REDUCED_CAPACITY | EXTRA_CAPACITY | WORKING | INFORMATION_ONLY
    capacity_impact_percent: float (nullable)
    effective_from: date (NOT NULL)
    effective_to: date (nullable)
    is_active: bool (default True)
    priority: int (default 0)

Indexes:
    idx_cal_recurring_calendar (calendar_id)
    idx_cal_recurring_scope (scope_type, scope_id)
    idx_cal_recurring_active (is_active)
```

### 4.5 `shift_patterns` (new table)

```python
class ShiftPatternORM(Base):
    __tablename__ = "shift_patterns"

    id: str (PK)
    organization_id: str (FK → organizations.id)
    code: str (NOT NULL)
    name: str (NOT NULL)
    description: str (nullable)
    pattern_type: str   # STANDARD | DAY_SHIFT | NIGHT_SHIFT | TWO_SHIFT | THREE_SHIFT |
                        # ROTATING | FOUR_ON_FOUR_OFF | CUSTOM
    rotation_cycle_days: int (nullable)
    timezone: str (default "UTC")
    is_active: bool (default True)

Indexes:
    idx_shift_patterns_org (organization_id)
    ux_shift_patterns_org_code (organization_id, code) UNIQUE
```

### 4.6 `shift_pattern_days` (new table)

```python
class ShiftPatternDayORM(Base):
    __tablename__ = "shift_pattern_days"

    id: str (PK)
    shift_pattern_id: str (FK → shift_patterns.id, CASCADE DELETE)
    day_offset: int (NOT NULL)   # 0-based offset in the rotation cycle
    is_working_day: bool (default True)
    start_time: time (nullable)
    end_time: time (nullable)
    break_minutes: int (default 0)
    hours: float (nullable)
    shift_label: str (nullable)   # e.g. "Day", "Night", "Off"

Indexes:
    idx_shift_pattern_days_pattern (shift_pattern_id)
    ux_shift_pattern_days_offset (shift_pattern_id, day_offset) UNIQUE
```

### 4.7 Assignment Tables (new tables)

#### `site_calendar_assignments`

```python
class SiteCalendarAssignmentORM(Base):
    __tablename__ = "site_calendar_assignments"

    id: str (PK)
    site_id: str (FK → sites.id, NOT NULL)
    calendar_id: str (FK → platform_calendars.id, NOT NULL)
    effective_from: date (nullable)
    effective_to: date (nullable)
    is_default: bool (default False)
    priority: int (default 0)

Indexes:
    idx_site_cal_assign_site (site_id)
    idx_site_cal_assign_cal (calendar_id)
```

#### `department_calendar_assignments`

```python
class DepartmentCalendarAssignmentORM(Base):
    __tablename__ = "department_calendar_assignments"

    id: str (PK)
    department_id: str (FK → departments.id, NOT NULL)
    calendar_id: str (FK → platform_calendars.id, NOT NULL)
    effective_from: date (nullable)
    effective_to: date (nullable)
    is_default: bool (default False)
    priority: int (default 0)

Indexes:
    idx_dept_cal_assign_dept (department_id)
    idx_dept_cal_assign_cal (calendar_id)
```

#### `employee_calendar_assignments`

```python
class EmployeeCalendarAssignmentORM(Base):
    __tablename__ = "employee_calendar_assignments"

    id: str (PK)
    employee_id: str (FK → employees.id, NOT NULL)
    calendar_id: str (FK → platform_calendars.id, NOT NULL)
    effective_from: date (nullable)
    effective_to: date (nullable)
    is_default: bool (default False)
    priority: int (default 0)

Indexes:
    idx_emp_cal_assign_emp (employee_id)
    idx_emp_cal_assign_cal (calendar_id)
```

#### `project_calendar_assignments` (PM module)

```python
class ProjectCalendarAssignmentORM(Base):
    __tablename__ = "project_calendar_assignments"

    id: str (PK)
    project_id: str (FK → projects.id, NOT NULL)
    calendar_id: str (FK → platform_calendars.id, NOT NULL)
    effective_from: date (nullable)
    effective_to: date (nullable)
    is_default: bool (default False)
    priority: int (default 0)

Indexes:
    idx_proj_cal_assign_project (project_id)
    idx_proj_cal_assign_cal (calendar_id)
```

#### `resource_calendar_assignments` (PM module)

```python
class ResourceCalendarAssignmentORM(Base):
    __tablename__ = "resource_calendar_assignments"

    id: str (PK)
    resource_id: str (FK → resources.id, NOT NULL)
    calendar_id: str (FK → platform_calendars.id, NOT NULL)
    effective_from: date (nullable)
    effective_to: date (nullable)
    is_default: bool (default False)
    priority: int (default 0)

Indexes:
    idx_res_cal_assign_resource (resource_id)
    idx_res_cal_assign_cal (calendar_id)
```

---

## 5. EnterpriseCalendarResolver — Behavior

### 5.1 Resolution Order

```
1. GLOBAL calendar (organization_id + type=GLOBAL)
2. SITE calendar (assigned to site_id via site_calendar_assignments)
3. DEPARTMENT calendar (assigned to department_id via department_calendar_assignments)
4. EMPLOYEE calendar (assigned to employee_id via employee_calendar_assignments)
   — only if resource is EMPLOYEE-backed (Resource.worker_type == EMPLOYEE)
5. PROJECT calendar (assigned to project_id via project_calendar_assignments)
6. RESOURCE calendar (assigned to resource_id via resource_calendar_assignments)
   — only if resource is EXTERNAL (no employee_id)
7. Apply exceptions and recurring events from each level
   (lower level overrides higher level)
```

### 5.2 Resolver Interface

```python
# src/core/platform/calendar/application/enterprise_calendar_resolver.py

@dataclass
class ResolvedCalendarContext:
    date: date
    base_hours: float
    available_hours: float
    assigned_hours: float           # injected by caller, not computed here
    remaining_hours: float          # available - assigned
    capacity_percent: float         # available / base * 100
    utilization_percent: float      # assigned / available * 100
    status: str                     # AVAILABLE | CONSTRAINED | UNAVAILABLE | OVERTIME
    source_chain: list[str]         # ["GLOBAL-DE", "SITE-HAMBURG", "PROJECT-REFIT", "RESOURCE-JOHN"]
    overrides: list[str]            # ["RESOURCE_WORKING_HOURS", "TRAINING_EVENT"]
    timezone: str
    working_start: time | None
    working_end: time | None
    exceptions: list[dict]          # active exceptions for this date


class EnterpriseCalendarResolver:
    def __init__(
        self,
        calendar_repo: PlatformCalendarRepository,
        working_rule_repo: CalendarWorkingRuleRepository,
        exception_repo: CalendarExceptionRepository,
        recurring_event_repo: CalendarRecurringEventRepository,
        assignment_repo: CalendarAssignmentRepository,
        organization_id: str,
    ) -> None: ...

    def resolve_calendar_context(
        self,
        *,
        site_id: str | None = None,
        department_id: str | None = None,
        employee_id: str | None = None,
        project_id: str | None = None,
        resource_id: str | None = None,
        worker_type: str | None = None,
        target_date: date,
    ) -> ResolvedCalendarContext: ...

    def resolve_range(
        self,
        *,
        site_id: str | None = None,
        department_id: str | None = None,
        employee_id: str | None = None,
        project_id: str | None = None,
        resource_id: str | None = None,
        worker_type: str | None = None,
        start: date,
        end: date,
    ) -> list[ResolvedCalendarContext]: ...

    def get_source_chain(
        self,
        *,
        site_id: str | None = None,
        department_id: str | None = None,
        employee_id: str | None = None,
        project_id: str | None = None,
        resource_id: str | None = None,
        worker_type: str | None = None,
    ) -> list[str]: ...
```

### 5.3 WorkingTimeCalculator

```python
# src/core/platform/calendar/application/working_time_calculator.py

class WorkingTimeCalculator:
    """
    Pure computation layer. No DB access — works on resolved calendar context.
    
    Derived capacity formula:
        base_hours = working_end - working_start - break_minutes/60
                    (from effective working rules for the date)
        
        unavailable = sum(hours from UNAVAILABLE exceptions + recurring events)
        extra       = sum(hours from EXTRA_WORKING exceptions + OVERTIME events)
        
        available_hours = max(0, base_hours - unavailable + extra)
        
        capacity_percent    = available_hours / base_hours * 100
        utilization_percent = assigned_hours / available_hours * 100
        remaining_hours     = available_hours - assigned_hours
    """

    def compute_day(
        self,
        working_rules: list[CalendarWorkingRule],
        exceptions: list[CalendarException],
        recurring_events: list[CalendarRecurringEvent],
        target_date: date,
        assigned_hours: float = 0.0,
    ) -> DayCapacity: ...
```

---

## 6. Service Contracts — New Services

### 6.1 Platform CalendarService (enterprise_calendar_service.py)

```python
class CalendarService:
    def list_calendars(self, *, calendar_type: str | None = None, active_only: bool | None = None) -> list[PlatformCalendar]
    def get_calendar(self, calendar_id: str) -> PlatformCalendar | None
    def create_calendar(self, *, organization_id: str, code: str, name: str, calendar_type: str, ...) -> PlatformCalendar
    def update_calendar(self, calendar_id: str, ...) -> PlatformCalendar
    def delete_calendar(self, calendar_id: str) -> None   # raises if assigned
    def get_global_calendar(self, organization_id: str) -> PlatformCalendar | None
    def ensure_global_calendar(self, organization_id: str) -> PlatformCalendar  # bootstrap
```

### 6.2 CalendarAssignmentService (calendar_assignment_service.py)

```python
class CalendarAssignmentService:
    def assign_site_calendar(self, site_id: str, calendar_id: str, ...) -> SiteCalendarAssignment
    def assign_department_calendar(self, department_id: str, calendar_id: str, ...) -> DepartmentCalendarAssignment
    def assign_employee_calendar(self, employee_id: str, calendar_id: str, ...) -> EmployeeCalendarAssignment
    def assign_project_calendar(self, project_id: str, calendar_id: str, ...) -> ProjectCalendarAssignment
    def assign_resource_calendar(self, resource_id: str, calendar_id: str, ...) -> ResourceCalendarAssignment
    
    def get_site_calendar(self, site_id: str, at_date: date | None = None) -> SiteCalendarAssignment | None
    def get_department_calendar(self, department_id: str, at_date: date | None = None) -> DepartmentCalendarAssignment | None
    def get_employee_calendar(self, employee_id: str, at_date: date | None = None) -> EmployeeCalendarAssignment | None
    def get_project_calendar(self, project_id: str, at_date: date | None = None) -> ProjectCalendarAssignment | None
    def get_resource_calendar(self, resource_id: str, at_date: date | None = None) -> ResourceCalendarAssignment | None
    
    def list_calendar_assignments(self, calendar_id: str) -> dict[str, list]  # all entities using this calendar
    def remove_assignment(self, assignment_id: str, assignment_type: str) -> None
```

### 6.3 CalendarExceptionService (calendar_exception_service.py)

```python
class CalendarExceptionService:
    def list_exceptions(self, calendar_id: str, *, start: date | None = None, end: date | None = None) -> list[CalendarException]
    def add_exception(self, calendar_id: str, *, exception_date: date, exception_type: str, name: str, ...) -> CalendarException
    def update_exception(self, exception_id: str, ...) -> CalendarException
    def delete_exception(self, exception_id: str) -> None
    
    # Entity-scoped exception helpers
    def add_site_exception(self, site_id: str, calendar_id: str, ...) -> CalendarException
    def add_department_exception(self, department_id: str, calendar_id: str, ...) -> CalendarException
    def add_employee_exception(self, employee_id: str, calendar_id: str, ...) -> CalendarException
    def add_resource_exception(self, resource_id: str, calendar_id: str, ...) -> CalendarException
```

### 6.4 RecurringEventService (recurring_event_service.py)

```python
class RecurringEventService:
    def list_recurring_events(self, calendar_id: str) -> list[CalendarRecurringEvent]
    def add_recurring_event(self, calendar_id: str, *, title: str, event_type: str, recurrence_rule: str, ...) -> CalendarRecurringEvent
    def update_recurring_event(self, event_id: str, ...) -> CalendarRecurringEvent
    def delete_recurring_event(self, event_id: str) -> None
    
    # Expand recurrences for a date range
    def expand_occurrences(self, event_id: str, start: date, end: date) -> list[date]
```

### 6.5 ShiftPatternService (shift_pattern_service.py)

```python
class ShiftPatternService:
    def list_shift_patterns(self, *, active_only: bool | None = None) -> list[ShiftPattern]
    def get_shift_pattern(self, pattern_id: str) -> ShiftPattern | None
    def create_shift_pattern(self, *, code: str, name: str, pattern_type: str, ...) -> ShiftPattern
    def update_shift_pattern(self, pattern_id: str, ...) -> ShiftPattern
    def delete_shift_pattern(self, pattern_id: str) -> None
    def get_day(self, pattern_id: str, day_offset: int) -> ShiftPatternDay | None
    def set_day(self, pattern_id: str, day_offset: int, **fields) -> ShiftPatternDay
```

### 6.6 PM ProjectCalendarAdapter (project_calendar_adapter.py)

```python
class ProjectCalendarAdapter:
    """
    PM-side adapter. Delegates all calendar logic to Platform's EnterpriseCalendarResolver.
    PM scheduling engine calls this instead of WorkCalendarEngine directly.
    """
    def __init__(
        self,
        resolver: EnterpriseCalendarResolver,
        assignment_service: CalendarAssignmentService,
    ) -> None: ...

    def get_project_calendar_context(self, project_id: str, target_date: date) -> ResolvedCalendarContext: ...
    def working_days_between(self, project_id: str, start: date, end: date) -> int: ...
    def add_working_days(self, project_id: str, start: date, n: int) -> date: ...
    def is_working_day(self, project_id: str, target_date: date) -> bool: ...
```

### 6.7 PM ResourceAvailabilityService (resource_availability_service.py)

```python
class ResourceAvailabilityService:
    """
    Resolves a PM resource's full calendar context respecting the employee-vs-external rule.
    """
    def get_availability(
        self,
        resource_id: str,
        *,
        project_id: str | None = None,
        target_date: date,
        assigned_hours: float = 0.0,
    ) -> ResolvedCalendarContext: ...

    def get_availability_range(
        self,
        resource_id: str,
        *,
        project_id: str | None = None,
        start: date,
        end: date,
        assignments: dict[date, float] | None = None,  # date → assigned_hours
    ) -> list[ResolvedCalendarContext]: ...

    def is_available(self, resource_id: str, target_date: date) -> bool: ...
```

### 6.8 PM ResourceCapacityCalculator (resource_capacity_calculator.py)

```python
class ResourceCapacityCalculator:
    """
    Derives capacity for a resource over a date range.
    Does NOT persist capacity_percent — returns derived values only.
    """
    def compute(
        self,
        resource_id: str,
        start: date,
        end: date,
        assigned_hours_by_date: dict[date, float] | None = None,
    ) -> ResourceCapacitySummary: ...


@dataclass
class ResourceCapacitySummary:
    resource_id: str
    start: date
    end: date
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    days: list[ResolvedCalendarContext]
    conflicts: list[str]
    source_chain: list[str]
```

---

## 7. Desktop API — Platform Calendar

```python
# src/api/desktop/platform/enterprise_calendar.py

class EnterpriseCalendarDesktopApi:
    # Calendars
    def list_calendars(self, *, calendar_type: str | None = None) -> DesktopApiResult[tuple[CalendarDto, ...]]
    def get_calendar(self, calendar_id: str) -> DesktopApiResult[CalendarDto]
    def create_calendar(self, command: CalendarCreateCommand) -> DesktopApiResult[CalendarDto]
    def update_calendar(self, command: CalendarUpdateCommand) -> DesktopApiResult[CalendarDto]
    def delete_calendar(self, calendar_id: str) -> DesktopApiResult[None]

    # Working Rules
    def list_working_rules(self, calendar_id: str) -> DesktopApiResult[tuple[WorkingRuleDto, ...]]
    def save_working_rule(self, command: WorkingRuleCommand) -> DesktopApiResult[WorkingRuleDto]
    def delete_working_rule(self, rule_id: str) -> DesktopApiResult[None]

    # Exceptions
    def list_exceptions(self, calendar_id: str, ...) -> DesktopApiResult[tuple[ExceptionDto, ...]]
    def add_exception(self, command: ExceptionCreateCommand) -> DesktopApiResult[ExceptionDto]
    def update_exception(self, command: ExceptionUpdateCommand) -> DesktopApiResult[ExceptionDto]
    def delete_exception(self, exception_id: str) -> DesktopApiResult[None]

    # Recurring Events
    def list_recurring_events(self, calendar_id: str) -> DesktopApiResult[tuple[RecurringEventDto, ...]]
    def add_recurring_event(self, command: RecurringEventCreateCommand) -> DesktopApiResult[RecurringEventDto]
    def update_recurring_event(self, command: RecurringEventUpdateCommand) -> DesktopApiResult[RecurringEventDto]
    def delete_recurring_event(self, event_id: str) -> DesktopApiResult[None]

    # Shift Patterns
    def list_shift_patterns(self) -> DesktopApiResult[tuple[ShiftPatternDto, ...]]
    def create_shift_pattern(self, command: ShiftPatternCreateCommand) -> DesktopApiResult[ShiftPatternDto]
    def update_shift_pattern(self, command: ShiftPatternUpdateCommand) -> DesktopApiResult[ShiftPatternDto]
    def delete_shift_pattern(self, pattern_id: str) -> DesktopApiResult[None]

    # Assignments
    def assign_site_calendar(self, command: SiteCalendarAssignCommand) -> DesktopApiResult[AssignmentDto]
    def assign_department_calendar(self, command: DeptCalendarAssignCommand) -> DesktopApiResult[AssignmentDto]
    def assign_employee_calendar(self, command: EmpCalendarAssignCommand) -> DesktopApiResult[AssignmentDto]
    def assign_project_calendar(self, command: ProjectCalendarAssignCommand) -> DesktopApiResult[AssignmentDto]
    def assign_resource_calendar(self, command: ResourceCalendarAssignCommand) -> DesktopApiResult[AssignmentDto]
    def remove_assignment(self, assignment_id: str, assignment_type: str) -> DesktopApiResult[None]
    def list_calendar_assignments(self, calendar_id: str) -> DesktopApiResult[AssignmentSummaryDto]

    # Resolution
    def resolve_calendar_context(self, command: ResolveContextCommand) -> DesktopApiResult[ResolvedContextDto]
    def get_source_chain(self, command: SourceChainCommand) -> DesktopApiResult[tuple[str, ...]]

    # Calculation
    def calculate_working_days(self, command: WorkingDaysCommand) -> DesktopApiResult[WorkingDaysResultDto]
    def calculate_resource_availability(self, command: ResourceAvailabilityCommand) -> DesktopApiResult[ResourceAvailabilityDto]
    def calculate_resource_capacity(self, command: ResourceCapacityCommand) -> DesktopApiResult[ResourceCapacityDto]
```

---

## 8. Platform QML — Calendar Management Workspace Changes

### 8.1 AdminCalendarDetailPage.qml — Extended Sections

**Current sections:** Overview, Holidays, Calculator, Audit  
**New sections:** Overview, Working Rules, Exceptions, Recurring Events, Shift Pattern, Assignments, Usage, Audit

**Overview:** extend with new fields — calendar_type, scope, timezone, locale, is_default, effective dates, priority, base_calendar.  
**Working Rules:** `AdminDetailTableSection` showing 7-day rule rows. Toolbar: Edit Rules, Refresh.  
**Exceptions:** `AdminDetailTableSection` with exception_date, exception_type, name, impact_type. Toolbar: Add Exception, Delete, Refresh.  
**Recurring Events:** `AdminDetailTableSection` with title, event_type, recurrence_rule, impact_type. Toolbar: Add Recurring Event, Delete, Refresh.  
**Shift Pattern:** shows linked shift pattern (if any). Toolbar: Assign Pattern, Remove, Refresh.  
**Assignments:** `AdminDetailTableSection` showing all entities (sites, departments, employees, projects, resources) using this calendar.  
**Usage:** `AdminInformationalDetailSection` — resolver diagnostics, source chain preview.  
**Audit:** existing pattern (delegate to shared audit workspace).

### 8.2 AdminSiteDetailPage.qml — Calendar Section

Add `{ "label": "Calendar" }` section before Documents.

**Calendar section content:**
- `SectionHeading` "Calendar Assignment"
- `InlineMessage` info: "The site calendar defines location-specific working rules, shutdowns, and local holidays."
- `SectionCard` "Assigned Calendar" — show assigned calendar name, type, effective dates, source chain.
- `SectionCard` "Site Exceptions" — `AdminDetailTableSection` of site-specific exceptions.
- `SectionCard` "Inherited Chain" — show global → site chain.
- Toolbar actions: Assign Calendar, Add Exception, Refresh.

### 8.3 AdminDepartmentDetailPage.qml — Calendar Section

Add `{ "label": "Calendar" }` section.

**Calendar section content:**
- Assigned department calendar with source chain (global → site → department).
- Department recurring meetings.
- Department recurring training.
- Department-specific exceptions.
- Effective working schedule derived preview.
- Toolbar: Assign Calendar, Add Recurring Event, Add Exception, Refresh.

### 8.4 AdminEmployeeDetailPage.qml — Calendar Section

Add `{ "label": "Calendar" }` section.

**Calendar section content:**
- Assigned employee calendar with source chain (global → site → department → employee).
- Vacation management (exceptions with type=VACATION).
- Sick leave (exceptions with type=SICK_LEAVE).
- Recurring meetings / training.
- Availability preview for next 4 weeks (capacity table).
- Toolbar: Assign Calendar, Add Vacation, Add Exception, Add Recurring Event, Refresh.

---

## 9. PM QML — Resource Calendar Section

### 9.1 ResourceCalendarSection.qml (new)

Location: `src/ui_qml/modules/project_management/qml/resources/sections/ResourceCalendarSection.qml`

**Content:**
- `SectionHeading` "Resource Calendar"
- `InlineMessage` info: "Calendar rules are managed in Platform Admin. This section shows the resolved availability for this resource."
- `SectionCard` "Calendar Source" — show source type (Employee Calendar / PM Resource Calendar / Inherited), calendar name, source chain.
- `SectionCard` "Working Rules" — effective start/end, hours/day, shift code.
- `SectionCard` "Exceptions" — upcoming exceptions for next 30 days (table).
- `SectionCard` "Overtime Rules" — max overtime hours/day, max overtime hours/week.
- `SectionCard` "Capacity Preview" — table: date, base hours, available hours, assigned hours, remaining hours, capacity%, utilization%, status.
- `SectionCard` "Conflicts" — any allocation-over-capacity conflicts.
- Toolbar actions: Refresh, Manage Exceptions (for external resources only, opens Platform calendar for the resource calendar), View Availability.

**Employee-backed resource display:**
- Show "Employee Calendar: [employee name] — inherited from Platform Employee."
- Source chain: GLOBAL → SITE-X → DEPT-Y → EMP-Z
- Cannot edit employee calendar rules from PM. Show link/info pointing to Platform Admin Employee section.

**External resource display:**
- Show "PM Resource Calendar" as source.
- Allow: Assign Calendar, Add Resource Exception, Add Recurring Event.
- Source chain: GLOBAL → RESOURCE-X

### 9.2 ResourcesDetailPanel.qml — Add Calendar Tab

Extend `panels/ResourcesDetailPanel.qml` to add "Calendar" as a section in the resource detail view, lazy-loaded via `LazySectionLoader`.

### 9.3 Scheduling Calendar Context Section

Location: `src/ui_qml/modules/project_management/qml/scheduling/sections/SchedulingCalendarSection.qml`

**Content (read-only):**
- Assigned project calendar name, type.
- Source chain for the project: GLOBAL → SITE → PROJECT.
- Working-day summary: working days/week, hours/day.
- Key exceptions preview.
- Toolbar: Refresh (no CRUD — calendar owned by Platform Admin).

---

## 10. Validation Rules — Implementation Locations

All validators live in respective service `_validate_*()` private methods, called before persistence.

| Rule | Location |
|---|---|
| Calendar cannot be deleted if assigned to active site/dept/project/resource | `CalendarService.delete_calendar()` → calls `AssignmentRepository.count_active_assignments(calendar_id)` |
| Calendar effective dates must be valid (from < to) | `CalendarService._validate_effective_dates()` |
| Working start must be before working end | `WorkingRuleService._validate_time_window()` |
| Hours per day must match working window unless overridden | `WorkingTimeCalculator._validate_hours_consistency()` |
| Granularity must be one of [5, 10, 15, 30, 60] | `CalendarService._validate_granularity()` |
| Recurring events must have valid RRULE | `RecurringEventService._validate_rrule()` |
| Resource assignment cannot exceed derived available capacity | `ResourceAvailabilityService.check_allocation()` → returns warning/conflict, not hard block unless override=False |
| Time entry cannot be created outside valid calendar unless override | `CalendarExceptionService.is_time_entry_valid(resource_id, date, hours)` |
| Project calendar assignment must reference valid project | `CalendarAssignmentService._validate_project_exists()` |
| Resource calendar assignment must reference valid resource | `CalendarAssignmentService._validate_resource_exists()` |
| Employee-backed PM resource: employee_id required if worker_type == EMPLOYEE | `ResourceService._validate_employee_linkage()` (already exists implicitly — enforce explicitly) |
| Employee-backed resource inherits employee calendar | `ResourceAvailabilityService._resolve_source()` — checks `worker_type == EMPLOYEE` → routes to employee calendar |
| PM resource calendar must not duplicate employee calendar rules | `RecurringEventService._validate_no_employee_duplication()` — warns if resource is employee-backed and event matches employee calendar |

---

## 11. Tests — Test Cases

### 11.1 `src/tests/platform/test_enterprise_calendar_foundation.py`

```python
def test_global_calendar_created_on_bootstrap()
def test_global_calendar_working_hours_default()
def test_site_calendar_overrides_global_holiday()
def test_department_calendar_recurring_meeting_reduces_capacity()
def test_employee_calendar_vacation_blocks_availability()
def test_calendar_delete_blocked_if_assigned()
def test_calendar_effective_dates_validation()
def test_working_rule_start_before_end_enforced()
def test_exception_types_persist_correctly()
def test_recurring_event_rrule_expanded()
def test_shift_pattern_days_created_correctly()
def test_assignment_service_site_assign()
def test_assignment_service_department_assign()
def test_assignment_service_employee_assign()
def test_resolver_returns_global_when_no_overrides()
def test_resolver_site_overrides_global()
def test_resolver_department_overrides_site()
def test_resolver_employee_overrides_department()
def test_resolver_source_chain_correct()
def test_working_time_calculator_derived_capacity()
def test_overtime_increases_availability()
def test_shutdown_makes_day_unavailable()
def test_granularity_validation_rejects_invalid()
def test_rrule_validation_rejects_invalid()
```

### 11.2 `src/tests/project_management/test_enterprise_calendar_pm_integration.py`

```python
def test_project_calendar_assigned_and_resolved()
def test_project_calendar_enables_weekend_work()
def test_resource_calendar_overrides_working_hours()
def test_resource_exception_vacation_unavailable()
def test_resource_recurring_training_reduces_capacity()
def test_employee_backed_resource_inherits_employee_calendar()
def test_employee_vacation_blocks_pm_resource()
def test_employee_training_reduces_pm_resource_capacity()
def test_external_resource_uses_pm_resource_calendar()
def test_employee_backed_resource_not_duplicate_employee_rules()
def test_resource_allocation_over_capacity_flagged()
def test_time_entry_outside_calendar_blocked()
def test_project_schedule_uses_project_calendar_working_days()
def test_resource_capacity_derived_not_stored()
def test_capacity_percent_calculated_from_rules()
def test_utilization_percent_calculated_correctly()
def test_allocation_validator_respects_calendar()
```

---

## 12. Schema Bootstrap — "Migration" Strategy

No Alembic. Tables auto-created by SQLAlchemy `create_all`.

**Required actions:**
1. Import all new ORM files into `src/infra/persistence/orm/__init__.py` (or wherever `create_all` is triggered) so the tables are included.
2. In `PlatformServiceBundle.build_platform_service_bundle()` → call `CalendarService.ensure_global_calendar(org.id)` after org bootstrap.
3. On bootstrap, if `working_calendars` has a "default" record, create a `platform_calendars` entry of type GLOBAL with the same working days/hours and bridge the two.

**Safe evolution:**
- All new tables have no `NOT NULL` constraints that would break existing data.
- `platform_calendars` entries for GLOBAL type are created by `ensure_global_calendar()`.
- Existing `Site.default_calendar_id` field remains valid — it can coexist with `site_calendar_assignments`.

### Index priorities (add to ORM `__table_args__`):

```python
# platform_calendars
Index("idx_platform_calendars_org", "organization_id")
Index("idx_platform_calendars_scope", "scope_type", "scope_id")
UniqueConstraint("organization_id", "code", name="ux_platform_calendars_org_code")

# calendar_exceptions  
Index("idx_cal_exceptions_cal_date", "calendar_id", "exception_date")

# assignment tables
Index("idx_site_cal_assign_site", "site_id")
Index("idx_dept_cal_assign_dept", "department_id")
Index("idx_emp_cal_assign_emp", "employee_id")
Index("idx_proj_cal_assign_project", "project_id")
Index("idx_res_cal_assign_resource", "resource_id")
```

---

## 13. RepositoryBundle Updates

Add to `src/infra/composition/repositories.py`:

```python
from src.core.platform.infrastructure.persistence.repositories.enterprise_calendar import (
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyShiftPatternRepository,
    SqlAlchemyCalendarAssignmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)

# Add to RepositoryBundle dataclass:
platform_calendar_repo: SqlAlchemyPlatformCalendarRepository
calendar_working_rule_repo: SqlAlchemyCalendarWorkingRuleRepository
calendar_exception_repo: SqlAlchemyCalendarExceptionRepository
calendar_recurring_event_repo: SqlAlchemyCalendarRecurringEventRepository
shift_pattern_repo: SqlAlchemyShiftPatternRepository
calendar_assignment_repo: SqlAlchemyCalendarAssignmentRepository
project_calendar_assignment_repo: SqlAlchemyProjectCalendarAssignmentRepository
resource_calendar_assignment_repo: SqlAlchemyResourceCalendarAssignmentRepository
```

### PlatformServiceBundle Updates

Add to `src/infra/composition/platform_registry.py`:

```python
enterprise_calendar_service: CalendarService
working_rule_service: WorkingRuleService
calendar_exception_service: CalendarExceptionService
recurring_event_service: RecurringEventService
shift_pattern_service: ShiftPatternService
calendar_assignment_service: CalendarAssignmentService
enterprise_calendar_resolver: EnterpriseCalendarResolver
working_time_calculator: WorkingTimeCalculator
```

### ProjectManagementServiceBundle Updates

Add to `src/infra/composition/project_registry.py`:

```python
project_calendar_adapter: ProjectCalendarAdapter
resource_availability_service: ResourceAvailabilityService
resource_capacity_calculator: ResourceCapacityCalculator
```

---

## 14. Implementation Sequence (Phased Execution)

### Step 1 — ORM + Schema (no service logic yet)
1. Write `src/core/platform/infrastructure/persistence/orm/enterprise_calendar.py` (all new tables)
2. Write `src/core/modules/project_management/infrastructure/persistence/orm/calendar_assignment.py`
3. Update ORM imports so `create_all` picks up new tables
4. Run existing tests to confirm no table creation breakage

### Step 2 — Domain Models
1. Write `src/core/platform/calendar/domain/enterprise_calendar.py` (all dataclasses + enums)
2. Write `src/core/modules/project_management/domain/calendar/assignment.py`

### Step 3 — Repositories + Contracts
1. Extend `src/core/platform/calendar/contracts.py` with new ABCs
2. Write `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py`
3. Write `src/core/modules/project_management/infrastructure/persistence/repositories/calendar_assignment.py`
4. Update `RepositoryBundle`

### Step 4 — Platform Services
1. Write `enterprise_calendar_service.py`
2. Write `working_rule_service.py`
3. Write `calendar_exception_service.py`
4. Write `recurring_event_service.py`
5. Write `shift_pattern_service.py`
6. Write `calendar_assignment_service.py`
7. Write `enterprise_calendar_resolver.py`
8. Write `working_time_calculator.py`
9. Update `PlatformServiceBundle` + `build_platform_service_bundle()`

### Step 5 — PM Adapters
1. Write `project_calendar_adapter.py`
2. Write `resource_availability_service.py`
3. Write `resource_capacity_calculator.py`
4. Update `ProjectManagementServiceBundle`

### Step 6 — Desktop APIs
1. Write `src/api/desktop/platform/enterprise_calendar.py` + DTOs
2. Write `src/api/desktop/project_management/resource_availability.py`
3. Register in `runtime.py`

### Step 7 — Tests
1. Write platform tests (`test_enterprise_calendar_foundation.py`)
2. Write PM integration tests (`test_enterprise_calendar_pm_integration.py`)
3. Run all existing tests to confirm no regressions

### Step 8 — Platform QML
1. Extend `AdminCalendarDetailPage.qml` (new sections)
2. Add Calendar section to `AdminSiteDetailPage.qml`
3. Add Calendar section to `AdminDepartmentDetailPage.qml`
4. Add Calendar section to `AdminEmployeeDetailPage.qml`
5. Write new dialogs (CalendarEditorDialog, CalendarWorkingRuleDialog, CalendarExceptionDialog, CalendarRecurringEventDialog, ShiftPatternEditorDialog, CalendarAssignmentDialog)
6. Extend `AdminDialogHost.qml`

### Step 9 — PM QML
1. Write `ResourceCalendarSection.qml`
2. Extend `ResourcesDetailPanel.qml`
3. Write `SchedulingCalendarSection.qml`

### Step 10 — Controller/Presenter wiring
1. Extend platform admin controller for all new calendar API calls
2. Extend PM resources controller for resource calendar API calls
3. Extend PM scheduling controller for calendar context API calls

---

## 15. Risks and Remaining Work

| Risk | Mitigation |
|---|---|
| PM `work_calendar_engine.py` and `work_calendar_service.py` are PM-local duplicates | Refactor PM scheduling engine to use `ProjectCalendarAdapter` in Step 5; existing tests guard against regression |
| `Resource.capacity_percent` is currently static and may be used in existing queries/UI | Audit all reads of `capacity_percent`; mark as presentational; derive from `ResourceCapacityCalculator` on read; do not break existing serialization |
| No Alembic = manual schema management | Document all new tables in this plan; ORM `create_all` is the migration; `ensure_global_calendar()` bootstraps data |
| RRULE validation requires `python-recurrence` or `dateutil.rrule` | Confirm `python-dateutil` is installed; use `dateutil.rrule.rrulestr()` for validation and expansion |
| QML controller calls must follow `execute_desktop_operation` pattern | All new API methods use the existing `execute_desktop_operation` wrapper |
| Calendar assignment queries must be scoped to `organization_id` | All assignment lookups join through `platform_calendars.organization_id` for tenant isolation |
| Site `default_calendar_id` bridge | Old FK stays; new `site_calendar_assignments` is the enterprise source; resolver checks assignment table first, falls back to `default_calendar_id` |

---

## 16. Summary of Files to Create / Modify

### New Files (create)

**Backend — Platform:**
- `src/core/platform/calendar/domain/enterprise_calendar.py`
- `src/core/platform/infrastructure/persistence/orm/enterprise_calendar.py`
- `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py`
- `src/core/platform/calendar/application/enterprise_calendar_service.py`
- `src/core/platform/calendar/application/working_rule_service.py`
- `src/core/platform/calendar/application/calendar_exception_service.py`
- `src/core/platform/calendar/application/recurring_event_service.py`
- `src/core/platform/calendar/application/shift_pattern_service.py`
- `src/core/platform/calendar/application/calendar_assignment_service.py`
- `src/core/platform/calendar/application/enterprise_calendar_resolver.py`
- `src/core/platform/calendar/application/working_time_calculator.py`
- `src/api/desktop/platform/enterprise_calendar.py`
- `src/api/desktop/platform/models/enterprise_calendar.py`

**Backend — PM:**
- `src/core/modules/project_management/domain/calendar/__init__.py`
- `src/core/modules/project_management/domain/calendar/assignment.py`
- `src/core/modules/project_management/infrastructure/persistence/orm/calendar_assignment.py`
- `src/core/modules/project_management/infrastructure/persistence/repositories/calendar_assignment.py`
- `src/core/modules/project_management/application/scheduling/project_calendar_adapter.py`
- `src/core/modules/project_management/application/resources/resource_availability_service.py`
- `src/core/modules/project_management/application/resources/resource_capacity_calculator.py`
- `src/api/desktop/project_management/resource_availability.py`

**Tests:**
- `src/tests/platform/test_enterprise_calendar_foundation.py`
- `src/tests/project_management/test_enterprise_calendar_pm_integration.py`

**QML:**
- `src/ui_qml/platform/qml/Platform/Dialogs/CalendarEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/CalendarWorkingRuleDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/CalendarExceptionDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/CalendarRecurringEventDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/ShiftPatternEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/CalendarAssignmentDialog.qml`
- `src/ui_qml/modules/project_management/qml/resources/sections/ResourceCalendarSection.qml`
- `src/ui_qml/modules/project_management/qml/scheduling/sections/SchedulingCalendarSection.qml`

### Modified Files (extend)

**Backend:**
- `src/core/platform/calendar/contracts.py` — add new ABCs
- `src/infra/composition/repositories.py` — add 8 new repos
- `src/infra/composition/platform_registry.py` — add 8 new services to bundle
- `src/infra/composition/project_registry.py` — add 3 new PM services

**QML — Platform:**
- `src/ui_qml/platform/qml/workspaces/admin/detail/AdminCalendarDetailPage.qml` — extend sections
- `src/ui_qml/platform/qml/workspaces/admin/detail/AdminSiteDetailPage.qml` — add Calendar section
- `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDepartmentDetailPage.qml` — add Calendar section
- `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEmployeeDetailPage.qml` — add Calendar section
- `src/ui_qml/platform/qml/workspaces/admin/dialogs/AdminDialogHost.qml` — add new dialog cases

**QML — PM:**
- `src/ui_qml/modules/project_management/qml/resources/panels/ResourcesDetailPanel.qml` — add Calendar section

---

*Plan authored 2026-06-02. Execution starts with Step 1 (ORM + Schema). All steps are incremental and backward-compatible.*
