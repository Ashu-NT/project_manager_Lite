# Calendar System Audit — Findings & Recommendations

Date: 2026-08-01 (original investigation); updated 2026-10-06 with a second,
Backbone Hardening pass — see "2026-10-06 Backbone Hardening Audit"
immediately below, which is the current ground truth. The 2026-08-01
material (Resolution Status table + original investigation) is kept below
it for history: the engine it describes is the same one; the 2026-10-06
pass verifies what's still true, finds what's newly open, and adds a
future-readiness (PM scheduling) section the original pass didn't cover.

Status: no code has been changed as a result of the 2026-10-06 pass yet —
it is an investigation-only report, pending review. Do not treat any
"ADD NOW" item below as done until it has its own resolution entry.

---

## 2026-10-06 Backbone Hardening Audit (current)

Scope: same investigation-first process already used for Organization,
Site, Department, Employee, and Party. Five parallel audits (domain/ORM/
migrations, application/resolver, API/presenter/QML/permissions, seed/deps/
tests/PM-coupling, future-readiness) plus a re-verification of the
2026-08-01 findings below. TECHASH is pre-release; schema/domain changes are
justified over preserving weak legacy behavior. **Central Calendar QML
modernization has not started and should not until this report is
reviewed.**

Headline: this is not a blank-slate calendar. The 2026-08-01 pass already
built a genuinely sophisticated engine (working hours, holidays/exceptions
with partial-day impact, RRULE recurring events, shift-pattern rotation,
a bulk date-range resolver) and fixed real bugs (cross-tenant assignment
validation, a dead QML action path, the PM scheduling stub, shift-pattern
wiring). This pass verifies that work is intact and finds what's still open.

### A. Current Calendar domain model

One real engine, not a template:

| Entity | What it holds |
|---|---|
| `PlatformCalendar` | Header: `id, organization_id, tenant_id(ORM only), code, name, calendar_type, timezone="UTC", description, base_calendar_id, scope_type, scope_id, locale, is_default, is_active, effective_from/to, priority, version, created/updated_by/at` |
| `CalendarWorkingRule` | Per-weekday template: `weekday(0-6), is_working_day, start_time, end_time, break_start_time, break_end_time, break_minutes, hours_override, shift_code, effective_from/to, priority`. `compute_hours()` derives real hours. |
| `CalendarException` | One model covers holidays and 11 other exception types (SHUTDOWN, VACATION, SICK_LEAVE, TRAINING, MEETING, NON_WORKING, EXTRA_WORKING, REDUCED_HOURS, OVERTIME, MAINTENANCE_WINDOW, SITE_CLOSED) with `impact_type` (UNAVAILABLE/REDUCED_CAPACITY/EXTRA_CAPACITY/WORKING/INFORMATION_ONLY), optional `start_time/end_time/hours_override` for partial-day impact, and a built-in `approval_status` (PENDING/APPROVED/REJECTED) workflow nothing else currently drives. `exception_date` is a bare `date` (correct — avoids timezone-shift misclassification). |
| `CalendarRecurringEvent` | RFC5545 `RRULE`-based recurring impact (via `python-dateutil`, a real, already-used dependency — not a shim). |
| `ShiftPattern` / `ShiftPatternDay` | Full rotation model (STANDARD/DAY/NIGHT/TWO_SHIFT/THREE_SHIFT/ROTATING/FOUR_ON_FOUR_OFF/CUSTOM), `rotation_cycle_days`, `anchor_date`. Now actually consulted by the resolver (wired in during the 2026-08-01 pass — was previously dead CRUD). |
| `SiteCalendarAssignment` / `DepartmentCalendarAssignment` / `EmployeeCalendarAssignment` | Minimal join rows: `{target}_id, calendar_id, effective_from/to, is_default, priority`. No `organization_id`/`tenant_id` column on any of these. |
| `ProjectCalendarAssignment` / `ResourceCalendarAssignment` | Same shape, live in PM (FK to PM's own tables), `calendar_id` FKs back to `platform_calendars` — correct, intentional layering, not duplication. |

**Answer to "what does Calendar mean today"**: already category D — a general
scheduling/calendar engine (working week + hours + breaks, holidays,
arbitrary exceptions with partial-day hours, recurring events, shift
rotations). Broader than the Organization→Site→Department→Employee fallback
use case this pass was scoped around — clearly built with PM capacity
scheduling already in mind.

### B. Calendar ownership / organization scoping

- Every `PlatformCalendar` is organization-scoped: `organization_id` is a
  non-null FK (`CASCADE`), `UniqueConstraint(organization_id, code)`.
  `tenant_id` is a nullable FK (`RESTRICT`). No cross-organization sharing
  exists or is intended.
- **"Global Calendar" is not global.** It's an ordinary per-organization row
  (`id=f"global-{org_id[:8]}"`, `code="GLOBAL"`, `calendar_type=GLOBAL`) that
  merely applies org-wide (vs. Site/Department/Employee-scoped) — "global"
  describes scope *level*, not cross-tenant sharing. Confirms the name-vs-
  source split proposed below is required: **Effective Calendar: "Global
  Calendar" (name) / Source: "Inherited from Organization" (source)** —
  never conflate the two.

### C. Organization default semantics

- `ensure_global_calendar()` creates one per org, idempotent (returns
  existing if present, backfills working rules if missing).
- Hardcoded at bootstrap: Mon–Fri, 08:00 start, 8-hour duration, 60-min
  break, **timezone literal `"UTC"`** (not derived from the Organization's
  own `timezone_name`).
- Possible correctness bug: end time computed as `08:00 + 8h = 16:00`, with
  the 60-min break stored as metadata but not subtracted from the window —
  verify whether the intended default is "8h ending 16:00" or "8h work + 1h
  break ending 17:00" before relying on it for capacity math.
- Zero holidays seeded by default — explicit, not silent.
- Uniqueness enforced functionally via `(organization_id, code)` + the
  idempotent service check, not a dedicated DB constraint — equivalent in
  practice.
- **Priority A: deletion/deactivation of the org's own default/GLOBAL
  calendar is not actually guarded.** `delete_calendar()` only blocks when
  `count_active_assignments_for_calendar() > 0` — the default calendar is
  the *fallback*, not an assignment, so it typically has zero rows in the
  assignment tables and is not protected by this check, even though
  deleting it breaks every entity that falls back to it. Deactivation has
  the same silent blast-radius problem (drops out of the resolver chain
  with no warning of how many entities are affected).

### D. Site override semantics

- Optional, correctly falls back to Organization when absent.
- **Priority A: no duplicate-assignment protection** (no DB unique
  constraint on `site_id`, no repository-level replace-existing check) —
  contrast with `CalendarWorkingRule`, which has `UniqueConstraint(calendar_id, weekday)`.
- Cross-organization assignment is blocked procedurally at the service
  layer (`_ensure_calendar_in_scope`/`_ensure_site_in_scope`) — fixed in the
  2026-08-01 pass, confirmed still in place. Not schema-enforced (no org
  column on the assignment table). **Priority B** (works today, fragile
  long-term).
- **UI label inconsistency confirmed**: the Site calendar-summary presenter
  uses generic `"override"`/`"inherited"` wording, never naming the source
  entity — unlike Department/Employee (see Y).

### E. Department override semantics

- Confirmed correct: the resolver's Department branch has no dependency on
  `site_id` — an organization-level Department (no site) correctly resolves
  Department → Organization without crashing.
- Same duplicate-assignment/schema-cross-org gaps as Site.
- The Department calendar-summary presenter independently reimplements the
  fallback chain via sequential API round-trips rather than delegating to
  the canonical resolver (see G).

### F. Employee override semantics

- Confirmed correct for all four documented cases (site-bound department;
  org-level department + explicit employee site; org-level department, no
  site; explicit employee override) — the resolver is case-blind by design
  and no bug was found in its own logic; correctness for any given case
  depends on the caller passing the right ids (not independently stress-
  tested here).
- Same duplicate-assignment/schema-cross-org gaps as Site/Department.
- The Employee summary presenter also reimplements the chain independently.
- **Priority A**: assigning an Employee's calendar override requires only
  `task.manage` — no `employee.manage` check, no calendar-specific
  permission. Anyone with PM task-management rights can silently change any
  employee's calendar.

### G. Effective Calendar resolution algorithm

- One real canonical resolver exists for calculations:
  `EnterpriseCalendarResolver` + `WorkingTimeCalculator`. Chain:
  `GLOBAL → SITE → DEPARTMENT → EMPLOYEE (if worker_type ∈ {EMPLOYEE, None}) → PROJECT → RESOURCE (if worker_type == EXTERNAL)`.
  Working rules: innermost calendar with a rule for that weekday wins
  outright. Exceptions/recurring events: collected from every calendar in
  the chain, applied in priority order (`UNAVAILABLE` short-circuits;
  `REDUCED_CAPACITY`/`EXTRA_CAPACITY` accumulate; `WORKING` overrides hours;
  `INFORMATION_ONLY` is cosmetic).
- **Priority A: the UI's "effective calendar" display does not go through
  this resolver.** `src/ui_qml/platform/controllers/calendars/context.py`
  independently reimplements the Employee→Department→Site→Organization
  fallback three separate times (once each for Site/Department/Employee
  summaries), via sequential list/get calls, never calling
  `EnterpriseCalendarResolver`. What the UI shows and what the engine
  actually uses for capacity math can disagree.
- **Specific bug**: `calendar_assignment_context()`'s displayed "assigned
  calendar" is `assignments[0] if assignments else None` — a raw, unfiltered
  first-item pick — instead of the date-filtered `get_*_assignment(id, at_date=...)`
  the resolver itself uses. A future-dated or expired assignment sorting
  first would display the wrong calendar.
- Resolver already has a bulk-range method, `resolve_range()` (see AA).

### H. Working-week model

Not day-only. `CalendarWorkingRule` is per-weekday with `start_time`,
`end_time`, `break_start_time`, `break_end_time`, `break_minutes`, optional
`hours_override`, optional `shift_code` (resolved against a
`ShiftPattern`/`ShiftPatternDay` rotation). `effective_from/to` and
`priority` allow multiple time-bounded rules per weekday. Overnight/multi-
shift-per-day validation was not independently confirmed either way —
verify directly before UI work.

### I. Working-hours model

Already hours-capable, not day-only. Real start/end/break/hours_override
exist and are already consumed by `WorkingTimeCalculator.compute_day()` to
produce `base_hours/available_hours/remaining_hours/capacity_percent/utilization_percent/status`.

### J. Holiday model

Not a separate model — holidays are `CalendarException` with
`exception_type=HOLIDAY`, `impact_type=UNAVAILABLE`. Date-only (correct),
org-owned, manually configured (no country-based auto-population).

### K. Exception/special-day model

Already fully covers cases like "Christmas Eve 08:00–12:00" and "Saturday
stock count 09:00–14:00" via `CalendarException`'s `start_time`/`end_time`/
`hours_override`/`impact_type` — no new modeling needed. The dormant
`approval_status` workflow (PENDING/APPROVED/REJECTED) needs a product
decision: wire it to a real approval UI later, or document it as currently
a no-op gate.

### L. Timezone semantics

- `timezone` is a real, explicit, stored field per calendar (default
  `"UTC"`, overridable) — consistent with the "store UTC, convert per
  client" principle.
- But the engine performs zero timezone conversion itself — no
  `ZoneInfo`/`astimezone` usage anywhere in the resolver/calculator/shim.
  Every entry point takes a plain `date`; localizing "today"/"now" to the
  calendar's own timezone is entirely the caller's unenforced
  responsibility.
- **Confirmed violation**: PM's `calendar_cache.py:188` computes "today" via
  naive `date.today()` (server-local clock) for its own cache-freshness
  check. **Priority B** (contained to caching, not core calculation
  correctness).
- Zero DST-transition test coverage anywhere.
- Recommendation: document "caller must localize first" as an explicit
  contract; fix the one known violation; add a `business_today(calendar)`/
  `localize_today` helper on the engine itself so callers stop reimplementing
  this; add DST-boundary regression tests.

### M. Lifecycle/delete semantics

- `is_active: bool` — simple 2-state, not an enum; no need for a richer
  lifecycle just for symmetry with Employee/Party.
- Inactive calendar: excluded from the resolver chain (falls through
  silently), cannot be newly assigned, presumably still historically
  readable.
- **Priority A, same root cause as C**: deletion is guarded only by
  assignment count; the org's own default/GLOBAL calendar isn't an
  "assignment" of anything, so it isn't protected and can likely be deleted
  today.

### N. Assignment integrity

| Check | Status |
|---|---|
| Tenant/org match | Procedural only (service-layer ambient-context checks), not schema-enforced. **Priority B.** |
| Target entity exists | FK-level only. |
| Calendar exists + active | Enforced (`_require_calendar`). |
| Calendar compatible org | Enforced procedurally (same as tenant/org match). |
| Only one override per target | **Not enforced anywhere** — no DB constraint, no repo-level dedupe. **Priority A** (contrast with `CalendarWorkingRule`'s own unique constraint — the pattern already exists, just wasn't applied here). |
| Concurrency/transaction behavior | Not independently verified; low-risk follow-up. |

### O. Assignment APIs

Explicit, well-named commands already exist: `assign_site_calendar`/
`remove_site_assignment`, `assign_department_calendar`/
`remove_department_assignment`, `assign_employee_calendar`/
`remove_employee_assignment`, plus PM-delegated `assign_project_calendar`/
`assign_resource_calendar`. Good — matches the target pattern already.

**Boundary issue**: the Platform file `calendar_assignment_service.py`
directly imports PM's concrete domain classes (`ProjectCalendarAssignment`,
`ResourceCalendarAssignment`) to construct instances. The overall pattern
(two join tables in PM, `calendar_id` FK back to Platform, composition-root
wiring) is correct and intentional per the 2026-08-01 pass. The narrower
issue is the literal cross-module import of concrete domain classes inside
a Platform file — fixable without touching the overall design (accept
pre-constructed objects, or a thin PM-side factory callback). **Priority B.**

### P. Central Calendar workspace/read model

- Desktop API (`EnterpriseCalendarDesktopApi`, ~45 methods) is real and
  substantial, not a placeholder: calendar CRUD, working rules, exceptions,
  recurring events, shift patterns, all 5 assignment types,
  `resolve_calendar_context`, `calculate_working_days`, `get_source_chain`,
  `calculate_resource_capacity`.
- Two DTO vocabularies exist side by side: the rich `CalendarDto` family
  (real Platform workspace) and a simpler `WorkingCalendarSnapshotDto`
  family (PM's Scheduling API, rewired to real data in the 2026-08-01 pass
  rather than left as a hardcoded stub). Low priority to converge.
- **QML workspace is not modernized**: `CalendarsWorkspacePage.qml` uses the
  `AdminEntityWorkspace` shell but with no search, no pagination, and an
  Inspector still using the old generic `{"label":"Details"}/{"label":"Info"}`
  synthetic-row pattern already eliminated elsewhere.
- **Bug**: the "Working Days" column is bound to `f"{code} | {timezone}"` —
  header doesn't match content. **Priority B.**
- `AdminCalendarDetailPage.qml` tabs today: Overview, Working Rules,
  Exceptions, Recurring Events, Assignments, Calculator, **Audit**. The
  Audit tab (a redirect) still exists despite the no-per-entity-Audit-tab
  convention already established for Party/Employee/Department.
- `isEnterpriseCalendar` naming leaks into QML state — part of the broader
  naming cleanup.

### Q. Pagination/search

None exists on the central Calendar controller — only full-list load.
Calendar cardinality per organization is inherently small, so this is lower
urgency than Party's case — defer full pagination infrastructure, keep
reads bounded/clean when the workspace is modernized.

### R. Permissions — the single most consequential finding

**There is no `calendar.read`/`calendar.manage` permission anywhere in the
system.** Every Calendar operation — CRUD, all 5 assignment types,
exceptions, recurring events, shift patterns, working rules, at both the
application-service layer and the QML layer — is gated exclusively by
`task.read`/`task.manage`, a Project-Management permission. Confirmed
identically at both layers. Backwards for a capability meant to be a
Platform backbone independent of any one module, and a real production
authorization risk: anyone with PM task-management rights can read, edit,
or reassign any organization's calendars and all Site/Department/Employee
overrides. **Priority A — the single highest-impact fix in this audit.**

### S. Activity

Zero `record_activity` calls exist anywhere in any Calendar application
service — confirmed by checking imports, not sampling. Calendar create/
update/delete, every assignment/removal, every exception/recurring-event/
shift-pattern/working-rule mutation currently writes no Activity at all.

### T. Audit

Centralized Audit (`Platform → Control → Audit`) is presumably intact as
the general mechanism, but Calendar Detail still has its own "Audit" tab
(redirect, not a duplicate store) — should be removed per the convention
already established for Party/Employee/Department.

### U. Existing calculations

Already real and working: `is_working_day`, `next_working_day`,
`add_working_days`, `working_days_between`, `working_day_dates_between`
(via `GlobalCalendarShim` and PM's `BoundProjectCalendar`, both delegating
to the one resolver). **`resolve_range()` already exists** — a full bulk
date-range projection, efficient (one chain build + bulk per-calendar
fetch, not per-day queries), with perf guardrails. This is effectively the
exact API future UI work would need, already built.

### V. PM/current module consumers

| Consumer | Classification |
|---|---|
| `ProjectCalendarAdapter`/`BoundProjectCalendar` | Clean — pure pass-through, zero data ownership |
| `ProjectCalendarAssignment`/`ResourceCalendarAssignment` | Legitimate join tables in PM (FK constraint forces this), `calendar_id` FK to Platform |
| `CalendarProtocol` | Clean structural interface, PM-only consumer |
| `calendar_assignment_service.py` importing PM domain types | Boundary violation, **Priority B** (see O) |
| PM's old `CalendarEvent`/`CalendarService` (agenda feature) | Already deleted in the 2026-08-01 pass — confirmed resolved |
| `calendar_cache.py` naive `date.today()` | Timezone-correctness gap, **Priority B**, contained |
| PM `Resource.employee_id`/`worker_type` | Clean, working, intentional contract already co-designed with the resolver |

### W. Future HR/Procurement/Accounting boundary

No evidence of scope creep into clock-in/out, absence requests, vacation
balances, overtime, payroll, or shift rostering. The dormant exception-
approval workflow is the only HR-adjacent surface, and it's generic, not
wired to any actual HR process. Boundary is currently clean.

### X. Shared assignment UI/component architecture

`AdminCalendarAssignmentSection.qml` is genuinely shared — directly
instantiated by Site/Department/Employee's own calendar sections, not
duplicated three times. The gap is one layer underneath: the data each
consumer feeds into that shared component comes from three independently
reimplemented, label-inconsistent summary builders (see G, Y).

### Y. Summary/read DTO consistency

Key *names* are consistent across the three summary builders (`hasCalendar`,
`calendarId`, `calendarName`, `source`, `workingWeekLabel`, `timeZone`,
`holidaySetLabel`). Source-label *wording* is not: Site says generic
`"override"`/`"inherited"`; Department says `"Department override"`/
`"Inherited from Site"`/`"Inherited from Organization"`; Employee adds
`"Employee override"`/`"Inherited from Department"`. Converge all three
onto one canonical vocabulary computed once via the resolver's own
`source_chain`, not independently per entity.

### Z. Correctness and scalability gaps

See Priority table below.

### AA. Visual Calendar / date-range projection readiness

Already exists. `EnterpriseCalendarResolver.resolve_range(*, site_id, department_id, employee_id, project_id, resource_id, worker_type, start, end)`
returns `list[ResolvedCalendarContext]` — builds the chain once, bulk-
fetches rules/exceptions/recurring events per calendar with in-process
caching, computes each day in pure Python (zero DB calls in the loop).
Suspicious-range guard (>5000 days or >20 years) and perf logging
(>250ms/range). Richer than a hypothesized contract would need — already
carries hours, capacity%, utilization%, status, source chain, per-day
exceptions. Nothing to build; needs exposing through a Desktop API method +
presenter when UI work begins (not confirmed whether the Desktop API
already exposes a range method directly — check before assuming a new
endpoint is needed).

### AB. Daily capacity calculation readiness

Already exists, not day-only. `CalendarWorkingRule`/`CalendarException`/
`WorkingTimeCalculator.compute_day()` already produce real hourly capacity
today — "8 available hours Monday / 4 on a special half-day / 0 on a
holiday" is answerable with the current model, not a future build.

### AC. Calendar assignment/usage projection

Already exists. `list_calendar_assignments(calendar_id)` returns sites/
departments/employees/projects/resources via 5 bounded queries — good
foundation for a future Assignments tab and pre-edit impact warnings, no
N+1.

### AD. Recommended shared calendar presentation contract

Does not exist yet; no consumer needs it today. When UI work begins, follow
the existing `ActivityItemViewModel` precedent (dataclass + `serialize_*`
helper + tone/icon mapping, in `src/ui_qml/shared/models/`) for a
`CalendarDayViewModel`/`CalendarEntryViewModel` — never inside the Calendar
domain. **Prepare contract only — do not build now.**

### AE. Future PM Resource Schedule integration contract

Already anticipated: `project_id`/`resource_id`/`worker_type` are already
first-class resolver inputs, correctly gated (EMPLOYEE and RESOURCE are
mutually exclusive branches of one slot). PM's `Resource` domain already
carries `employee_id`/`worker_type` fields clearly co-designed with this.
The boundary is already in place and working. Gap: the resolver's
`project_assignment_repo`/`resource_assignment_repo` constructor params are
typed as bare `Any` — no formal Platform-side `Protocol` contract exists
for them. Worth adding now (cheap, correctness-only, not a UI feature)
before more consumers accumulate against an untyped boundary.

### AF. Future Team Schedule / Workload integration

Same underlying contract as AE — Platform supplies availability/working-
time only; PM supplies assignment/task/project/progress. No additional
readiness gap found beyond AE's.

### AG. Future-readiness classification

| Capability | Status | Why |
|---|---|---|
| Date-range projection API | **ADD NOW** *(already built)* | `resolve_range()` exists, efficient, richer than hypothesized |
| Working-hours-per-day model | **ADD NOW** *(already built)* | `CalendarWorkingRule`/`CalendarException` already model real hours |
| Assignment/usage aggregate read | **ADD NOW** *(already built)* | `list_calendar_assignments()` exists, non-N+1 |
| Resource↔Employee link | **ADD NOW** *(already built)* | PM's `Resource.employee_id`/`worker_type` already present, already consumed |
| Typed contracts for project/resource assignment repos | **ADD NOW** | Currently untyped `Any` — cheap correctness fix |
| Shared calendar presentation DTO (QML-facing) | **PREPARE CONTRACT ONLY** | No consumer yet; follow `ActivityItemViewModel` precedent when UI work starts |
| Month/Week QML grid primitives | **DEFER** | Zero exist anywhere in the app; correctly scoped to the future UI pass |
| `GlobalCalendarShim` retirement | **DEFER** | Still load-bearing (4 real PM consumers); needs its own migration pass |

### Fields/concepts: KEEP / RENAME / REMOVE / ADD NOW / DEFER

**KEEP** — `PlatformCalendar` and its fields; `CalendarWorkingRule`,
`CalendarException`, `CalendarRecurringEvent`, `ShiftPattern`/
`ShiftPatternDay`; the GLOBAL→SITE→DEPARTMENT→EMPLOYEE/PROJECT-RESOURCE
chain; `AdminCalendarAssignmentSection.qml`; `EnterpriseCalendarResolver`/
`WorkingTimeCalculator`; pycountry and python-dateutil as currently used.

**RENAME** *(pending explicit decision — see note)* — `enterprise_calendar.py`
file names across every layer; `EnterpriseCalendarService`/
`EnterpriseCalendarResolver`/`EnterpriseCalendarDesktopApi` class names;
`isEnterpriseCalendar` QML state; the three summary builders' source-label
vocabulary; the "Working Days" column.

> **Open tension, needs an explicit decision before this item is executed**:
> the 2026-08-01 pass explicitly considered this and concluded the opposite
> — "rename the things that collide with the engine's name, keep the
> engine's own name (Enterprise Calendar) because it's accurate." The
> 2026-10-06 instruction was to drop "Enterprise"/"legacy" naming everywhere
> in favor of standard naming, consistent with Organization/Site/Department/
> Employee/Party. Recorded here so whoever executes the migration sequence
> below picks one deliberately rather than silently overriding the earlier
> decision.

**REMOVE** — `calendar_catalog_presenter.py`'s dead
`calendar_api=None  # removed — kept for signature compat during transition`
constructor parameter; the per-entity "Audit" tab on
`AdminCalendarDetailPage.qml`.

**ADD NOW** (Priority A — correctness) — `calendar.read`/`calendar.manage`
permissions, dual-checked with the target entity's own manage permission
for assignment mutations; duplicate-assignment prevention (DB constraint +
repo upsert-by-target) for Site/Department/Employee; explicit delete/
deactivate protection for the organization's own default/GLOBAL calendar;
unify the UI's effective-calendar display onto the real resolver and fix
the unfiltered-first-assignment display bug; fix PM's `calendar_cache.py`
naive `date.today()`; typed `Protocol` for the resolver's PM-facing repo
params; Activity recording for Calendar CRUD and assignment mutations
(dual-recorded: Calendar's own Activity for CRUD, target entity's Activity
for assignment changes — same shape as the Employee Documents precedent).

**DEFER** — full pagination/search for the central workspace;
`GlobalCalendarShim` retirement; shared calendar presentation DTO; Month/
Week QML grid primitives; PM Resource/Team Schedule UI; country-based
holiday auto-population (would need a new dependency, explicitly out of
scope); DST-transition test suite; wiring the dormant exception-approval
workflow.

### Priority

**A — correctness/integrity (fix before any QML modernization)**
1. No `calendar.read`/`calendar.manage` permission — everything gated by
   the wrong module's permission (`task.manage`).
2. Organization default/GLOBAL calendar is not actually protected from
   deletion/deactivation.
3. No duplicate-assignment prevention on any of the three override tables.
4. UI "effective calendar" display bypasses the real resolver (three
   independent reimplementations, one with a confirmed display bug).
5. Zero Activity coverage for any Calendar mutation.

**B — strong shared-platform foundation**
1. Cross-org assignment check is procedural only, not schema-enforced.
2. `calendar_assignment_service.py` imports PM's concrete domain types
   directly.
3. PM's `calendar_cache.py` timezone-correctness gap.
4. Source-label wording inconsistency across Site/Department/Employee
   summaries.
5. "Working Days" column content/label mismatch; per-entity Audit tab still
   present.
6. Hardcoded default-calendar seed values duplicated between the backfill
   migration and the service; bootstrap timezone hardcoded to UTC instead
   of the Organization's own timezone.
7. No typed contract for the resolver's PM-facing repo parameters.

**C — useful enhancement**
1. Remove the dead `calendar_api=None` shim parameter.
2. Converge the two parallel DTO vocabularies.
3. Add DST-transition and day-boundary regression tests.
4. A small `business_today(calendar)` helper on the engine.

**D — defer**
1. `GlobalCalendarShim` retirement.
2. Full pagination infrastructure.
3. Shared QML calendar-grid primitives / PM schedule UI.
4. Country-based holiday auto-population.
5. Exception approval-workflow activation.

### Recommended final Calendar architecture

One engine, one name (pending the rename decision). One resolution path for
both calculation and display — retire the three independently-reimplemented
UI summary builders in favor of the real resolver's `source_chain`,
translated once into a canonical label vocabulary. Calendar-specific
permissions, layered with target-entity permissions for assignment
mutations. Integrity constraints that match the model's own existing
precedent (`CalendarWorkingRule`'s unique constraint is the template).
Explicit default-calendar protection, independent of the generic
assignment-count delete guard. PM remains a pure consumer — fix the one
backwards import, leave everything else PM does today alone. Activity split
by ownership (Calendar CRUD → Calendar Activity; assignment changes → both
the target entity's Activity and Calendar's own).

### Recommended migration sequence

1. Add `calendar.read`/`calendar.manage` permissions; update every
   `require_permission`/`hasPermission` call site (service + QML) with
   dual-permission checks on assignment mutations.
2. Add duplicate-assignment DB constraints + repo-level upsert-by-target for
   Site/Department/Employee assignments.
3. Add explicit default/GLOBAL-calendar delete/deactivate protection.
4. Fix the UI summary builders to call the real resolver; fix the
   unfiltered-first-assignment display bug.
5. Add Activity recording (Calendar CRUD + assignment events, dual-recorded).
6. Fix PM's `calendar_cache.py` timezone bug; add `business_today()`; add
   DST regression tests.
7. Fix the backwards PM-domain import in `calendar_assignment_service.py`;
   add the typed `Protocol` for project/resource assignment repos.
8. (Pending the naming decision) Rename files/classes off "Enterprise,"
   clean up `isEnterpriseCalendar` and the dead shim parameter.
9. Only then: begin central Calendar QML modernization (pagination is
   low-priority; fix the mislabeled column and remove the Audit tab as part
   of that pass, not before).

### Proposed final central Calendar Detail tabs

Based on what the backend actually supports today:

- **Overview** — name, timezone, working-week summary, holiday/exception
  summary, assignment/usage counts (already computable).
- **Calendar** — month view using the already-existing `resolve_range()`
  projection; no new backend work needed to populate it, only new QML.
- **Assignments** — the existing `list_calendar_assignments()` read,
  already efficient, already real.
- **Activity** — once Activity recording is added (currently zero
  coverage).

No "Holidays" tab (already correctly merged into Exceptions in the
2026-08-01 pass), no "Events" tab (no independent event capability exists),
no Audit tab (remove the current one). Working Rules/Exceptions/Recurring
Events/Shift Patterns/Calculator editing likely belong as actions or
sub-panels within Overview/Calendar rather than separate top-level tabs,
but that's a UI-design call for when modernization actually begins.

---

## Resolution Status (2026-08-01)

| # | Finding | Outcome |
|---|---|---|
| §2.5 | `CalendarEvent`/PM `CalendarService` (dead agenda feature) | **Deleted** — domain class, service, ORM/mapper/repo split out of `cost_calendar.py`, composition wiring, tests, and a migration dropping `calendar_events`. |
| §2.6 | `cost_calendar.py` naming ghost | **Fixed** — `CalendarEvent` removed from the file entirely (see above), then the four `cost_calendar.py` files (contracts/orm/mappers/repositories) renamed to `cost.py` since only `CostItem`/`CostRepository` remained. |
| §2.7 | Scheduling desktop API calendar stub (hard-coded fake calendar) | **Wired for real** — `platform_calendar_api` now flows from the composition root's real `EnterpriseCalendarDesktopApi` into `ProjectManagementSchedulingDesktopApi`; `calendar_adapter_service.py` rewritten to translate real `list_calendars`/`get_calendar`/`list_working_rules`/`list_exceptions`/`save_working_rule`/`add_exception`/`delete_exception` calls; `calendar_id` threaded end-to-end from the QML dropdown through `workspace_builder.py` so switching calendars actually re-fetches; the three hard-coded "Default Calendar" literals (`calendar_builder.py`, `row_builders.py`) now read the real calendar name. Legacy `work_calendar_service` fallback path (used only when no platform API is wired, e.g. some unit tests) preserved unchanged. |
| §3 | Broken `updateCalendar`/`addCalendarHoliday`/`deleteCalendarHoliday` QML path | **Removed** — the three dead functions, their `@Slot` wrappers, the `WorkingCalendarEditorDialog.qml`/`WorkingCalendarHolidayDialog.qml` files, and the dead `isEnterpriseCalendar`-false routing branches deleted (they were unreachable in production since every calendar is enterprise-owned). The redundant "Holidays" tab in `AdminCalendarDetailPage.qml` — which duplicated the already-working "Exceptions" tab and was the only thing driving the broken actions — was removed rather than revived, since keeping two tabs for the same data would have reproduced the exact "two things doing the same job" confusion this audit is about. |
| §5 item 5 | `ShiftPattern`/`ShiftPatternDay` never consulted by resolution | **Wired in** — `ShiftPatternDay.compute_hours()` added; `ShiftPattern.anchor_date` added (domain/ORM/mapper/migration) as the rotation's day-0 reference; `EnterpriseCalendarResolver` now accepts an optional `shift_pattern_repo`, resolves the working rule's `shift_code` against a pattern, computes `(target_date - anchor_date).days % rotation_cycle_days`, and looks up the matching `ShiftPatternDay`, feeding it into `WorkingTimeCalculator.compute_day()` (both the single-day and bulk-range paths) where it fully overrides the weekday-based schedule for that day. Desktop API gained `set_shift_pattern_day`/`delete_shift_pattern_day` (day-level CRUD was previously missing entirely from the desktop API). |
| §5 item 6 | Retire `GlobalCalendarShim` | **Deferred**, as originally recommended — it is correct and load-bearing today; retiring it needs a separate audit of every PM consumer. |
| §5 item 7 | Update the superseded Ownership Plan doc | **Done** earlier in this engagement — its status line now points here. |
| §4 naming inventory | `PlatformCalendarController`/broken methods, dead comments (`WorkCalendarEngine` fallback comment, `CalendarResolver = None`) | Cleaned up as part of the QML fix above; the stale `scheduling_engine.py` comments were left as-is (out of scope — they reference an already-deleted class name in a comment only, no behavior change needed). |
| §6.3 | Architecture guardrail test for the platform/calendar → project_management boundary | **Added** — `test_platform_calendar_does_not_import_project_management_at_module_scope` in `src/tests/architecture/test_architecture_guardrails_legacy_orm.py`. |

Not done (explicitly out of scope for this pass, noted for a future one):
admin QML UI for picking/assigning shift patterns and editing their days
(the backend/resolver support and desktop API are complete; only the admin
UI editor is missing), and the §6.1/§6.2 process recommendations (glossary
doc, ADR for the split-table pattern) — a short ADR was added instead (see
`docs/architecture_decisions/`).

---

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
