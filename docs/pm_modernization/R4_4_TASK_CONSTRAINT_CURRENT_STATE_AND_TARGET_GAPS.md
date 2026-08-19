# R4.4 Task Scheduling Constraints — Current State & Target Gaps

**Read-only audit. No code was modified. No resource leveling changes were made or proposed for implementation.**

Scope: Task-level scheduling constraints (`ConstraintType` enum + `Task.constraint_type`/`constraint_date`), as distinct from the already-modernized dependency foundation (FS/SS/FF/SF semantics, canonical calendar, `run_cpm`, Task Detail → Dependencies, Task Detail → Schedule Impact) and from the Milestone feature (`is_milestone`), neither of which is re-audited here.

---

## 1. Executive Summary

The constraint *engine* is real, correctly layered, and reasonably well-tested at the unit level for the cases it covers. The constraint *feature*, from a product standpoint, **does not exist today** — there is no way for a user, an importer, or any application/desktop command to ever set a task's `constraint_type`/`constraint_date`. Every production write-site for these two fields in the entire repository is a test fixture. The one constraint that *is* live and user-reachable is `DEADLINE`, which is really just `Task.deadline` (a separate, ordinary, persisted field) being fed into the same validator.

Concretely:

- **7 real enum values exist**: `MUST_START_ON`, `MUST_FINISH_ON`, `START_NO_EARLIER_THAN`, `START_NO_LATER_THAN`, `FINISH_NO_EARLIER_THAN`, `FINISH_NO_LATER_THAN`, `DEADLINE`. **No `ASAP`/`ALAP` enum member exists anywhere.** "ASAP" is simply the absence of a constraint (pure dependency-derived scheduling); "ALAP" does not exist as a concept in this codebase at all — not partially, not as dead code, not as a QML label. It must be built from scratch if wanted for R4.4.
- Of the 7 real types, only **4 drive the forward CPM pass** (MSO, MFO, SNET, FNET). The other 3 (SNLT, FNLT, DEADLINE) are validation-only — they can report a violation but never move a date.
- **The backward pass never reads any constraint field at all.** Total float, free float, and criticality are computed purely from the dependency graph and `project_early_finish` — a constraint can silently make a task's own float number meaningless (e.g., its LF was never re-anchored to its own MUST_FINISH_ON date) without any code path noticing.
- **Persistence for `constraint_type`/`constraint_date` is entirely absent** — not merely unwired at the application layer, but orphaned at *every* layer: the DB columns exist from a 2024-era migration, but `TaskORM` doesn't map them, the ORM↔domain mapper doesn't read/write them, and `TaskRepository.update`'s explicit write-column list omits them. A task can never carry a real constraint across a save/reload cycle even if something in-memory set one.
- **Resource leveling has zero awareness of any constraint type, including `DEADLINE`.** It is a blind, greedy, forward-only 1-working-day shift per iteration; nothing stops it from pushing a task's dates past any constraint, hard or soft, real or hypothetical. This is the central fact R4.4 must design around.
- The desktop/QML stack has a real, live, tested "Constraint Violations" panel in the Scheduling workspace fed by `ConstraintValidator`, but because nothing can populate `constraint_type`/`constraint_date` in production, that panel can currently only ever show `DEADLINE` violations. Task Detail has no constraint UI at all. A separate, unrelated "Constraints" panel elsewhere in Scheduling doesn't read the real enum at all — it synthesizes plausible-looking rows from `start_date`/`deadline`/`actual_start`/`actual_end`, which is a UI correctness risk (§34).
- Terminology has no single source of truth: three different consumers render the same enum value three different ways (title-cased, raw snake_case, or a hand-written English string that doesn't derive from the enum at all).

**Bottom line for R4.4**: leveling can be designed today only against `DEADLINE` and, if the product wants the other 6 types to matter, R4.4 (or a preceding slice) must first (a) wire `constraint_type`/`constraint_date` through the ORM/mapper/repository, (b) add an application/desktop mutation path with governance/concurrency parity to how dependencies are handled, and (c) decide whether the backward pass needs to become constraint-aware before leveling can make trustworthy float-based decisions. None of this exists yet.

---

## 2. Constraint Domain Model

`Task` (`src/core/modules/project_management/domain/tasks/task.py`, a `@validated_dataclass` — pydantic-backed) declares, in order (lines 33-45):

```python
start_date: date | None = None
end_date: date | None = None
duration_days: int | None = None
status: TaskStatus = TaskStatus.TODO
priority: int = 0
percent_complete: float = 0.0
actual_start: date | None = None
actual_end: date | None = None
deadline: date | None = None
constraint_type: str | None = None
constraint_date: date | None = None
is_milestone: bool = False
version: int = 1
```

`constraint_type` is a **plain `str | None`**, not typed as `ConstraintType` — the real enum lives one layer up, in the application/scheduling module (§3), and every consumer duck-types the string. `constraint_date` is a plain `date | None`.

**Subtle, real gap found**: `constraint_type` is routed through the shared `_normalize_text_fields` validator (`task.py:103-106`, shared with `code`/`description`):
```python
@field_validator("code", "description", "constraint_type", mode="before")
def _normalize_text_fields(cls, value: object) -> str:
    return normalize_optional_text(value)
```
`normalize_optional_text` (`src/core/platform/common/pydantic.py:30-31`) is `str(value or "").strip()`. **This means `constraint_type` can never actually hold `None` after pydantic validation runs — a `None` input is coerced to `""`.** The type annotation (`str | None`) is therefore misleading; in practice the field is always a string, empty or not. This doesn't break `apply_scheduling_constraints`'s `if raw_ct is None or cd is None: return est, eft` guard in the way it looks like it should — `"" is None` is `False`, so an unset constraint actually falls through to the `ConstraintType(str(""))` call, which raises `ValueError`, caught by an `except ValueError: return est, eft` one line later — so the *practical* outcome (no-op) is identical, but it happens via the wrong branch of a two-branch guard that looks like it's checking for "unset" when it's actually relying on "invalid enum string" to catch the unset case too. `constraint_date` has no such validator, so it genuinely can be `None`.

There is **no field validator restricting `constraint_type` to the real enum's values**, and **no cross-field validator** anywhere in `Task` (the existing `_validate_date_ranges` model_validator at `task.py:137+` checks `start_date`/`end_date`/`deadline` ordering, plus the `is_milestone`→duration normalization added for the Milestone feature, but never references `constraint_type`/`constraint_date`). A task can be constructed with `constraint_type="MUST_START_ON"` and no `constraint_date`, or `constraint_type="garbage"`, with zero domain-level rejection.

---

## 3. Constraint Enum / Supported Types

The real, single enum is `ConstraintType` — `src/core/modules/project_management/application/scheduling/cpm/constraint_validator.py:13-20`:

```python
class ConstraintType(str, Enum):
    MUST_START_ON = "must_start_on"
    MUST_FINISH_ON = "must_finish_on"
    START_NO_EARLIER_THAN = "start_no_earlier_than"
    START_NO_LATER_THAN = "start_no_later_than"
    FINISH_NO_EARLIER_THAN = "finish_no_earlier_than"
    FINISH_NO_LATER_THAN = "finish_no_later_than"
    DEADLINE = "deadline"
```

| Enum name | Persisted value | Human label (as actually rendered anywhere) | Requires date? | Default | Validated? | Hard/soft (per code) | User-settable today? | Used in production today? |
|---|---|---|---|---|---|---|---|---|
| (none / ASAP) | — | — | no | implicit default (no constraint) | n/a | n/a | n/a — it's the absence of a value | **Yes** — every task with no constraint set behaves this way |
| (none / ALAP) | **does not exist** | — | — | — | — | — | — | **No — not implemented at all**, not even as dead code |
| `MUST_START_ON` | `"must_start_on"` | "Must Start On" (one serializer) / raw `"must_start_on"` (another) / `str(ConstraintType.MUST_START_ON)` bug-prone (a third) | yes | n/a | no enum-membership check anywhere upstream of the two consumers that parse it | Hard (`hard_violations`, `constraint_validator.py:71`) | **No** — no writer exists outside tests | **No** — never persisted (§4) |
| `MUST_FINISH_ON` | `"must_finish_on"` | same three-way inconsistency | yes | n/a | same | Hard | No | No |
| `START_NO_EARLIER_THAN` | `"start_no_earlier_than"` | same | yes | n/a | same | **Soft** (`soft_violations`, `constraint_validator.py:82`) — despite actually moving the schedule (§8) | No | No |
| `START_NO_LATER_THAN` | `"start_no_later_than"` | same | yes | n/a | same | Hard (`hard_violations:73`) — despite never moving the schedule (§9) | No | No |
| `FINISH_NO_EARLIER_THAN` | `"finish_no_earlier_than"` | same | yes | n/a | same | Soft (`soft_violations:83`) | No | No |
| `FINISH_NO_LATER_THAN` | `"finish_no_later_than"` | same | yes | n/a | same | Hard (`hard_violations:74`) | No | No |
| `DEADLINE` | `"deadline"` | "Deadline" | n/a — reads `task.deadline` directly, not `constraint_date` | n/a | n/a | Hard (`hard_violations:75`) | **Yes** — via `task.deadline`, a real, separate, persisted field | **Yes** — the only live type |

Note the hard/soft split (`constraint_validator.py:68-85`) is inverted relative to what a reader would naively expect from "which ones actually move the schedule" — see §5.

---

## 4. ORM / Database Model

`constraint_type`/`constraint_date` are **orphaned at every persistence layer**, confirmed end-to-end:

- **Migration**: `src/infra/persistence/migrations/versions/i2j3k4l5m6n7_pm_enterprise_upgrade.py:27-29` did add `tasks.constraint_type`/`tasks.constraint_date` DB columns (plus an index) as part of the original enterprise-upgrade migration.
- **ORM model**: `TaskORM` (`src/core/modules/project_management/infrastructure/persistence/orm/task.py:34-90`) does **not** declare either as a `mapped_column`. Its mapped attributes run `id`...`deadline`...`is_milestone`...`version` — `constraint_type`/`constraint_date` are simply absent from the class body.
- **Mapper**: `task_to_orm`/`task_from_orm` (`src/core/modules/project_management/infrastructure/persistence/mappers/task.py:9-52`) never read or write either field in either direction.
- **Repository write path**: `TaskRepository.update` (`infrastructure/persistence/repositories/tasks/task.py:75-101`) calls `update_with_version_check(..., {"project_id": ..., ..., "deadline": task.deadline, ...}, ...)` with an explicit column dict — `constraint_type`/`constraint_date` are not in that dict.

**Practical consequence**: even if a future code path set `task.constraint_type = "must_start_on"` in memory and called `task_repo.update(task)`, it would be silently dropped — no error, no persistence, and the very next `task_from_orm(...)` reload would produce a `Task` with `constraint_type=""` (per §2's normalizer) again. The DB columns from the original migration are dead weight — present in the schema, never read or written by any ORM path.

- **Can `constraint_date` exist without a type?** Only via direct dataclass construction bypassing all real write paths (test fixtures do this) — no validation prevents it (§2).
- **Can a type requiring a date be stored without one?** Same answer — nothing prevents it in memory; moot for persistence since nothing persists either field.
- **Can ASAP/ALAP carry an irrelevant date?** N/A — neither exists as a settable value; "ASAP" is `constraint_type` being empty/unset, which by definition carries no date.
- **DB CHECK constraints**: none found referencing `constraint_type`/`constraint_date` (only unrelated `CheckConstraint`s on `tasks` for `parent_task_id`/`sort_order`/`wbs_code`, confirmed by reading the full `TaskORM.__table_args__`).
- **Migration history**: one migration only (`i2j3k4l5m6n7`), never revisited or completed with ORM wiring in any later migration.
- **Legacy/null behavior**: every row's `constraint_type`/`constraint_date` DB columns are simply never touched by the app — whatever null/default the original migration left them at is permanent from the application's point of view.

**DB integrity gap identified**: a real schema/ORM mismatch — columns exist in the database that the ORM model doesn't know about. This is not merely "unused," it's a latent trap: any future migration or raw-SQL tooling that assumes `TaskORM`'s column set matches the table's actual columns would be wrong.

---

## 5. Constraint Date Semantics (hard vs. soft, normalization)

**Hard/soft is an explicit code-level category**, not inferred: `ConstraintValidationResult.hard_violations`/`soft_violations` (`constraint_validator.py:67-85`):
- Hard: `MUST_START_ON`, `MUST_FINISH_ON`, `START_NO_LATER_THAN`, `FINISH_NO_LATER_THAN`, `DEADLINE`.
- Soft: `START_NO_EARLIER_THAN`, `FINISH_NO_EARLIER_THAN`.

**This classification measures violation severity for reporting, not "does it move the schedule."** Cross-referencing against §7 (forward-pass driving types — MSO, MFO, SNET, FNET): SNET and FNET *do* move the schedule (they're forward-pass-driving) yet are labeled "soft," while SNLT and FNLT *never* move the schedule (validation-only) yet are labeled "hard." The hard/soft split is about how strictly a *deviation* should be treated in reporting (a task starting later than an SNET floor is "soft" because SNET's job was already done by moving the date forward — any remaining deviation is comparatively minor; a task finishing later than an FNLT ceiling is "hard" because nothing already prevented that overrun). This is a reasonable violation-severity model, but it is **not** the same axis as "minimum boundary / maximum boundary / exact pin / direction-only" that R4.4 will need for leveling decisions (§37).

Re-derived, purely from `apply_scheduling_constraints`/`ConstraintValidator` code, which constraints impose which kind of boundary:
- **Minimum boundaries** (floor): `START_NO_EARLIER_THAN`, `FINISH_NO_EARLIER_THAN` — schedule-driving.
- **Maximum boundaries** (ceiling): `START_NO_LATER_THAN`, `FINISH_NO_LATER_THAN`, `DEADLINE` — validation-only, never enforced by moving a date.
- **Exact pins**: `MUST_START_ON`, `MUST_FINISH_ON` — schedule-driving, unconditional override (§12/§13).
- **Direction-only (no boundary at all)**: none exist today — this is exactly the gap where ALAP would sit if it were built.

**Constraint date normalization — none exists.** Reading `apply_scheduling_constraints` (`task_date_math.py:144-189`) line by line: `cd = getattr(task, "constraint_date", None)` is used completely raw in every branch (`est = cd`, `eft = cd` for MSO/MFO; `est = cd`/`eft = cd` in the SNET/FNET floor branches) — there is no call to any working-day check (`is_working_day`/`next_working_day`) on `cd` itself anywhere in this function. The calendar is only used to project the *other* end of the span from `cd` (`calendar.add_working_days(cd, duration)`), never to validate or snap `cd`. `ConstraintValidator` doesn't check this either — it only computes working-day overrun *between* `cd` and the computed date, never asking whether `cd` itself is a working day. **So: a `MUST_START_ON` date of a Saturday is used exactly as given — the effective constraint becomes Saturday, not Monday, not Friday, and not an error.** No test exercises this scenario in either direction (confirmed by the test-coverage audit, §31/§32).

---

## 6. ASAP

Not a settable value — it is simply the state of `constraint_type` being unset/empty, in which case `apply_scheduling_constraints` returns `(est, eft)` unchanged (`task_date_math.py:161-162`, the `if raw_ct is None or cd is None: return est, eft` guard, which per §2 is practically reached via the `ValueError`-catch path for an empty string rather than a true `None` check, but the outcome is identical).

- **Is it the default?** Yes, by absence.
- **Does it require `constraint_date`?** N/A.
- **Does it simply accept dependency-derived earliest start?** Yes — whatever `compute_milestone_dates`/`compute_duration_dates` computed from the dependency graph passes through untouched.
- **Root tasks?** A root task (no incoming dependencies) with no `start_date` set gets `run_forward_pass`'s "unanchored root" fallback (documented in the Schedule Impact work, `R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md`) — orthogonal to constraints; no constraint code path is involved.
- **If `task.start_date` exists?** `compute_duration_dates`/`compute_milestone_dates` use it as a floor for a root task with no incoming deps — again orthogonal to the constraint functions, which never run for an unconstrained task.
- **`actual_start`?** Handled entirely by `apply_actual_date_constraints`, a separate function that runs before `apply_scheduling_constraints` — unrelated to "ASAP" as a constraint concept; this is just the normal actual-date override path (§18).
- **Backward pass?** No effect — there's nothing for the backward pass to react to.
- **Does ASAP affect float?** No — it's the baseline case float is computed relative to.
- **Does QML expose it?** No explicit "ASAP" label anywhere; it's simply what's shown when no constraint fields are populated (which, per §21, is always, today).

---

## 7. ALAP

**Does not exist in this codebase in any form** — not as an enum value, not as a partially-implemented code path, not as a QML label, not as a dead/legacy artifact. Confirmed by exhaustive grep across the constraint files, the CPM engine, and every QML file — zero hits for "ALAP," "as late as possible," or any synonym tied to scheduling semantics.

Consequently, none of the sub-questions in the original brief have current-code answers:
- How project finish is established: purely by the dependency graph's forward pass reaching `project_early_finish`, unrelated to any per-task "prefer late" concept.
- LS/LF placement: computed by `run_backward_pass` (§16) — this *is* the LS/LF machinery ALAP would need to hook into, but nothing hooks into it today.
- Whether ALAP modifies forward dates or only final placement: moot, no implementation exists.
- Interaction with total float: moot.
- Critical-path coherence: moot.
- Whether ALAP tasks can move after CPM: moot.
- **Used in production?** No — confirmed absent, not merely unused.

This is a **build-from-scratch** item if the product wants it, not a "wire up an existing implementation" item.

---

## 8. START NO EARLIER THAN (SNET)

`apply_scheduling_constraints`, `task_date_math.py:179-183`:
```python
elif ct == ConstraintType.START_NO_EARLIER_THAN:
    if est is None or est < cd:
        est = cd
        eft = calendar.add_working_days(cd, duration) if duration > 0 else cd
```

Exactly `max(dependency_ES, constraint_date)` in effect — confirmed by direct code, not inferred: the branch only fires when `est is None or est < cd`, i.e. it raises `est` up to `cd` **only when the dependency-derived date is earlier**; if the dependency-derived date is already later, it's left untouched. This is a true floor, matching the request's example formula. No calendar snapping of `cd` occurs (§5). `actual_start`/`duration`/`float`/backward pass: `apply_actual_date_constraints` runs *before* this in the call chain (§17), so a prior actual-date adjustment feeds into `est` here and can still be raised further by SNET; the backward pass never re-derives LS/LF from this — see §16 (float/criticality blind spot). Labeled "soft" in `ConstraintValidationResult` despite driving the schedule (§5).

---

## 9. START NO LATER THAN (SNLT)

**Confirmed: not a scheduling constraint at all in the forward pass — it is validation-only.** `apply_scheduling_constraints`'s own docstring states this explicitly (`task_date_math.py:152`: *"SNLT, FNLT, DEADLINE are validation-only -- reported by ConstraintValidator but never drive the forward-pass schedule"*), and there is no `elif ct == ConstraintType.START_NO_LATER_THAN` branch anywhere in that function — confirmed by reading the full function body (§5's quoted excerpt covers every branch that exists).

Applying the request's own example directly: if a dependency implies B's earliest start is 10 Sep and B has `START_NO_LATER_THAN = 8 Sep`, **the current behavior is neither "reject" nor "silently move B before its dependency" — it's a third outcome: B is scheduled at 10 Sep (the dependency wins, unconditionally) and `ConstraintValidator.validate()` separately reports a `START_NO_LATER_THAN` violation** (`constraint_validator.py:190-193`, `if deadline is None and est and est > cd: violations.append(...)` — actual code checks `est > cd`) as a **hard violation** — but this is purely informational; nothing in the schedule itself reflects an "infeasible" state, no exception is raised, no flag is set on the task, and the schedule that gets persisted (if this task's dates were ever committed) is the 10-Sep date, silently exceeding the ceiling every time CPM runs, forever, unless something acts on the violation report (nothing currently does — §25, §33). This is the closest the current system comes to "expose an infeasible/conflicting schedule," and it is a report, not an enforcement.

---

## 10. FINISH NO EARLIER THAN (FNET)

`task_date_math.py:184-187`:
```python
elif ct == ConstraintType.FINISH_NO_EARLIER_THAN:
    if eft is None or eft < cd:
        eft = cd
        est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd
```

A true floor on finish, symmetric to SNET: fires only when the dependency-derived finish is earlier than `cd`. For a duration-bearing task, the finish boundary is back-solved to a start via `calendar.add_working_days(cd, -(duration - 1))` — this IS calendar-aware (it walks backward through the calendar's working-day arithmetic, same primitive used everywhere else in CPM), but `cd` itself is used raw with no working-day check (§5). For a milestone (`duration <= 0`), `est = cd` directly — start and finish collapse to the same date, consistent with milestone semantics used throughout the CPM engine.

---

## 11. FINISH NO LATER THAN (FNLT)

**Also validation-only**, symmetric to SNLT (§9) — no `elif ct == ConstraintType.FINISH_NO_LATER_THAN` branch exists in `apply_scheduling_constraints`; confirmed by the same docstring and by exhaustively reading the function.

- Constrains latest finish? No — reported only, never enforced by moving a date.
- Overrides earliest finish? No.
- Reports violation? Yes — `ConstraintValidator._check_task` (`constraint_validator.py:194-197` region), classified as a **hard** violation.
- Changes float? No — the backward pass never reads it (§16), so LF/float are computed as if the FNLT ceiling didn't exist.
- Criticality differently? No — same reason.

This is flagged explicitly by the audit brief as important for leveling — confirmed: since FNLT is purely a report today, resource leveling (which is itself constraint-blind, §25) has literally nothing to consult even if it wanted to respect FNLT; the fact would have to be computed and threaded through as new plumbing, not merely "read an existing field."

---

## 12. MUST START ON (MSO)

`task_date_math.py:171-173`:
```python
if ct == ConstraintType.MUST_START_ON:
    est = cd
    eft = calendar.add_working_days(cd, duration) if duration > 0 else cd
```

- **Exact-date pin**: yes, unconditional — `est = cd` regardless of what the dependency graph or prior `est` value was.
- **Calendar normalization**: none — `cd` used raw (§5).
- **Non-working date behavior**: used as-is; no rejection, no snapping.
- **Dependencies requiring a later start**: MSO wins unconditionally, even overriding a later dependency-implied start — confirmed by direct trace (§17/§20 multi-predecessor scenarios): the branch has no comparison against the incoming `est` at all, unlike SNET/FNET which only override when beneficial.
- **`actual_start` differs**: MSO wins over a lone `actual_start` too — confirmed by tracing call order: `apply_actual_date_constraints` runs first and can raise `est` to `actual_start`, but `apply_scheduling_constraints` runs *after* and unconditionally sets `est = cd`, discarding that. This only stops if `actual_end` is also set (the whole function short-circuits at the top, `task_date_math.py:156-157`, before reaching the MSO branch) — i.e., MSO can override a *started* task's actual start, but not a *completed* one.
- **Conflict reported?** Yes, via `DependencyConstraintConflict`/`_check_dependency_conflict` (`constraint_validator.py:122-150`) — restricted (per its own docstring and confirmed by code) to MUST_START_ON/MUST_FINISH_ON overriding a dependency-implied date. Verified this also fires correctly for multi-predecessor cases (§20) since the capture point is the already-resolved multi-predecessor maximum, not a per-edge value.
- **Does CPM still compute float meaningfully?** No — per §16, the backward pass doesn't know MSO exists; LS/LF for this task and its whole successor chain are computed as if the pin weren't there. A task pinned earlier than its dependencies would need could show float relative to a backward-pass LS that assumes it could have started even earlier than the pin — a number that doesn't reflect reality.

---

## 13. MUST FINISH ON (MFO)

`task_date_math.py:175-177`:
```python
elif ct == ConstraintType.MUST_FINISH_ON:
    eft = cd
    est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd
```

Symmetric to MSO. Duration back-solving is calendar-aware via `add_working_days` (negative count), same primitive as FNET. Milestone behavior: `duration <= 0` collapses `est = cd` too. Dependency conflicts: covered by the same `_check_dependency_conflict`, restricted to MSO/MFO (confirmed, and confirmed this is enforced by code, not just docstring intent — the function's logic only branches on those two `ConstraintType` values). Actual finish: identical short-circuit as MSO — the whole `apply_scheduling_constraints` function returns early if `actual_end` is set, so MFO can never override a completed task's actual finish; it *can* still override a task that has only `actual_start` set (no `actual_end`), same asymmetry as MSO. Calendar normalization of `cd` itself: none, same as every other type (§5).

---

## 14. Calendar Interaction (project calendar authority)

Every constraint calculation in `apply_scheduling_constraints`/`apply_actual_date_constraints` receives its calendar as an explicit `calendar: CalendarProtocol` parameter, threaded from `SchedulingEngine._compute_task_dates` → `self._task_calendar` → `self._resolve_task_calendar(task.id)` (`scheduling_engine.py:307-318`), which resolves the **same** per-resource/per-project calendar authority (`self._calendar_resolver`/`self._resource_calendar_map`) already established for the canonical dependency-math primitives — confirmed no separate/legacy calendar object exists in the constraint code path. `pure_cpm.run_cpm`'s copy of this logic (`pure_cpm.py`) takes the same `calendar: CalendarProtocol` argument uniformly. `ConstraintValidator` is constructed with its own `calendar: CalendarProtocol` (`constraint_validator.py:102-103`) — worth noting this is a *second* calendar reference threaded independently rather than reusing the scheduling engine's resolved instance, but both are sourced from the same authoritative resolver by their respective callers (`constraint_builder.py`, `schedule_change_impact_service.py`), not from any old global/Mon–Fri fallback. No disagreement was found. The only calendar gap is the one already noted repeatedly: `cd` (the constraint date itself) is never run through any working-day check by either the scheduling code or the validator (§5).

---

## 15. Forward CPM Pass — exact order

Traced through `SchedulingEngine._compute_task_dates` (`scheduling_engine.py:272-305`) and `pure_cpm.py`'s equivalent (same shape, confirmed by the shared `compute_task_dates_common` helper in `date_compute.py`):

```
┌─────────────────────────────────────────────────────────────────────┐
│ _compute_task_dates(task, incoming_deps, es, ef)                    │
│                                                                       │
│  1. compute_task_dates_common(...)          [date_compute.py]       │
│     ├─ compute_milestone_dates / compute_duration_dates              │
│     │      → resolves ALL incoming dependency edges (any of         │
│     │        FS/SS/FF/SF) into ONE candidate via                    │
│     │        max(successor_boundary(...) for each edge)             │
│     │      → this is the dependency-derived (est, eft)              │
│     ├─ on_dependency_implied(est, eft)      [captured BEFORE        │
│     │      actuals/constraints get a chance to override it —        │
│     │      becomes CPMTaskInfo.dependency_implied_start/finish,      │
│     │      the basis for DependencyConstraintConflict AND for       │
│     │      actual-vs-planned variance reporting]                    │
│     └─ apply_actual_date_constraints(task, est, eft, duration)       │
│            → actual_end set: pins (est, eft) to actual dates,        │
│              short-circuits everything else downstream               │
│            → actual_start only: raises est floor to actual_start     │
│                                                                       │
│  2. apply_scheduling_constraints(task, est, eft)  [task_date_math.py]│
│     → skipped entirely if task.actual_end is set                     │
│     → MUST_START_ON / MUST_FINISH_ON: unconditional override         │
│     → START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN: raise-if-lower │
│     → START_NO_LATER_THAN / FINISH_NO_LATER_THAN / DEADLINE:         │
│         NOT HANDLED HERE — validation-only, no-op in this function   │
│                                                                       │
│  return (est, eft)  →  becomes this task's ES/EF                     │
└─────────────────────────────────────────────────────────────────────┘
```

So the proven order is: **dependencies → actuals → constraints** (constraints applied last, with the power to override both of the earlier steps, except when blocked by a completed `actual_end`). This matches the audit brief's second example ordering, not the first. This ordering is exactly why MSO/MFO can silently override both a dependency-implied date (§20) and a lone `actual_start` (§18) — each earlier step's output is just the input the next step is free to discard.

---

## 16. Backward CPM Pass — float, criticality

`run_backward_pass` (`src/core/modules/project_management/application/scheduling/cpm/passes.py:86-150`, read in full for this audit) takes `(tasks_by_id, topo_order, deps_by_predecessor, es, ef, project_early_finish, calendar)` — **no constraint or deadline field appears anywhere in its signature or body.** End-tasks (no outgoing deps) get `lf = project_early_finish`; every other task's LS/LF is derived purely by propagating backward through dependency edges (with the documented FS/FF vs. SS/SF normalization fix, `passes.py:117-136`, unrelated to constraints).

**Consequence, confirmed by code, not inference**: LS, LF, total float, free float, and criticality are computed as if `constraint_type`/`constraint_date`/`deadline` don't exist. A task pinned by MSO/MFO to a date earlier or later than its dependency graph would otherwise produce still gets an LS/LF computed from the unconstrained dependency graph — so its reported "total float" can be a number that has nothing to do with the actual room it has (or doesn't have) to move given its real pin. ALAP (§7), SNLT (§9), FNLT (§11), and DEADLINE (§19) are exactly the categories the brief called out as needing backward-pass awareness for correct CPM reporting — **none of them get any**. This is a structural gap, not a missing test — no amount of test-writing against current code can demonstrate a constraint changing backward-pass output, because the code cannot do that.

---

## 17. Dependency × Constraint Interaction

Combination behaviors, traced from code (not simulated), building on §15's proven call order:

| Combination | Dependency-implied date | Constraint-imposed date | Final computed date | Conflict fact produced? | Float/criticality impact |
|---|---|---|---|---|---|
| A FS→B, B SNET(date) later than implied | implied | later floor | constraint wins (raises est) | No — `_check_dependency_conflict` only fires for MSO/MFO | Backward pass unaware either way |
| A FS→B, B SNET(date) earlier than implied | implied | earlier floor | **dependency wins** (SNET is a floor, doesn't lower) | No | none |
| A FS→B, B SNLT(date) earlier than implied | implied | ceiling (unenforced) | **dependency wins** — SNLT never drives scheduling | No (SNLT isn't in `_check_dependency_conflict`'s scope — MSO/MFO only); a plain `ConstraintValidator` violation is reported separately, not a `DependencyConstraintConflict` | none |
| A FS→B, B MSO(date) earlier than implied | implied | pin | **constraint wins unconditionally** | **Yes** — `DependencyConstraintConflict` (confirmed: `test_constraint_dependency_conflict.py:72`) | none (backward pass blind) |
| A FF→B, B MFO(date) | implied via FF boundary | pin | constraint wins | Yes (confirmed: `test_constraint_dependency_conflict.py:116`) | none |
| Mixed predecessors (FS+SS+FF) + hard constraint on the successor | resolved to ONE value first (`compute_duration_dates` takes `max()` across all incoming edges before constraints ever run) | pin/floor applied to that resolved value | see §20 | Yes for MSO/MFO, verified correct even with 3 predecessors (§20) | none |

**No SS/SF combination is exercised by any existing test against any constraint type** (confirmed by the test-coverage audit, §32) — only FS (with MSO) and FF (with MFO) are tested.

---

## 18. Actual-Date Interaction

**Actual start, no actual end** (`apply_actual_date_constraints`, `task_date_math.py:136-139`): if `a_start > est`, raises `est` to `a_start` (recomputing `eft` from duration). This happens *before* `apply_scheduling_constraints` runs. Consequence, traced precisely:
- vs. `SNET`/`FNET`: whichever is later wins by the normal floor logic, since both are just successive floor-raises on the same `est`.
- vs. `MSO`: **MSO wins over a lone `actual_start`** — confirmed by call order; the constraint function runs after and unconditionally overwrites `est`, with no check preserving a prior actual-start-derived value (only `actual_end` triggers the short-circuit that would prevent this).
- vs. dependency-implied start: same relationship as above — `actual_start` is folded in as one more floor-raise before constraints get the final say.

Does `actual_start` "replace," "floor," "generate variance," or "generate constraint violation"? **It floors** (raises `est` if higher, never lowers it) — confirmed by the exact conditional `if est is None or a_start > est`. Separately, **it does generate variance reporting** — this is the mechanism `find_dependency_actual_variances` (used by Task Detail → Schedule Impact, per the earlier Schedule Impact work) already covers, comparing `actual_start` against dependency-required dates; that mechanism is unrelated to `ConstraintType` and was not re-audited here (out of scope per the brief). It does **not** generate a `ConstraintValidator` violation on its own — the validator only compares final computed dates against `constraint_type`/`constraint_date`/`deadline`, never against `actual_start` directly.

---

## 19. Actual Finish Interaction

**`actual_end` set** (`apply_actual_date_constraints:126-134`): `eft` is pinned to `actual_end` unconditionally; `est` becomes `actual_start` if present, else back-solved from duration. Critically, this happens *before* the check in `apply_scheduling_constraints` (`task_date_math.py:156-157`) that says `if task.actual_end is not None: return est, eft` — i.e., **once a task is complete, the entire scheduling-constraints function is a no-op**, regardless of `constraint_type`. This means:
- `FNET`/`MFO`: cannot override a completed task's actual finish — confirmed, the short-circuit happens before any constraint branch is reached.
- `FF`/`SF` dependencies into this task: irrelevant once complete — the actual dates are authoritative, matching the general principle (established in the earlier dependency-modernization work) that actual dates are historical truth.
- No test combines `actual_end` with any `ConstraintType` (confirmed, §32) — this precedence (actual completion beats every constraint type unconditionally) is real, correct-looking behavior, but entirely unverified by any test.

---

## 20. Multiple Predecessors + Constraint

Traced precisely through `compute_duration_dates`/`compute_milestone_dates` (`task_date_math.py:33-106`) and `_check_dependency_conflict` (`constraint_validator.py:122-150`):

**D has A(FS)→D, B(SS)→D, C(FF)→D, plus D: SNET(date) earlier than what all three require.** Step 1 of the forward pass (§15) already collapses all three incoming edges into a single `est` via `max()` over each edge's converted boundary — dependency type (FS/SS/FF) is fully resolved before constraints ever see the task. Since SNET's `cd` is earlier than this already-resolved `est`, the floor check (`est < cd`) is false — **the 3-way dependency maximum wins**, unchanged.

**Same three predecessors, D: MSO(date) earlier than all three require.** MSO's unconditional-override branch fires regardless of the incoming `est` — **the constraint wins**, discarding what all three dependencies required. `_check_dependency_conflict` **does** fire correctly here, confirmed by reading its logic against `CPMTaskInfo.dependency_implied_start` (`application/scheduling/models/cpm.py`): the captured "dependency-implied" value used for comparison is the *already-resolved, post-max* value from step 1, not a single edge's value — so the conflict check is inherently correct for any number of predecessors, not just the single-predecessor case the existing tests happen to exercise. This is a case where the implementation is more general than its test coverage suggests.

**Actual_start (no actual_end) + MSO with a different date**: per §12/§18, MSO wins — confirmed by the same call-order tracing (`apply_actual_date_constraints` runs first, `apply_scheduling_constraints`'s MSO branch runs after and unconditionally overwrites).

---

## 21. `DependencyConstraintConflict`

Restricted, by both docstring and enforced code logic, to `MUST_START_ON`/`MUST_FINISH_ON` only (`_check_dependency_conflict`, `constraint_validator.py:122-150`) — SNET/SNLT/FNET/FNLT/DEADLINE never produce this fact, only a separate `ConstraintViolation` if applicable. Exact fields returned (`constraint_validator.py:35-55`): `task_id`, `task_name`, `constraint_type`, `constraint_date`, `dependency_required_date`, `direction` (`"start"`/`"finish"`), `difference_working_days` (signed — positive means the constraint pulled the task earlier than required, negative means later), `code="DEPENDENCY_CONSTRAINT_CONFLICT"`. It is explicitly **non-blocking** — a reported fact, not a raised error (confirmed by its own docstring and by the absence of any exception-raising in `_check_dependency_conflict`); scheduling proceeds using the constraint-driven date regardless. Verified correct for multi-predecessor cases (§20). Schedule Impact does expose it correctly as the "conflicts" driver in `TasksScheduleImpactSection.qml` — but renders the **raw** `constraint_type` value with no humanization (e.g. literally `"must_start_on"` in the UI message), unlike the Scheduling workspace's separate violations table which does title-case it (§27-30 for the full QML trace).

---

## 22-24. Actual/Completed-Task Interaction (started-but-not-finished, completed)

Covered precisely in §18/§19 for the CPM math. Summary for the two states the brief asks about specifically:

- **Started, not finished** (`actual_start` set, `actual_end` unset): planned finish IS still recalculated (only `est` is floored to `actual_start`; `eft` is recomputed from duration each pass). Constraints still apply to both start and finish in this state — MSO/MFO/SNET/FNET can all still override, since the `actual_end is not None` short-circuit hasn't triggered. Start CAN still move (constraints or later dependency changes can raise it further). Duration is handled the same as any in-progress task (recomputed from the floored start).
- **Completed** (`actual_start` and `actual_end` both set): `apply_scheduling_constraints` is a total no-op (`task_date_math.py:156-157`) — dates are left exactly as `apply_actual_date_constraints` pinned them (`eft = actual_end`, `est = actual_start`). CPM does NOT report constraint/dependency violations against a completed task differently from an active one — `ConstraintValidator.validate()` runs the identical check against whatever the final `es`/`ef` ended up being, regardless of completion state; there is no special-case skip for completed tasks in the validator (only in the forward-pass constraint-application function). This means a completed task whose actual dates happen to violate its own `deadline`/`SNLT`/`FNLT` will still show up as a violation in the Scheduling workspace panel — which is arguably correct (it did finish late) but is not something any test confirms.

---

## 25. Deadlines vs. Constraints

`task.deadline` is a **wholly separate field** from `constraint_type`/`constraint_date`, confirmed: `apply_scheduling_constraints` never reads `task.deadline` at all (its entire body only inspects `constraint_type`/`constraint_date`). `ConstraintValidator._check_task` checks `deadline` **independently and unconditionally**, producing its own `ConstraintType.DEADLINE` violation, alongside (not instead of) whatever `constraint_type`-driven violation may also exist on the same task. Both `DEADLINE` and `FINISH_NO_LATER_THAN`/`MUST_FINISH_ON` land in `hard_violations` — but `deadline` and `FNLT`/`MFO` are otherwise unrelated fields that happen to express a similar idea (a finish ceiling/pin) through entirely separate code paths and, in `deadline`'s case, a genuinely different, actually-persisted field. **`deadline` never affects CPM/forward-pass scheduling** — confirmed absent from `apply_scheduling_constraints` — it is purely a reporting fact, exactly like FNLT.

---

## 26. Baseline vs. Constraint

Confirmed **absent and one-directional**. `BaselineService._apply_baseline_creation_decision` (`application/scheduling/baselines/baseline_service.py:142-246`) reads the live CPM schedule snapshot (`earliest_start`/`earliest_finish`/duration/planned_cost) and copies it into immutable `BaselineTask` rows — it never reads `task.deadline`/`constraint_type`/`constraint_date`. Nothing anywhere in the codebase reads a baseline snapshot back into current CPM or constraint calculations (grepped for any deadline/baseline cross-reference — zero hits). The relationship is exactly current-schedule → baseline archive, never the reverse; no accidental coupling exists.

---

## 27. Resource Leveling Interaction

**Two implementations exist; only one is live.** `ResourceLevelingMixin` (`application/scheduling/leveling/leveling_mixin.py`), mixed into `SchedulingEngine`, is reachable from `DashboardService.auto_level_overallocations`/`manually_shift_task_for_leveling`. `ResourceLevelingEngine` (`resource_leveling_engine.py`) is a standalone duplicate with identical logic and zero callers outside its own tests — **dead code**, but analyzed too since either could become the R4.4 starting point.

**Algorithm shape**: a greedy, iterative, **forward-only, fixed 1-working-day shift** per iteration (`shift_working_days=1` hardcoded), not a real candidate-date search. Each iteration: find the single worst resource/day overload → pick one task off it (sorted by `percent_complete`, then priority, then start date) → shift that task forward by exactly one working day → persist immediately → re-scan from scratch, up to 60 iterations. There is no computation of alternate candidate dates, no search for the nearest resource-free slot, and no post-shift re-check that the move actually resolved the conflict for that specific task.

**Constraint awareness — grepped and read in full, zero references to `constraint_type`/`constraint_date`/`deadline`/`ConstraintType` anywhere in any leveling file.** No guard of any kind ("task has hard constraint → skip") exists for any of the 7 real constraint types, nor for `DEADLINE`/`deadline` specifically. For every single constraint type — including the one that's actually live in production (`DEADLINE`) — the current algorithm **could** push a task's dates past it, because nothing checks. The only reason SNET/FNET (floors) wouldn't currently be "violated" by a forward-only shift is that a forward push can't violate a *minimum* — an accidental non-violation, not an enforced one, and one that would immediately stop holding if leveling ever gained the ability to shift backward.

**Candidate search inputs actually consulted**: `actual_start`/`actual_end` (excludes a task from candidacy — treated identically whether merely started or fully completed, no distinction), calendar (for iterating workdays and computing the shift), resource capacity (`capacity_percent` scales the conflict threshold). **Not consulted at all**: constraint minimum/maximum/exact-date (none exist), dependency-derived minimum start (only the *existence* of a successor is checked as an exclusion gate — the actual dependency-implied date/type/lag is never read).

**Leveling + SNET/FNLT/MSO/MFO/ALAP scenarios** (from the brief, §29-32): since no constraint field is ever read, the answer to every one of these hypothetical scenarios is the same — the algorithm has no mechanism to reject, flag, or route around a constraint violation; it would shift the task and commit, unconditionally, exactly as it does today for a completely unconstrained task. There is no "exclude constrained tasks" list, no "shift other tasks around them" logic, and no "report unresolved conflict" output distinct from the ordinary conflict-reduction loop. ALAP specifically (§32) is moot since it doesn't exist as a concept anywhere (§7), so there is nothing for leveling to interact with.

**Other exclusion guards found** (useful precedent for how a future constraint-aware guard could be structured): outgoing-successor existence (crude — only checks *outgoing* edges, not incoming), `actual_start`/`actual_end` presence, `percent_complete > 0.0`, `start_date is None`, and summary/parent tasks being excluded structurally via `select_leaf_tasks` before leveling ever sees them. No `is_milestone`/`is_summary`/manual-pin flag is checked directly in the leveling files themselves. Priority is used only as a tie-breaking sort key among already-eligible candidates, never as an exclusion threshold.

**Existing tests are entirely constraint-agnostic** — three test files (`test_resource_leveling_workflow.py`, `test_dashboard_leveling_flow.py`, `test_leveling_dependency_boundary.py`) cover resource-capacity shifting, dependency-successor exclusion, and event emission, but none ever sets `constraint_type`, `constraint_date`, or `deadline` on any task, and none set `actual_start`/`actual_end` either — the exclusion behavior for actual dates exists in production code with zero direct test coverage.

One additional, directly relevant finding from `test_leveling_dependency_boundary.py`: a leveling shift on a task with an *incoming* dependency is silently reverted by the very next `recalculate_project_schedule` call, because CPM ignores a task's persisted `start_date` whenever it has a usable incoming dependency. This is a pinned regression test, not a fix — it documents that leveling's writes and CPM's reads can already disagree today, independent of constraints, and is worth keeping in mind when designing how R4.4 leveling and constraint-aware CPM should cooperate.

---

## 28. Governance / Mutation Flow

**There is no mutation flow to trace for `constraint_type`/`constraint_date`** — confirmed by an exhaustive search (every desktop scheduling file, `lifecycle.py`'s `create_task`/`update_task`, `TaskCreateCommand`/`TaskUpdateCommand`, every QML file in the Tasks module, and the full ORM/mapper/repository chain) that no application command, desktop command, QML dialog, or importer ever constructs or persists these two fields outside test fixtures. The DB columns from the original migration are orphaned (§4) — there is no ORM mapping to even receive a value if one were somehow set.

For `deadline` (the one real, settable, comparable field): mutation flow is QML → `PMTaskListController.updateTask` → `TaskUpdateCommand` → desktop API → `TaskLifecycleMixin.update_task` → `replace()` → `TaskRepository.update` (version-checked) → commit → `domain_events.tasks_changed.emit(...)`.

- **Governance**: dependency mutations are explicitly governed — `add_dependency`/`remove_dependency`/`update_dependency` (`application/tasks/commands/dependency.py`) check `is_governance_required(...)` against a fixed allowlist (`DEFAULT_GOVERNED_ACTIONS = {"baseline.create", "dependency.add", "dependency.remove", "dependency.update", "project_cost.approve"}`, `policy.py:6-12`) and route through an approval service with request-time/apply-time re-validation when governed. **`update_task` (deadline changes) has zero references to governance/approval anywhere** — it commits immediately regardless of `PM_GOVERNANCE_MODE`. There is no `"task.update"` or `"deadline.*"` governed action defined. **This is a real, documented gap**: changing a deadline (which, per §11/§25, can shift what the Scheduling workspace reports as a hard violation, and which will eventually matter to leveling) participates in none of the same governance machinery dependency changes do.
- **Optimistic concurrency**: `expected_version` IS threaded through `update_task` for deadline changes (`lifecycle.py:140-144` checks `task.version != expected_version` before building the replacement), and `TaskRepository.update` performs the real DB-level version-checked write. If `constraint_type`/`constraint_date` mutation existed on the same `Task` aggregate/update path, it would naturally inherit this same protection — provided someone also adds the two fields to the repository's explicit write-column list (§4's gap), which today would silently drop any value even if the rest of the write path were wired up.
- **Events/invalidation**: `update_task`/`create_task` emit only the generic `domain_events.tasks_changed` signal, which every workspace controller subscribes to generically and responds to with a full workspace-list rebuild (`do_refresh`). **Deadline edits use the generic `_request_domain_refresh` facade, not the targeted one** — only `PMDependencyController` was given a dedicated `refresh_after_dependency_mutation` callback (built earlier this session) that force-reloads the open Task Detail sections (Dependencies, Schedule Impact, the selected row). A deadline edit does not reset the "already loaded" flags on those lazy sections, so if a user has Schedule Impact or Dependencies open while editing a deadline, those panels will not reflect the new deadline's effect on drivers/violations until the user navigates away and back into Task Detail. **This is the exact class of staleness bug already fixed for dependency mutations earlier in this project — the fix was never extended to the task-update/deadline path.**

---

## 29. Performance

No dedicated constraint-specific performance harness exists, and none is needed as a separate concern: constraint evaluation (`apply_scheduling_constraints`) runs as an O(1) extra step per task inside the same single forward CPM pass whose performance characteristics are already documented (`R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md` §15 — one non-persisting `run_cpm` pass, no per-task repository calls). `ConstraintValidator.validate()` is a second O(n) pass over the already-computed schedule dict, called once per `list_constraint_violations`/`get_task_schedule_overview`/preview request — not per task, not N+1. Since `constraint_type`/`constraint_date` are never populated in production today (§4/§21), there is currently zero real-world extra cost being paid for the 6 non-DEADLINE types; the only constraint-adjacent cost actually incurred today is one extra `deadline` comparison per task inside `_check_task`, negligible next to the CPM pass itself. No changed-task-diff optimization exists for constraint validation specifically, but none is needed at current scale since the whole validator run is already O(n) over leaf tasks and is triggered on-demand (workspace refresh / Schedule Impact load), not on every keystroke.

---

## 30. Desktop DTOs

Only **one** desktop DTO is shaped for constraints: `SchedulingConstraintViolationDto` (`api/desktop/scheduling/models/constraints.py:6-19`) — carries both the raw enum value (`constraint_type`) and a display label (`constraint_type_label`), plus `constraint_date`/`constraint_date_label`, `computed_date`/`computed_date_label`, `overrun_working_days`, a ready-to-display `message` string, and `severity`/`severity_label`. Trace: `ConstraintValidator.validate()` → `ConstraintViolation` → `serialize_constraint_violation` (title-cases the enum value) → `build_constraint_violations` (runs the validator over every leaf task in the project, returns `.violations` only, never `.dependency_conflicts`) → `ProjectManagementSchedulingDesktopApi.list_constraint_violations` → presenter → Scheduling workspace QML.

**No DTO exists for `DependencyConstraintConflict` at all.** It reaches the desktop layer only through a *different* feature's DTO, `ScheduleConflictDto` (`api/desktop/scheduling/models/change_impact.py:66-74`, belonging to Task Detail → Schedule Impact) — which has **no** `_label` companion field, so it ships the raw `constraint_type.value` straight to QML with no humanization at all (confirmed rendered as literal `"must_start_on"` in `TasksScheduleImpactSection.qml:277`). The two DTOs never share a code path — `ConstraintValidator(...).validate(...)` is called independently, from scratch (a fresh CPM run each time), at both `constraint_builder.py:21` (project-wide) and `schedule_change_impact_service.py:261,365` (task-scoped) — no shared cache, no single source of truth.

---

## 31. Task Detail QML

**Confirmed, by exhaustive search across every dialog/section file in `qml/workspaces/tasks/`** (`TaskEditorDialog.qml`, `TasksDependenciesSection.qml`, `TasksScheduleImpactSection.qml`, `TasksDetailPanel.qml`, `TasksWorkspacePage.qml`, `TasksWorkspaceState.qml`, `TasksDialogHost.qml`, and every other dialog/section/component under that tree): **`TaskEditorDialog.qml` has zero references to any constraint keyword** (constraint, MSO, MFO, SNET, SNLT, FNET, FNLT, or their spelled-out forms). There is no field, dropdown, checkbox, or date picker anywhere in Task Detail that lets a user view or edit `constraint_type`/`constraint_date`. The only constraint-adjacent content anywhere in the Task Detail tree is `TasksScheduleImpactSection.qml`'s read-only conflict/driver display (§21/§33), which shows raw, unlabeled values, not an editor.

**Answering the brief's direct question**: today the user cannot understand ASAP/ALAP/SNET/SNLT/FNET/FNLT/MSO/MFO from Task Detail at all, in any form, labeled or raw — there is simply no surface for it there.

---

## 32. Scheduling Workspace QML

Two independent, differently-scoped, differently-sourced panels both plausibly answer to "Constraints," which is itself worth flagging as a naming/architecture ambiguity:

**a) "Constraint Violations" panel** (`SchedulingDiagnosticsPanel.qml`) — a project-wide, read-only `DataTable` (columns: activity, constraint type, required date, computed date, overrun days, severity), fed by exactly the `list_constraint_violations`/`build_constraint_violations`/`ConstraintValidator` path (§30). This IS the real thing — humanized labels ("Must Start On", "Hard Constraint"), one row per (task, violation) across every leaf task, no create/edit affordance, only a "Refresh Diagnostics"/"Run CPM" action.

**b) A second, task-scoped "Constraints" panel** (`SchedulingDetailPanel.qml`'s `constraintTableModel`, built by `presenters/scheduling/detail_builder.py`) — **does not read `task.constraint_type`/`constraint_date` at all.** It synthesizes plausible-looking rows purely from `start_date` ("Planned Start"), `deadline` ("Finish No Later Than" — see the mislabeling issue in §34), `actual_start` ("Actual Start Locked"), `actual_end` ("Actual Finish Locked"). It is structurally disconnected from the real `ConstraintType` enum/validator machinery entirely.

Both are read-only; neither has editing capability; the backend HAS a serialize/build path with no orphaned edit capability behind it (there's no hidden write endpoint waiting to be wired up — the write path simply doesn't exist anywhere, §28).

---

## 33. Schedule Impact QML

`TasksScheduleImpactSection.qml` surfaces constraint-adjacent facts in two places, both read-only, no simulation runs automatically:
- **Drivers**: `build_schedule_drivers()` (`task_schedule_overview.py:184-227`) DOES read the real `constraint_type`/`constraint_date` duck-typed fields (lines ~207-216) and would append a `kind="constraint"` driver — but since these fields are never populated in production, this branch is dead in practice, and unlike the validator/scheduling-constraints functions, it has **no enum validation guard at all** — if it ever fired with an invalid raw value, it would render whatever garbage string was stored, uncaught.
- **Conflicts**: the real `DependencyConstraintConflict` mechanism (§21), reused via a second, independent `ConstraintValidator(...).validate(...)` call scoped to the single selected task, rendered with the raw unlabeled `constraint_type.value` (e.g. literal `"must_start_on"`) in the conflict message — inconsistent with the Scheduling workspace's labeled rendering of the identical underlying data (§34).

Confirmed this does not duplicate CPM math (it reuses `ConstraintValidator`) and does not duplicate the Scheduling workspace's data pipeline (they're two independent call sites producing differently-formatted output from the same validator class).

---

## 34. Existing Tests

See §31's full matrix (reproduced from the dedicated test-coverage audit) — condensed here:

| Constraint | Domain | Forward CPM | Backward CPM/float | Dependency (FS/SS/FF/SF) | Actuals | Calendar | Conflict | Mutation | QML | Leveling |
|---|---|---|---|---|---|---|---|---|---|---|
| MUST_START_ON | GOOD | GOOD | MISSING (structural) | PARTIAL (FS only) | MISSING | MISSING | GOOD | MISSING (structural) | MISSING | MISSING |
| MUST_FINISH_ON | not found | GOOD | MISSING | PARTIAL (FF only) | MISSING | MISSING | GOOD | MISSING | MISSING | MISSING |
| START_NO_EARLIER_THAN | GOOD (soft) | not found | MISSING | MISSING | MISSING | MISSING | N/A | MISSING | MISSING | MISSING |
| START_NO_LATER_THAN | GOOD | N/A (validation-only) | MISSING | MISSING | MISSING | MISSING | N/A | MISSING | MISSING | MISSING |
| FINISH_NO_EARLIER_THAN | not found | not found | MISSING | MISSING | MISSING | MISSING | N/A | MISSING | MISSING | MISSING |
| FINISH_NO_LATER_THAN | not found | N/A (validation-only) | MISSING | MISSING | MISSING | MISSING | N/A | MISSING | MISSING | MISSING |
| DEADLINE | GOOD | N/A (validation-only) | MISSING | MISSING | MISSING | MISSING | N/A | GOOD (field itself) | MISSING | MISSING |

"MISSING (structural)" means no test *could* show the behavior because the code path doesn't exist (backward pass, persistence) — not merely an oversight.

Real test files: `src/tests/pm/test_constraint_validator.py` (11 tests, pure validator unit tests, mocked calendar), `src/tests/project_management/dependency/test_constraint_dependency_conflict.py` (4 tests, real `run_cpm`, MSO+FS and MFO+FF only), `src/tests/project_management/dependency/test_schedule_change_impact_extensions.py` (1 relevant test — task-scoped conflict surfacing, MSO+FS only), `src/tests/project_management/dependency/test_task_schedule_overview.py` (1 test whose name mentions "constraint" but never actually sets one — the constraint-driver branch is untested despite the test's name).

---

## 35. Missing Tests

Concrete gaps, verified by reading the test files (not inferred):
- FS + `START_NO_EARLIER_THAN`, FS + `START_NO_LATER_THAN` (only MSO+FS and MFO+FF exist).
- Any SS/SF combination with any constraint type — zero exist.
- Multiple predecessors + a constraint (all existing tests use a single edge; §20's multi-predecessor analysis is code-trace-only, unverified by any test).
- `actual_start` + `MUST_START_ON`, `actual_end` + `MUST_FINISH_ON` together (the "which one wins" behavior in §12/§13/§18/§19 is entirely unverified by test, despite being a genuinely interesting, non-obvious interaction).
- A `constraint_date` falling on a non-working day, in either direction — confirmed the code has no guard either way (§5), and confirmed no test exercises it.
- `FINISH_NO_EARLIER_THAN`/`FINISH_NO_LATER_THAN` domain-validator branches specifically (only SNET/SNLT/MSO/MFO/DEADLINE get direct validator tests; the two FNET/FNLT branches in `_check_task` are untested).
- ALAP + dependency — moot, ALAP doesn't exist.
- Leveling + SNET, leveling + FNLT, leveling + MSO/MFO — zero tests; leveling tests never set any constraint field at all (§27).
- A completed task's `ConstraintValidator` behavior — confirmed by code that violations are still checked/reported for completed tasks (§22-24), but no test demonstrates this.
- An invalid/unknown `constraint_type` string is the ONE combination that IS tested (`test_constraint_validator.py`'s `test_unknown_constraint_type_string_is_silently_ignored`) — included here only for completeness against the brief's explicit list.

---

## 36. Backend Defects

1. **`constraint_type`/`constraint_date` are fully unreachable in production** (§4/§28) — no ORM column mapping despite DB columns existing, no mapper, no repository write, no application/desktop command, no QML, no importer. This is the central defect underlying nearly every other finding in this report.
2. **Domain field type mismatch**: `constraint_type: str | None` can never actually be `None` after pydantic validation (`normalize_optional_text` coerces `None`→`""`) — the "is unset" check downstream relies on catching the resulting `ValueError` from an invalid empty-string enum lookup, not on a clean `None` check, even though the code visually looks like it's checking for `None` (§2).
3. **Backward pass is fully constraint-blind** (§16) — float/LS/LF/criticality for a constrained task (hypothetically) or a `deadline`-bearing task (actually, today) are computed as if the constraint/deadline doesn't exist. This will directly affect any R4.4 leveling logic that relies on float to decide what's safe to move.
4. **Constraint dates are never checked against the working-calendar** (§5) — a MUST_START_ON/MUST_FINISH_ON/SNET/FNET date landing on a weekend/holiday is used exactly as given, with no rejection or snapping, in either the scheduling function or the validator.
5. **Governance parity gap**: deadline changes (the one live constraint-adjacent mutation) participate in none of the approval/governance machinery dependency changes do (§28) — despite being capable of flipping a task from compliant to violating a hard constraint.
6. **Stale-UI risk on deadline edits**: unlike dependency mutations (fixed earlier this project via `refresh_after_dependency_mutation`), a deadline edit only triggers the generic workspace-list refresh — open Task Detail Schedule Impact/Dependencies panels do not reflect the new deadline's effect until the user leaves and re-enters Task Detail (§28).
7. **`build_schedule_drivers`'s constraint-driver branch has no enum validation guard** (§33), unlike every other consumer of `constraint_type` — if it ever fired with a garbage value, it would render it uncaught (currently unreachable in practice, but a latent gap).

---

## 37. UI/UX Defects

1. **Two same-named "Constraints" panels in the Scheduling workspace read from entirely different, unrelated data models** (§32) — one is the real `ConstraintType`/validator pipeline, the other synthesizes rows from unrelated plain fields (`start_date`/`deadline`/`actual_start`/`actual_end`) and never touches the real enum at all. A user (or future developer) has no way to tell these apart by name alone.
2. **The second "Constraints" panel actively mislabels data**: it displays "Finish No Later Than" for *any* task with a `deadline` set, regardless of whether that task has an actual `FINISH_NO_LATER_THAN` constraint (which, per §4, can never exist in production today) — this is a plausible-looking label attached to the wrong underlying fact (§27's finding, `constraint_label_for_activity`, `presenters/scheduling/formatters.py:46-55`).
3. **Terminology inconsistency across the same underlying data**: the Scheduling workspace's violations table shows "Must Start On" (title-cased); Task Detail → Schedule Impact's conflict banner, for the *exact same* `DependencyConstraintConflict.constraint_type` value, shows the raw `"must_start_on"` (§21/§30) — because `ScheduleConflictDto` has no label field and nothing downstream humanizes it.
4. **No user-facing surface anywhere exposes the abbreviations or full names** the brief's target terminology calls for (ASAP/ALAP/SNET/SNLT/FNET/FNLT/MSO/MFO) — confirmed by grep across all QML and code strings; these forms exist only in code identifiers and documentation, never in a rendered string.
5. **Task Detail has no constraint UI at all** (§31) — a user cannot view, let alone edit, a task's constraint even if one somehow existed.

---

## 38. Dead / Duplicate Code

- **`ResourceLevelingEngine`** (`resource_leveling_engine.py`) is a complete standalone duplicate of `ResourceLevelingMixin`'s logic, with zero callers outside its own tests — dead code (§27). Not deleted per this audit's read-only mandate; flagged for a future cleanup pass, same treatment as prior "delete proven dead code" phases in this project.
- **At least four distinct places interpret constraint-related task state**, only two of which key off the real `ConstraintType` enum with validation:
  1. `apply_scheduling_constraints` (the real forward-pass math, one implementation, confirmed not duplicated — `SchedulingEngine`'s wrapper and `pure_cpm.run_cpm` both call the same function).
  2. `ConstraintValidator._check_task`/`_check_dependency_conflict` (a second, independent hand-written interpretation of the same seven values, for post-hoc reporting — not derived from #1, semantics duplicated by hand across the two files).
  3. `constraint_label_for_activity` (`presenters/scheduling/formatters.py:46-55`) — a **third, semantically-independent** interpretation that doesn't read `ConstraintType` at all, inventing its own priority order from `actual_end`/`actual_start`/`deadline`/`start_date`. Live, reachable, used by two other files, but completely untested and disconnected from the real model (§37 UI defect #2).
  4. `build_schedule_drivers`'s constraint-driver branch — a fourth interpretation, reads the real fields but with no enum validation (§33/§36).
- **Five enum→label mapping sites, no shared source of truth** (§30/§37): title-casing (`constraint_serializer.py`), raw passthrough with no transform (`task_schedule_overview.py`, `change_impact_serializer.py`), and hand-written English strings unrelated to the enum (`formatters.py`). No canonical "Must Start On (MSO)"-style label function exists anywhere.
- **No dead QML**: confirmed no `.qml` file anywhere references `ConstraintType`/`constraint_type` at all — there is no orphaned/unreachable constraint-editing QML lying around; the absence is total, not a dead leftover.
- **DB columns from the original migration are orphaned** at the ORM layer (§4) — not "dead code" in the traditional sense, but dead schema.

---

## 39. Current Precedence Model

Derived purely from the traced code (§15/§17/§18/§19), presented as the actual, proven order — not the brief's example, confirmed to match reality:

```
dependency graph (FS/SS/FF/SF, resolved via max() across ALL incoming edges)
        ↓
actual-date constraints (actual_start floors est; actual_end pins both and
        short-circuits everything below)
        ↓
task scheduling constraints (MSO/MFO: unconditional override, even of the
        above; SNET/FNET: floor-only, raises but never lowers; SNLT/FNLT/
        DEADLINE: NOT APPLIED HERE — validation-only)
        ↓
final ES/EF  (this is what the forward pass produces)
        ↓
backward pass / float / criticality (dependency graph ONLY —
        constraints/deadline have NO influence here at all; this is a
        separate, parallel computation that never re-reads the forward
        pass's constraint decisions)
        ↓
ConstraintValidator.validate() (post-hoc, reads final ES/EF + constraint_type/
        constraint_date + deadline together; produces ConstraintViolation
        [all 7 types + deadline] and DependencyConstraintConflict [MSO/MFO
        only, compared against the pre-constraint dependency-implied date
        captured back at step 1])
```

The critical, non-obvious fact this diagram makes explicit: **the backward pass is not "after" the forward pass in a way that lets it react to constraints** — it's a structurally separate computation that happens to run after, but never consumes the forward pass's constraint-driven overrides as an input to LS/LF logic. Any future constraint-aware leveling work needs to either (a) make the backward pass constraint-aware, or (b) treat float/criticality as untrustworthy for constrained tasks and compute feasibility a different way (§40, question 10).

---

## 40. Decisions Required for R4.4

1. **Which constraints are absolute/immovable?** Per code: `MUST_START_ON`/`MUST_FINISH_ON` are the only types that unconditionally override everything upstream of them (dependencies, a lone `actual_start`). Nothing currently stops leveling (or anything else) from moving them anyway, though — "immovable" today describes their effect on the *forward pass*, not any protection against being *reassigned*.
2. **Which are minimum boundaries?** `START_NO_EARLIER_THAN`, `FINISH_NO_EARLIER_THAN` (schedule-driving floors) — plus, arguably, `DEADLINE`/`FINISH_NO_LATER_THAN`/`START_NO_LATER_THAN` in the sense that they're semantically ceilings, but they impose no boundary on the *schedule itself* today (validation-only).
3. **Which are maximum boundaries?** `START_NO_LATER_THAN`, `FINISH_NO_LATER_THAN`, `DEADLINE` — semantically, but currently enforced as reports, not schedule limits.
4. **Which merely change scheduling direction?** None exist today — this is exactly ALAP's slot, and ALAP doesn't exist (§7).
5. **Which can resource leveling move?** Today: all of them, unconditionally, because leveling reads none of them (§27) — this question has no nuanced answer yet; it's uniformly "leveling doesn't know any of this exists."
6. **Which should cause leveling to choose another task instead?** Not decided in code; no such logic exists. Precedent exists for *how* such a guard would be wired (the existing `actual_start`/`actual_end`/successor-existence exclusion checks in `leveling.py`/`leveling_mixin.py`, §27) — a constraint guard would most naturally slot in next to those.
7. **Which should allow movement but report violation?** Arguably matches today's SNLT/FNLT/DEADLINE model (report without enforcing) — but that model exists in the *CPM validator*, not in leveling, which doesn't call the validator at all today.
8. **How should infeasible dependency+constraint combinations be represented?** Today: silently, via `DependencyConstraintConflict` (MSO/MFO only) or a plain `ConstraintViolation` (everything else) — never as a raised error, never as a blocked schedule (§9/§17).
9. **How should actual dates override/violate planned constraints?** Today: a completed task (`actual_end` set) always wins over every constraint type, unconditionally (§19); a merely-started task (`actual_start` only) can still be overridden by MSO/MFO (§18) — this asymmetry is real, traced, and unverified by any test, and worth an explicit product decision on whether it's the intended behavior going forward.
10. **Does leveling need constraint facts directly, or can canonical scheduling provide a feasibility API?** Given the backward pass's total constraint-blindness (§16/§39), and that `ConstraintValidator` already exists as a separate, callable, post-hoc check — the more consistent path with the existing architecture is likely a feasibility/violation-check API leveling calls after proposing a candidate date, rather than leveling re-implementing constraint semantics itself (mirroring how `ConstraintValidator` is already called independently by both the Scheduling workspace and Schedule Impact, §30/§33). This audit does not decide this — it is flagged as the natural design seam given what already exists.

---

## 41. Recommended Fix Sequence (audit observation only — not a plan to implement)

In rough dependency order, purely reflecting what would need to exist before what, based on this audit's findings — not a commitment or a proposal to build any of it now:

1. Decide product scope: is the goal "make DEADLINE-aware leveling" (small, uses only what's already live) or "make all 7 constraint types real" (large — requires §4's persistence wiring, §28's mutation/governance/concurrency work, and QML editing UI before leveling can even have real data to consult)?
2. If going beyond DEADLINE: wire `constraint_type`/`constraint_date` through `TaskORM`/mapper/repository (§4), then an application command + desktop command + QML editor (§28/§31), with governance parity to dependency changes (§28) and the same concurrency protection the `version` field already provides for free once the fields are in the update-column list.
3. Decide whether backward-pass constraint-awareness is required before leveling can trust float/criticality for constrained tasks, or whether a separate feasibility-check API is the better seam (§40 Q10).
4. Only then does it make sense to add leveling-side guards — the exclusion-check precedent already exists in `leveling.py`/`leveling_mixin.py` (§27) and would be the natural place to add them.
5. Independently of the above (can happen anytime, low-risk): fix the terminology inconsistencies (§37 #3), fix the mislabeled second "Constraints" panel (§37 #2), and delete the confirmed-dead `ResourceLevelingEngine` duplicate (§38) — none of this requires deciding the bigger scope question first.

---

## 42. Decision Table

Populated strictly from repository evidence in this audit.

| Constraint | Backend (persisted/mutable?) | Forward CPM | Backward CPM/Float | Dependency interaction | Leveling awareness | QML exposure | Correct as-is? |
|---|---|---|---|---|---|---|---|
| ASAP (default) | N/A — absence of a value | Pass-through | N/A | N/A | N/A (unconstrained, moves freely) | Implicit (no label) | Yes — correctly the baseline case |
| ALAP | Does not exist | Does not exist | Does not exist | Does not exist | Does not exist | Does not exist | N/A — not implemented |
| MUST_START_ON (MSO) | No — never persisted | Unconditional override | Blind (no LS/LF re-anchor) | Conflict reported (MSO/MFO only), verified multi-predecessor-safe | None — could be violated freely | Raw value in Schedule Impact only; no editor anywhere | No — engine correct, but unreachable + leveling-unsafe |
| MUST_FINISH_ON (MFO) | No | Unconditional override | Blind | Conflict reported, same as MSO | None | Same as MSO | No — same reasons |
| START_NO_EARLIER_THAN (SNET) | No | Floor (raises only) | Blind | Not covered by conflict mechanism | None | Not surfaced anywhere in QML | No — labeled "soft" despite driving the schedule; inconsistent with SNLT's "hard"-but-inert label |
| START_NO_LATER_THAN (SNLT) | No | **Not applied** — validation only | Blind | Not covered | None | Only in the project-wide violations table, if it were ever non-empty | No — never enforces the ceiling it names |
| FINISH_NO_EARLIER_THAN (FNET) | No | Floor (raises only) | Blind | Not covered | None | Not surfaced | No — same "soft" labeling inconsistency as SNET |
| FINISH_NO_LATER_THAN (FNLT) | No | **Not applied** — validation only | Blind | Not covered | None | Only in violations table | No — same as SNLT |
| DEADLINE | **Yes** — via `task.deadline`, real & persisted | **Not applied** — validation only | Blind | Not covered (separate from `DependencyConstraintConflict`) | **None** — the one live type leveling could push past today with zero warning | Violations table (labeled); second "Constraints" panel mislabels it as "Finish No Later Than" | Partially — the field itself is real and correctly wired for CRUD/governance-adjacent basics, but has the same backward-pass blindness and total leveling blindness as everything else |

---

*This audit found no counter-evidence to the central claim that six of the seven real constraint types are currently unreachable in production; `DEADLINE` is the sole live exception, and even it is invisible to resource leveling. No code was changed. No leveling work was started.*
