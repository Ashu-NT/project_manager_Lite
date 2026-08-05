# Rate Card Cost-Engine Cutover Plan

- Status: **implemented and tested** (uncommitted) — all 13 implementation
  tasks complete as of 2026-08-05. `project_management` suite verified at
  366 passed with exactly this repo's 24 known pre-existing failures (zero
  regressions), via full-suite runs plus a targeted `git stash` comparison
  against the pre-cutover baseline.
- Companion to [ADR-PF-005](../architecture_decisions/ADR-PF-005-rate-card-precedence.md)
  and [project_finance_existing_state_and_implementation_plan.md](project_finance_existing_state_and_implementation_plan.md) —
  Rate Cards themselves are implemented and tested (uncommitted); this
  document planned, and now records the completion of, the cutover of
  `CostPolicyEngine`/`LaborCostEngine` onto them.
- Date: 2026-08-05

## Implementation notes (post-completion)

Two pre-existing tests (`test_technical_math_reporting_cost_policy.py`,
`test_finance_layer_integration.py`) encoded the old "`Resource.hourly_rate`
applies to any historical date" assumption — they created a resource "now"
then queried a fixed historical `as_of`. Fixed by passing
`rate_effective_on` explicitly at resource creation in those tests, rather
than loosening the new date-scoped resolution behavior. The desktop
`ResourceUpdateCommand` boundary and the resource CSV importer both submit
full-form payloads (`hourly_rate` always present, never `None` to signal
"unchanged") — both were updated to diff against the stored resource and
translate an unchanged value back to `None` before calling
`update_resource`, so an unrelated edit (address, contact, etc.) doesn't
spuriously trip the new mandatory `expected_version`/`effective_on` rule.
A migration regression test (`test_project_finance_rate_card_migration.py`)
verifies the backfilled legacy line's `effective_from` is the fixed
`1970-01-01` epoch, not the migration's run date. See
`test_rate_card_cost_engine_cutover.py` for the engine-level cutover
coverage (disagreement, COST/BILLING separation, unresolved-rate exclusion,
EVM fail-closed, effective-date revision selection).

## Context

`CostPolicyEngine`/`LaborCostEngine` still resolve labor rates the old
way — `ProjectResource.hourly_rate` if set, else `Resource.hourly_rate`,
current value only — one of the finance doc's five P0 release-blocking
findings. This plan has been through six review rounds:

- **Round one** fixed a hidden `date.today()`, an optional resolver with
  a silent legacy fallback, per-resource resolver calls instead of
  batching, and silently dropping unresolved rates.
- **Round two** found the N+1 wasn't actually fully closed (candidate
  reads still needed a per-card follow-up query), the batch repository
  reads weren't tenant-scoped at the SQL level, "unresolved" diagnostics
  would have duplicated computation instead of sharing it, EVM's
  actual-cost entry point stayed unsafe under a mere log warning,
  savepoint/`IntegrityError` handling was in the wrong layer, and
  zero-rate vs. "not configured yet" was never actually defined.
- **Round three** found the contracts layer would have imported an
  application-layer type (wrong dependency direction / circular-import
  risk), the creation path left `effective_from` `None` while the update
  path assumed a real date (a genuine contradiction), `get_actual_cost`'s
  draft example silently narrowed EVM's actual cost to labor-only, and
  the incompleteness signal stopped at the backend with no path to the
  desktop API layer.
- **Round four** found the `positive → 0` transition produced an invalid
  date interval on a same-day edit, the already-written (unapplied)
  migration seeds legacy cards/lines without the new `card_kind`/a real
  `effective_from` this plan now requires, `RateCardResolver` would have
  instantiated the concrete SQLAlchemy reader itself instead of depending
  on the `RateResolutionReader` contract, `get_or_create_legacy_card` had
  no explicit "must not commit" acceptance criterion, and the desktop
  DTO's `is_complete` naming was flagged as likely to become ambiguous.
- **Round five** found a genuinely blocking mistake: seeding backfilled
  legacy lines with `effective_from` = the migration's own run date would
  make every historical report *before* that date suddenly unresolved —
  `Resource.hourly_rate` was, in effect, treated as applicable to any
  historical date before this cutover, and the backfill must preserve
  that, not silently regress it. Also flagged: verify (not necessarily
  add) protection against concurrent `update_resource` calls racing on
  the same rate-line supersession, and make a currency-only change on an
  otherwise-unchanged positive rate an explicit, tested case rather than
  leaving it implicit.
- **Round six** found `expected_version` needed to be mandatory (not just
  "existing policy") for any rate-affecting update, a genuine wording
  contradiction between the implementation section (deactivate-and-replace
  on a same-day edit) and the tests section (still said "amends in
  place"), and — the biggest gap — no defined path for the engines to
  actually obtain `tenant_id`/`organization_id` to pass into
  `resolve_many(...)` at all. Checked directly: `Project` has
  `organization_id` but no `tenant_id` field, so both engines gain a
  `tenant_context_service` dependency neither currently has.

This revision incorporates all six rounds.

**Explicit scope boundary (unchanged since round one):** this cutover
does not make historical reports immune to a later rate change — that
needs Phase C's `ProjectCostEntry` posted ledger. What this slice
delivers: cost/billing separation, an explainable batch-resolved
precedence model, explicit per-caller effective dates, and an honest,
traceable signal when a rate can't be resolved — through to the desktop
API response DTO. **Displaying that signal in QML is deliberately the
next, separate step** — consistent with this project's own established
backend-first/UI-last ordering (see the Rate Cards plan and ADR-005's
execution plan, both of which treat the UI-facing step as always last,
never a co-requisite of backend correctness work) — not silently dropped,
just sequenced after this slice rather than bundled into it.

**Per-work-date granularity, acknowledged and scoped out:** actual labor
resolves one rate per **project**, not per work-date, because
`TaskAssignment.hours_logged` is a single aggregated total with no
per-date breakdown in this engine's current data model. Per-work-date
resolution is future work tied to Phase C's time-entry-level costing.

## 1. Dependency direction: contracts and application both depend on domain

`RateSelectionSnapshot` and `RateModifier` currently live in
`application/financials/rate_cards/{rate_card_resolver,rate_card_precedence}.py`.
The new read/resolution contracts (below) need to reference
`RateSelectionSnapshot` — if contracts imported it from `application/`,
that's `contracts → application`, backwards, and a real circular-import
risk once the engines (which depend on `contracts`) and the resolver
(which lives in `application` and depends on `contracts`) are both live.

**Fix:** move both into `domain/financials/rate_cards.py` (alongside the
existing `ProjectRateCard`/`RateCardLine`/`RateType`/`RateLineOrigin` —
no new file needed, same package). `application/.../rate_card_precedence.py`
and `rate_card_resolver.py` import `RateModifier`/`RateSelectionSnapshot`
from `domain/` instead of defining them. Resulting direction:
`contracts → domain`, `application (resolver) → domain` + `→ contracts`,
`engines → contracts` only — contracts never import the concrete
`RateCardResolver` module, and domain never imports either.

## 2. Read contracts — one dedicated adapter, tenant-scoped, deduplicated

New file `contracts/repositories/rate_resolution.py` (flat, matching this
codebase's existing `contracts/repositories/*.py` convention):

```python
@dataclass(frozen=True, slots=True)
class ResourceRateContext:
    resource_id: str
    role: str | None
    department_id: str | None
    skill_codes: frozenset[str]

@dataclass(frozen=True, slots=True)
class RateResolutionCandidate:
    line: RateCardLine
    card_project_id: str | None
    card_version: int

class RateResolutionReader(Protocol):
    def list_resource_contexts(
        self, *, tenant_id: str, organization_id: str, resource_ids: tuple[str, ...],
    ) -> tuple[ResourceRateContext, ...]: ...

    def list_candidates(
        self, *, tenant_id: str, organization_id: str, project_id: str | None,
        rate_type: RateType, unit: str, as_of: date,
    ) -> tuple[RateResolutionCandidate, ...]: ...

@dataclass(frozen=True, slots=True)
class UnresolvedLaborRate:
    resource_id: str
    project_id: str | None
    as_of: date
    reason_code: str   # RATE_CARD_NO_APPLICABLE_RATE | RATE_CARD_AMBIGUOUS_SELECTION | RESOURCE_NOT_FOUND
    detail: str

@dataclass(frozen=True, slots=True)
class ResolvedLaborRate:
    resource_id: str
    snapshot: RateSelectionSnapshot   # imported from domain/financials/rate_cards.py

@dataclass(frozen=True, slots=True)
class RateResolutionBatch:
    resolved: tuple[ResolvedLaborRate, ...]
    unresolved: tuple[UnresolvedLaborRate, ...]
    @property
    def is_complete(self) -> bool: return not self.unresolved

class LaborRateResolver(Protocol):
    def resolve_many(
        self, *, tenant_id: str, organization_id: str, project_id: str | None,
        resource_ids: tuple[str, ...], rate_type: RateType, as_of: date, unit: str,
    ) -> RateResolutionBatch: ...
```

**One dedicated adapter, not two repos partially implementing a shared
protocol:** `infrastructure/persistence/repositories/rate_resolution_reader.py`
(kept in this codebase's existing `infrastructure/persistence/repositories/`
location, not a new `sqlalchemy/reads/` path that doesn't exist anywhere
else here) — `SqlAlchemyRateResolutionReader(session)` implements
`RateResolutionReader` on its own, querying `resources LEFT JOIN
resource_skills` for contexts (one query) and
`project_rate_cards JOIN rate_card_lines` for candidates (one query),
both **explicitly filtered by the given `tenant_id`/`organization_id` in
the `WHERE` clause** — not solely an ambient after-the-fact check.

**The resource/skill join returns one row per skill, not one per
resource** — a resource with three skills produces three joined rows.
`list_resource_contexts` must group by `resource_id` before returning,
not emit duplicate/partial contexts:

```python
contexts: dict[str, dict] = {}
for row in rows:
    entry = contexts.setdefault(
        row.resource_id,
        {"resource_id": row.resource_id, "role": row.role,
         "department_id": row.department_id, "skill_codes": set()},
    )
    if row.skill_code:
        entry["skill_codes"].add(row.skill_code)
return tuple(
    ResourceRateContext(
        resource_id=v["resource_id"], role=v["role"],
        department_id=v["department_id"],
        skill_codes=frozenset(v["skill_codes"]),
    )
    for v in contexts.values()
)
```

exactly one immutable `ResourceRateContext` per resource — this is what
keeps the design's promised two-query bound genuinely true rather than
silently returning multiple partial rows per skilled resource.
`list_candidates`' single query filters, all at once: tenant, org,
`rate_type`, normalized `unit`, line `is_active`, card `is_active`, the
effective-date interval, and **both** scopes together
(`card.project_id = :project_id OR card.project_id IS NULL`).

`resolve_many` deduplicates its input first —
`resource_ids = tuple(dict.fromkeys(resource_ids))` — so duplicate ids in
the caller's list produce exactly one deterministic result per resource,
not a repeated/undefined one.

**`RateCardResolver` depends on the `RateResolutionReader` contract, never
the concrete SQLAlchemy class directly:**

```python
class RateCardResolver:
    def __init__(
        self, *, reader: RateResolutionReader,
        tenant_context_service: TenantContextService, clock: Clock,
    ) -> None:
        self._reader = reader
        self._tenant_context_service = tenant_context_service
        self._clock = clock
```

Composition builds the concrete adapter and injects it:

```python
rate_resolution_reader = SqlAlchemyRateResolutionReader(session=session)
rate_card_resolver = RateCardResolver(
    reader=rate_resolution_reader,
    tenant_context_service=tenant_context_service,
    clock=system_clock,
)
```

so the dependency stays `Application RateCardResolver → RateResolutionReader
contract ← SqlAlchemyRateResolutionReader`, never
`Application → concrete SQLAlchemy adapter` directly. `RateCardResolver`
also uses this same injected `clock` (not a hidden module-level
`_utc_now()`) when stamping `RateSelectionSnapshot.resolved_at` — one
clock source for both this and `ResourceService` (below), not two
independent ways of asking "what time is it."

`resolve_many()` gains this reader-backed batch path; the existing
single-resource `resolve()` (now taking explicit
`tenant_id`/`organization_id` too, no unscoped signature) reuses the same
batch machinery for a batch of one, raising when that one resource is
unresolved (strict — for a future Phase C posting operation), rather
than duplicating classification logic.

**`resolve_many` catches only the specific, expected per-resource
failures** — `BusinessRuleError` with code `RATE_CARD_NO_APPLICABLE_RATE`
or `RATE_CARD_AMBIGUOUS_SELECTION`, plus a resource missing from the
fetched contexts (checked directly). Anything else — a database error, a
tenant-context failure, a programming error — propagates and fails the
whole call; a bare `except Exception` would silently convert real bugs
into "this resource has no rate."

(`RateSelectionSnapshot` is already genuinely immutable from round one —
frozen dataclass, scalar `modifier_applied`/`modifier_multiplier` fields,
`modifiers_applied` a computed `MappingProxyType` property, never a
stored mutable field. No further change needed there beyond its move to
`domain/` in step 1.)

## 3. Explicit `as_of` everywhere — no `date.today()` inside engines

`CostPolicyEngine.build_snapshot`, `get_cost_control_totals`,
`get_cost_source_breakdown`, `get_actual_cost`, and `LaborCostEngine`'s
methods all take `as_of: date` as a **required** parameter, sourced by
each call site from what's actually being calculated.

**Where the engines get `tenant_id`/`organization_id` for
`resolve_many(...)` — verified against the actual domain model, not
assumed.** `resolve_many` requires both explicitly; neither engine
currently has a way to produce them. Checked directly: `Project` (domain
model) carries `organization_id` but **no `tenant_id` field at all** —
so `organization_id` can come from the project the engine already
fetches (`project_repo.get(project_id)`, which is itself already
tenant-scoped internally — trustworthy, not invented), but `tenant_id`
cannot come from the project object and must come from the ambient
`TenantContextService`, exactly like every other service in this module
already resolves it. **Fix:** both engines gain a
`tenant_context_service: TenantContextService` constructor dependency
(neither currently has one). Each `as_of`-taking method does:

```python
project = self._project_repo.get(project_id)
if project is None:
    raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
context = self._tenant_context_service.require_organization_context(
    operation_label="resolve project labor rates"
)
# defense in depth, same pattern already used in RateCardResolver (§2):
if project.organization_id and project.organization_id != context.organization_id:
    raise BusinessRuleError(
        "Project does not belong to the active organization.",
        code="PROJECT_ORGANIZATION_MISMATCH",
    )
batch = self._rate_resolver.resolve_many(
    tenant_id=context.tenant_id,
    organization_id=context.organization_id,
    project_id=project_id,
    resource_ids=resource_ids,
    rate_type=RateType.COST,
    as_of=as_of,
    unit="HOUR",
)
```

Never inferred from "the first resolved resource" or any other implicit
source — the project fetch (already trustworthy) plus the ambient
tenant context (same source every other service in this module already
uses) are the only two inputs.

## 4. `get_actual_cost` (EVM) fails closed on the *full* actual-cost total

```python
def get_actual_cost(self, project_id: str, as_of: date) -> float:
    snapshot = self.build_snapshot(project_id=project_id, as_of=as_of)
    if snapshot.unresolved_labor_rates:
        raise BusinessRuleError(
            "Actual cost cannot be calculated because one or more labor "
            "rates could not be resolved.",
            code="ACTUAL_COST_INCOMPLETE",
        )
    return self._sum_bucket_map(snapshot.actual_map, snapshot.project_currency)
    # unchanged from today's implementation — the full actual-cost total
    # (labor + non-labor), not snapshot.actual_labor_total. EVM's AC means
    # total actual cost; narrowing it to labor-only here would itself be a
    # regression this cutover must not introduce.
```

Non-strict interactive reads (`build_snapshot`/`get_cost_control_totals`/
`get_cost_source_breakdown`) stay non-strict, exposing
`unresolved_labor_rates`/`is_complete` as additive fields on
`CostPolicySnapshot`/`CostControlTotals` (default empty tuple). EVM's
entry point alone fails closed.

## 5. One computation for rich results — and it reaches the desktop API

`LaborCostEngine` gains `calculate_project_labor_details`/
`calculate_project_labor_plan_vs_actual` returning
`LaborDetailsResult`/`LaborPlanResult` (`rows` + `unresolved_rates` +
`is_complete`); the existing `get_project_labor_details`/
`get_project_labor_plan_vs_actual` become thin wrappers returning
`list(result.rows)` — **one** computation, never a second query run
separately to answer "what was unresolved."

**The signal is threaded through to the desktop API DTO, not left
backend-only.** `FinancialsApi.get_finance_snapshot(project_id) ->
FinancialSnapshotDto` (`api/desktop/financials/api.py:130`, backed by
`FinanceService.get_finance_snapshot`) already the concrete desktop-facing
entry point for exactly this data. `FinancialSnapshotDto`
(`api/desktop/financials/models/snapshots.py`) gains additive fields —
**`labor_rates_complete: bool`, `unresolved_labor_rate_count: int`**
(named precisely rather than a bare `is_complete`, which on a *full*
financial snapshot could later be misread as "the whole snapshot is
complete" rather than specifically "labor rates resolved" — the internal
`LaborPlanResult.is_complete` stays fine since that type is unambiguously
labor-only already) — populated by `serialize_snapshot` from
`CostPolicySnapshot.unresolved_labor_rates`. This is still backend/API-layer
work (a DTO field), not a QML change —
**an actual visible QML warning banner is the deliberate next step,
scoped out of this slice per the backend-first ordering this project
already follows elsewhere**, not silently dropped: the data reaches the
API boundary now, ready for a UI slice to consume.

## 6. Legacy rate-card seeding: concurrency in the repository, real uniqueness constraint

`ProjectRateCardRepository` gains
`get_or_create_legacy_card(*, tenant_id, organization_id, currency_code) -> ProjectRateCard`.
Its SQLAlchemy implementation owns `session.begin_nested()` + catching
`IntegrityError` + re-fetching on collision — `ResourceService` never
touches a savepoint, a session, or `IntegrityError`; it only calls the
repository method.

**Acceptance criterion: `get_or_create_legacy_card` must never commit.**
It may open a nested transaction (savepoint), `flush()`, catch
`IntegrityError`, and re-fetch — but the outer transaction (resource +
legacy card, if newly created + legacy line + audit record) commits
exactly once, at the end of `create_resource`/`update_resource`, same as
every other governed mutation in this module. A failure anywhere after
the card is created must roll back the resource, the card, and the line
together — nothing about this seeding step is allowed to introduce a
second, independent commit boundary into what's otherwise one atomic
resource-creation transaction.

**Real database constraint, not just a deterministic id.** Migration
(not yet applied — still directly editable) adds `card_kind: str | None`
to `project_finance_rate_cards`, plus a **partial unique index**
expressing the actual invariant directly rather than leaning on
nullable-unique semantics:

```sql
CREATE UNIQUE INDEX uq_legacy_rate_card_per_org
ON project_finance_rate_cards (tenant_id, organization_id)
WHERE card_kind = 'legacy';
```

(via SQLAlchemy `Index(..., unique=True, postgresql_where=..., sqlite_where=...)`
— both dialects support partial/filtered indexes, so one `Index`
definition covers both backends this codebase runs on.) `card_kind` is
added everywhere a real column needs a matching layer, not only the
migration: `ProjectRateCard` domain model, `ProjectRateCardORM`, the
mapper, `get_or_create_legacy_card`'s query, and tests for all of the
above.

**The already-written (unapplied) migration's own seed step must be
updated to match, not just new code going forward.**
`l0m1n2o3p4q5_add_project_finance_rate_cards.py`'s
`_backfill_legacy_rate_lines` currently seeds cards/lines with no
`card_kind` and no `effective_from` — under this plan's rules that's now
inconsistent data the moment it lands, and `get_or_create_legacy_card`
(which looks cards up by `tenant_id`/`organization_id`/`card_kind="legacy"`)
would never find a migration-seeded card that has `card_kind=NULL`,
creating a second, genuinely duplicate legacy card per organization
instead of reusing the first. Since this migration hasn't been applied
anywhere yet, edit it directly rather than layering a follow-up migration
on top: its seed step gains `card_kind="legacy"` on the card, and
`origin=LEGACY_SEEDED` on each line.

**The backfilled `effective_from` must NOT be the migration's own run
date.** Before this cutover, `Resource.hourly_rate` was read directly
with no date-scoping at all — effectively applicable to *any* historical
date. Seeding `effective_from=2026-08-05` (the migration's run date)
would make every historical report `as_of` before that date suddenly
resolve to "no applicable rate" — a real regression, not a neutral
default. **Use a documented system epoch instead:**

```python
# All backfilled legacy lines start here, not on the migration's own run
# date — Resource.hourly_rate was effectively applicable to any
# historical date before this cutover, and the backfill must preserve
# that rather than silently making earlier reports incomplete.
LEGACY_RATE_BACKFILL_EFFECTIVE_FROM = date(1970, 1, 1)
```

`resources` has no `created_at` column to derive a more precise
per-resource start date from (confirmed by reading `ResourceORM`), so a
fixed, documented epoch — not a derived "earliest task/assignment/
timesheet date," which would need cross-table scanning for uncertain
benefit — is the simpler and safer choice here.

Migration test additions: an existing resource with `hourly_rate > 0`
backfills to exactly one legacy card with `card_kind == "legacy"` and
exactly one line with `effective_from == LEGACY_RATE_BACKFILL_EFFECTIVE_FROM`;
a second resource created afterward via `get_or_create_legacy_card`
reuses that same migration-seeded card rather than creating another one;
**and, the regression this whole fix exists for:** resolving `as_of=date(2026, 6, 1)`
(before the migration's own run date of 2026-08-05) against a
`hourly_rate=50` resource still resolves successfully to `50`, proving
historical reports don't regress.

## 7. Creation establishes a real effective date; zero-rate transitions, fully enumerated

**Round three's contradiction:** creation was going to leave
`effective_from` `None` ("open-ended"), while the update algorithm
compares dates against `current_line.effective_from` — that comparison
is meaningless against `None`, and an unset start date also makes it
impossible to know when a legacy rate actually began applying.

**Fix — a minimal, scoped `Clock`.** No Clock abstraction exists
anywhere in this codebase yet (ADR-005's proposed one is unrelated and
not accepted/implemented). Add a small, self-contained
`application/common/clock.py`: `Clock` Protocol (`.today() -> date`,
`.now() -> datetime`) + `SystemClock` — not an attempt to preempt or
implement ADR-005's broader design. Both `ResourceService` and
`RateCardResolver` (§2) take this same `Clock` as a constructor
dependency (composition wires one shared `SystemClock()` instance into
both; tests inject a fixed fake) — one clock source for the whole
cutover, not a per-class ad hoc one.

`create_resource` gains `rate_effective_on: date | None = None`; when
`hourly_rate > 0`, resolve `effective_on = rate_effective_on or
self._clock.today()` and seed the line with a **real**
`effective_from=effective_on`, `effective_to=None` — never an unset start
date.

**Zero-rate transitions, all four cases, not just the two the previous
draft implied — and `positive → 0`/`positive → positive` both need a
same-day-vs-later-date split, since closing with `effective_to =
effective_on - 1 day` is only valid when `effective_on` is strictly after
the current line's own `effective_from`:**

```python
if current_line.effective_from == effective_on:
    # Same-day: the current line must not resolve on or after this date.
    # Deactivating (not closing with an invalid effective_to before its
    # own effective_from) preserves its audit record without producing a
    # backwards date interval.
    deactivate(current_line)
elif effective_on > current_line.effective_from:
    close(current_line, effective_to=effective_on - timedelta(days=1))
else:
    raise BusinessRuleError(
        "A backdated rate change requires the dedicated rate-card workflow.",
        code="LEGACY_RATE_BACKDATE_NOT_ALLOWED",
    )
# then, only for positive -> positive: open a new line effective_from=effective_on
```

| Transition | Same day | Later date | Earlier date |
|---|---|---|---|
| `0 → positive` | Create new line, `effective_from=effective_on`. | (n/a — no current line to compare against) | |
| `positive → positive` | Deactivate current line, open a new one, both `effective_from=effective_on`. | Close current (`effective_to = effective_on - 1 day`), open a new one. | Raise `LEGACY_RATE_BACKDATE_NOT_ALLOWED`. |
| `positive → 0` | Deactivate the current line. **No replacement.** | Close the current line (`effective_to = effective_on - 1 day`). **No replacement.** | Raise `LEGACY_RATE_BACKDATE_NOT_ALLOWED`. |
| `0 → 0` | No financial change; `effective_on` not required at all. | | |
| currency-only change while `hourly_rate == 0` | Update the resource; create/touch **no** rate line. | | |

`0` still means "not configured" throughout — `positive → 0` never
creates a zero-rate replacement line, it only retires the old one.

`update_resource` gains `effective_on: date | None = None`; raises
`ValidationError` if `hourly_rate`/`currency_code` is changing and
`effective_on` is not supplied (never defaults to `self._clock.today()`
silently for an *edit* — the caller must state the date a rate change
takes effect; only *creation* falls back to the clock, since "when did
this resource first exist" is unambiguously "now"). Edits that don't
touch `hourly_rate`/`currency_code` never need `effective_on`.

**Currency-only change on an unchanged positive rate is not a special
case — it's the same `positive → positive` path, explicitly.** `80 EUR`
→ `80 USD` (amount unchanged, currency changed) goes through the exact
same same-day-deactivate / later-date-close-and-open logic as an amount
change, because the *rate line itself* is denominated in a currency and
that's what changed — updating only `Resource.currency_code` while
leaving the old `80 EUR` line active would leave the two silently
inconsistent. The trigger condition for requiring `effective_on` is
"`hourly_rate` changed **or** `currency_code` changed," already stated
above; this is that condition's own explicit worked case, not a new rule.

**Concurrent supersession is serialized by the existing resource
optimistic-concurrency check — but only if `expected_version` is actually
supplied, and today it's optional, which is not sufficient on its own.**
Two concurrent `update_resource` calls can both read the same active
line, both omit `expected_version`, and both succeed — creating two
overlapping active replacement lines with no conflict ever detected.
Relying on optimistic concurrency while still allowing callers to omit
the version is not a real guarantee.

**Fix: `expected_version` becomes required specifically when the call is
rate-affecting**, detected from what's actually being changed, not from a
blanket "always required" rule that would needlessly break every
non-financial resource edit:

```python
rate_affecting_change = hourly_rate is not None or currency_code is not None
if rate_affecting_change and expected_version is None:
    raise ValidationError(
        "expected_version is required when changing the resource rate "
        "or currency.",
        code="RESOURCE_RATE_VERSION_REQUIRED",
    )
```

An ordinary non-financial update (name, role, capacity, etc.) keeps
today's existing `expected_version` policy unchanged. A rate- or
currency-changing update now mandatorily participates in the resource
row's optimistic check within the same transaction as the line
supersession — so the second of two racing calls genuinely fails as
stale, rather than merely being assumed to.

## 8. Wire everything; resolver required, not optional

- `CostPolicyEngine.__init__`/`LaborCostEngine.__init__` gain
  `rate_resolver: LaborRateResolver` **and** `tenant_context_service:
  TenantContextService` — both required, no `| None` default, no hidden
  fallback branch. Existing direct-construction unit tests inject a small
  `FixedLaborRateResolver` fake and a fake/stub tenant context.
- **Checked directly, and corrected here: neither `FinanceService` nor
  `ReportingService` currently has `tenant_context_service` either** (a
  first draft of this fix wrongly assumed one of them already did). Both
  gain it as a new constructor dependency, passed straight through to the
  `CostPolicyEngine`/`LaborCostEngine` instances they build — the same
  new dependency, threaded one layer further than originally scoped.
- `ResourceService.__init__` gains `project_rate_card_repo:
  ProjectRateCardRepository` and `clock: Clock`.
- `infra/composition/project_registry.py` builds **one** `SystemClock()`
  instance, shared by `ResourceService` and `RateCardResolver` (§2), and
  passes `platform_services.tenant_context_service` into
  `CostPolicyEngine`/`LaborCostEngine` alongside the real resolver/reader/
  repo wiring at all sites.

## Tests

- Contracts (`contracts/repositories/rate_resolution.py`) import nothing
  from `application/` — a direct import-graph assertion, not just a
  convention note.
- Creation seeds a line with a non-null `effective_from`.
- All four zero-rate transitions from the table above, individually.
- A backdated update raises `LEGACY_RATE_BACKDATE_NOT_ALLOWED`. A
  same-day `positive → positive` edit **deactivates the current line and
  creates one active replacement** with the same `effective_from` — assert
  the old line ends `is_active=False`, the new one `is_active=True`,
  `effective_from` equal to the edit date, `effective_to=None`. (Not
  "amends in place" — deactivate-and-replace is the chosen policy
  throughout, including this case, for the same auditability reason it
  already applies to `positive → 0`.)
- `get_actual_cost` raises `ACTUAL_COST_INCOMPLETE` when incomplete, and
  — regression-specific — a fixture with **both** labor and non-labor
  actual cost proves the returned total still includes both once this
  lands (guards against silently narrowing AC to labor-only).
- Disagreement, not just parity: `Resource.hourly_rate=50`,
  `ProjectResource.hourly_rate=60`, a COST line at `80` → result is `80`.
- COST vs. BILLING never mixed at the engine level.
- Missing/ambiguous rate → in `unresolved_rates`, excluded from (not
  zeroed into) totals; `get_project_labor_details`/`_plan_vs_actual` and
  their `calculate_*` counterparts proven to share one computation, not
  run it twice.
- `FinancialSnapshotDto.labor_rates_complete`/`unresolved_labor_rate_count`
  reflect an incomplete underlying snapshot — the desktop-API-boundary
  end of the incompleteness chain, tested explicitly.
- `positive → 0` on the same day as the current line's own
  `effective_from` deactivates it rather than producing an invalid
  (`effective_to` before `effective_from`) interval.
- The migration's own `_backfill_legacy_rate_lines` seeds `card_kind`
  and `effective_from == LEGACY_RATE_BACKFILL_EFFECTIVE_FROM` (not the
  migration's run date), and a subsequent `get_or_create_legacy_card`
  call reuses that seeded card rather than creating a duplicate.
- **The regression round five exists for:** resolving `as_of` *before*
  the migration's own run date against a backfilled resource still
  succeeds — proves historical reports don't silently go incomplete
  because of when the migration happened to run.
- A currency-only change on an otherwise-unchanged positive rate (e.g.
  `80 EUR → 80 USD`) goes through the same same-day/later-date
  supersession as an amount change — the old-currency line does not stay
  active alongside a `Resource.currency_code` that no longer matches it.
- A rate/currency-changing `update_resource` call with no
  `expected_version` raises `RESOURCE_RATE_VERSION_REQUIRED` — it's no
  longer optional for this specific case, even though it stays optional
  for a non-financial edit.
- Two `update_resource` calls with the **same** `expected_version`,
  both rate-affecting: the first succeeds, the second fails as stale
  (`STALE_WRITE`/`ConcurrencyError`) — and, critically, only **one**
  active replacement line exists afterward, not two overlapping ones.
- `RateCardResolver` is constructed with an injected `RateResolutionReader`
  fake in tests — never instantiates `SqlAlchemyRateResolutionReader`
  itself.
- `get_or_create_legacy_card` never calls `session.commit()` — a test
  that forces a failure immediately after it returns proves the resource
  row itself also rolls back (single outer transaction, not two).
- `list_candidates` returns both project-scoped and organization-wide
  cards in one call; proven not to trigger any further per-card/per-
  resource query via SQLAlchemy statement events
  (`event.listens_for(engine, "before_cursor_execute")`), not by mocking
  `Session.execute`.
- Duplicate resource ids in a single `resolve_many` call produce exactly
  one result per resource.
- `get_or_create_legacy_card` reuses one card per org across multiple
  resources; a forced `IntegrityError` on a racing create still returns
  the existing card without losing the resource being created in the
  same transaction; the partial unique index itself is exercised (two
  direct-insert attempts at the DB level, not just through the app).
- `resolve_many`/`resolve()` reject a `tenant_id`/`organization_id` that
  doesn't match the ambient context, and reject it as a real parameter,
  not only via an internal ambient check.
- An unexpected exception inside `resolve_many` propagates rather than
  becoming an `unresolved` entry.
- All composition call sites receive a real resolver/repo/clock/
  `tenant_context_service`, not `None`/a stub.
- `CostPolicyEngine`/`LaborCostEngine` resolve `tenant_id` from the
  ambient `TenantContextService` and `organization_id` from the fetched
  `Project`, never from any resource — a `Project.organization_id`
  mismatched against the ambient context raises
  `PROJECT_ORGANIZATION_MISMATCH` rather than silently proceeding.
- The skill-join grouping produces exactly one `ResourceRateContext` per
  resource even when a resource has multiple skills (assert count, not
  just content, for a multi-skill fixture).

## Verification

Run the new test file, then the full existing suite for
`CostPolicyEngine`/`LaborCostEngine`/`FinanceService`/`ReportingService`/
`ResourceService`/desktop financials API plus
`test_project_finance_rate_cards.py`, comparing against a clean-baseline
run via `git stash` to separate genuine regressions from this repo's
known pre-existing failures, as done for the Rate Cards work itself.
