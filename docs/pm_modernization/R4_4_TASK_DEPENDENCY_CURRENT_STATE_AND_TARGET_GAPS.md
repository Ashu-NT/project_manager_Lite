# PRE-R4.4 — Task→Task Dependency Vertical-Slice Audit

Status: read-only audit. No code was changed to produce this document. No commits were made.

**Since superseded, in part:** the follow-up PRE-R4.4 ENTERPRISE FOUNDATION
UPGRADE implementation pass acted on this audit's findings. See
[`R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md`](./R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md)
for what was built in response to each finding below — this document
remains the accurate *before* snapshot and is not itself updated in place.

Branch audited: `refactor/safe-start` (HEAD `7272de6d` at audit time).

Method: seven independent code-reading passes, each required to cite `file:line`
and quote the actual code for every claim, with no assumption of textbook PM
semantics. Findings below are cross-checked; where two independent passes
reached the same conclusion by different routes, that is noted, because it is
the strongest evidence available short of executing the code live.

---

## 1. Executive Summary

The system supports a **real, non-trivial four-type dependency model** (FS/SS/FF/SF)
with **calendar-aware lag**, application-layer **cycle/duplicate/self/cross-project
validation**, and a live CPM engine that **genuinely treats dependencies as the
primary driver of computed dates** (not inert graph metadata). That is a
materially stronger foundation than a "just stores edges" system.

It is also, in its current state, **not safe to build R4.4 leveling directly on
top of** without first closing several concrete defects this audit proves with
code citations:

1. **`DependencyType` has four members (FS, FF, SS, SF) and all four are wired
   through every scheduling code path** — an earlier working assumption that SF
   was absent was wrong (§4). The real problems are semantic, not coverage:
   - `lag_days` means a *different number of working days* depending on type:
     FS effectively gets `lag + 1` working days of separation; SS/FF/SF get
     `lag − 1`. SS/FF/SF cannot distinguish `lag=0` from `lag=1` (§5).
   - The CPM **backward pass is off by one working day for SS/FF/SF** (it is
     the correct inverse only for FS), which **inflates total float and can
     hide the true critical path** (§11, §15 in the outline / §11 below).
   - A predecessor with **mixed successor types** (e.g. one FS successor and
     one SS successor) has its SS/SF late-date constraints **silently
     discarded** in the backward pass (§11).
2. **Four separate, hand-duplicated implementations of the same date math**
   exist (`SchedulingEngine`, `CPMCalculator`, `TaskDependencyDiagnosticsMixin`,
   and a dead `DependencyResolver`). They do not all agree, and the
   `DependencyResolver` class — the one that documents lead/negative-lag
   support most explicitly — has **zero production callers** (§11, §17).
3. **Hard scheduling constraints silently override dependency-driven dates**
   with no warning anywhere in the system, and the one validator meant to
   catch this (`ConstraintValidator`) checks the *already-overridden* output,
   so the check is structurally unable to fire (§12).
4. **Resource leveling shifts on any task that has a dependency are silently
   reverted by the very next schedule recalculation**, because CPM ignores
   `task.start_date` whenever the task has usable incoming dependencies. The
   user is told leveling succeeded; the persisted schedule says otherwise
   (§13).
5. **`update_dependency` (editing an existing dependency's type/lag) is fully
   wired to live QML but bypasses governance/approval entirely**, is
   **non-atomic** (commits before the schedule recalculation and activity log
   run), and its cycle-check branch is **dead code** because the duplicate
   check short-circuits first (§8, §16).
6. **No optimistic concurrency control exists on dependencies at all** — no
   version column, no version-checked update, no rowcount check on delete.
   Two concurrent edits silently overwrite each other; a concurrent double-delete
   reports success while deleting nothing (§16).
7. **Negative lag (lead) is accepted at every layer with zero validation**, is
   **completely untested**, and is non-monotonic for FS (`lag=-1` and `lag=-2`
   produce the identical date) (§5, §22).
8. In the UI, the Task Detail dependency table's column headed **"Lag" actually
   renders the linked task's raw UUID**, not the lag value; the real lag is
   buried inside the "Type" column instead (§19). Edit and Delete mutation
   errors are silently discarded by the QML layer — only Create surfaces
   errors in-dialog (§19).
9. There is **no Planning workspace** and **no dependency-line/arrow rendering
   anywhere in the app** (§20). The Scheduling workspace has a read-only
   dependency table (which gets the "Lag" column right, unlike Task Detail)
   but its `SchedulingWorkspaceController.createDependency/updateDependency/
   deleteDependency` methods are fully built and **never called by any QML** —
   an orphaned backend surface (§19–20).
10. Test coverage is strong for the "happy path" of each dependency type,
    cycle/duplicate/cross-project/self rejection, and tenant isolation. It is
    **entirely absent** for: negative lag, the update/edit flow (despite being
    live UI), multiple predecessors combining constraints, actual-date ×
    dependency interaction, and constraint × dependency interaction (§21–22).
11. **A pre-existing planning document (`docs/pm_modernization/README.md`)
    overstates completion**: it marks `DependencyResolver` and
    `ResourceLevelingEngine` "✅ added" as if they were the live implementation.
    Both are confirmed dead code with zero production callers (§25). This
    audit's evidence should supersede those claims for R4.4 planning purposes.

None of this requires "resource leveling migration" work to fix — items 1–9
above are dependency-semantics and QML-wiring defects that exist independently
of R4.4's leveling scope, and several of them (3, 4, 6) are exactly the kind of
foundation issue that would silently corrupt whatever leveling migration is
built on top of them if left unaddressed. §25–26 lay out a recommended
sequencing.

---

## 2. Dependency Domain Model

**File:** `src/core/modules/project_management/domain/tasks/task.py`, `class TaskDependency` (line 309).

### Complete field list — five fields, no more

```python
id: str
predecessor_task_id: str
successor_task_id: str
dependency_type: DependencyType = DependencyType.FINISH_TO_START
lag_days: int = 0
```
(`task.py:310-314`)

Explicitly **absent** (checked against the whole class body and against
`dependency_to_orm`/`dependency_from_orm`, `infrastructure/persistence/mappers/task.py:85-102`):
`project_id`, `version`, `created_at`, `updated_at`, `created_by`, `updated_by`,
`tenant_id`, `organization_id`, any lag-unit field, `lag_hours`. Project scope is
derived only at runtime by dereferencing the predecessor/successor tasks
(e.g. `application/tasks/commands/dependency.py:38,184,218,272`).

Contrast: sibling aggregates in the *same file* have a `version` field —
`Task.version` (`task.py:44`) and `TaskAssignment.version` (`task.py:191`).
`TaskDependency` is the only one of the three without it — a direct
structural cause of finding §16.

### Enum and default

`domain/enums.py:20-24`:
```python
class DependencyType(str, Enum):
    FINISH_TO_START = "FS"
    FINISH_TO_FINISH = "FF"
    START_TO_START = "SS"
    START_TO_FINISH = "SF"
```
Default is `FINISH_TO_START` at four separate layers: domain field
(`task.py:313`), `create` staticmethod (`task.py:352`), ORM column
(`orm/task.py:159`), and the QML→Python handler's literal `"FS"` fallback
(`presenters/tasks/dependency_command_handler.py:25,34`).

### Validation — the complete set (four validators, nothing more)

1. `_validate_predecessor_task_id` (`task.py:316-323`) — required, non-blank,
   `code="DEPENDENCY_PREDECESSOR_REQUIRED"`.
2. `_validate_successor_task_id` (`task.py:325-332`) — same,
   `code="DEPENDENCY_SUCCESSOR_REQUIRED"`.
3. `_validate_lag_days` (`task.py:334-337`) — entire body is
   `return int(value if value not in (None, "") else 0)`. **No sign check, no
   bound, no clamp.**
4. `_validate_not_self_dependency` (`task.py:339-346`, `@model_validator(mode="after")`) —
   raises `code="DEPENDENCY_SELF"` when `predecessor_task_id == successor_task_id`.

No validator exists for `dependency_type` beyond Pydantic's own enum coercion.

### Is lag negative (lead) allowed? — Yes, unrestricted, at every layer

Checked and found no clamp at: the domain validator above; the ORM column
(`lag_days: Mapped[int] = mapped_column(nullable=False, default=0)`,
`orm/task.py:162`, **no `CheckConstraint`**, and `TaskDependencyORM` has **no
`__table_args__` at all**); the baseline migration (`ef8d1d37eabf_baseline.py:171`,
plain `sa.Column('lag_days', sa.Integer(), nullable=False)`); the API command
DTO (`api/desktop/tasks/commands/dependency_commands.py:14,21`, plain
`lag_days: int = 0`, no `__post_init__`); the QML→Python handler
(`optional_int(payload, "lagDays") or 0`, `dependency_command_handler.py:26`,
and `optional_int` at `presenters/tasks/validation.py:17-27` rejects only
non-integers); and the QML widget itself (`TaskDependencyEditorDialog.qml:113`,
a plain `AppControls.TextField` with no validator, no `IntValidator`, no
bounds).

Empirically: `TaskDependency.create('a', 'b', lag_days=-99).lag_days` returns
`-99`.

### Lag units

**Working days, not calendar days.** Every consumer feeds `lag_days` into
`calendar.add_working_days(...)` (evidence in §7/§11). There is no unit field;
the unit is implicit in the field name and in which calendar function
consumes it, and is not configurable per dependency.

### Mutability

**Not frozen.** `@validated_dataclass` (`task.py:308`) resolves to
`pydantic_dataclass(target, config=ConfigDict(validate_assignment=True))`
(`src/core/platform/common/pydantic.py:10,20-23`) — no `frozen=True`.
Empirically: `d.__dataclass_params__.frozen` is `False`; `d.lag_days = -5`
succeeds; but `d.successor_task_id = <predecessor id>` is **blocked** by the
`DEPENDENCY_SELF` validator, because `validate_assignment=True` re-runs the
`mode="after"` model validator on every attribute assignment, not just
construction. There are no setter/update *methods* on the class — only the
four validators plus `create`. Codebase convention is replace-style:
`application/tasks/commands/dependency.py:282-286` builds a `candidate` via
`dataclasses.replace(dependency, ...)`.

### Notable secondary defects surfaced in this section

- **SF and SS produce identical dates for zero-duration/milestone tasks**
  (`dependency_diagnostics.py:381-382` vs `:385-386`; `cpm_calculator.py:135-137`
  vs `:141-143` — both branches compute `add_working_days(pred_es, lag_days)`).
  For duration-bearing tasks they differ correctly.
- **FS forward/backward lag asymmetry**: forward pass adds `lag_days + 2`
  working days for FS; backward pass subtracts `lag_days + 1`. Replicated
  identically across all four scheduling implementations (see §11).

---

## 3. ORM / Database Model

**ORM class:** `TaskDependencyORM`, `infrastructure/persistence/orm/task.py:143-172`.
Table: `task_dependencies`.

### Columns — exactly five, mirroring the domain

| Column | Definition | Line |
|---|---|---|
| `id` | `String, primary_key=True` | 146 |
| `predecessor_task_id` | `String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False` | 147-151 |
| `successor_task_id` | `String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False` | 152-156 |
| `dependency_type` | `SAEnum(DependencyType), default=FINISH_TO_START, nullable=False` | 157-161 |
| `lag_days` | `mapped_column(nullable=False, default=0)` | 162 |

**Enum storage format:** `SAEnum(DependencyType)` persists the enum *name*
(`FINISH_TO_START`), not its value (`"FS"`) — confirmed by the baseline
migration's literal column definition (`ef8d1d37eabf_baseline.py:170`:
`sa.Enum('FINISH_TO_START', 'FINISH_TO_FINISH', 'START_TO_START', 'START_TO_FINISH', name='dependencytype')`).
DTOs and QML transport `"FS"` etc. This name/value split matters for any raw-SQL
reporting or data-fix tooling.

### Foreign keys and ON DELETE

Both FKs target `tasks.id` with **`ondelete="CASCADE"`** — deleting a task
silently deletes all its dependency rows at the DB level. This is *weaker*
than the sibling `tasks` self-referential FK, which uses `ondelete="RESTRICT"`
(`orm/task.py:45-50`). The FK targets `tasks.id` alone, not the composite
`(project_id, id)` key that exists on `tasks` (`uq_tasks_project_id`,
`orm/task.py:51`) — **the database cannot prevent a cross-project dependency
row**; nothing in the schema ties predecessor and successor to the same
project.

### Unique constraints

`ux_task_dependencies_pair` — unique index on `(predecessor_task_id,
successor_task_id)` (`orm/task.py:167-172`; added by migration
`k4l5m6n7o8p9_add_pm_integrity_unique_constraints.py:53-58`).

- **Duplicate `A→B` rows:** rejected by this index.
- **Can `A-FS→B` and `A-SS→B` coexist?** **No.** The index covers only the
  ordered pair, not `dependency_type`. A given ordered task pair can carry at
  most one relationship type, system-wide — this is a real, undocumented
  product constraint, not an incidental gap. The application-layer duplicate
  check (`dependency_diagnostics.py:135-151`) agrees: it also matches only on
  the pair.
- **Can `A→B` and `B→A` coexist?** Yes at the DB level (different ordered
  pairs); blocked only by the application-layer cycle check (§10).

### Indexes

`idx_dep_predecessor` (on `predecessor_task_id`), `idx_dep_successor` (on
`successor_task_id`), plus the unique pair index above — all declared at
`orm/task.py:165-172`, all present since the baseline migration or the one
that added the unique constraint. Both `list_by_task`'s `OR` arms (§17) are
served by these.

### Project / tenant / org scoping columns — none

`task_dependencies` has no `project_id`, `tenant_id`, or `organization_id`
column. Scoping is achieved purely by joining through
`predecessor_task_id`/`successor_task_id` → `tasks` → `projects` at the
repository layer (§9, §15). This is corroborated by the architecture doc
(`docs/architecture/enterprise-platform-architecture.md:1539`): *"task_dependencies
| TaskDependencyORM | … INHERITED (via task→project) … Scope via
predecessor_task_id / successor_task_id → tasks → projects."*

### Version / optimistic-concurrency column — none

Not in the ORM, not in either migration, not in the domain model. Both
`TaskORM.version` (`orm/task.py:85`) and `TaskAssignmentORM.version`
(`orm/task.py:122`) exist in the very same file — the omission on
dependencies is an asymmetry, not a codebase-wide convention (see §16).

### Migration history — full chain to HEAD

Only two migrations touch `task_dependencies`:

1. `ef8d1d37eabf_baseline.py:166-177` — creates the table with all five
   columns, both CASCADE FKs, PK on `id`, and the two non-unique indexes. All
   four `dependency_type` enum values, **including `START_TO_FINISH`, are
   present from the baseline** — this is not a later addition.
2. `k4l5m6n7o8p9_add_pm_integrity_unique_constraints.py` (Create Date
   2026-05-31) — adds `ux_task_dependencies_pair`. Carries a pre-flight guard
   (`_assert_clean`, `:27-47`) that aborts if the DB already holds duplicate
   `(predecessor, successor)` pairs, directing the operator to
   `python -m tools.pm_data_integrity_check`; nothing is auto-deleted. Its own
   docstring: *"defense-in-depth uniqueness the application layer already
   enforces on new writes."*

Confirmed this is the current head state (no later migration alters the
table): the revision chain continues linearly through
`l5m6n7o8p9q0_add_project_code.py` → `m6n7o8p9q0r1_add_pm_entity_codes.py` → …
with no further reference to `task_dependencies`.

**Answer for the audit's explicit question:** Can `A FS→B` and `A SS→B` both
exist simultaneously? **No** — rejected by both the application-layer
duplicate check and the DB unique index, because uniqueness is scoped to the
ordered pair, not the pair-plus-type. This appears to be an intentional
design constraint (one relationship per ordered pair) but is not documented
anywhere as such — it is only observable by reading the validation code and
the index definition together.

---

## 4. FS / SS / FF / SF Support

**Correction carried through this whole audit:** an initial scoping pass
misread `domain/enums.py` (grepped with insufficient context and only saw 3 of
4 members). **All four `DependencyType` members exist and are fully wired
end-to-end.** Two independent research passes each caught and corrected this
before doing any further work, citing:

- Enum: `domain/enums.py:20-24` (all four members, quoted in §2).
- DB enum: `ef8d1d37eabf_baseline.py:170` (all four values, present since baseline).
- CPM forward pass: `application/scheduling/services/scheduling_engine.py:333-344` (milestone), `:380-404` (duration) — SF handled at lines 342, 397.
- CPM backward pass: `application/scheduling/cpm/passes.py:123-135` — SF handled at line 133.
- `CPMCalculator`: `application/scheduling/cpm/cpm_calculator.py:132-143,171-186` — SF at 141, 182.
- Dead `DependencyResolver`: `application/scheduling/dependencies/dependency_resolver.py:88-99,115-133` — SF at 97, 128.
- Dependency-impact preview: `application/tasks/queries/dependency_diagnostics.py:378-386,413-433` — SF at 385, 420.
- Three separate label maps, all rendering SF as `"Start -> Finish"`:
  `api/desktop/tasks/utils/dependency_utils.py:39`,
  `api/desktop/portfolio/utils/dependency_type_utils.py:10`,
  `api/desktop/scheduling/formatters/dependency_formatter.py:9`.
- API surface test: `src/tests/project_management/test_project_management_desktop_api_tasks_bulk_assign.py:127`
  — `assert [item.value for item in api.list_dependency_types()] == ["FS", "FF", "SS", "SF"]`.
- Behavioral test: `src/tests/project_management/test_technical_math_reporting_scheduling.py:38,63-68`
  exercises SF with `lag_days=3` and asserts computed dates.

### There is no enum-coverage mismatch, but there IS a semantics mismatch

Every CPM branch site (forward milestone, forward duration, backward, both
`CPMCalculator` variants, the dead `DependencyResolver`, and the diagnostics
preview — six sites total) is an explicit `if/elif` covering **all four**
values with **no `else`**. So: no unhandled enum value, no silent coercion of
SS/FF/SF into FS. **What actually differs across types is the correctness of
the lag arithmetic and of the backward-pass late-date derivation** — see §5
and §11. Framing this as "CPM only supports a subset of types" would be
**incorrect**; the correct framing is "CPM supports all four types, but three
of the four have a lag-unit bug and a backward-pass bug that FS does not
have."

### Unhandled/unknown `dependency_type` values

Because every branch site is a bare `if/elif` with **no `else`, no log, no
exception**, an unrecognized `dependency_type` value (a legacy DB string, or a
hypothetical 5th future enum member added without touching every one of the
six branch sites) makes that dependency **silently contribute nothing** to the
schedule — no error, no warning, no log line.
(`dependency_resolver.py:133` is the one site that is explicit about this:
`return None`.)

### Effective forward-pass formulas (derived, working days, lag = L)

| Type | Code (forward) | Effective ES/EF offset |
|---|---|---|
| FS | `add_working_days(EF_pred, L+2)` | `ES_succ = EF_pred + (L+1)` wd |
| SS | `add_working_days(ES_pred, L)` | `ES_succ = ES_pred + (L−1)` wd for `L≥1`; `= ES_pred` for `L∈{0,1}` |
| FF | `add_working_days(EF_pred, L)`, back-solved to ES | `EF_succ = EF_pred + (L−1)` wd for `L≥1`; `= EF_pred` for `L∈{0,1}` |
| SF | `add_working_days(ES_pred, L)`, back-solved to ES | `EF_succ = ES_pred + (L−1)` wd for `L≥1`; `= ES_pred` for `L∈{0,1}` |

(Quoted verbatim in §5/§11.)

---

## 5. Lag / Lead Semantics

### Unit: working days, confirmed, not calendar days

No `timedelta(days=lag)` exists anywhere in the dependency math; every lag
application goes through `calendar.add_working_days(...)`.

### The `add_working_days` contract (needed to read every formula in this doc)

Three behaviorally-identical implementations:
`application/scheduling/calendars/working_day_snapshot.py:31-48`,
`src/core/platform/application/time_management/calendar/capacity/global_calendar_shim.py:54-95`,
`application/scheduling/calendars/project_calendar_adapter.py:114-158`.
Quoting `working_day_snapshot.py:31-48`:

```python
def add_working_days(self, start: date, working_days: int) -> date:
    if working_days == 0:
        return start
    if working_days > 0:
        current = self.next_working_day(start, include_today=True)
        remaining = working_days - 1
        while remaining > 0:
            current += timedelta(days=1)
            if self.is_working_day(current):
                remaining -= 1
        return current
    current = start
    remaining = -working_days
    while remaining > 0:
        current -= timedelta(days=1)
        if self.is_working_day(current):
            remaining -= 1
    return current
```

Key, load-bearing asymmetry:
- `n == 0` → returns `start` **unchanged, even if `start` is a non-working day**.
- `n > 0` → **inclusive**: `start` counts as day 1 (if working). `n=1` ⇒ the
  first working day at-or-after `start`. `n=2` ⇒ the next working day strictly
  after that.
- `n < 0` → **exclusive**: `n=-1` ⇒ the first working day strictly before `start`.

### Finding: `lag_days` means a different number of working days per type

FS uses `lag_days + 2`; SS/FF/SF use bare `lag_days`. Because positive
counting is inclusive, **FS gets `lag+1` working days of separation while
SS/FF/SF get `lag−1`.** A "2-day lag" on an FS link is a 3-working-day gap; the
same "2-day lag" on an SS/FF/SF link is a 1-working-day gap.

### Finding: SS/FF/SF cannot distinguish `lag=0` from `lag=1`

`n=0` returns `start` unchanged; `n=1` returns the first working day
at-or-after `start`, which **is** `start` when `start` is already a working
day. So for SS/FF/SF, `lag_days=0` and `lag_days=1` produce the identical
computed date whenever the predecessor's relevant date already falls on a
working day (the common case).

### Finding: SS/FF/SF at `lag=0` can schedule onto a non-working day

Because `n==0` short-circuits *before* any working-day check, if the
predecessor's `ES`/`EF` itself falls on a non-working day (possible — root
tasks are anchored from raw `task.start_date` with no calendar snapping,
`scheduling_engine.py:366-368`), the SS/FF/SF successor is scheduled directly
onto that same non-working day. `lag=1` would have snapped it forward; `lag=0`
does not.

### Finding: negative lag (lead) is non-monotonic for FS

`add_working_days(EF, lag+2)`: `lag=0` → `n=2` → `EF+1` wd. `lag=-1` → `n=1` →
`EF` itself. `lag=-2` → `n=0` → the zero short-circuit → **also `EF`**. So
`lag=-1` and `lag=-2` are indistinguishable on an FS link; the lead only
starts moving again from `lag=-3` (`n=-1`, exclusive counting).

### Finding: negative lag is entirely unvalidated (repeated from §2, load-bearing here)

No sign check anywhere: domain validator, ORM column, migration, API DTO,
presenter coercion (`optional_int`), or QML `TextField`. Empirically
`lag_days=-99` persists and computes without error.

### Finding: `DependencyResolver`'s own docstring is aspirational, not descriptive

`application/scheduling/dependencies/dependency_resolver.py:25`: *"Supports all
four dependency types with lag (and negative lag = lead)."* This is the
**one file in the codebase that documents lead support most explicitly**, and
it is dead code with zero production callers (§11, §17) — so the closest thing
to a specification for negative-lag behavior is unreachable from the live
system.

### Test coverage for lag

Positive lag: well covered across all four types
(`test_technical_math_reporting_scheduling.py::test_cpm_dependency_type_math`).
**Negative lag/lead: zero tests anywhere in the repository** — confirmed by
grepping every occurrence of `lag_days=` and `lag` in `src/tests/`; every
value used across the entire suite is non-negative.

---

## 6. Date Semantics

### FS with `lag=0` is EXCLUSIVE

A predecessor finishing 2026-09-10 (Thursday) gives an FS successor with
`lag=0` an ES of **2026-09-11** (the next working day), not the same day.

Derivation: `add_working_days(pred_ef, dep.lag_days + 2)` with `lag=0` ⇒ `n=2`
⇒ day 1 = `pred_ef` itself, day 2 = the next working day strictly after
`pred_ef`. There is no literal `+1` or `+timedelta` anywhere in the FS path —
the "+1 day" effect is entirely an artifact of the `+2` constant interacting
with `add_working_days`'s inclusive-counting convention
(`scheduling_engine.py:382`: `add_working_days(pred_ef, dep.lag_days + 2)`).

**Pinned by test**, explicitly and with the exclusivity called out in a
comment: `src/tests/project_management/test_cpm_flow.py:40-41`:
```python
# B starts the next working day after A finishes (FS, lag 0).
assert infoB.earliest_start == wc.next_working_day(infoA.earliest_finish, include_today=False)
```
Also `test_technical_math_reporting_scheduling.py::test_cpm_dependency_type_math:44-49`.

### Task duration is inclusive

`eft = add_working_days(est, duration)` (`scheduling_engine.py:414`) — a
1-day task has `EF == ES`; a 5-day task spans `ES … ES+4` working days.
`end_date` is therefore the last working day of the task, not an
exclusive/half-open boundary.

### Test coverage caveat

For SS/FF/SF, the same test file's assertions (lines 51-68) simply restate the
implementation's own expression (e.g. `wc.add_working_days(p.earliest_start,
3)` for an SS lag of 3) rather than independently deriving the expected date —
so those assertions would **not** catch the §5 lag-unit and off-by-one
findings even though they nominally "cover" SS/FF/SF. Only the FS assertion
independently pins exclusivity via `next_working_day(..., include_today=False)`.

---

## 7. Calendar Interaction

**Lag is calendar-aware.** The authority is `EnterpriseCalendarResolver`,
reached through a project-scoped adapter — but **three different CPM entry
points reach the calendar through three different wrappers**, which can
disagree.

### Live path wiring

`SchedulingEngine.__init__` receives a base calendar and a
`ProjectCalendarAdapter` (`scheduling_engine.py:60-83`). Composition root
(`src/infra/composition/project_registry.py:271-283`):
```python
_pre_project_calendar_adapter = ProjectCalendarAdapter(
    resolver=platform_services.enterprise_calendar_resolver,
    assignment_service=platform_services.calendar_assignment_service,
)
scheduling_engine = SchedulingEngine(
    session, repositories.task_repo, repositories.dependency_repo,
    platform_services.global_calendar_shim,
    ..., project_calendar_adapter=_pre_project_calendar_adapter,
)
```
Per run, `scheduling_engine.py:122-134` binds the project calendar and freezes
it into an in-memory `WorkingDaySnapshotCalendar` via
`_build_working_day_snapshot` (`:196-227`), which pre-resolves a padded
horizon via `calendar.working_day_dates_between(...)`.

`ProjectCalendarAdapter.is_working_day` → `get_context` →
`self._resolver.resolve_calendar_context(project_id=..., target_date=...)`
(`project_calendar_adapter.py:73-83`); working-day-ness is `ctx.available_hours
> 0`. Fallback `GlobalCalendarShim` also wraps the same resolver
(`global_calendar_shim.py:34-42`) but degrades to a hardcoded Mon-Fri check on
any exception (`:42`).

**Confirmed shared authority with §45's capacity migration** (per
`docs/pm_modernization/qml_redesign/project_management_qml_target_ui_ux_design.md:3710`
"45. R4.3 — Calendar Capacity Authority Migration"): the resource-capacity
authority (`EnterpriseResourceAvailabilityService`, wired at
`project_registry.py:293-296`) is constructed from the **same**
`platform_services.enterprise_calendar_resolver` instance, just wrapped
differently. §45's own doc text explicitly excludes CPM from that migration
(lines 3790-3794): *"Explicitly not touched this pass: resource leveling
(...) and CPM — both noted as an explicit R4.4 backlog item."*

### Finding: three CPM entry points use three different calendar wrappers

- `SchedulingEngine` (live recalculation): project-scoped
  `WorkingDaySnapshotCalendar` over `EnterpriseCalendarResolver`. ✓
- `TaskDependencyDiagnosticsMixin` (the add/update-dependency **impact
  preview** shown to the user before saving): uses `self._work_calendar_engine`
  throughout (`dependency_diagnostics.py:336,344,380-386,404,414-433`) — a
  *different* calendar object injected at `project_registry.py:306`, **not**
  the project adapter.
- `ScheduleChangeImpactService` (forecasting): a plain injected calendar with
  no project adapter (`forecasting/schedule_change_impact_service.py:88`).

**Consequence:** the preview a user sees before confirming a dependency
change can compute different dates than what actually gets persisted.

### Other calendar findings

- `ProjectCalendarAdapter._get_site_id_for_project` is a stub returning `None`
  (`project_calendar_adapter.py:70-71`) — the site tier of the
  org→site→department calendar chain is never supplied from PM.
- Calendar binding failures are silently swallowed:
  `scheduling_engine.py:133-134` — bare `except Exception: pass`, falling
  back to the global calendar with no signal to the caller.
- `add_working_days` horizon exhaustion only `logger.warning`s and returns a
  wrong date rather than raising (`project_calendar_adapter.py:129-138`,
  `global_calendar_shim.py:69-77`).

---

## 8. Create / Update / Delete Flows

Composition: `TaskDependencyMixin` is composed onto `TaskService`
(`application/tasks/service.py:90`), alongside `TaskDependencyDiagnosticsMixin`
(`:89`). Repository: `SqlAlchemyDependencyRepository`
(`infrastructure/persistence/repositories/tasks/task.py:388`). A second entry
point exists — the Scheduling workspace reaches the *same* `TaskService`
methods via `api/desktop/scheduling/api.py:230,240,251` — so every finding
below applies to both surfaces, even though (per §19) no Scheduling QML
actually calls them.

### CREATE — full chain, all wired

| # | Hop | Evidence |
|---|---|---|
| 1 | QML toolbar → `createRequested()` | `TasksDependenciesSection.qml:75-83` |
| 2 | Panel re-emit | `TasksDetailPanel.qml:300` |
| 3 | Dialog host opens editor | `TasksWorkspacePage.qml:472` → `TasksDialogHost.qml:138-143` |
| 4 | Dialog submits payload | `TaskDependencyEditorDialog.qml:36,52-72` |
| 5 | Host → controller slot | `TasksDialogHost.qml:318-322` → `tasks_workspace_controller.py:629-631` |
| 6 | Facade → dependency controller | `task_mutation_facade.py:72-73` → `pm_dependency_controller.py:82-91` |
| 7 | Presenter → command handler → DTO | `tasks_workspace_presenter.py:375-376` → `dependency_command_handler.py:12-28` |
| 8 | Desktop API resolves direction, coerces types | `api/desktop/tasks/api.py:653-688` |
| 9 | Application command — the real gate | `application/tasks/commands/dependency.py:48-125` |
| 10 | Apply — domain construct, repo write, schedule sync, activity, commit, event | `dependency.py:127-167` |
| 11 | Domain construction (validators fire) | `TaskDependency.create(...)`, `task.py:348-360` |
| 12 | Repository insert | `repositories/tasks/task.py:424-427` |
| 13 | DB insert | `TaskDependencyORM`, `orm/task.py:143-172` |

**Gates:** permission (`task.manage`, governance-conditional —
`dependency.py:63-83`; governance is **off by default**,
`src/core/platform/domain/approval/policy.py:15` reads `PM_GOVERNANCE_MODE`
defaulting to `"off"`); project-scope check on the **predecessor's** project
only (`dependency.py:78-83` — see §15 finding 4b); full diagnostics validation
(self/existence/cross-project/duplicate/cycle,
`dependency_diagnostics.py:73-176`, mapped to exceptions at `dependency.py:95-99`);
leaf-task-only guard (`_require_leaf_task`, `dependency.py:61-62` →
`hierarchy_support.py:160-165`, `code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"`).

**Transaction:** correctly atomic — repo add → schedule sync (`commit=False`) →
activity record (`commit=False`) → one `session.commit()`
(`dependency.py:139-158`), rollback on exception.

**Schedule recalculation:** yes — creating a dependency **always** triggers a
full CPM run (`dependency.py:141` → `schedule_sync.py:9-20` →
`SchedulingEngine.recalculate_project_schedule`), in the same transaction.
Silent no-op if `_scheduling_engine` is `None` (`schedule_sync.py:17-19`).

**Domain event:** `domain_events.tasks_changed.emit(predecessor.project_id)`
post-commit only (`dependency.py:166`).

**Governance-apply path gap:** `_apply_dependency_add_decision`
(`dependency.py:127-167`, called from the approval-approved path at
`project_registry.py:722-730`) contains **no permission check, no
project-scope check, and no re-run of diagnostics** — verified by full read.
If the world changed between the original request and a later approval (a
task moved project, became a summary parent, or a conflicting edge appeared),
the apply is unvalidated. Cross-*tenant* is still blocked at the repository
layer, but cross-project and cycle rules are not re-asserted (TOCTOU).

### UPDATE — exists, is fully wired to QML, and is the weakest of the three flows

Contrary to the mixin's own docstring (`dependency.py:25`: *"update has no
governed path (dead, unwired)"* — the "dead, unwired" half is **stale and
incorrect**), `update_dependency` (`dependency.py:259-326`) is reachable end
to end from a live edit affordance in `TasksDependenciesSection.qml` (inline
`EntityDialog`, `:108-208`) through `TasksDetailPanel.qml:305` →
`TasksWorkspacePage.qml:476-480` → `updateDependency(payload)` →
`pm_dependency_controller.py:93-102` → `dependency_command_handler.py:30-42` →
`api.py:690-701` → `dependency.py:259-326`.

Scope: **`dependency_type` and `lag_days` only** — there is no backend path to
change `predecessor_task_id`/`successor_task_id`; re-pointing an edge requires
delete-and-recreate.

Confirmed defects, all found by tracing the live chain, not by assumption:

- **No governance/approval gate.** `add_dependency`/`remove_dependency` both
  consult `is_governance_required(...)`; `update_dependency` has **no**
  `is_governance_required` call and no `_apply_*_decision` split (verified by
  full read of lines 259-326). `DEFAULT_GOVERNED_ACTIONS`
  (`policy.py:6-11`) has no `dependency.update` entry to enable this even by
  configuration. With `PM_GOVERNANCE_MODE=required`, a non-admin with
  `task.manage` cannot add/remove an edge without approval but **can freely
  retype/relag any existing edge**, which shifts the project schedule via the
  same-severity recalculation the governance policy exists to gate.
- **Non-atomic.** `dependency.py:302-323`: `repo.update()` → **`session.commit()`
  at line 304** → *then* schedule sync (`commit=True`, a **second**
  transaction) → *then* activity record. The `except: rollback()` at 321-323
  cannot undo anything after line 304 — a failure in CPM recalculation or
  activity logging leaves a **committed dependency change with a stale
  project schedule and no audit record**. Contrast the correct
  all-`commit=False`-then-one-commit ordering in both `add` (`:141-158`) and
  `remove` (`:219-242`).
- **Cycle check is dead code on this path.** `update_dependency` re-runs
  diagnostics on the *existing* (already-in-graph) pair (`:288-289`), so
  `dependency_diagnostics.py:135-151` returns `DEPENDENCY_DUPLICATE` and
  **returns before reaching the cycle check at `:156`**. Line 294 then
  explicitly whitelists `DEPENDENCY_DUPLICATE`. Net effect: `update_dependency`
  runs **no graph validation at all**; `dependency.py:298-299`'s
  `DEPENDENCY_CYCLE` branch can never fire. Not exploitable today (type/lag
  changes can't add an edge), but this leaves no safety net if a future
  version allows re-pointing endpoints through this method.
- **Omits the leaf-task guard** that `add_dependency` performs
  (`_require_leaf_task`, `dependency.py:61-62`) — verified absent from
  lines 259-326.

### DELETE — full chain, atomic, with a real confirmation dialog

Confirmation dialog present and correctly danger-styled:
`TasksDialogHost.qml:463-484` (`confirmLabel: "Remove Dependency"`,
`confirmDanger: true`). Chain: confirm → `deleteDependencyRequested(id)`
(`TasksWorkspacePage.qml:177-181`) → `deleteDependency` slot
(`tasks_workspace_controller.py:637-639`) → `pm_dependency_controller.py:104-113`
→ `dependency_command_handler.py:44-48` → `api.py:703-704` (a **thin
passthrough with no validation of its own**) → `remove_dependency`
(`dependency.py:169-210`) → `_apply_dependency_remove_decision`
(`:212-244`) → `SqlAlchemyDependencyRepository.delete` (`repositories/tasks/task.py:466-473`).

**Gates:** permission-before-load ordering (global check at `:176/:178` runs
*before* `self._dependency_repo.get(dep_id)` at `:179`, preventing an
unauthorized caller from probing dependency ids via error-shape differences);
project-scope check, conditional on `if project_id:` (`:184-191`, see §15
finding 4a).

**Transaction:** correctly atomic and ordered, same pattern as create.

**Schedule recalculation:** yes, in the same transaction (`:221` →
`schedule_sync.py`). Two silent-degradation edge cases: if `project_id`
resolves to `None` (both endpoint tasks already gone), no recalculation *and*
no `tasks_changed` event fires (`:243`, `:15-16`); if `_scheduling_engine` is
`None`, the edge is removed with zero downstream effect.

**Dead QML signal, confirmed by full-file read:**
`TasksDependenciesSection.qml:22` declares `signal deleteRequested(var
dependencyData)` — the panel (`TasksDetailPanel.qml:306`) forwards it, but
**nothing in the section ever emits it.** Deletion is reachable **only**
through the detail-panel's contextual action bar; there is no in-row/in-section
delete affordance. The same asymmetry applies to editing — `openEditSelected()`
(`:53-57`) is invoked only from outside the section.

### Concurrency — none, on any of the three flows

See §16 for the full write-up; summarized here because it is directly a flow
defect: no `version` column, `SqlAlchemyDependencyRepository.update`
(`:440-455`) is a blind SELECT-then-mutate-all-fields, and `delete`
(`:466-473`) never inspects `rowcount` — a concurrent double-delete reports
"Dependency removed" while removing nothing.

---

## 9. Graph Integrity

All five integrity rules the audit asked about are enforced in the
**application layer** (`dependency_diagnostics.py`, called from `dependency.py`),
not by QML filtering, and not fully by the database:

| Rule | Enforced where | Evidence |
|---|---|---|
| Predecessor exists | App (`dependency.py:55-60`) + diagnostics (`:88-100`) + repo (`_ensure_task_in_scope`, `repositories/tasks/task.py:417-422`) | `code="TASK_NOT_FOUND"` |
| Successor exists | Same, mirrored | `code="TASK_NOT_FOUND"` |
| Same project | App only — `dependency_diagnostics.py:112-125` | `code="DEPENDENCY_CROSS_PROJECT"`; **not enforced in DB** (no composite FK) or repository (`_scoped_task_ids()` filters by tenant/org only, not project, `repositories/tasks/task.py:419`) |
| `predecessor != successor` | Domain validator (`task.py:339-346`) + diagnostics short-circuit (`dependency_diagnostics.py:73-86`, checked *first*) | `code="DEPENDENCY_SELF"`; **not enforced in DB** — no `CHECK` constraint, unlike the analogous `ck_tasks_wbs_parent_not_self` that *does* exist on `TaskORM` (`orm/task.py:36-39`) |
| No duplicate pair | App (`dependency_diagnostics.py:135-151`) **and** DB unique index (`ux_task_dependencies_pair`) | `code="DEPENDENCY_DUPLICATE"` |

**QML's role is cosmetic only, and this is provable, not assumed:**
`build_dependency_task_options` (`presenters/tasks/dependency_mapper.py:44-53`)
filters the picker to same-project, non-self, non-summary tasks — but the
task list it filters is already pre-scoped to one project by
`load_tasks_for_project(desktop_api, selected_task.project_id)`
(`dependencies_builder.py:89`). That is a consequence of the data source, not
an enforced rule; a caller that bypasses the dialog (e.g. a scripted API call,
or the identical `SchedulingWorkspaceController` surface) hits the exact same
backend gates with no QML involved. The QML→Python handler
(`dependency_command_handler.py:12-28`) validates only *presence* of the
payload keys, no integrity rule.

**A caller that bypasses `TaskDependencyMixin` and hits the repository
directly could create a cross-project row successfully** — `_scoped_task_ids()`
(`repositories/tasks/task.py:403-415`) filters by tenant+org, never by
project, so `SqlAlchemyDependencyRepository.add` alone does not stop it. In
practice the only production path *is* through the mixin, so this is a
defense-in-depth gap rather than a live exploit.

**Additional integrity gate not in the original ask:** summary/WBS-parent
tasks are barred from participating in any dependency at all
(`_require_leaf_task`, `dependency.py:61-62` → `hierarchy_support.py:160-165`,
`code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"`) — enforced on `add_dependency`,
**not** on `update_dependency` (§8).

**At-rest detection (not prevention) also exists**, for auditing already-bad
data: `infrastructure/persistence/health/integrity_checks.py` has categories
`cross_project_dependency` (`:189-202`, error severity), `self_dependency`
(`:203-213`, error), and `duplicate_dependency` (`:214-232`, warning) — but
**no `dependency_cycle` category**, so a persisted cycle (see §10's TOCTOU
finding) is invisible to `python -m tools.pm_data_integrity_check` and would
only surface as a `SCHEDULE_CYCLE` crash the next time CPM runs.

---

## 10. Cycle Detection

**Implemented — application layer only, BFS reachability probe, run before
the new edge is added.**

Entry point `_find_cycle_path_ids`
(`application/tasks/queries/dependency_diagnostics.py:279-292`):
```python
def _find_cycle_path_ids(self, deps, predecessor_id, successor_id):
    graph: dict[str, list[str]] = {}
    for dependency in deps:
        graph.setdefault(dependency.predecessor_task_id, []).append(dependency.successor_task_id)
    path = self._find_path(graph, successor_id, predecessor_id)
    if not path:
        return None
    return [predecessor_id, *path]
```
Core BFS, `_find_path` (`:294-308`):
```python
@staticmethod
def _find_path(graph, start, target):
    queue = deque([(start, [start])])
    visited: set[str] = set()
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        if node in visited:
            continue
        visited.add(node)
        for nxt in graph.get(node, []):
            if nxt not in visited:
                queue.append((nxt, [*path, nxt]))
    return None
```

**Indirect cycles ARE caught — this is structural, not a special case.** The
graph is built from *all* existing project edges
(`self._dependency_repo.list_by_project(project_id)`, `:134` — one SQL
query) and BFS traverses transitively with no depth limit. Adding `P→S` closes
a cycle iff `S` already reaches `P`; hop count is irrelevant to the algorithm.

**Concrete trace for the audit's requested A→B, B→C, then C→A case:**
Creating `C→A` calls `add_dependency(predecessor_id=C, successor_id=A, ...)`
→ diagnostics builds `graph = {A: [B], B: [C]}` → `_find_path(graph, start=A,
target=C)` walks `A → B → C`, returns `[A, B, C]` → `_find_cycle_path_ids`
returns `[C, A, B, C]` → `dependency.py:97-98` raises
`BusinessRuleError(code="DEPENDENCY_CYCLE")` with detail `"Cycle path: Task C
-> Task A -> Task B -> Task C"`. **Nothing is persisted.**

**Self-cycle (A→A):** rejected at two independent layers — the diagnostics
short-circuit (`dependency_diagnostics.py:73-86`, checked *first*, before any
repo access) and the domain model's `_validate_not_self_dependency` (§2, §9),
which is the backstop for any caller that skips diagnostics (e.g. the
approval-apply path).

**Error codes:** `DEPENDENCY_CYCLE` (`dependency_diagnostics.py:165`), raised
as `BusinessRuleError` (`dependency.py:98,299`). A second, independent
backstop exists at *scheduling* time (not creation time): `graph.py:55-59`
raises `code="SCHEDULE_CYCLE"` when Kahn's topological sort in
`build_project_dependency_graph` fails to consume every task — this only
fires against already-persisted data.

### Gaps found in cycle protection

1. **No cycle check in the domain layer** (impossible by design — a single
   aggregate can't see other edges) **and none in the repository/DB.**
2. **The approval-apply path bypasses cycle re-validation** —
   `_apply_dependency_add_decision` (`dependency.py:127-167`, called from
   `project_registry.py:722-731`) contains no diagnostics call. Two pending
   approval requests (e.g. `A→B` and `B→A`, each individually valid at
   request time) approved close together could both apply and persist a
   cycle. **This is a genuine TOCTOU hole.**
3. **No at-rest `dependency_cycle` integrity-check category** (§9) — a
   persisted cycle is invisible to the data-integrity tool and would only
   surface as a `SCHEDULE_CYCLE` crash at CPM time.
4. `_find_path` stores a full copy of the path on every queue entry
   (`[*path, nxt]`, line 307) — O(V·depth) memory worst case, vs. O(V) for a
   predecessor-map-plus-backtrack. Not a correctness issue; a micro-optimization
   opportunity noted for completeness (see also §17's honest non-finding that
   cycle detection is *not* a scale problem in query terms).

### Transitive / redundant dependencies — silently accepted, no rule exists

Given `A→B`, `B→C`, an explicit `A→C` passes every check (self: no; existence:
yes; cross-project: no; duplicate: no existing `A→C` row; cycle: `_find_path`
from `C` to `A` over `{A:[B], B:[C]}` finds nothing) and is persisted with **no
warning**. Grep for `redundant|transitive` across the whole repo returns only
unrelated comments in three unconnected files. No `DEPENDENCY_REDUNDANT` code
exists. The impact-preview (`include_impact=True`) would typically report "no
schedule shift detected" for a genuinely redundant edge — which reads as
reassurance, not as a redundancy signal — but note `add_dependency` always
calls diagnostics with `include_impact=False`, so even that signal is absent
at write time in practice.

### Multiple predecessors — combined by `max()` over candidate ES; see §11 for the full formula and its bugs.

### Multiple successors / fan-out — no limit, and the repository query is efficient

No cap anywhere (grepped `MAX_DEPEND|dependency_limit|too many dependenc`,
zero hits). `SqlAlchemyDependencyRepository.list_by_task`
(`repositories/tasks/task.py:487-497`) fetches predecessors *and* successors
in **one** query using `or_(predecessor_task_id==task_id,
successor_task_id==task_id)`, backed by both non-unique indexes. The desktop
API's `list_dependencies` additionally pre-builds a `tasks_by_id` lookup map
once (`api.py:614-651`) rather than looking up each linked task individually
— total cost for a task with K dependencies is 3 queries regardless of K, not
`1+K`. (Contrast the genuine N+1 in the *Scheduling* workspace's
project-wide read — see §17.)

---

## 11. Scheduling / CPM Consumption

### Which engine is authoritative

**Four implementations of the same date math exist; one is authoritative in
production.**

| Implementation | File | Wired into production? |
|---|---|---|
| `SchedulingEngine` | `application/scheduling/services/scheduling_engine.py:50` | **Yes — authoritative.** Constructed at `project_registry.py:275`; consumed by `scheduling_facade_service.py:14`, `constraint_builder.py:18`, `dashboard_service.py:77,161,182,204`, `dashboard/reporting/portfolio.py:89`, `commands/schedule_sync.py:20`, `infrastructure/reporting/builders/kpi.py:51,112,181` |
| `CPMCalculator` | `application/scheduling/cpm/cpm_calculator.py:34` | Only one call site: `application/portfolio/queries/portfolio_executive.py:222` |
| `DependencyResolver` | `application/scheduling/dependencies/dependency_resolver.py:21` | **Dead code.** Zero non-definition, non-`__init__.py` references anywhere in `src/` |
| `TaskDependencyDiagnosticsMixin._simulate_schedule` | `application/tasks/queries/dependency_diagnostics.py:60,310` | Only for the (also largely unreachable — see §17) impact-preview read path |

### Proof that dependencies genuinely drive computed dates, not inert metadata

Forward pass, `application/scheduling/cpm/passes.py:28-33`:
```python
for task_id in topo_order:
    task = tasks_by_id[task_id]
    incoming = deps_by_successor.get(task_id, [])
    est, eft = compute_task_dates(task, incoming, es, ef)
    es[task_id] = est
    ef[task_id] = eft
```
`incoming` comes from `application/scheduling/cpm/graph.py:61-67`, indexed by
predecessor/successor. The specific fold from edge data into a date,
`scheduling_engine.py:374-386`:
```python
for dep in incoming_deps:
    pred_es = es.get(dep.predecessor_task_id)
    pred_ef = ef.get(dep.predecessor_task_id)
    if pred_es is None and pred_ef is None:
        continue
    if dep.dependency_type == DependencyType.FINISH_TO_START:
        if pred_ef:
            candidate_es.append(self._task_calendar.add_working_days(pred_ef, dep.lag_days + 2))
    elif dep.dependency_type == DependencyType.START_TO_START:
        if pred_es:
            candidate_es.append(self._task_calendar.add_working_days(pred_es, dep.lag_days))
    # ... FF / SF, quoted in full in §5/§4
```
then `est = max(candidate_es)` (`:413`), `eft = add_working_days(est, duration)`
(`:414`).

**Important corollary, provable from the same code:** when a task has *any*
usable incoming dependency, **its own `task.start_date` is completely
ignored** — `task.start_date` is consulted only in the `if not incoming_deps:`
branch (`:365-370`) and the `if not candidate_es:` fallback (`:406-411`), never
combined with dependency candidates via `max`. **Dependencies are the sole
driver of ES for every non-root task.** This is the direct cause of §13's
leveling-gets-reverted finding.

Results are persisted onto `Task.start_date`/`end_date`
(`application/scheduling/cpm/results.py:28-34`) and written via
`self._task_repo.update(info.task)` (`scheduling_engine.py:183-184`, under
`if persist:`).

### Backward pass — same formulas, dual direction

`cpm/passes.py:123-135` (quoted with FS/FF/SS/SF branches). Combination:
`if cand_lf_dates: lf = min(cand_lf_dates); ls = add_working_days(lf, -(duration-1))`
`elif cand_ls_dates: ls = min(cand_ls_dates); lf = add_working_days(ls, duration-1)`
(`:137-150`).

### CONFIRMED BUG (two independent audit passes, same conclusion): mixed successor types silently discard SS/SF late-date constraints

The `if cand_lf_dates: ... elif cand_ls_dates: ...` structure
(`passes.py:137-150`) means a predecessor with **both** an FS-or-FF successor
**and** an SS-or-SF successor takes only the `cand_lf_dates` branch — every
SS/SF late-date constraint on that task (the whole `cand_ls_dates` list) is
computed and then **thrown away**. Consequence: LS/LF end up too late, total
float is overstated, and a genuinely critical task can be wrongly reported
non-critical. Not guarded, not logged, not tested.

### CONFIRMED BUG (two independent audit passes): backward pass is a correct inverse only for FS

Forward FS uses `lag+2` (correct, symmetric with backward's `-(lag+1)`, both
compensating for inclusive/exclusive counting correctly). Forward SS/FF/SF use
bare `lag`; backward SS/FF/SF also use bare `lag` (`-lag`, `passes.py:127,130,133`)
— but because forward's positive-inclusive counting already produces
`lag−1` (§5), and backward's negative-exclusive counting produces exactly
`-lag`, **the two are not inverses of each other for SS/FF/SF.** A positive-lag
SS/FF/SF edge is under-applied by one working day in one direction relative to
the other, injecting spurious float (or false non-criticality via the §11
float-clamp finding below) specifically on SS/FF/SF chains. FS does not have
this defect.

### Multiple predecessors — combined by `max()`, proven with formula and code

`cpm_calculator.py:151-195`, the reduction:
```python
est = max(candidate_es)
eft = self._calendar.add_working_days(est, duration)
```
For a successor `D` with predecessors `A FS→D`, `B SS→D`, `C FF→D`: FS
contributes `add_working_days(EF_A, lag+2)`; SS contributes
`add_working_days(ES_B, lag)`; FF is back-solved to an ES via
`add_working_days(add_working_days(EF_C, lag), -(duration-1))`. `D`'s ES is
the max of the three. Milestone (zero-duration) tasks use the same `max()`
reduction at `cpm_calculator.py:148`/`dependency_diagnostics.py:389`.

**Duplicated in the diagnostics preview** (`dependency_diagnostics.py:364-433`),
near-verbatim but not literally shared code with `CPMCalculator` — one
already-visible divergence: the diagnostics FF/SF branch computes the
back-solve *unconditionally* (`:419,422`) while `CPMCalculator` guards it with
`if duration > 0 else ef_s` (`:180,185`). Any future fix to the FS `+2` or the
FF back-solve must be applied in (at minimum) four places or the preview will
disagree with the committed schedule.

**No validation exists for over-constrained multiple-predecessor combinations**
(e.g. an SS predecessor whose derived start exceeds an FF predecessor's
derived finish on the same successor) — the system just takes the max and
moves on; there is no warning surfaced anywhere.

### Total float, free float, critical path

`cpm/results.py:36-45`:
```python
if est is not None and lst is not None:
    if lst < est:
        total_float = 0
    else:
        days = calendar.working_days_between(est, lst)
        total_float = max(0, days - 1)
else:
    total_float = None
is_critical = total_float == 0 if total_float is not None else False
```
**Negative float is clamped to 0** — an infeasible/over-constrained schedule
reports zero float rather than a negative number, destroying the "how late am
I" signal and force-marking such tasks critical.

**Free float: NOT FOUND anywhere in the codebase** — grepped `free_float` /
`freefloat` / "free float" across all of `src/`, zero hits.
`CPMTaskInfo` (`scheduling/models/cpm.py:10-20`) has only `total_float_days`.

**Critical-path membership is purely `total_float == 0` per task** — no
longest-path trace exists. `SchedulingEngine.recalculate_project_schedule`
exposes no critical-path id list at all; only `CPMCalculator` (the
lesser-used implementation) derives one via a filter
(`cpm_calculator.py:89`).

### Domain/CPM enum-coverage check — no mismatch, but a semantics mismatch (restated from §4 for completeness of this section)

All four enum values are branched on in all six CPM code sites, with no
`else`. The real mismatch is arithmetic correctness (above), not coverage.

---

## 12. Constraint Interaction

**Constraints are applied *after* dependencies and *after* actuals in the
live engine, and hard constraints win unconditionally with no warning.**

Pipeline order, `scheduling_engine.py:236-246`:
```python
est, eft = compute_task_dates_common(...)          # dependencies, then actuals
return self._apply_scheduling_constraints(task, est, eft)   # constraints last
```
Resolution, `scheduling_engine.py:261-308` (verbatim for the conflicting
cases):
```python
if ct == ConstraintType.MUST_START_ON:
    est = cd
    eft = cal.add_working_days(cd, duration) if duration > 0 else cd
elif ct == ConstraintType.MUST_FINISH_ON:
    eft = cd
    est = cal.add_working_days(cd, -(duration - 1)) if duration > 0 else cd
elif ct == ConstraintType.START_NO_EARLIER_THAN:
    if est is None or est < cd:
        est = cd; ...
elif ct == ConstraintType.FINISH_NO_EARLIER_THAN:
    if eft is None or eft < cd:
        eft = cd; ...
```

**Answer to the audit's explicit example** (A FS→B, B has Must-Start-On 5 Sep,
A finishes 8 Sep): `MUST_START_ON` performs a bare `est = cd` with **no
comparison to the dependency-derived ES**. The final computed date is 5 Sep —
**the successor is scheduled to start before its predecessor finishes**, and
nothing raises, warns, or logs this. `SNET`/`FNET` are one-sided floors (`if
est < cd`) and only ever push a task *later*, so they cannot themselves break
a dependency minimum in this direction. `SNLT`, `FNLT`, `DEADLINE` are
validation-only per the engine's own docstring (`scheduling_engine.py:270-272`)
— they never drive the schedule.

**The one validator meant to catch this can't, structurally.**
`ConstraintValidator.validate` (`cpm/constraint_validator.py:100-120`) checks
`info.earliest_start`/`earliest_finish` — but that is the *already-overridden*
output of `SchedulingEngine`, which already forced `es=cd` for MSO. The
predicate `es != cd` at line 104 is therefore **unreachable on the live
path**. Confirmed by the wiring: the validator's only production caller,
`api/desktop/scheduling/builders/constraint_builder.py:15-25`, runs
`scheduling_engine.recalculate_project_schedule(...)` and validates *that*
result. That whole function is also wrapped in `except Exception: return ()`
— any internal failure yields "no violations" rather than an error.

**A general "successor starts before predecessor finishes + lag" consistency
check: NOT FOUND anywhere in the codebase.** `dependency_diagnostics.py`
contains no violation-detection logic (grepped `violat` in that file — zero
hits); it only detects cycles and computes what-if schedule shifts, neither of
which is the same thing as flagging an already-committed
constraint/dependency conflict.

**Engine divergence:** `CPMCalculator._compute_task_dates`
(`cpm_calculator.py:98-113`) has **no** `_apply_scheduling_constraints`
equivalent at all — the portfolio-executive read path
(`portfolio/queries/portfolio_executive.py:222`) ignores MSO/MFO/SNET/FNET
entirely, while the dashboard/desktop/reporting paths honor them. **The same
project can show two different computed schedules depending on which screen
the user is looking at.** `dependency_diagnostics.py`'s preview has the same
omission.

**Actuals interact with constraints too:** constraints are skipped entirely
for a task with `actual_end` set (`scheduling_engine.py:274-275`, early
return) — meaning the one place a MSO/MFO conflict *is* structurally reachable
by the validator is for already-completed tasks, an inverted reporting
behavior relative to what a planner would want to see.

---

## 13. Leveling Interaction

**Do NOT read this as R4.4 leveling-migration work — this section only
documents today's behavior, per the audit's own stop condition.**

### Two implementations; only one is live

- `ResourceLevelingMixin` (`application/scheduling/leveling/leveling_mixin.py:21`)
  — `SchedulingEngine` inherits it (`scheduling_engine.py:50`, asserted by
  `src/tests/architecture/test_architecture_guardrails_services.py:143`).
  **Live path**, reached via `DashboardService.auto_level_overallocations`
  (`dashboard_service.py:177`) and `manually_shift_task_for_leveling`
  (`:198`).
- `ResourceLevelingEngine` (`application/scheduling/leveling/resource_leveling_engine.py:28`)
  — documented in its own module as "replaces the mixin pattern." **Dead
  code**: zero non-definition callers anywhere in `src/`. (This directly
  contradicts `docs/pm_modernization/README.md`'s Implementation Order step 6,
  which marks it "✅ added" with "ResourceLevelingMixin kept for backward
  compat; new code should use ResourceLevelingEngine" — see §25.)

### Leveling never reads `dependency_type` or `lag_days` — confirmed absent

The only dependency data leveling touches is the raw edge set, to build a
successor-existence map (`application/scheduling/leveling/leveling.py:16-20`):
```python
def build_successors_map(deps):
    successors = defaultdict(set)
    for dep in deps:
        successors[dep.predecessor_task_id].add(dep.successor_task_id)
    return successors
```
`dependency_type` never appears in `leveling.py`, `leveling_mixin.py`, or
`resource_leveling_engine.py`; `lag_days` appears once in `scheduling_engine.py`
(line 218, for calendar-snapshot padding sizing — unrelated to leveling).

### The only dependency-aware guard is "refuse to move any task with a successor"

`leveling.py:90-98` skips leveling candidates with any successor;
`leveling_mixin.py:95-100` **raises** for the manual path:
```python
if successors.get(task.id):
    raise BusinessRuleError(
        "Manual leveling supports only tasks without successors.",
        code="RESOURCE_LEVELING_DEPENDENCY_BLOCK",
    )
```
The shift itself is a blind forward push with no dependency awareness
(`leveling_mixin.py:262-267`).

### Findings for R4.4 to inherit as known state (not fixed here)

1. **Cannot mathematically violate a dependency minimum today** — but only by
   accident of two crude restrictions: all shifts are strictly forward (which
   can never break a dependency's *lower*-bound semantics on the shifted
   task's own successors), and any task with a successor is refused outright
   (so outgoing edges are never disturbed). No violation could be constructed
   from this code.
2. **Leveling is largely inert on real, dependency-linked networks** — because
   almost every task in a real plan has a successor, `choose_auto_level_task`
   returns `None` immediately and the loop reports `iterations=0` while doing
   nothing.
3. **CONFIRMED, high-impact for R4.4: any leveling shift on a task that has
   incoming dependencies is silently reverted by the next CPM run.**
   `DashboardService` calls `recalculate_project_schedule` immediately after
   leveling (`dashboard_service.py:182,204`). Because CPM ignores
   `task.start_date` whenever a task has usable incoming dependencies (§11),
   and then overwrites `start_date`/`end_date` from ES/EF and persists them,
   a leveled task with predecessors snaps straight back to its
   dependency-driven date. **The user is told leveling succeeded; the
   persisted schedule doesn't reflect it.** Only dependency-free root tasks
   keep their leveled dates.
4. **Leveling can violate scheduling constraints/deadlines** — it never reads
   `constraint_type`/`constraint_date`/`deadline`, so a forward shift can push
   a task past a hard constraint or deadline with no check.
5. **The dead `ResourceLevelingEngine.commit_actions` has a wider hole** — it
   re-validates only actual dates and never re-consults the dependency
   repository at all; a dependency added between simulate and commit would be
   silently ignored, with no CPM re-run inside the method. **If R4.4 promotes
   this class to the live path, finding #1's accidental safety is lost** and
   must be re-established deliberately.

### Phase P — the invariant R4.4 must satisfy, and a pinned regression

This pass does not fix finding 3. It preserves it as a regression test —
`src/tests/project_management/dependency/test_leveling_dependency_boundary.py::test_auto_leveling_shift_on_a_dependency_linked_task_is_silently_reverted_by_the_next_cpm_run`
— that asserts *today's* (broken) behavior: leveling a dependency-linked
task, then recalculating, silently discards the leveling decision with no
error. If R4.4 ever fixes this, that test's final assertion should flip as
a deliberate, visible change to the test — not disappear as a side effect
of an unrelated refactor.

**The invariant R4.4 must satisfy:** after leveling modifies a task's
planned dates, a subsequent canonical schedule recalculation must NOT
silently erase a valid leveling decision.

**What that requires, and why it can't be solved partially here:** R4.4
must reconcile four inputs — dependency minimum dates, hard constraints,
resource-capacity leveling, and actual dates — through *one* schedule
model, not four independently-consulted ones (which is what today's
`SchedulingEngine`/leveling mixin split already is, per finding 3 above and
§11/§12 of this document). Patching leveling alone (e.g. teaching it to
respect a task's dependency-driven earliest start) would still leave CPM
free to silently overwrite a leveling decision that a hard constraint check
never saw and vice versa — the same class of "two different computed
schedules depending on which code path ran last" bug this audit already
found between the dashboard and portfolio-executive read paths (§12). That
reconciliation is explicitly out of scope for this dependency-foundation
pass and belongs to the dedicated R4.4 leveling decision.

---

## 14. Actual-Date Interaction

**Field names, exactly as they exist:** `Task.actual_start`, `Task.actual_end`
(`domain/tasks/task.py:39-40`). **There is no `actual_finish` field** — every
consumer uses `actual_end`.

### Actuals override planned dates, and propagate to successors

Order of application, `application/scheduling/cpm/date_compute.py:17-22`:
dependency math runs first, then `apply_actual_constraints` overwrites.
`SchedulingEngine._apply_actual_constraints` (`scheduling_engine.py:433-455`):
```python
a_start = task.actual_start; a_end = task.actual_end
if a_end is not None:
    fixed_ef = a_end
    fixed_es = a_start if a_start is not None else (
        add_working_days(fixed_ef, -(duration-1)) if duration > 0 else fixed_ef
    )
    return fixed_es, fixed_ef
if a_start is not None:
    if est is None or a_start > est:
        est = a_start
        eft = est if duration <= 0 else add_working_days(est, duration)
```
**Semantics:**
- `actual_end` set ⇒ **hard, unconditional override** of EF (dependency-driven
  date discarded).
- `actual_start` set (no `actual_end`) ⇒ **one-sided floor only** — raises ES
  *only if* `a_start > est`. If the task actually started **earlier** than
  its dependency-driven ES, the earlier actual start is **silently discarded**
  and the (later) dependency-driven date wins — the schedule keeps reporting
  a start date later than what actually happened, with no flag.

**Propagation is proven, not assumed:** the return value of this function is
exactly what `passes.py:32-33` writes into the `es`/`ef` dicts that
*successors* read at `scheduling_engine.py:375-376`. So once a predecessor has
`actual_end` recorded, its actual finish — not its planned finish — drives
every downstream FS/FF successor's date; once it has `actual_start`, the
actual start drives SS/SF successors. `CPMCalculator`'s equivalent
(`cpm_calculator.py:197-219`) is behaviorally identical.

### Baseline dates are never used by CPM — NOT FOUND

No CPM file imports or references anything from
`application/scheduling/baselines/`. The forward-pass basis is:
dependency-derived date → else `task.start_date` (the live/current date, which
CPM itself overwrites every run) → then actuals override. Baselines are a
separate, purely comparative concern
(`baselines/baseline_comparison_service.py`) and never feed into
dependency-driven date computation.

### Test coverage

`test_technical_math_reporting_scheduling.py::test_schedule_actual_date_
constraints_override_computed_dates` (lines 71-89) tests actuals overriding
computed dates — but on a **single task with no dependencies at all**. **No
test exists** where an incoming dependency and an actual date compete (e.g. a
predecessor's `actual_end` pulling a successor's ES, or a successor whose
`actual_start` is earlier than its dependency-derived ES — the "one-sided
floor discards the earlier actual" behavior above is entirely unverified).

---

## 15. Authorization / Tenancy

### Tenant/organization isolation — genuinely enforced in SQL, not just implied by UI

`SqlAlchemyDependencyRepository._scoped_task_ids()`
(`repositories/tasks/task.py:403-415`) builds a tenant+org-filtered task-id
subquery from `TenantContextService.require_active_scope_ids`
(`src/core/platform/application/tenant/tenancy/tenant_context.py:472-499`,
hard-fails with `TENANT_CONTEXT_REQUIRED`/`ORGANIZATION_CONTEXT_REQUIRED` if
absent). Every dependency operation is constrained by it: `add`, `get`,
`update`, `delete`, `delete_for_task`, `list_by_task`, `list_by_project` (all
cited in §3/§17).

**Cross-tenant bypass attempt — rejected, traced end to end:** a caller
passing a `predecessor_task_id`/`successor_task_id` from a different tenant
hits `self._task_repo.get(predecessor_id)` (`dependency.py:55`), whose
tenant+org join filter returns `None` for the foreign row, so
`dependency.py:56-57` raises `code="TASK_NOT_FOUND"`. Defense-in-depth: even
bypassing that, `SqlAlchemyDependencyRepository.add`'s own
`_ensure_task_in_scope` re-validates both ids (`:425-426`).
**Cross-project within the same tenant** is separately rejected by
`DEPENDENCY_CROSS_PROJECT` (§9).

### Findings

**Project-scope enforcement is conditional and fail-open in three of four
write/read methods.** `get_dependency` (`dependency.py:39`),
`remove_dependency` (`:185`), and `update_dependency` (`:274`) each guard
`require_project_permission` with `if project_id:`, where `project_id` is
derived from whichever endpoint task resolves first. If **both** endpoints
fail to resolve, the project-scope check is **skipped entirely** and only the
global `task.manage`/`task.read` check applies. Reachability is low in
practice (CASCADE deletes and the repository's own dual-endpoint scope check
make an unresolvable-endpoint dependency hard to obtain), but the code
pattern is fail-open rather than fail-closed.

**`add_dependency` never scope-checks the successor's project** — only
`predecessor.project_id` is passed to `require_project_permission`
(`:70-83`). Because the cross-project rule runs afterward and rejects any
mismatch, this is not a write-authorization bypass — but it **is an
information-disclosure oracle within a tenant**: a user with `task.manage` on
project A but no visibility into project B can submit a create with a task id
from B and get back `DEPENDENCY_CROSS_PROJECT` ("tasks are in different
projects") rather than the indistinguishable `TASK_NOT_FOUND` a
nonexistent id would produce — distinguishing "exists in a project I can't
see" from "doesn't exist."

**The scoped-permission primitive itself fails open for principals with no
scope grants.** `UserSessionContext.has_scope_permission`
(`src/core/platform/domain/security/auth/session.py:336-347`): after
confirming the permission code is held globally, it loads the principal's
project-scope rows and — **if that mapping is empty, returns `True`
unconditionally** (`:345-346`), granting the permission on *every* project id.
Every dependency project-scope check in this audit rests on this primitive, so
"a project-scope check exists in the code" does **not** by itself guarantee
per-project enforcement at runtime — it depends on whether the calling
principal was provisioned with explicit `scoped_access["project"]` rows.
Tenant/org isolation is unaffected (enforced independently in SQL). This
appears to be intentional "unrestricted user" semantics rather than a bug, but
it means the project-scope checks throughout this audit are conditionally
effective, not unconditionally effective.

**Read paths are also scoped:** `get_dependency` and `list_dependencies_for_task`
(`dependency.py:31-46,246-257`) both require global `task.read` plus
project-scoped `task.read`, inheriting the same primitive above.

---

## 16. Concurrency

**No optimistic concurrency control exists on `TaskDependency`, at any layer —
confirmed absent, not merely undocumented.**

- **Domain:** no `version` field (§2), unlike sibling aggregates `Task`
  and `TaskAssignment` in the same file.
- **Repository — blind overwrite.** `SqlAlchemyDependencyRepository.update`
  (`repositories/tasks/task.py:440-455`) re-selects by `id` only, then
  unconditionally assigns all four mutable columns:
  ```python
  row.predecessor_task_id = dependency.predecessor_task_id
  row.successor_task_id  = dependency.successor_task_id
  row.dependency_type    = dependency.dependency_type
  row.lag_days           = dependency.lag_days
  ```
  No `WHERE version = :expected`, no `rowcount` assertion, no
  `ConcurrencyError` raise. Contrast `SqlAlchemyTaskRepository.update`
  (`:75-101`), which *does* use `update_with_version_check` with
  `stale_message="Task was updated by another user."` — dependencies are the
  outlier, not the convention.
- **Delete never inspects `rowcount`** (`:466-473`) — a concurrent
  double-delete: the second caller's earlier `get()` snapshot still shows the
  row, the `DELETE` matches zero rows, and the flow proceeds to commit, emit
  `tasks_changed`, and report "Dependency removed" to a user who removed
  nothing.
- **No `IntegrityError` translation** on the dependency write path — a grep
  across `application/tasks/commands/dependency.py` for `IntegrityError`
  returns zero matches (other command files in the same package, e.g.
  `hierarchy.py`, `lifecycle.py`, do have handlers). If two concurrent
  transactions both pass the application-level duplicate check and race into
  `ux_task_dependencies_pair`, the loser gets a raw `sqlalchemy.exc.IntegrityError`
  surfaced as plain text to the user, not a clean `DEPENDENCY_DUPLICATE`.
  `except Exception as exc: ... raise exc` blocks at three sites
  (`dependency.py:161-164,239-242,321-323`) roll back but deliberately
  re-raise unchanged.

**Explicit statement of impact:** two concurrent edits to the same dependency
**will** silently overwrite each other with no conflict signal and no lost
data audit trail — e.g. user A changes type FS→SS while user B concurrently
changes lag 0→5; both reads succeed against the same stale snapshot, both
writes blindly assign all four columns, and the second commit wins wholesale.

---

## 17. Query / Performance Model

### Repository layer itself is well-shaped

`SqlAlchemyDependencyRepository` — every method (`add`, `get`, `update`,
`delete`, `delete_for_task`, `list_by_task`, `list_by_project`,
`repositories/tasks/task.py:424-497`) issues **exactly one** SQL statement per
logical operation (`add`/`update` additionally run the two `_ensure_task_in_scope`
existence checks, so 2-3 SELECTs, not a loop). Indexes are correct and used
(§3). `list_by_project` (`:457-464`) fetches an entire project's edge set in
one statement.

**The N+1 is introduced one layer up, in the desktop API — not in the
repository.**

### CONFIRMED N+1: Scheduling workspace's project-wide dependency read

`api/desktop/scheduling/api.py:176-203`:
```python
tasks_by_id = {t.id: t for t in list_tasks(normalized_id)}   # 1 SELECT
dependencies_by_id = {}
for task_id in tasks_by_id:                                  # loop over EVERY task
    for dep in list_deps(task_id):                           # 2 SELECTs each
        dependencies_by_id[dep.id] = dep
```
`list_deps` is `task_service.list_dependencies_for_task`. **Cost: `2N + 1` SQL
statements for a project with N tasks** — 6,001 statements for a 3,000-task
project — and it discards roughly half the work, since every internal edge is
fetched twice (once via its predecessor's row, once via its successor's) and
then de-duplicated in a Python dict. **The efficient alternative already
exists and is already tenant-scoped**:
`DependencyRepository.list_by_project` — it is simply not exposed on the
application service, so the desktop API cannot reach it directly and falls
back to the per-task loop. This method is called **unconditionally on every
Scheduling-workspace `refresh()`** (`presenters/scheduling/workspace_builder.py:96-100`),
and every dependency mutation triggers a refresh via the `tasks_changed` event.

Partial mitigation that does exist: `workspace_controller_base.py:262-283`
coalesces multiple domain-events-in-one-event-loop-turn into a single refresh
via a zero-delay `QTimer.start(0)` — genuinely useful, but **not** a
time-window debounce; ten separate user interactions still cause ten full
refreshes, and if no Qt event loop is running the refresh executes
synchronously with zero coalescing (`:267-270`).

### CONFIRMED: full synchronous CPM recompute + ~3N task writes on every single dependency mutation

`_sync_project_schedule` (`application/tasks/commands/schedule_sync.py:9-20`)
is an unconditional pass-through to full `recalculate_project_schedule` — no
debounce, no dirty-flag, no batching — called from **every** create, update,
and delete. Inside, the dominant cost is the persist loop
(`scheduling_engine.py:183-184`): `for info in result.values():
self._task_repo.update(info.task)`, and `SqlAlchemyTaskRepository.update`
(`repositories/tasks/task.py:71-101`) issues **3 statements per task**
(re-fetch, scope check, version-checked update) for **every leaf task in the
project**, whether or not that task's dates actually changed — there is no
diffing before calling `update`. **Net: ~3N+3 SQL statements to add, edit, or
delete one dependency**, all inside the caller's transaction. For a
3,000-task project, ~9,000 statements for one edge change. This compounds
directly with the §17 N+1 above whenever the Scheduling workspace is open,
since a mutation there triggers both costs.

### CONFIRMED: an unnecessary unpaginated whole-project task fetch inside cycle checking

`dependency_diagnostics.py:153` loads **every task in the project**
(`task_repo.list_by_project`, no LIMIT/OFFSET) purely to resolve task *names*
for the cycle-path error message (rendered only on the cycle branch,
`:161-176`). This could be deferred behind `if cycle_path_ids:` or narrowed to
the already-existing batched `task_repo.list_by_ids(cycle_path_ids)`
(`repositories/tasks/task.py:131-136`).

### Cycle-check performance — an honest non-finding: this is NOT a scale problem

Exactly **2 DB queries** per cycle check (`dependency_repo.list_by_project`
and — only for the error-message names — `task_repo.list_by_project`),
regardless of graph depth or size, plus 2 `task_repo.get` calls for
predecessor/successor existence. The BFS itself is pure in-memory O(V+E) with
no per-hop query. **Do not carry forward a claim that cycle detection is
expensive** — it isn't; the two whole-project fetches it triggers are cheap
relative to the CPM recompute that runs immediately afterward in the same
request anyway.

### An impact-preview engine (~370 lines) that is effectively dead code

`get_dependency_diagnostics` (the function powering the "impact preview" —
before/after dates, risk level, shift-tracing) has exactly two call sites in
the entire codebase, **both with `include_impact=False`**
(`dependency.py:84-90,287-293`). No controller, presenter, or desktop API ever
requests the impact computation. `_simulate_schedule`, `_build_impact_rows`,
`_trace_paths_from_source`, `_impact_risk_level`, and both
`_compute_dates_*`/`_apply_actual_constraints` copies in this file —
approximately 370 of its 567 lines — are reachable **only from tests**. This
matches the finding in §19 that no DTO ever surfaces `DependencyDiagnostic`'s
richer fields to the UI.

### `DependencyResolver` is also dead code — restated here because it matters for performance planning

Zero production callers (§11). Its docstring is the most explicit
lead/lag-support claim in the codebase, but nothing runs it — do not budget
R4.4 work assuming this class is "already built and tested in production,"
per the (incorrect) implication in `docs/pm_modernization/README.md` (§25).

### Honest non-findings

- The repository's own methods are all single-statement — no loops.
- `delete_for_task` is one scoped DELETE; CASCADE FKs mean deleting a task
  doesn't fan out into per-edge deletes.
- `assignment_repo.list_by_tasks` inside the CPM recompute is correctly
  batched (one IN-query), evidence a prior N+1 there was already fixed.
- Data-integrity health checks (cross-project/self/duplicate) are each a
  single SQL statement with a sample limit — no scanning loops.
- Task Detail's own per-task dependency load (§8's create-flow trace, ~4
  SELECTs per Dependencies-tab open) is correctly lazy and memoized against
  re-selecting the same task.

---

## 18. Desktop API / DTOs

### Full field trace: domain → serializer → DTO → presenter → controller → QML

`TaskDependency` (5 fields, §2) → `serialize_dependency`
(`api/desktop/tasks/serializers/dependency_serializer.py:12-40`) →
`TaskDependencyDesktopDto` (`api/desktop/tasks/models/dependency.py:6-16`, 9
fields: `id`, `direction`, `direction_label`, `linked_task_id`,
`linked_task_name`, `dependency_type`, `dependency_type_label`, `lag_days`,
`relationship_label`).

**Field loss at the DTO boundary:** `predecessor_task_id`/`successor_task_id`
are **not** discrete DTO fields — both endpoints survive only fused into the
`relationship_label` string; one endpoint survives separately as
`linked_task_id`. A consumer can only tell which end is which via `direction`.

Presenter mapper `to_dependency_record_view_model`
(`presenters/tasks/dependency_mapper.py:9-32`) — fuses type and lag into a
single `subtitle` string (`"{type_label} | Lag {+Nd}"`, line 26), puts
`direction_label` into `status_label` (line 25), and puts
`"Linked task ID: {uuid}"` into `meta_text` (line 28). This is the direct
cause of the §19 "Lag column shows a UUID" defect.

Controller: `PMDependencyController` — `dependencies` (`QVariantMap`),
`dependenciesTableModel` (`QObject`/`DynamicTableModel`), mutation slots
`createDependency`/`updateDependency`/`deleteDependency`
(`controllers/tasks/pm_dependency_controller.py:72-113`).

### The richer diagnostic model never reaches a DTO

`DependencyDiagnostic` (`dependency_diagnostics.py:45-57`) — `is_valid`,
`code`, `summary`, `detail`, `impact_rows` (before/after dates, shift days,
trace path), `suggestions`, `risk_level` — is never exposed as a desktop DTO
(grepped `diagnostic` across `api/desktop/tasks/api.py`, zero hits). Its only
non-test consumers collapse the whole structure into a single exception
string (`dependency.py:91-99`). Combined with §17's finding that the
preview path is unreachable from any live UI call, this whole subsystem is
currently invisible to users.

### Scheduling workspace has a *better*-mapped, parallel DTO — for a read-only surface

`SchedulingDependencyDto` (`api/desktop/scheduling/models/dependencies.py:24-34`)
and `to_dependency_record` (`presenters/scheduling/record_mappers.py:190-212`)
correctly give `lag` and `direction` their own distinct fields/columns — see
§19. `status_label` here is a hardcoded `"Linked"` constant
(`serializers/dependency_serializer.py:25` in the scheduling package), which
is itself a minor "why does this ever change" question but not a defect.

---

## 19. Current Task Detail QML

File: `qml/workspaces/tasks/sections/TasksDependenciesSection.qml` (211
lines), mounted behind a `LazySectionLoader` in `TasksDetailPanel.qml:288`.

### Predecessor vs. successor — NOT visually differentiated

Rendered in **one undifferentiated `DataTable`** (`:89-105`). No split view,
no grouping, no direction filter. The only signal of direction is the text
value `"Predecessor"`/`"Successor"` — appearing in the column **headed
"Status"** (`:50`), because the mapper assigns `status_label =
direction_label`. The three text columns are explicitly `sortable: false`
(`:47-49`), so the user can't even sort to group by direction.

### `dependency_type` display

Shown as a spelled-out label (`"Finish -> Start"` etc.), fused into the
`subtitle`/"Type" column. The raw code (`"FS"`) is never shown to the user —
it exists in QML only for combo preselection.

### `lag_days` display — CONFIRMED display defect

The lag value is rendered only as a `"| Lag +0d"` fragment **inside the
"Type" column**. **The column actually headed `"Lag"` renders the linked
task's raw UUID** (`"Linked task ID: <uuid>"`, from `meta_text`) — a direct
consequence of the presenter fusing fields incorrectly (§18). The Scheduling
workspace's parallel read-only panel binds the equivalent column correctly
(`row_builders.py:115`: `lag` ← `state.lagLabel`), so the two surfaces
disagree on what their own "Lag" column means.

### Create — exists, fully wired, gated correctly

`canCreate: root._hasTask && !root._isSummary &&
root.dependencyTaskOptions.length > 0` (`TasksDetailPanel.qml:296`). Full
chain traced and confirmed reachable to the backend (§8).

### Edit — exists, but selection-gated and scope-limited to type/lag only

No per-row edit button; reachable only via a contextual "Edit" action that
requires a selected row (`TasksWorkspaceState.qml:248-250`). Matches the
backend's type/lag-only scope exactly (§8).

### Delete — exists and reaches the backend, but the section's own signal is dead code

`TasksDependenciesSection.qml:22` declares `signal deleteRequested(var
dependencyData)`, forwarded by the panel — but nothing in the 211-line
section file ever emits it (confirmed by full-file grep, one match: the
declaration itself). The live delete path is the detail-panel's contextual
"Remove" action, which does correctly reach a confirmation dialog and then
the backend (§8).

### Selectors — scoped correctly in Python, with zero QML-side re-validation

The linked-task ComboBox binds `root.taskOptions` verbatim with no filtering
of its own; the filtering (same-project, non-self, non-summary) happens
entirely in the presenter (§9). The lag `TextField` in the *create* dialog has
no numeric input mask (`TaskDependencyEditorDialog.qml:113`), unlike the
*edit* popup, which sets `inputMethodHints: Qt.ImhFormattedNumbersOnly`
(`TasksDependenciesSection.qml:165`) — an inconsistency between the two
dialogs that edit the same field.

### Error surfacing — inconsistent across the three mutations

- **Create:** errors ARE surfaced in-dialog (`TasksDialogHost.qml:320-321,38-52`
  sets `dialog.errorMessage` and keeps the dialog open with entered values
  intact — a cycle rejection genuinely reaches the user here, with its "Cycle
  path: A -> B -> C" detail).
- **Edit:** errors are **NOT** surfaced in-place — `TasksWorkspacePage.qml:476-480`
  discards the returned result, and the popup has already closed itself
  before the result comes back. The section's own `_editError` InlineMessage
  is cleared on save and never assigned a backend message — a dead error
  slot.
- **Delete:** same discard pattern (`TasksWorkspacePage.qml:177-181`).
- Edit/delete failures are not *entirely* swallowed — `run_mutation` still
  writes them to the workspace-level error banner — but the message is
  detached from the form, and the user's entered values are gone by the time
  it appears.
- Regardless of surface, the rich diagnostic (`impact_rows`,
  `suggestions`, `risk_level`) never crosses the boundary at all (§18) — only
  `str(exception)`.

---

## 20. Current Planning QML

**There is no Planning workspace.** `ls
src/ui_qml/modules/project_management/qml/workspaces/` lists exactly:
`collaboration, dashboard, financials, portfolio, projects, register,
resources, scheduling, tasks, timesheets`. A case-insensitive path search for
"planning" across the whole `ui_qml` tree returns nothing. **The Scheduling
workspace is the only schedule-visualization surface**, and this section
documents it in place of "Planning."

### The Scheduling timeline has zero dependency-line rendering

`SchedulingTimelinePanel.qml` is a genuine Gantt-like bar-lane timeline —
positioned bars, one lane per activity, critical-path coloring, progress
overlay, a baseline "ghost" bar, a today marker, gridlines. Its only data
input is `property var timelineModel`; the file contains no reference to
dependencies at all. **No dependency arrows/lines are drawn anywhere in the
app** — a grep for `Shape|ShapePath|Canvas|PathLine|arrow` across the entire
scheduling and tasks QML trees returns only unrelated `cursorShape:` hits. No
link-rendering primitive exists in this codebase today.

### The Scheduling workspace DOES have a read-only dependency table — and it is better-labeled than Task Detail's

`SchedulingDetailPanel.qml:151-181`, section 2 of 8
(`["Overview","Dependencies","Constraints","Calendars","Baselines",
"Resources","Activity Feed","Change Impact"]`). Subtitle text is honest about
scope: *"Read-only predecessor and successor visibility from the current
schedule network."* Columns: `Related Activity | Type | Lag | Direction |
Status | Network Note` — and unlike Task Detail, **`Lag` and `Direction` are
each correctly and separately mapped** (`row_builders.py:107-116`).

### Create/Edit/Delete/Select in Scheduling — NOT FOUND in QML, but fully built and orphaned in the backend

Searched exhaustively (`SchedulingWorkspace.qml`, `SchedulingWorkspacePage.qml`,
`SchedulingWorkspaceState.qml`, `SchedulingDialogHost.qml`,
`SchedulingActionBar.qml`, `SchedulingPanelFrame.qml`, all nine panel files):
no create control, no edit control, no delete control, no task selector. A
case-insensitive grep for "dependenc" across the entire scheduling QML tree
returns only the three read-only properties, the panel's own title/columns,
and page-level pass-throughs.

**The backend surface is fully built and simply never called:**
`SchedulingWorkspaceController` exposes `createDependency`, `updateDependency`,
`deleteDependency` (`:702,706,710`), `dependencyTypeOptions`,
`dependencyTaskOptions` (`:280-281,284-285`), backed by
`mutation_handler.py:115,125,136` and dedicated
`SchedulingDependencyCreateCommand`/`UpdateCommand` DTOs
(`api/desktop/scheduling/commands/dependency_commands.py:6,15`). **No
Scheduling QML invokes any of it.** This is genuinely orphaned write capacity,
not a stub — it would need only QML wiring, not new backend work, to become
live (which is directly relevant to sequencing in §26).

---

## 21. Existing Tests

Searched exhaustively across `src/tests/project_management/` (170 files) and
`src/tests/pm/` (10 files). **No test file anywhere has "dependency" in its
filename** — all coverage is incidental to CPM, business-rule, or
tenant-hardening test files. Every test cited below was opened and read (not
inferred from its name).

| # | Capability | Status | Evidence |
|---|---|---|---|
| 1 | FS | ✅ | `test_cpm_flow.py::test_cpm_forward_backward_basic:26,41`; `test_technical_math_reporting_scheduling.py::test_cpm_dependency_type_math:35,43-49` |
| 2 | SS | ✅ | `test_technical_math_reporting_scheduling.py:36,51-55` |
| 3 | FF | ✅ | `test_technical_math_reporting_scheduling.py:37,57-61`; `test_cpm_flow.py:28,44` |
| 4 | SF | ✅ | `test_technical_math_reporting_scheduling.py:38,63-68` |
| 5 | Lag (positive) | ✅ | same test, all four types with lag 2-3; persistence round-trip: `test_project_management_desktop_api_tasks_bulk_assign.py:165,172` |
| 6 | Negative lag / lead | ❌ **NO TEST FOUND** | grepped every `lag_days=`/`lag` occurrence in `src/tests/` — all non-negative |
| 7 | Self-dependency | ⚠️ partial | domain: `test_task_domain_validation.py:123-127` ✅; DB scan: `test_data_integrity.py:152-157,257-264` ✅; **service-level `add_dependency(x,x)` guard: no test** |
| 8 | Duplicate dependency | ✅ | service: `test_business_rules_and_edge_cases.py:64-68`; diagnostics: `:197-210`; DB constraint: `test_data_integrity.py:160-168` |
| 9 | Indirect cycle (3+ hop) | ✅ | `test_business_rules_and_edge_cases.py::test_dependency_diagnostics_cycle_includes_path_names:213-231` (asserts full path names); 2-hop also covered. **Gap: no 4+ hop test, no `SCHEDULE_CYCLE` path test** |
| 10 | Multiple predecessors combining constraints | ❌ **NO TEST FOUND** | every dependency-using test has exactly one incoming edge per successor; the mixed-type fan-in case is entirely uncovered; the only multi-predecessor *creation* is in a perf test gated by `PM_RUN_PERF_TESTS` and asserting only wall-clock SLAs, zero date assertions |
| 11 | Multiple successors / fan-out | ✅ | `test_technical_math_reporting_scheduling.py:35-38,43-68` — one predecessor, four successors, each independently asserted |
| 12 | Cross-project attempt | ✅ | `test_business_rules_and_edge_cases.py:70-72`; `test_data_integrity.py:141-149` |
| 13 | Delete flow | ⚠️ partial | desktop-API level ✅ (`test_project_management_desktop_api_tasks_bulk_assign.py:174,177`); repo tenant-scoping ✅; **no test of `remove_dependency`'s `DEPENDENCY_NOT_FOUND`, governed-approval branch, or activity record** |
| 14 | Update / edit flow | ❌ **NO TEST FOUND — largest single gap.** | grepped `update_dependency`/`updateDependency` across all of `src/` — **zero occurrences under `src/tests/`**, at every layer (service, both desktop APIs, both presenters, both controllers) — despite being fully live UI (§8) |
| 15 | Authorization / tenant isolation | ✅ best-covered item | project-scope: `test_phase0a4_other_safety_corrections.py:97-104,107-127`; cross-org read: `test_repository_tenant_hardening_priority.py:78-80`; cross-org write: `:118-119,130,159-168`; scope-contract shape: `test_phase0c_repository_scope_ids.py:74-92`; governance: `test_phase_b_approval_workflow.py::test_dependency_add_requires_and_applies_approval:70-97`. Minor gap: `TENANT_CONTEXT_REQUIRED` untested for the Task→Task repo specifically |
| 16 | CPM date calculations | ✅ | `test_cpm_flow.py` (ES/EF/critical); `test_technical_math_reporting_scheduling.py` (all 4 types incl. Gantt cross-check and reactive-to-new-dependency test) |
| 17 | Actual-date interaction | ❌ **NO TEST FOUND for the interaction** | the one actual-date test uses a single task with **no dependencies at all** — the predecessor-actual→successor-date and one-sided-floor-discard behaviors are entirely unverified |
| 18 | Constraint interaction | ❌ **NO TEST FOUND** | the only constraint test file (`src/tests/pm/test_constraint_validator.py`) uses `MagicMock` CPM infos with exactly one task in every single case — no dependency object appears anywhere in that file |
| 19 | Leveling interaction | ⚠️ partial | ✅ `test_resource_leveling_workflow.py::test_manual_resource_leveling_rejects_task_with_successors:82-94`; **gap: the auto-leveling tests in the same file create no dependencies at all** |

### Summary of hard test gaps (repeated for visibility, matches §1 executive summary)

Negative lag/lead, multiple predecessors combining constraints, the
update/edit flow end to end, actual-date × dependency interaction,
constraint × dependency interaction. All five have **zero** coverage at any
layer.

---

## 22. Missing Tests

(Explicit list, derived from §21, for direct use in R4.4 planning — not new
rules, just naming what to write.)

1. Negative lag/lead for each of FS/SS/FF/SF, including the FS `lag=-1` vs
   `lag=-2` degenerate-plateau case documented in §5.
2. `update_dependency` at every layer: service-level type/lag change, the
   governance-bypass behavior (does it actually skip approval under
   `PM_GOVERNANCE_MODE=required`?), the non-atomic commit-then-sync ordering
   under a simulated mid-sync failure, and the dead-cycle-check path.
3. Multiple predecessors of mixed types on one successor (e.g. one FS + one
   SS) — assert the actual combined ES, not just that *a* date was produced.
4. Actual-date × dependency: predecessor `actual_end` pulling a successor's
   FS/FF date; a successor `actual_start` earlier than its dependency-derived
   ES (verify the one-sided-floor "discard" behavior is actually intended).
5. Constraint × dependency conflict: MSO/MFO that would place a task before
   its FS predecessor's finish — assert what the persisted schedule and the
   `ConstraintValidator` output actually are (today: silent override, no
   report — a test would pin this as documented current behavior even before
   any fix).
6. Auto-leveling (not just manual) against a dependency-linked project, and a
   direct test of the §13 finding that a leveled shift on a
   dependency-connected task is reverted by the next `recalculate_project_schedule`.
7. 4+ hop indirect cycle, and the `SCHEDULE_CYCLE` scheduling-time backstop
   path specifically.
8. `remove_dependency`'s `DEPENDENCY_NOT_FOUND` raise, its governed-approval
   branch, and its activity-record write.
9. Concurrency: two concurrent `update_dependency` calls on the same row
   (confirm last-write-wins with no error); a concurrent delete-after-delete
   (confirm the "succeeds" response despite deleting nothing).
10. A query-count regression guard on `api/desktop/scheduling/api.py`'s
    project-wide dependency read (to catch the §17 N+1 if it worsens, and to
    prove it when it's fixed).

---

## 23. Current UX Gaps

1. Task Detail's "Lag" column shows a linked-task UUID, not the lag value
   (§19) — the single most visible/confusing defect for an end user.
2. Predecessor/successor direction is only distinguishable via a column
   literally headed "Status" in Task Detail (§19); the Scheduling workspace's
   parallel read-only table gets this right with a dedicated "Direction"
   column, so the two surfaces are inconsistent with each other.
3. Edit and Delete mutation errors are silently discarded by the QML layer —
   a failed edit or delete gives no in-context feedback to the user, unlike
   Create (§19).
4. No in-row edit/delete affordance in the Task Detail dependency table — both
   require selecting a row first and using a separate contextual action bar;
   the section's own `deleteRequested` signal is dead code (§8, §19).
5. Terminology is inconsistent across the three surfaces that touch this
   concept (Task Detail dialog, Task Detail table, Scheduling table):
   predecessor/successor is named "Predecessor"/"Successor" as row data,
   "Current task depends on other task" in the create dialog, "Status" as a
   Task Detail column header, and "Direction" as a Scheduling column header;
   the linked task itself is called "Linked task," "Task," and "Related
   Activity" depending on which screen; two independent, currently-identical
   but structurally free-to-drift label maps exist for the type names; the
   lag field label differs between the two dialogs that edit it ("Lag Days"
   vs "Lag (days)"), as does its input validation (one has a numeric input
   mask, the other doesn't).
6. No dependency visualization (lines/arrows) anywhere in the app, and no
   Planning workspace exists at all (§20) — the Scheduling timeline shows
   bars and criticality color but no relationships between them.
7. The Scheduling workspace's fully-built create/edit/delete dependency
   capability is entirely unreachable from any QML — a real backend feature
   with zero UI (§20).
8. The impact-preview ("this change will shift these N tasks by this many
   days") feature implied by the diagnostics engine's existence does not
   actually reach any user, anywhere, today (§17, §18) — despite ~370 lines of
   application code existing to compute it.

---

## 24. Backend Gaps

1. **No optimistic concurrency on `TaskDependency`** — no version column, no
   version-checked update, no rowcount check on delete (§16).
2. **`update_dependency` bypasses governance/approval entirely** and is the
   only one of the three mutation flows that is non-atomic (§8).
3. **Negative lag is accepted with zero validation at every layer** and is
   non-monotonic for FS (§2, §5).
4. **The backward CPM pass is a correct inverse of the forward pass only for
   FS** — SS/FF/SF are off by one working day, and mixed-successor-type tasks
   silently drop SS/SF late-date constraints entirely (§11).
5. **Hard constraints silently override dependency-driven dates with no
   warning**, and the validator meant to catch this checks
   already-overridden output, making the check structurally dead on the live
   path (§12).
6. **`CPMCalculator` (used by the portfolio view) applies zero scheduling
   constraints**, while the live `SchedulingEngine` (used by dashboard/desktop)
   applies all of them — the same project can show two different schedules
   depending on which screen is open (§11, §12).
7. **Leveling shifts on any dependency-connected task are silently reverted
   by the very next schedule recalculation** (§13).
8. **Four duplicated hand-written implementations of the same dependency date
   math**, one of which (`DependencyResolver`) is dead code whose docstring
   is the codebase's most explicit lead/lag specification — meaning the
   closest thing to a spec for negative-lag behavior is unreachable from the
   live system (§11, §17).
9. **A genuine N+1** in the Scheduling workspace's project-wide dependency
   read (`2N+1` queries), despite an efficient single-query repository method
   already existing and simply not being exposed on the application service
   (§17).
10. **A full synchronous CPM recompute plus ~3N task writes on every single
    dependency mutation**, with no debounce, dirty-flag, or diffing (§17).
11. **The cycle-check branch of `update_dependency` is dead code** because
    the duplicate check short-circuits first (§8).
12. **The approval-apply path for `add_dependency` re-validates nothing** —
    no permission check, no project-scope check, no diagnostics — a TOCTOU
    hole for two concurrently-approved requests (§8, §10).
13. **No `dependency_cycle` at-rest integrity-check category** exists, unlike
    the analogous categories for self/cross-project/duplicate (§9).
14. **No `IntegrityError` translation** on the dependency command path — a
    duplicate-pair race leaks a raw SQLAlchemy exception to the user instead
    of the clean `DEPENDENCY_DUPLICATE` code (§16).
15. **The rich `DependencyDiagnostic` impact-preview model never reaches a
    desktop DTO** and is called with `include_impact=False` at both of its
    two call sites — effectively dead application logic (§17, §18).

---

## 25. Decision Points for R4.4

These are framed as decisions, not recommendations — R4.4 planning should make
an explicit call on each, informed by the evidence above.

1. **Fix the lag-unit/off-by-one bugs (§5, §11) before or alongside building
   leveling on top of CPM?** These bugs corrupt float and critical-path
   accuracy today, independent of leveling. Building R4.4's leveling logic
   against a CPM engine that already has an inconsistent notion of "how late
   can this task be" risks baking the same inconsistency into leveling
   decisions.
2. **Which CPM implementation is "the" implementation going forward?**
   `SchedulingEngine` is authoritative today; `CPMCalculator` is a stale
   duplicate used only by one portfolio read path and is missing constraint
   support entirely; `DependencyResolver` is dead. R4.4 should either
   consolidate onto one implementation or explicitly document why three
   survive.
3. **Does R4.4 leveling get to move a task that has dependencies at all?**
   Today's leveling avoids this entirely by refusing any task with a
   successor — which is also why leveling is largely inert (§13). If R4.4
   changes this, the dependency-consistency check that doesn't exist today
   (§12) becomes load-bearing rather than optional.
4. **Promote `ResourceLevelingEngine` to the live path, or keep
   `ResourceLevelingMixin`?** The existing planning doc
   (`docs/pm_modernization/README.md`, Implementation Order step 6) already
   claims this was done; it was not (§17, §13) — `ResourceLevelingMixin` is
   still what `SchedulingEngine` inherits and what `DashboardService` calls.
   If `ResourceLevelingEngine` is promoted, its `commit_actions` needs a
   dependency re-check added (§13, finding 5), since today it has none.
5. **Should `update_dependency` gain governance parity with add/remove, or
   should governance be explicitly scoped to exclude type/lag edits?** Right
   now it's an accidental gap, not a decision (§8, §24-2).
6. **Is one relationship-type-per-ordered-pair (the `ux_task_dependencies_pair`
   constraint, §3) the intended long-term model, or should R4.4 allow
   `A-FS→B` and `A-SS→B` to coexist?** This is currently enforced by a DB
   index with no accompanying product documentation — worth making an
   explicit call before more UI is built assuming one behavior or the other.
7. **Does R4.4 need the impact-preview feature (`DependencyDiagnostic`,
   `include_impact=True`) at all?** ~370 lines of application code already
   implement it and are fully unreachable from production. Either wire it up
   (it would directly serve R4.4's "warn before this dependency change shifts
   N tasks" needs) or remove it as dead weight — leaving it as-is (tested only
   by unit tests, never called in production) is the worst of both options.
8. **Fix or formally accept the `add_dependency`/`update_dependency`/
   `remove_dependency` performance profile (§17) before scaling target project
   sizes?** The existing modernization README's own stated target is "up to
   5,000 interactive tasks per project" — at that scale the current ~3N-write
   CPM persist loop and the Scheduling workspace's `2N+1` read are each
   thousands of statements per single dependency edit.
9. **Concurrency control: add a `version` column to `TaskDependency` now, or
   accept last-write-wins as a documented limitation for R4.4's scope?**
   Given R4.4 is explicitly about leveling (which will itself mutate
   schedules concurrently with users editing dependencies), this is a
   reasonable point to close the gap rather than defer it further.

---

## 26. Recommended Dependency-Work Sequence (informational — no implementation performed)

This ordering is offered as a starting point for scoping R4.4/related work; it
is not a plan the audit was asked to author in detail, and nothing in it has
been implemented as part of this pass.

1. **Correctness fixes with no architectural risk** (small, mechanical, high
   value): the SS/FF/SF lag-unit and backward-pass off-by-one bugs (§11); the
   mixed-successor-type late-date-discard bug (§11); the `update_dependency`
   non-atomic commit ordering and its dead cycle-check branch (§8). These are
   bugs in already-shipped behavior, not new scope.
2. **Concurrency and governance parity** (§16, §8/§24-2): add a version
   column and version-checked update/delete to `TaskDependencyRepository`;
   decide and implement governance parity for `update_dependency`.
3. **Constraint/dependency consistency reporting** (§12): at minimum, make the
   silent MSO/MFO-over-dependency override *visible* (a warning, a flagged
   row, something) before any leveling work starts moving tasks around a
   graph that already has this class of silent conflict.
4. **Decide the fate of `CPMCalculator`, `DependencyResolver`, and the
   impact-preview engine** (§25 items 2, 7) — consolidate, wire up, or
   deliberately delete, rather than carrying three-and-a-half implementations
   of the same math into R4.4.
5. **Only then**, build R4.4 leveling against a CPM foundation whose
   dependency semantics are internally consistent and whose leveling-safety
   guarantees (today: "never touch a task with a successor") are being
   *deliberately* relaxed rather than accidentally broken.
6. **UX cleanup** (§23) — the "Lag" column bug, error-surfacing on edit/delete,
   terminology consistency — can proceed in parallel with any of the above; it
   has no scheduling-correctness dependency.
7. **Performance** (§17, §24-9/-10) — the N+1 and the ~3N-write CPM persist
   loop — should be addressed before or alongside any change that increases
   how often dependency mutations happen (which leveling changes plausibly
   will, if it starts actively rebalancing a dependency-aware graph).

---

## 27. Current-State Diagram

```
   Task A                                   Task B
     │                                        │
     │  TaskDependency                        │
     │  predecessor_task_id = A.id            │
     │  successor_task_id  = B.id             │
     │  dependency_type ∈ {FS,SS,FF,SF}        │
     │  lag_days: int (unbounded, incl. <0)    │
     ▼                                        ▼
┌──────────────────────────────────────────────────────────┐
│ VALIDATION (application layer only — §9, §10)             │
│  domain/tasks/task.py           → DEPENDENCY_SELF          │
│  tasks/queries/dependency_diagnostics.py:                  │
│    self (73) → exists (88,101) → cross-project (112)       │
│    → duplicate (135) → CYCLE via BFS (156, _find_path)     │
│  NOT enforced in DB except: unique(pred,succ) pair index,   │
│  CASCADE FKs. NOT enforced: self-dependency CHECK,          │
│  cross-project CHECK, cycle (impossible in SQL DDL).        │
└──────────────────────────────────────────────────────────┘
     │  (validated, persisted — commands/dependency.py)
     ▼
┌──────────────────────────────────────────────────────────┐
│ SCHEDULING ENGINE (authoritative: SchedulingEngine — §11)  │
│  forward pass:  ES_succ = f(type, pred ES/EF, lag, calendar)│
│    FS: add_working_days(EF_pred, lag+2)                     │
│    SS: add_working_days(ES_pred, lag)      ← off-by-one     │
│    FF: back-solved from add_working_days(EF_pred, lag)      │
│    SF: back-solved from add_working_days(ES_pred, lag)      │
│    fan-in: ES = max(all candidate ES)                        │
│  backward pass: correct inverse only for FS (§11)            │
│  ACTUALS override planned dates here, before CONSTRAINTS     │
│  CONSTRAINTS (MSO/MFO) override the result AFTER, silently,  │
│    with no consistency check against the dependency (§12)    │
│  CALENDAR: EnterpriseCalendarResolver via 3 different         │
│    wrappers depending on entry point (§7) — can disagree      │
└──────────────────────────────────────────────────────────┘
     │  persisted onto Task.start_date / end_date
     ▼
┌──────────────────────────────────────────────────────────┐
│ RESOURCE LEVELING (§13 — today: refuses any task with a     │
│  successor; never reads dependency_type/lag_days; a shift   │
│  on a dependency-connected task is reverted by the very      │
│  next recalculation above)                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 28. Decision Table

Filled only with findings proven above; "Correct?" reflects whether the
*current* behavior matches a defensible target semantics, not whether the
capability exists at all.

| Capability | Backend | QML | Correct? |
|---|---|---|---|
| FS | ✅ implemented, calendar-aware | ✅ create/edit/delete all reach it | ✅ semantics verified correct (exclusive, pinned by test) |
| SS | ✅ implemented | ✅ | ❌ lag off-by-one vs FS; `lag=0`/`lag=1` indistinguishable; backward pass not a true inverse |
| FF | ✅ implemented | ✅ | ❌ same off-by-one family as SS; back-solve unconditional in the diagnostics preview (diverges from `CPMCalculator`) |
| SF | ✅ implemented (contrary to an initial, corrected assumption) | ✅ | ❌ same off-by-one family; collapses to SS's formula for zero-duration tasks |
| Lag | ✅ persisted, calendar-aware | ✅ editable in both dialogs | ⚠️ unit inconsistent across types (§5); no unit field |
| Lead (negative lag) | ✅ accepted, unvalidated | ✅ accepted, unvalidated | ❌ non-monotonic for FS; zero test coverage; the one file documenting it (`DependencyResolver`) is dead code |
| Create dependency | ✅ full chain, atomic, governed (governance off by default) | ✅ | ✅ correct, including cycle/duplicate/self/cross-project rejection and confirmation UX |
| Edit dependency (type/lag only) | ✅ reachable, but non-atomic and ungoverned | ✅ | ❌ bypasses approval gating; commits before schedule sync; dead cycle-check branch; zero test coverage |
| Delete dependency | ✅ full chain, atomic, confirmed via dialog | ✅ via detail-panel action bar only | ⚠️ correct backend behavior; the section's own delete signal is dead QML code |
| Cycle prevention | ✅ BFS over full project graph, catches indirect cycles | — | ⚠️ correct at creation time; **TOCTOU gap on the approval-apply path**; no at-rest integrity-check category |
| Cross-project protection | ✅ application-layer rejection | — (QML pre-filters, doesn't enforce) | ⚠️ correct in the only live path; **not enforced in DB or repository** — a direct repository call could still create one |
| Calendar-aware lag | ✅ yes | — | ❌ three different CPM entry points use three different calendar wrappers that can disagree with each other |
| Constraint interaction | ✅ resolved (constraint wins) | — | ❌ silent, unconditional override with no warning; the validator meant to catch it structurally cannot |
| Leveling preserves graph | ✅ cannot mathematically violate a dependency minimum today | — | ❌ only because leveling refuses any task with a successor, making it largely inert; a leveled shift on a dependent task is silently reverted by the next recalculation anyway |
| Concurrency control | ❌ none | — | ❌ no version column; last-write-wins; concurrent delete reports false success |
| Multiple predecessors | ✅ `max()` reduction | — (no over-constraint warning surfaced) | ⚠️ mechanically consistent but untested for mixed types; no conflict warning |
| Multiple successors | ✅ no limit, efficient single-query fetch | ✅ | ✅ |
| Query/read model | ✅ repository is efficient; ✅ Task Detail read path is efficient and lazy | — | ❌ Scheduling workspace's project-wide read is a confirmed N+1 (`2N+1`), despite an efficient method existing one layer down |
| Mutation performance | ⚠️ correct, but expensive | — | ❌ ~3N task writes + full synchronous CPM recompute on every single create/edit/delete, no debounce |
| Authorization / tenancy | ✅ enforced in SQL for tenant/org | — | ⚠️ correct for tenant/org; project-scope checks are conditionally fail-open on a shared "no scope rows ⇒ allow all" primitive, and successor's project is never scope-checked on create |
| Desktop DTO fidelity | ⚠️ 9 fields exposed | ⚠️ several fields mis-rendered | ❌ "Lag" column shows a UUID in Task Detail; predecessor/successor endpoints not both exposed as discrete fields; rich diagnostic model never exposed at all |
| Dependency visualization | — | ❌ not implemented anywhere | ❌ no Planning workspace exists; no dependency lines/arrows anywhere in the app |
| Scheduling workspace dependency CRUD | ✅ fully built (`createDependency`/`updateDependency`/`deleteDependency` on `SchedulingWorkspaceController`) | ❌ never called by any QML | ❌ orphaned backend capability |

---

## Appendix — Secondary code-quality defects noted in passing

Not requested by the audit's numbered sections, but surfaced during the
tracing above and worth a mention for whoever picks up R4.4 work in these
files:

- `application/scheduling/cpm/graph.py:11` annotates `tasks_by_id: Dict[str,
  Task]` but only `Callable` is imported from `typing` — harmless today only
  because `from __future__ import annotations` defers evaluation; would
  `NameError` under any runtime-annotation tooling.
- `application/scheduling/cpm/passes.py:118-119` indexes `ls[succ_id]`/
  `lf[succ_id]` directly rather than via `.get()` — safe today only because
  `graph.py` pre-filters dependencies to tasks present in `tasks_by_id`.
- `application/scheduling/cpm/results.py:34` mutates the caller's
  `tasks_by_id` dict in place, undermining the "no mutation" contract
  `cpm_calculator.py:81` otherwise tries to establish via `_task_snapshot`.
- Calendar-binding failures are swallowed with bare `except Exception: pass`
  in two places in `scheduling_engine.py` (§7) — a broken enterprise calendar
  degrades to the global calendar with no operator-visible signal.
