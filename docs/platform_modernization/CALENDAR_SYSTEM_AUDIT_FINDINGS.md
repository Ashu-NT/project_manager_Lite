# Calendar System Audit — Findings & Recommendations

Date: 2026-08-01
Status: investigation complete, no code changes made as part of this document
Relationship to prior doc: this supersedes the discovery section of
`docs/platform_modernization/PLATFORM_CALENDAR_OWNERSHIP_MIGRATION_PLAN.md`
("the Ownership Plan"). That plan described moving a first-generation
`WorkingCalendar`/`Holiday`/`WorkCalendarEngine` model from PM into Platform.
That migration finished and was then **entirely superseded** by a second,
much larger rewrite (the "Enterprise Calendar" system described below) that
the Ownership Plan document was never updated to reflect. Its own target
tables (`WorkingCalendar`, `Holiday`) were dropped by migration
`o8p9q0r1s2t3_drop_legacy_working_calendars`. Treat the Ownership Plan as
historical background only — the ground truth is this document.

## TL;DR

There is **one real calendar engine** in this codebase
(`src/core/platform/calendar/`, the "Enterprise Calendar" system). Everything
else that has "calendar" in its name is one of:

1. an **adapter** that hands the engine's data to another module in the
   shape that module's older code expected (`GlobalCalendarShim`,
   `ProjectCalendarAdapter` / `BoundProjectCalendar`),
2. a **join table** recording which engine calendar a PM project/resource
   uses (`ProjectCalendarAssignment`, `ResourceCalendarAssignment`),
3. an **unrelated feature** that only shares the English word "calendar"
   (PM's `CalendarEvent` agenda entries; Maintenance's
   `MaintenanceCalendarFrequencyUnit` recurrence cadence), or
4. **dead or half-migrated code** left over from two successive ownership
   migrations (first `WorkCalendarEngine`→Platform, then the flat
   working-calendar model → the current hierarchical Enterprise Calendar
   model).

The team's confusion is earned: the word "calendar" currently names at least
**eight structurally different things** across two modules, one of which
(`api/desktop/scheduling` calendar DTOs) is a stub that always returns a
hard-coded Mon–Fri/8h calendar regardless of what's actually configured, and
one QML action path (`update_calendar`/`add_calendar_holiday`/
`delete_calendar_holiday` in `admin_calendar_actions.py`) calls controller
methods that **do not exist** and will throw `AttributeError` if triggered
from the UI today.

---

## 1. The one real system: Platform Enterprise Calendar

Location: `src/core/platform/calendar/**`, `src/core/platform/infrastructure/persistence/{orm,mappers,repositories}/enterprise_calendar.py`, `src/api/desktop/platform/enterprise_calendar.py`, `src/ui_qml/platform/controllers/admin/*calendar*`.

This is the single source of truth for working days, hours, holidays, and
shift patterns, scoped per tenant/organization. Everything else in the
codebase either consumes it directly or through an adapter.

### 1.1 Domain model

| Type | Purpose |
|---|---|
| `PlatformCalendar` | A calendar header: `code`, `name`, `calendar_type`, `timezone`, `is_default`, `priority`, `version`. |
| `CalendarType` enum | `GLOBAL`, `SITE`, `DEPARTMENT`, `EMPLOYEE`, `PROJECT`, `RESOURCE` — a label only; actual scoping comes from assignment tables (§1.4), not this enum. |
| `CalendarWorkingRule` | Per-weekday template (start/end time, break minutes, `hours_override`). |
| `CalendarException` | One-off deviation on a date (`ExceptionType`: HOLIDAY, SHUTDOWN, VACATION, TRAINING, OVERTIME, …; `ImpactType`: UNAVAILABLE, REDUCED_CAPACITY, EXTRA_CAPACITY, WORKING, INFORMATION_ONLY). |
| `CalendarRecurringEvent` | Recurring block defined by an RFC5545 `RRULE` string (meetings, maintenance windows). |
| `ShiftPattern` / `ShiftPatternDay` | Org-level rotation templates. **Fully CRUD-wired end to end (domain → ORM → API → admin UI) but never consulted by the resolver** — a scaffolded, dangling feature. |
| `SiteCalendarAssignment` / `DepartmentCalendarAssignment` / `EmployeeCalendarAssignment` | Join rows: which calendar applies to a site/department/employee, with `effective_from/to`, `priority`, `is_default`. |

Tables created by `n7o8p9q0r1s2_add_platform_enterprise_calendars`:
`platform_calendars`, `calendar_working_rules`, `calendar_exceptions`,
`calendar_recurring_events`, `shift_patterns`, `shift_pattern_days`,
`site_calendar_assignments`, `department_calendar_assignments`,
`employee_calendar_assignments`, `project_calendar_assignments`,
`resource_calendar_assignments`.

The last two are the PM-owned assignment tables described in §2 — they were
added in the *same* migration as the rest, i.e. schema-wise they were always
designed as siblings, not an afterthought.

### 1.2 Resolution algorithm — `EnterpriseCalendarResolver` + `WorkingTimeCalculator`

Fixed precedence chain (`_build_chain`):

```
GLOBAL → SITE → DEPARTMENT → EMPLOYEE (only if worker_type ∈ {EMPLOYEE, None})
                            → PROJECT → RESOURCE (only if worker_type == EXTERNAL)
```

EMPLOYEE and RESOURCE are mutually exclusive branches of the same slot — a
worker is either an internal employee or an external resource, never both.

- **Working rules** (weekday templates): the *innermost* calendar in the
  chain that has a rule for that weekday wins outright — full replacement,
  not a merge.
- **Exceptions and recurring events**: collected from *every* calendar in
  the chain, then applied in priority order. The first `UNAVAILABLE`
  exception by priority short-circuits the rest of the day's evaluation.
  `REDUCED_CAPACITY`/`EXTRA_CAPACITY` accumulate; `WORKING` overrides
  start/end time; `INFORMATION_ONLY` has no numeric effect.
- `resolve_range()` bulk-fetches once per range and caches per-calendar
  rules/exceptions/recurring events in-process, with logged perf
  guardrails (>50ms/day, >250ms/range).

### 1.3 Assignment — `CalendarAssignmentService`

One service, five assignment kinds: site, department, employee, project,
resource. Site/department/employee use platform-owned repos; **project and
resource delegate to two repositories owned by the PM module** (see §2) —
this is a deliberate, necessary layering choice, not an accident, because
the FK anchor (`projects`/`resources`) is PM-owned and Platform must not
depend on PM's schema.

### 1.4 Tenant scoping

Enforced at every layer: service (`TenantContextService.require_active_organization_id`),
repository (`TenantScopedRepositorySupport`, every query filtered by
`tenant_id`/`organization_id`, joined transitively through the parent
calendar for child tables), and ORM (`tenant_id`/`organization_id` columns
on `PlatformCalendarORM` with `RESTRICT`/`CASCADE` FKs respectively).

*(This is also the layer where this audit found and fixed a real cross-tenant
data-integrity gap earlier in this session: `assign_site/department/employee_calendar`
were not validating that the target site/department/employee actually
belonged to the active tenant/org before writing the assignment row. Fixed
in `enterprise_calendar.py`'s repository layer; see git history for that
commit.)*

### 1.5 History baked into the schema

Migration `o8p9q0r1s2t3_drop_legacy_working_calendars` records the mapping
from the *first-generation* model this system replaced:

```
working_calendars  → platform_calendars (type=GLOBAL) + calendar_working_rules
holidays           → calendar_exceptions (type=HOLIDAY, impact=UNAVAILABLE)
```

`EnterpriseCalendarService.ensure_global_calendar()` performs the one-time
data migration from the legacy shape before the drop migration removes the
old tables.

---

## 2. The PM-side pieces (not a second engine)

### 2.1 `ProjectCalendarAssignment` / `ResourceCalendarAssignment` — legitimate join tables

`src/core/modules/project_management/domain/calendar/assignment.py` +
their ORM (`project_calendar_assignments`, `resource_calendar_assignments`).
Both FK `calendar_id → platform_calendars.id`. They exist in PM (not
Platform) purely because their *other* FK (`project_id`/`resource_id`)
points at PM-owned tables, and Platform code must never depend on PM's
schema. `EnterpriseCalendarResolver` and `CalendarAssignmentService` accept
these two repos as `Any`-typed constructor parameters for exactly this
reason — the composition root is the only place allowed to know both
modules concretely. **This is correct, intentional architecture, not
confusion** — but the fact that "calendar assignment" data lives in two
different modules' persistence trees, wired together only at the
composition root, is exactly the kind of thing that needs a one-paragraph
comment or ADR note so new engineers don't assume it's a duplicate.

### 2.2 `ProjectCalendarAdapter` / `BoundProjectCalendar` — the real bridge

`src/core/modules/project_management/application/scheduling/calendars/project_calendar_adapter.py`.
Pure pass-through: wraps `EnterpriseCalendarResolver` +
`CalendarAssignmentService`, exposes `is_working_day` /
`add_working_days` / `working_days_between` / `next_working_day`. Owns
**zero** calendar data itself. This is what `SchedulingEngine` binds to per
project (`bind_for_project`) for all CPM forward/backward-pass date math.
Its own docstring: *"PM scheduling uses this instead of calling
WorkCalendarEngine directly. All calendar logic stays in Platform — PM only
consumes."* This is the correct end state of the migration, actively
tested, not legacy.

### 2.3 `GlobalCalendarShim` — the fallback bridge

`src/core/platform/calendar/application/global_calendar_shim.py`. Lives in
the *platform* module but exists purely to serve PM: it implements the same
`WorkCalendarEngine`-shaped interface (via `CalendarProtocol`) but only ever
resolves the GLOBAL level (no site/department/project scope). Used as the
base/fallback calendar for `SchedulingEngine`, and directly by
`DashboardService`, `BaselineService`, `PortfolioResourcePoolService`,
`ReportingService` — services that need *a* calendar without a specific
project context. This is the same kind of compatibility shim the RBAC
hardening effort earlier in this engagement fully retired
(`RBAC-TRANSITION-ONLY` code) — except this one has **not** been retired
yet and is still load-bearing. It is a reasonable candidate for a future,
smaller follow-up once every consumer is confirmed to only need
project-scoped resolution.

### 2.4 `CalendarProtocol` — the PM-side common interface

`src/core/platform/calendar/application/calendar_protocol.py`. A 4-method
structural `Protocol` implemented by both adapters above. Used extensively
(30+ call sites) but **only inside PM** — it's what lets PM's
scheduling/CPM/leveling/reporting/dashboard code hold "a calendar" without
caring whether it's the global shim or a project-bound adapter. Not dead;
not a platform-level unification (that unification already happens one
level down, inside `EnterpriseCalendarResolver`).

### 2.5 `CalendarEvent` / PM's `CalendarService` — unrelated, and apparently dead

`src/core/modules/project_management/domain/scheduling/calendar.py`. An
agenda/event record (`title`, `start_date`, `end_date`, optional
`project_id`/`task_id`) — closer to "a calendar view of tasks" than to a
working-day engine. Built in the composition root
(`ProjectManagementServiceBundle.calendar_service`) but **grep finds zero
consumers** in `ui_qml/` or `api/desktop_runtime/` — no desktop API method,
no view model. Only exercised by its own domain-validation test. This looks
abandoned; flagged for the team to decide (revive with real UI wiring, or
delete).

### 2.6 `cost_calendar.py` (contracts/orm/mappers) — a naming ghost

Three files named `cost_calendar.py` that bundle two **unrelated** things
under one filename: `CostItem`/`CostRepository` (project cost-tracking line
items — budget/PO/invoice, nothing to do with calendars) and
`CalendarEvent`/`CalendarEventRepository` (§2.5). **There is no `CostCalendar`
domain class anywhere.** Anyone searching the codebase for "cost calendar"
as a concept will find this filename and reasonably assume one exists. It
doesn't. This is pure file-organization debt, not a real second calendar
concept.

### 2.7 `api/desktop/scheduling/{models,commands,services,builders}/calendar*.py` — a stub mid-migration

`calendar_adapter_service.py`'s docstring says "Platform calendar
integration helpers," but it does **not** import anything from
`src.core.platform.calendar`. In the real composition wiring
(`desktop_api_builder.py`), `platform_calendar_api` is hard-coded to `None`,
so this whole layer always falls back to `_DefaultCalendar` — a
hand-written Mon–Fri/8h/no-holidays stand-in. Write endpoints are explicit
no-ops with comments in the source itself:

```python
def update_calendar(self, command): 
    # Calendar editing moved to Platform Admin → Calendar Management.
    # Stub kept for QML compatibility during transition.
    return self.get_calendar_snapshot()
```

This means **the desktop Scheduling workspace's "Calendar" tab currently
shows a hard-coded fake calendar**, not the tenant's real configured
calendar, and edits made there silently do nothing. This is the strongest
concrete evidence in the whole audit of an unfinished decommission — the
code says so itself.

### 2.8 Maintenance module — no relationship at all

`MaintenanceCalendarFrequencyUnit` (`DAILY`/`WEEKLY`/`MONTHLY`/…) is a
recurrence-cadence enum for preventive-maintenance due dates. Zero imports
of anything under `src.core.platform.calendar`. It shares the word
"calendar" and nothing else — no working days, no holidays, no hours.

---

## 3. Concrete broken code found

`src/ui_qml/platform/controllers/admin/admin_calendar_actions.py` defines
`update_calendar()`, `add_calendar_holiday()`, `delete_calendar_holiday()`,
which call `controller._calendar_controller.updateCalendar(...)` /
`.addCalendarHoliday(...)` / `.deleteCalendarHoliday(...)`. But
`PlatformCalendarController` (`calendar_controller.py`) only defines
`refresh()`, `calculateCalendarWorkingDays()`, `formatCalculationResult()` —
**it has no such methods.** These three actions are still wired to real
`@Slot`s on `AdminConsoleController` and real QML call sites
(`AdminDialogHost.qml`, `AdminCalendarDetailPage.qml`). Triggering them from
the running UI today would raise `AttributeError`. This is a leftover from
deleting the old `PlatformCalendarDesktopApi` without finishing the cleanup
of the QML action layer that called it — the replacement methods
(`update_enterprise_calendar`, `add_calendar_exception`,
`delete_calendar_exception`) already exist right next to the broken ones in
the same file and do work.

---

## 4. Why the word "calendar" causes confusion — a naming inventory

| Name | Module | What it actually is |
|---|---|---|
| `PlatformCalendar` | Platform | The real calendar engine's header entity |
| `CalendarType` | Platform | Enum label on `PlatformCalendar` |
| `CalendarProtocol` | Platform (consumed by PM) | Structural interface for "a working-day source" |
| `GlobalCalendarShim` | Platform | GLOBAL-only compat adapter, PM-facing |
| `ProjectCalendarAdapter` / `BoundProjectCalendar` | PM | Project-scoped compat adapter over the same engine |
| `ProjectCalendarAssignment` / `ResourceCalendarAssignment` | PM | Join rows: PM entity → Platform calendar |
| `CalendarEvent` / `CalendarService` | PM | Unrelated agenda/event feature, appears dead |
| `cost_calendar.py` (file) | PM | Misnomer — bundles `CostItem` + `CalendarEvent`, no calendar concept inside |
| `calendar_adapter_service.py` (Scheduling desktop API) | PM | Legacy stub, hard-coded fake data, not wired to Platform despite the name |
| `MaintenanceCalendarFrequencyUnit` | Maintenance | Unrelated recurrence-cadence enum |
| `repositories.calendar_repo` vs `repositories.platform_calendar_repo` | composition root | Two same-shaped names pointing at unrelated tables (PM agenda events vs. real platform calendar) |
| `calendar_service` vs `enterprise_calendar_service` | composition root / app_container services dict | Two same-shaped keys, PM agenda service vs. real platform calendar service |

Additional rot: a comment in `scheduling_engine.py` still says
`# fall back to default WorkCalendarEngine` even though that class was
deleted; a leftover `CalendarResolver = None  # type: ignore[assignment]`
name kept only for an `isinstance` check, per its own comment
("CalendarResolver removed — enterprise CalendarResolver handles hierarchy
resolution").

---

## 5. Recommended target architecture

The underlying design is actually sound — one engine, clean adapters at
module boundaries, correct tenant scoping. The problem is **naming and
unfinished cleanup**, not structure. Recommendations, roughly in priority
order:

1. **Rename for disambiguation, don't restructure.** The engine
   (`PlatformCalendar` / Enterprise Calendar) should keep its name — it's
   accurate. Rename the things that collide with it:
   - PM's `CalendarEvent`/`CalendarService` → `ProjectAgendaEvent` /
     `ProjectAgendaService` (or delete if truly unused — see item 3).
   - `cost_calendar.py` files → split into `cost.py` (CostItem) and
     `agenda_event.py` (CalendarEvent), or delete the latter with the
     feature.
   - `calendar_adapter_service.py` → rename to reflect what it is today
     (`legacy_scheduling_calendar_stub.py`) until it's either finished or
     removed, so its name stops implying a working platform integration.

2. **Finish or remove the Scheduling desktop API calendar stub (§2.7).**
   Either wire `platform_calendar_api` for real (point the Scheduling
   workspace's Calendar tab at `EnterpriseCalendarDesktopApi`) or remove the
   tab/DTOs entirely and document in the QML that calendar management lives
   in Platform Admin only. Shipping a UI element that silently shows fake
   data is worse than removing it.

3. **Decide the fate of `CalendarEvent`/PM `CalendarService` (§2.5).** If
   genuinely unused, delete it (domain, ORM, mapper, repo, composition
   wiring, tests) the same way the RBAC-transition dead code was removed
   earlier in this engagement. If it's an intended-but-unbuilt feature,
   say so in one comment at the top of the domain file so it stops reading
   as an abandoned calendar system.

4. **Fix the broken QML action path (§3).** Either implement
   `updateCalendar`/`addCalendarHoliday`/`deleteCalendarHoliday` on
   `PlatformCalendarController` for real, or delete the dead action
   functions and their QML call sites and route those UI actions through
   the working `update_enterprise_calendar`/`add_calendar_exception`/
   `delete_calendar_exception` path instead.

5. **Wire or remove `ShiftPattern`/`ShiftPatternDay` resolution.** Right
   now it's a fully-built CRUD feature that the resolver never reads. Either
   teach `EnterpriseCalendarResolver`/`WorkingTimeCalculator` to consult
   shift patterns, or remove the feature until there's a concrete use case —
   a half-wired feature is exactly the kind of thing that makes a new
   engineer assume "there must be two systems."

6. **Retire `GlobalCalendarShim` once safe.** Same shape of cleanup as the
   already-completed RBAC-transition removal: once every PM consumer
   (`DashboardService`, `BaselineService`, `PortfolioResourcePoolService`,
   `ReportingService`, `SchedulingEngine`'s fallback) is confirmed to only
   need project-scoped resolution or can call the resolver directly with
   `project_id=None`, delete the shim and the now-unneeded
   `CalendarProtocol` abstraction it exists to support. Not urgent — flagged
   for a future pass, not this one.

7. **Update `PLATFORM_CALENDAR_OWNERSHIP_MIGRATION_PLAN.md`.** Either mark
   it explicitly superseded/archived (pointing at this document) or delete
   it — as written today it documents a schema (`WorkingCalendar`,
   `Holiday`) that no longer exists, which is itself a source of confusion
   for anyone who finds it while searching docs for "calendar."

---

## 6. Recommendations for team clarity (process, not code)

1. **One glossary entry per name, in one place.** Add a short "Calendar
   Concepts" section to `docs/ARCHITECTURE.md` (or a new
   `docs/platform_modernization/CALENDAR_GLOSSARY.md`) listing every name
   from the table in §4 with a one-line definition and its owning module.
   New engineers should be able to grep one file instead of reverse-engineering
   the resolver.
2. **An ADR for the two-tables-one-service split (§2.1).** The
   project/resource-assignment-lives-in-PM-but-is-served-by-one-platform-service
   pattern is correct but non-obvious. A short ADR ("why calendar assignment
   data is split across two modules but exposed as one API") prevents future
   contributors from either duplicating it or wrongly trying to "fix" it by
   merging the tables.
3. **A standing lint/architecture-guardrail test** (this repo already has
   the pattern — see `src/tests/architecture/test_service_architecture.py`)
   asserting that nothing under `src/core/platform/calendar/` imports from
   `project_management` at module scope, to keep the `Any`-typed boundary
   in §2.1/§1.3 honest as the codebase evolves.
4. **Treat "stub kept for QML compatibility during transition" comments as
   tracked debt, not documentation.** Several found in this audit (§2.7)
   have been sitting since at least the Ownership Plan's Slice 2. Recommend
   a lightweight convention: any comment of that shape gets a matching entry
   in `docs/REMAINING_WORK.md` with a date, so "temporary" scaffolding is
   visible somewhere other than a code comment nobody re-reads.
5. **When a migration/rewrite fully replaces an earlier plan doc** (as the
   Enterprise Calendar rewrite did to the Ownership Plan), close the loop:
   mark the old doc `Status: superseded by <new doc>` at the top instead of
   leaving it looking current. Cheap to do, saves the next investigation
   from re-discovering the same history from scratch.

---

## 7. Suggested one-paragraph team summary

*"There is one calendar system (`src/core/platform/calendar/`, 'Enterprise
Calendar') that owns all working-day/holiday/hours logic for the whole app,
scoped per tenant. Project Management does not have its own calendar engine
— it only has two small adapters (`GlobalCalendarShim`,
`ProjectCalendarAdapter`) that let PM's scheduling code ask the one real
engine for working-day answers without PM having to import Platform types
directly everywhere, plus two join tables recording which platform calendar
a given project or resource uses. Everything else named 'calendar' in PM
(agenda events, the Scheduling tab's calendar stub, cost_calendar.py) is
either an unrelated feature or leftover scaffolding from two earlier
migrations and should not be confused with the real engine."*
