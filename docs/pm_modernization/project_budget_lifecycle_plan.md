# ProjectBudget / BudgetLine Lifecycle Plan

- Status: **implementation complete and verified (2026-08-06)** — revised four times after review; domain, repository/migration/RLS, application service, composition wiring, and the full test suite (53 tests including migration/RLS/architecture-guardrail cases) all pass. Uncommitted.
- Companion to [project_finance_existing_state_and_implementation_plan.md](project_finance_existing_state_and_implementation_plan.md)
  (Phase B item 5) and [rate_card_cost_engine_cutover_plan.md](rate_card_cost_engine_cutover_plan.md)
  (the most recently completed slice in this same bounded context, whose
  conventions this plan reuses throughout: tenant/org-scoped aggregates,
  optimistic concurrency via `update_with_version_check`, partial unique
  indexes for "at most one X" invariants, the shared `Clock` abstraction).
- Date: 2026-08-05

## Context

`docs/pm_modernization/project_finance_existing_state_and_implementation_plan.md`
(Phase B) calls for a versioned budget aggregate: "Add Budget/BudgetLine
lifecycle and approval integration. Approved versions become immutable and
supersede rather than update." Today `Project.planned_budget` is a single
mutable float with no line items, no dimensions (cost code/WBS), no
approval, and no history. This is the next Phase B item after
`ProjectFinancialProfile`/`ProjectCostCode` (Phase B1, done) and rate cards
+ the `CostPolicyEngine`/`LaborCostEngine` cutover (just completed). The
user chose this explicitly over "versioned planned-cost snapshots first."

This revision incorporates two review rounds. **Round one** found three
blocking issues in the first draft (business version vs. optimistic-
concurrency version conflated into one field; approve/supersede ordering
could race against the new "one approved row" DB constraint; the
governed-approval path had no rejection counterpart) plus several smaller
corrections (full lifecycle actor/timestamp metadata, cascade delete,
cost-code eligibility, one-open-version-per-project). **Round two** found:
the line's denormalized `project_id` was not actually constrained to match
its parent budget's `project_id` at the database level; the header-update
path never stated whether `currency_code` could change (it must not, once
lines exist in a given currency); the reject apply-handler omitted
`expected_version` while the approve handler included it (an
inconsistency); an actor fallback to an empty string was unacceptable for
a financial audit trail; a governed `approve_budget` call didn't check
staleness before creating a doomed-to-fail approval request; and two
further concurrent-write races (duplicate `create_budget` racing the
open-version index, and the revision-uniqueness index) needed named error
translation instead of a raw `IntegrityError`. **Round three** found: line
mutations (`add_line`/`update_line`/`delete_line`) only touched
`BudgetLine.row_version`, never the parent `ProjectBudget.row_version` —
letting a submit race a concurrent final-line deletion since the two
operations check different objects' versions and never conflict; the
governed apply/reject handlers had no *explicit* internal path that skips
`budget.approve` permission checking (a governance-only approver holding
`approval.decide` but not `budget.approve` would otherwise be blocked, or
the bypass would be implicit/undocumented); and a single `notes: str`
field on `ProjectBudget` would have each lifecycle transition silently
overwrite the previous transition's note. All three are resolved below.

**Scope boundary — read this first:**
In scope: the `ProjectBudget`/`BudgetLine` aggregate itself, its lifecycle,
governed approval on the approve step (including the rejection path),
repository/migration/RLS, composition wiring, and tests — a self-contained
slice, exactly like Rate Cards was delivered before its own separate
cutover phase.
Out of scope, explicitly deferred:
- No `CostPolicyEngine`/`EarnedValueCalculator` cutover onto approved
  budget totals — `Project.planned_budget` stays the BAC/threshold source
  this phase. A future cutover plan (mirroring
  `rate_card_cost_engine_cutover_plan.md`) will do that separately.
- No `ProjectPlannedCostVersion`/`ProjectPlannedCostLine` (Phase B item 6,
  next after this).
- No financial periods / `period_id` dimension (explicitly Phase C).
- No department or funding-source dimension (the aggregate-ownership table
  in the audit doc scopes `ProjectBudget` to Project/CostCode/WBS/Period/
  approval only).
- No QML section replacement.

## Domain model — `domain/financials/budget.py` (new)

Mirrors `ProjectBaseline`'s lifecycle pattern (`domain/scheduling/baseline.py`,
`application/scheduling/baselines/baseline_service.py`) and the Phase B1/
rate-card conventions (`domain/financials/configuration.py`,
`domain/financials/rate_cards.py`), with these decisions:

### Two separate version fields (blocking fix #1)

`ProjectBudget.version` cannot mean both "which business iteration is
this" (v1, v2, v3...) and "optimistic-concurrency row token" — updating a
budget's name/notes must not silently turn v2 into v3. Split into:

- `revision: int` — the business budget version within the project.
  Assigned once at creation, **never changes** on that row afterward.
  `UniqueConstraint(tenant_id, organization_id, project_id, revision,
  name="uq_pf_budget_project_revision")`.
- `row_version: int` — plain optimistic-concurrency token, incremented by
  `update_with_version_check` on every field-level update. Every
  `expected_version` parameter throughout the service/repository refers to
  `row_version`, never `revision`.

Same split on `BudgetLine`: `row_version` only (a line doesn't have its own
business "revision" — it belongs to one specific budget revision via
`budget_id`).

### 6-state lifecycle with full actor/timestamp metadata

`DRAFT, SUBMITTED, APPROVED, REJECTED, SUPERSEDED, CLOSED`. Explicit
transition map (mirrors `ProjectFinancialProfile.transition_to`'s style) —
no REJECTED/SUPERSEDED/CLOSED → anything path; the next iteration is
always a **new** `ProjectBudget` row (new `revision`), created fresh as
DRAFT, never a reopen.

```python
class BudgetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    CLOSED = "closed"

_ALLOWED_TRANSITIONS = {
    BudgetStatus.DRAFT: {BudgetStatus.SUBMITTED},
    BudgetStatus.SUBMITTED: {BudgetStatus.APPROVED, BudgetStatus.REJECTED},
    BudgetStatus.APPROVED: {BudgetStatus.SUPERSEDED, BudgetStatus.CLOSED},
    BudgetStatus.REJECTED: set(),
    BudgetStatus.SUPERSEDED: set(),
    BudgetStatus.CLOSED: set(),
}
```

Full metadata (every transition records who/when, not just submit/approve
as the first draft had):
`submitted_by/submitted_at, approved_by/approved_at, rejected_by/
rejected_at, superseded_by/superseded_at, closed_by/closed_at`.

**Round-three fix — per-transition notes, not one shared field.** A single
`notes: str` field would let each lifecycle transition silently overwrite
whatever the previous transition wrote there (a submission note erased by
the approval note, then erased by the closure note). Decision: `notes`
stays as general, freely-editable budget notes (changed only through
`update_notes()`, DRAFT-only like every other mutation), and each
transition writes into its **own** dedicated field instead of touching
`notes` at all:
`submission_notes: str = "", approval_notes: str = "", rejection_notes:
str = "", closure_notes: str = ""`. No note field for `supersede()` — it's
a system-triggered transition with no caller-supplied text, consistent
with its signature never taking one.

Lifecycle methods take **explicit actor and timestamp**, never calling
`datetime.now()` internally — the caller (service) supplies both, sourced
from an injected `Clock` (reuse the existing
`application/common/clock.py` built for the rate-card cutover — one clock
source across the module, not a second ad hoc one):

```python
def submit(self, *, submitted_by: str, submitted_at: datetime, notes: str = "") -> None:
    # ... transition-map check ...
    self.submission_notes = notes

def approve(self, *, approved_by: str, approved_at: datetime, notes: str = "") -> None:
    # ... transition-map check ...
    self.approval_notes = notes

def reject(self, *, rejected_by: str, rejected_at: datetime, notes: str = "") -> None:
    # ... transition-map check ...
    self.rejection_notes = notes

def supersede(self, *, superseded_by: str, superseded_at: datetime) -> None: ...

def close(self, *, closed_by: str, closed_at: datetime, notes: str = "") -> None:
    # ... transition-map check ...
    self.closure_notes = notes

def touch(self, *, updated_at: datetime) -> None:
    """Marks the aggregate root as changed without altering its status —
    called by every BudgetLine mutation so the parent's row_version
    advances too (see the line-mutation concurrency fix below)."""
    self.updated_at = updated_at
```

Each status-changing method validates via the transition map and raises a
specific code (`PROJECT_BUDGET_SUBMIT_STATUS_INVALID`, `..._APPROVE_...`,
`..._REJECT_...`, `..._SUPERSEDE_...`, `..._CLOSE_...`).

Two more domain methods back the restricted header-update surface (round
two — see the currency-immutability fix below): `rename(self, name: str)
-> None` and `update_notes(self, notes: str) -> None`, both plain field
mutations with no status check of their own — the service always calls
`ensure_mutable()` first, so these two stay simple.

### Immutability enforced structurally (not by convention)

`ProjectBudget.ensure_mutable()` raises `BusinessRuleError(code=
"PROJECT_BUDGET_IMMUTABLE")` unless `status == DRAFT`. Only DRAFT is
mutable — SUBMITTED is frozen too (a reviewer who wants changes rejects
it; the next iteration is a new DRAFT version, never a reopen). Every
mutating service method calls it on the freshly-fetched budget before
proceeding (baseline never enforces this structurally, only by
convention; the Phase B exit gate explicitly demands "approved budgets
cannot mutate," and this budget goes further by freezing SUBMITTED too).

### Mandatory v1 dimensions, currency

`cost_code_id` required, `task_id` optional (WBS). No department/
funding-source/period — the audit doc's own aggregate-ownership table
scopes `ProjectBudget` to Project/CostCode/WBS/Period/approval, and Period
is explicitly deferred to Phase C.

Currency: raw `Decimal amount` + `str currency_code` fields — checked
directly against the codebase's actual established convention for stored
domain-dataclass monetary fields (`RateCardLine.rate_amount: Decimal`/
`rate_currency: str`, `ProjectFinancialProfile.currency_code: str`), not
the `Money` dataclass (which exists at
`src/core/platform/finance/money/money.py` but is used for arithmetic in
application/engine code, never as a pydantic-validated stored field
anywhere in this codebase today). Add a `@property money -> Money:
return Money.of(self.amount, self.currency_code)` convenience for
arithmetic call sites without changing the storage shape.
`financial_numeric(FinancialNumericKind.MONEY)` (19,4) for the column —
not `RATE` (19,8), since this is a budget amount, not a rate. Every
`BudgetLine.currency_code` must equal its parent budget's `currency_code`
(checked in the service, not the dataclass, since a dataclass can't query
its parent) — single-currency v1, no per-line FX.

### Final field lists

```python
@validated_dataclass
class ProjectBudget:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    name: str
    currency_code: str
    status: BudgetStatus = BudgetStatus.DRAFT
    revision: int = 1
    row_version: int = 1
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    superseded_by: str | None = None
    superseded_at: datetime | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    notes: str = ""                 # general/draft notes — only via update_notes()
    submission_notes: str = ""      # written only by submit()
    approval_notes: str = ""        # written only by approve()
    rejection_notes: str = ""       # written only by reject()
    closure_notes: str = ""         # written only by close()
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
```

```python
@validated_dataclass
class BudgetLine:
    id: str
    tenant_id: str
    organization_id: str
    budget_id: str
    project_id: str                # denormalized, defense-in-depth (mirrors CostItem/Task pattern)
    cost_code_id: str               # required
    task_id: str | None = None      # optional, WBS dimension
    description: str = ""
    amount: Decimal = Decimal("0")
    currency_code: str = ""
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
```

**Round-two note on `created_at`/`updated_at` defaults.** The
`default_factory=_utc_now` above stays for standalone domain-level unit
tests that construct a `ProjectBudget`/`BudgetLine` directly with no
service in the loop. In `BudgetService`, however, every call that creates
or mutates a row explicitly passes `created_at=now`/`updated_at=now` (and
every lifecycle transition explicitly passes its own `*_at=now`) where
`now = self._clock.now()` — the service never lets the dataclass default
fire during a real request, since that would source a timestamp from a
different clock call than the rest of the same transaction. This keeps
the single-clock rule genuinely single, and keeps tests that inject a
fixed fake `Clock` fully deterministic.

Validators: `amount >= 0` (budgets are non-negative Money, per the audit
doc's own "Money, quantity, and rate decisions" section); `currency_code`
validated via `CurrencyCode(...).minor_unit_quantum()` exactly like
`RateCardLine`; identifiers via the same `_required_identifier` helper
pattern used throughout this module's domain files.

## Contracts (`contracts/repositories/budget.py`, new file)

Mirrors `ProjectRateCardRepository`'s ABC shape:

```python
class ProjectBudgetRepository(ABC):
    def add(self, budget: ProjectBudget) -> None: ...
    def get(self, budget_id: str) -> ProjectBudget | None: ...
    def list_for_project(self, project_id: str, *, include_superseded: bool = True) -> list[ProjectBudget]: ...
    def get_latest_for_project(self, project_id: str) -> ProjectBudget | None: ...
    def get_approved_for_project(self, project_id: str) -> ProjectBudget | None: ...
    def update(self, budget: ProjectBudget, *, expected_row_version: int) -> None: ...
    def delete(self, budget_id: str, *, expected_row_version: int) -> None: ...
    def add_line(self, line: BudgetLine) -> None: ...
    def get_line(self, line_id: str) -> BudgetLine | None: ...
    def update_line(self, line: BudgetLine, *, expected_row_version: int) -> None: ...
    def delete_line(self, line_id: str, *, expected_row_version: int) -> None: ...
    def list_lines(self, budget_id: str) -> list[BudgetLine]: ...
    def flush(self) -> None: ...
```

**Round-four fix — deletes are atomic, not check-then-delete.** A plain
`get()` + status/version check followed by a bare `DELETE ... WHERE
id=...` leaves a TOCTOU gap: a concurrent `submit_budget` between the
read and the delete would be silently discarded. Fix: both `delete`
methods take `expected_row_version` and are implemented via a new shared
helper, `delete_with_version_check` (added to `src/infra/persistence/db/
optimistic.py` alongside the existing `update_with_version_check`, same
shape — atomic `DELETE ... WHERE id=... AND version=:expected_version`,
`rowcount` checked, not-found vs. stale-write disambiguated by re-select).
Since *every* status-changing budget mutation already goes through
`update_with_version_check` (which always bumps `version`), a concurrent
`submit_budget` between the service's `ensure_mutable()` check and
`delete_budget`'s actual delete call is enough to make the row's version
no longer match — the atomic delete then correctly fails `STALE_WRITE`
instead of silently deleting a budget that just became SUBMITTED.

`flush()` exposes a session-flush point to the application service without
the service depending on SQLAlchemy directly — needed for the ordered
supersede-before-approve sequencing below.

`infrastructure/persistence/repositories/budget.py` —
`SqlAlchemyProjectBudgetRepository`, mirroring
`SqlAlchemyProjectRateCardRepository` line for line: a `_context()` helper
requiring `TenantContextService`, a `_require_entity_scope()` guard before
every `add`/`update` raising `BusinessRuleError(code=
"PROJECT_BUDGET_SCOPE_MISMATCH")`, every query filtered by
`tenant_id`/`organization_id` in the `WHERE` clause, `update()`/
`update_line()` implemented via the shared `update_with_version_check`
helper (`src/infra/persistence/db/optimistic.py`) checking `row_version`
— the same helper Rate Cards used, not a re-implementation.

## Application service (`application/financials/budgets/budget_service.py`)

Replaces the current one-line-docstring placeholder
(`application/financials/budgets/__init__.py`).

### Ordered supersede-before-approve, with a translated conflict error (blocking fix #2)

The naive "approve new, then supersede old, commit once" ordering can let
a mid-transaction flush see two `status='approved'` rows simultaneously
and trip the partial unique index (see migration section). Fix — explicit
ordering, superseding the old row and flushing it **before** approving the
new one, with each `expected_row_version` **captured into a local variable
before the mutating call**, not re-read from the object afterward (round
three: this protects against a future refactor where `supersede()`/
`approve()` might start touching `row_version` directly, which would make
`previous.row_version` after the call reflect the *new*, not the
*expected*, version):

```python
def _apply_approval_decision(self, *, budget_id, approved_by, expected_version, notes, commit):
    """Internal — no permission check. Only called by approve_budget()
    (already permission-checked) and by the composition-registered
    apply-handler (already authorized via ApprovalService's own
    'approval.decide' check — see the governed-approval section below for
    why this must be a distinct method, not a bypass flag)."""
    budget = self._require_budget(budget_id)
    now = self._clock.now()
    previous = self._budget_repo.get_approved_for_project(budget.project_id)
    try:
        with self._session.begin_nested():
            if previous is not None:
                previous_expected_version = previous.row_version
                previous.supersede(superseded_by=approved_by, superseded_at=now)
                self._budget_repo.update(previous, expected_row_version=previous_expected_version)
                self._budget_repo.flush()  # old row no longer satisfies the approved-only index
            budget_expected_version = expected_version
            budget.approve(approved_by=approved_by, approved_at=now, notes=notes)
            self._budget_repo.update(budget, expected_row_version=budget_expected_version)
            self._budget_repo.flush()
    except IntegrityError as exc:
        if self._is_approval_conflict(exc):
            raise BusinessRuleError(
                "Another budget version was approved for this project concurrently.",
                code="PROJECT_BUDGET_APPROVAL_CONFLICT",
            ) from exc
        raise
    self._audit_and_commit(..., commit=commit)
    return budget
```

The nested savepoint (`session.begin_nested()`) means a caught
`IntegrityError` only rolls back this budget-approval unit, not the whole
outer governance transaction — the same pattern already used for
`get_or_create_legacy_card`'s concurrency handling. `_is_approval_conflict`
matches the partial-index name in the exception message (same technique as
`_is_resource_code_integrity_error` in `resource_commands.py`). This
directly answers "two submitted versions approved concurrently" with a
named business error instead of a raw DB exception, without needing
pessimistic row locks (SQLite has no reliable `SELECT ... FOR UPDATE`, and
this repo's other concurrency-sensitive paths — rate cards, legacy-card
seeding — all use this same optimistic + translated-IntegrityError
approach, not locking).

**Round-four verification requirement.** `_is_approval_conflict` (and the
sibling `create_budget` conflict translators below) match by constraint/
index name in the raised exception's text. PostgreSQL surfaces the
violated constraint name directly; SQLite's uniqueness error text reports
the affected column list, not necessarily the index name verbatim. This
must be **verified empirically against SQLite** (the engine this test
suite actually runs on) while implementing, not assumed to work from the
Postgres-shaped example alone — if SQLite's message shape differs, the
matcher inspects `exc.orig`/the statement's target columns instead of a
literal index-name substring search. The test list's conflict-translation
tests are the concrete check for this, and must pass against the same
SQLite engine the rest of this test suite uses, not just in theory.

### Explicit internal permission-bypass path for governed decisions (round three)

The first two drafts registered the apply/reject handlers calling
`approve_budget(..., bypass_approval=True, commit=False)` directly,
implying `bypass_approval=True` also skips the `budget.approve` permission
check. That conflates two different things: "don't request governance
again" is not the same authorization decision as "skip permission
checking entirely." A user can legitimately hold `approval.decide` (so
`ApprovalService.approve_and_apply`/`reject` already let them through)
without holding `budget.approve` — the whole point of routing budget
approval through governance in the first place is to let exactly this
kind of reviewer decide without also being a day-to-day budget approver.

Fix: split each public, permission-checked entry point from a private,
unchecked "apply the already-authorized decision" method that only the
composition-registered handler calls — no implicit bypass flag, no
ambiguity about what's actually skipped:

```python
def approve_budget(self, budget_id, *, approved_by, notes="", expected_version):
    require_permission(self._user_session, "budget.approve", operation_label="approve project budget")
    budget = self._require_budget(budget_id)
    if budget.row_version != expected_version:
        raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
    if self._is_approval_governed():
        req = self._approval_service.request_change(
            request_type="budget.approve", entity_type="project_budget",
            entity_id=budget_id, project_id=budget.project_id,
            payload={"budget_id": budget_id, "expected_version": expected_version, "notes": notes},
        )
        raise BusinessRuleError(f"Approval required. Request {req.id} created.", code="APPROVAL_REQUIRED")
    return self._apply_approval_decision(
        budget_id=budget_id, approved_by=approved_by,
        expected_version=expected_version, notes=notes, commit=True,
    )

def reject_budget(self, budget_id, *, rejected_by, expected_version, notes=""):
    require_permission(self._user_session, "budget.approve", operation_label="reject project budget")
    return self._apply_rejection_decision(
        budget_id=budget_id, rejected_by=rejected_by,
        expected_version=expected_version, notes=notes, commit=True,
    )
```

`_apply_approval_decision` (shown above) and its counterpart
`_apply_rejection_decision` (same shape: fetch the budget, call
`budget.reject(rejected_by=..., rejected_at=self._clock.now(),
notes=notes)`, `self._budget_repo.update(budget,
expected_row_version=expected_version)`, audit, commit-if-requested)
**never check `budget.approve`** — by construction, they're only reachable
through `approve_budget`/`reject_budget` (already checked) or through the
composition handlers below (already authorized by `ApprovalService`'s own
`approval.decide` check). No `bypass_approval` parameter exists anywhere
in this design; there is nothing to bypass, because the two paths call
genuinely different methods.

### Governed approval — with a real rejection path (blocking fix #3, tightened in rounds two and three)

Checked directly against `src/core/platform/application/approval/
approval_service.py`: **the apply/reject handler receives only the
`ApprovalRequest` object** — `request.decided_by_user_id`/
`decided_by_username` are set by `ApprovalService` itself *after* the
handler already ran (both `approve_and_apply` and `reject` call the
handler before stamping decision fields), so the handler cannot read "who
decided" off the request. The actor must instead come from the
**currently active session principal at decision time** (who is calling
`approve_and_apply`/`reject` right now, already permission-checked by
`ApprovalService` itself via `require_permission(..., "approval.decide",
...)`) — never from `request.payload`, which was written by the original
*requester*, not the approver.

**Round-two correction — no empty-string actor fallback.** A review round
suggested a `user_session.require_principal()` guard; checked directly,
**no such method exists anywhere in the platform** — the actual, existing
convention throughout this exact file is `principal = self._user_session.
principal if self._user_session else None`. Rather than invent new
platform API surface, both handlers below explicitly raise if `principal`
is `None` instead of silently recording `""` as a financial actor — same
end guarantee (no empty-string actor ever reaches the ledger), built from
what's actually there.

**Round-two correction — `expected_version` on both decision paths.** The
first draft threaded `expected_version` through the approve handler but
not the reject handler — an inconsistency. Both now carry it, and
`reject_budget()`'s `expected_version` becomes a required keyword
(matching `submit_budget`/`approve_budget`/`close_budget`, none of which
are optional on this point either).

```python
def _require_actor(platform_services):
    principal = platform_services.user_session.principal
    if principal is None:
        raise BusinessRuleError(
            "An authenticated principal is required to decide a budget "
            "approval.",
            code="PROJECT_BUDGET_ACTOR_REQUIRED",
        )
    return principal.user_id

def _apply_budget_approval(req):
    # Calls the internal, unchecked decision method directly — NOT
    # approve_budget() — because this handler's authorization already
    # came from ApprovalService's own "approval.decide" check, which is
    # deliberately independent of "budget.approve" (see the explicit
    # internal permission-bypass section above).
    budget = budget_service._apply_approval_decision(
        budget_id=req.payload["budget_id"],
        approved_by=_require_actor(platform_services),
        expected_version=req.payload["expected_version"],
        notes=req.payload.get("notes", ""),
        commit=False,
    )
    return _result("budgets_changed", budget.project_id)

def _apply_budget_rejection(req):
    budget = budget_service._apply_rejection_decision(
        budget_id=req.payload["budget_id"],
        rejected_by=_require_actor(platform_services),
        expected_version=req.payload["expected_version"],
        notes=req.payload.get("notes", ""),
        commit=False,
    )
    return _result("budgets_changed", budget.project_id)

approval_service.register_apply_handler("budget.approve", _apply_budget_approval)
approval_service.register_reject_handler("budget.approve", _apply_budget_rejection)
```

**Round-two correction — check staleness *before* requesting governance.**
`approve_budget`'s governed branch now fetches the budget and compares
`budget.row_version != expected_version` (the same check every direct
mutation already does) **before** calling `request_change(...)`. Without
this, a caller holding a stale `expected_version` could create an approval
request that is already guaranteed to fail once applied — wasted
governance round-trip and a confusing failure far from its cause. The
check happens once, up front, and covers both branches (governed and
direct) rather than being duplicated in each.

`ApprovalService.register_reject_handler` already exists (confirmed
directly, same registration shape as `register_apply_handler`) — this
closes the "budget stuck permanently SUBMITTED after a governance
rejection" gap from the first draft: a rejected governance request now
deterministically drives `ProjectBudget.reject()` through the same atomic
commit `ApprovalService.reject()` already performs, not left to a separate
manual `reject_budget()` call that might never happen.

`expected_version` for the governed path is threaded through the approval
request's payload at `request_change(...)` time (captured when
`approve_budget` first raises `APPROVAL_REQUIRED`), so the eventual apply
handler still enforces optimistic concurrency against whatever
`row_version` the budget had when governance was requested.

### Full method list

- `create_budget(project_id, name, currency_code=None)` — permission
  `budget.manage`, **not** governed. Fetches `ProjectFinancialProfile` via
  `financial_profile_repo.get_by_project(project_id)` (`NotFoundError` if
  missing — a budget requires a financial profile for its default
  currency); `revision = latest.revision + 1 if any exist else 1`;
  service-level check for **at most one open (DRAFT/SUBMITTED) version per
  project** before inserting (`PROJECT_BUDGET_OPEN_VERSION_EXISTS` if
  violated — see migration section for the DB-level backstop); explicitly
  stamps `created_at`/`updated_at` from `self._clock.now()` (see the
  round-two clock note below — never relies on the dataclass's own
  `default_factory=_utc_now`); persists; audits `project_budget.create`.

  **Round-two addition — named conflict translation for concurrent
  creation.** Two concurrent `create_budget()` calls can both observe "no
  open budget, same latest revision" before either commits; the two
  partial/unique indexes correctly prevent both from *succeeding*, but the
  losing call must not surface a raw `IntegrityError`. The service wraps
  the insert in the same nested-savepoint + catch pattern used for
  `approve_budget`, translating by constraint name:
  `uq_pf_budgets_one_open_per_project` → `BusinessRuleError(code=
  "PROJECT_BUDGET_OPEN_VERSION_EXISTS")`; `uq_pf_budget_project_revision`
  → `ConcurrencyError(code="PROJECT_BUDGET_REVISION_CONFLICT")` (the
  revision race is transient and retry-safe — the losing caller simply
  re-reads the latest revision and retries — so it's modeled as a
  concurrency error, not a plain business-rule rejection).
- `submit_budget(budget_id, submitted_by, notes="", expected_version)` —
  `budget.manage`, **not** governed. Requires at least one `BudgetLine`
  (→ `PROJECT_BUDGET_EMPTY` otherwise, mirrors baseline's "cannot
  baseline: project has no tasks" business rule).
- `approve_budget` — **the only governed operation**, mirroring
  `CostLifecycleMixin`'s governed/direct branch exactly. Governed branch:
  `approval_service.request_change(request_type="budget.approve",
  entity_type="project_budget", entity_id=budget_id, project_id=...,
  payload={"budget_id": budget_id, "expected_version": expected_version,
  "notes": notes})` then raise `BusinessRuleError(code=
  "APPROVAL_REQUIRED")`. Otherwise: the ordered supersede-before-approve
  flow above.
- `reject_budget(budget_id, *, rejected_by, expected_version, notes="",
  commit=True)` — `expected_version` is **required**, matching every other
  lifecycle method (round-two fix: the first draft left it optional here,
  inconsistent with `submit_budget`/`approve_budget`/`close_budget`).
  Permission `budget.approve` when called directly (the
  apply-handler path bypasses this via internal invocation, same as other
  `_apply_*` handlers bypass their services' own permission checks by
  construction — they run with platform-level trust already established
  by `ApprovalService.reject()`'s own `approval.decide` check).
- `close_budget(budget_id, closed_by, notes="", expected_version)` —
  `budget.approve`, not governed.

### Line mutations must advance the parent budget's `row_version` too (blocking, round three)

`add_line`/`update_line`/`delete_line` only ever touched `BudgetLine`'s own
`row_version` in the first two drafts — never the parent
`ProjectBudget.row_version`. That leaves a real race: transaction A reads
a DRAFT budget, confirms it has at least one line, and submits it, while
transaction B concurrently deletes that same (last remaining) line —
neither operation's optimistic check conflicts with the other, since one
checks the *budget's* version and the other checks the *line's* version,
and a submitted budget with zero lines is exactly the state
`submit_budget`'s emptiness check exists to prevent. It also means a
budget's `row_version` doesn't actually represent the complete aggregate
state — a governance request could capture an `expected_version` that
doesn't reflect the budget's current lines.

Fix: every line mutation also updates the parent budget's `row_version`,
in the same transaction, via `ProjectBudget.touch()` (defined above) —
making `ProjectBudget` a real, version-tracked consistency boundary over
its lines, not just its own header fields:

```python
def add_line(self, budget_id, *, cost_code_id, task_id=None, description, amount,
             currency_code=None, expected_budget_version):
    budget = self._require_budget(budget_id)
    budget.ensure_mutable()
    if budget.row_version != expected_budget_version:
        raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
    # ... cost-code/task/currency eligibility checks (below), build BudgetLine, repo.add_line(line) ...
    now = self._clock.now()
    budget.touch(updated_at=now)
    self._budget_repo.update(budget, expected_row_version=expected_budget_version)
    self._commit()
    return line

def update_line(self, line_id, *, expected_line_version, expected_budget_version, ...):
    line = self._require_line(line_id)
    budget = self._require_budget(line.budget_id)
    budget.ensure_mutable()
    if budget.row_version != expected_budget_version:
        raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
    # ... mutate line fields, repo.update_line(line, expected_row_version=expected_line_version) ...
    budget.touch(updated_at=self._clock.now())
    self._budget_repo.update(budget, expected_row_version=expected_budget_version)
    self._commit()
    return line

def delete_line(self, line_id, *, expected_line_version, expected_budget_version):
    line = self._require_line(line_id)
    budget = self._require_budget(line.budget_id)
    budget.ensure_mutable()
    if budget.row_version != expected_budget_version:
        raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
    # Atomic delete-if-version-matches (round four) — a plain read-check-
    # then-delete-by-id would leave a TOCTOU gap where a concurrent update
    # to this same line is silently discarded.
    self._budget_repo.delete_line(line_id, expected_row_version=expected_line_version)
    budget.touch(updated_at=self._clock.now())
    self._budget_repo.update(budget, expected_row_version=expected_budget_version)
    self._commit()
```

Both concurrency tokens are necessary and serve different purposes:
`expected_line_version` protects the specific line being deleted (against
a concurrent edit to that same line); `expected_budget_version` protects
the aggregate boundary (against a concurrent submit/close/another line's
mutation). All of this stays inside one transaction, so a failure on the
parent-budget update (e.g. a stale `expected_budget_version`) rolls back
the line deletion too — the line is never left deleted with no matching
parent-version bump.

With this, the earlier race is closed: whichever of "submit" or "delete
the last line" commits first advances `ProjectBudget.row_version`; the
second call's `expected_budget_version` (captured before its own read) no
longer matches, and it fails with `STALE_WRITE` instead of silently
producing a SUBMITTED budget with no lines.

- `add_line(budget_id, *, cost_code_id, task_id=None, description,
  amount, currency_code=None, expected_budget_version)` — **cost-code
  eligibility check**: `cost_code_repo.get(cost_code_id)` must exist, be in
  the same tenant/org, and `is_effective_on(self._clock.today())`
  (combines active + effective-date-range — reuses the existing method, no
  new logic); if the project's `ProjectFinancialProfile.cost_code_policy
  == RESTRICTED` (confirmed field exists at
  `domain/financials/configuration.py`), `cost_code_id` must appear in
  `cost_code_repo.list_restrictions(project_id)` (confirmed method exists
  on `ProjectCostCodeRepository`) —
  `PROJECT_BUDGET_LINE_COST_CODE_NOT_PERMITTED` otherwise; `task_id` (if
  given) must belong to the same `project_id`; `currency_code` must equal
  the parent's. **Eligibility is checked only at write time** — a cost
  code deactivated later does not retroactively invalidate an
  already-approved budget line (no re-validation on read).
- `update_line(line_id, *, expected_line_version, expected_budget_version,
  ...)`/`delete_line(line_id, *, expected_line_version,
  expected_budget_version)` — `ensure_mutable()` on the freshly-fetched
  parent first, both `expected_*_version`s checked, parent `touch()`ed and
  saved alongside the line change (see above).
- `update_budget_header(budget_id, *, name=None, notes=None,
  expected_version)` — `ensure_mutable()` first; **`currency_code` is
  immutable after creation and is never a parameter here** (round-two
  fix: changing a budget's currency while its lines are denominated in the
  original currency would silently break the single-currency invariant).
  Only `name`/`notes` may change; the method never accepts `tenant_id`,
  `organization_id`, `project_id`, `revision`, `currency_code`, `status`,
  or any lifecycle-metadata field. Implemented via two small domain
  methods for clarity: `ProjectBudget.rename(name)` and
  `ProjectBudget.update_notes(notes)`, each callable only when
  `ensure_mutable()` already passed.
- `delete_budget(budget_id, *, expected_version)` — **explicit DRAFT-only
  check** (a decisive fix over `delete_baseline`, which today deletes
  regardless of status) fetched from the same read whose `row_version`
  becomes `expected_version`; the repository's `delete()` call is atomic
  (round four — see the repository section), so a concurrent submit
  between the DRAFT check and the actual delete surfaces `STALE_WRITE`
  rather than silently deleting a budget that just became SUBMITTED.
  Also updates `notes`/renames via `rename()`/`update_notes()` do not set
  `updated_at` themselves (round four) — the service calls
  `budget.touch(updated_at=self._clock.now())` immediately after either,
  the same `touch()` used by line mutations, so every mutation path shares
  one place that stamps the aggregate's `updated_at`.
- Reads: `get_budget`, `list_budgets_for_project`, `get_approved_budget`,
  `list_lines`, `get_totals_by_cost_code`, `get_totals_by_task` — gated by
  `finance.read`, computed in Python from `list_lines()`.

Constructor: `session, budget_repo, project_repo, financial_profile_repo,
cost_code_repo, task_repo, clock, user_session=None,
enterprise_audit_service=None, module_catalog_service=None,
tenant_context_service=None, approval_service=None` (`clock: Clock` is
required — the same instance the composition root already builds once and
shares with `ResourceService`/`RateCardResolver`). Audit via the existing
`record_audit_entry(...)` helper (`severity="high"`, `compliance_tag=
"financial"`, `commit=False`), own `_commit()` wrapping
`IntegrityError`/`Exception` with rollback.

**New permissions**: `budget.manage`, `budget.approve` in
`role_permission_catalog.py`, wired the same way `baseline.manage`/
`baseline.approve` are. Bump `SYSTEM_ROLE_POLICY_VERSION`.

## Migration (new revision after `l0m1n2o3p4q5`)

Purely additive — no legacy data to backfill (`Project.planned_budget` is
a single float with no line/version shape; its eventual split is Phase D's
job, not this migration's).

`project_finance_budgets`: `id, tenant_id, organization_id, project_id,
name, currency_code, status, revision, row_version, submitted_by,
submitted_at, approved_by, approved_at, rejected_by, rejected_at,
superseded_by, superseded_at, closed_by, closed_at, notes,
submission_notes, approval_notes, rejection_notes, closure_notes,
created_at, updated_at` (round-four fix: the first three drafts' column
list dropped the four per-transition notes columns added to the domain
model in round three — without a persisted column, each note would
silently vanish on reload). Composite FKs to `tenants`/`organizations`/
`projects` (same shape as rate cards). `UniqueConstraint(tenant_id,
organization_id, id)` (composite-child-FK enabler). `UniqueConstraint
(tenant_id, organization_id, project_id, revision, name=
"uq_pf_budget_project_revision")`. `CheckConstraint(status IN (...))`.

**Round-two addition —
`UniqueConstraint(tenant_id, organization_id, project_id, id, name=
"uq_pf_budget_scope_project_id")`.** Without this, the database can't
actually guarantee a line's denormalized `project_id` matches its parent
budget's `project_id` — both FKs (line→budget via `budget_id`, line→project
via `project_id`) could independently be valid while pointing at
*different* projects, since neither constrains the other. This extra
unique constraint on the parent (id + project_id together) is what makes a
**four-column** composite FK on the line possible (see below), which is
what actually enforces `BudgetLine.project_id == ProjectBudget.project_id`
as a real invariant, not just a service-level convention.

Two partial unique indexes (same `postgresql_where`/`sqlite_where`
technique already proven for `uq_pf_rate_cards_legacy_per_org`):

```sql
-- at most one APPROVED budget per project at any time
CREATE UNIQUE INDEX uq_pf_budgets_one_approved_per_project
ON project_finance_budgets(tenant_id, organization_id, project_id)
WHERE status='approved';

-- at most one open (draft/submitted) iteration per project at any time
CREATE UNIQUE INDEX uq_pf_budgets_one_open_per_project
ON project_finance_budgets(tenant_id, organization_id, project_id)
WHERE status IN ('draft','submitted');
```

The second index is the DB-level backstop for "one open version per
project" — normal enterprise workflow shouldn't let `v3 SUBMITTED` and
`v4 SUBMITTED` coexist unintentionally. A rejected version does **not**
block creating the next draft (REJECTED isn't in the `WHERE` clause); an
approved version **can** coexist with one draft/submitted successor (also
not in the `WHERE` clause) — only the open (draft/submitted) *count* is
capped at one. `info={"rls_scope": "tenant_organization"}`.

`project_finance_budget_lines`: `id, tenant_id, organization_id,
budget_id, project_id, cost_code_id, task_id, description, amount,
currency_code, row_version, created_at, updated_at`.

**Round-two fix — the line-to-budget FK is a four-column composite,
including `project_id`, not just `(tenant_id, organization_id, budget_id)`:**

```python
ForeignKeyConstraint(
    ["tenant_id", "organization_id", "project_id", "budget_id"],
    [
        "project_finance_budgets.tenant_id",
        "project_finance_budgets.organization_id",
        "project_finance_budgets.project_id",
        "project_finance_budgets.id",
    ],
    ondelete="CASCADE",
)
```

This is what actually guarantees `BudgetLine.project_id ==
ProjectBudget.project_id` at the database level — without it, a line
could legally reference a budget in Project A while itself claiming
Project B, since the two FKs (to the budget, to the project) don't
otherwise cross-check each other. `ondelete="CASCADE"` here is also the
fix over the first draft, which omitted it entirely — without it, deleting
a DRAFT budget with lines would fail unless the service manually deleted
every line first; CASCADE makes `delete_budget` correct with no extra
service-layer cleanup code.

The line also keeps a plain composite FK to `projects(tenant_id,
organization_id, id)` — now partly redundant with the four-column FK
above, but kept as additional, independent protection (consistent with
this codebase's general preference for defense-in-depth over removing a
check merely because another one already covers most of the same ground).
Composite FK to `project_finance_cost_codes(tenant_id, organization_id,
id)` with `ondelete="RESTRICT"` (cost codes are soft-deactivated, never
hard-deleted).

**Round-four fix — `task_id` uses `ondelete="RESTRICT"`, not `SET NULL`.**
`SET NULL` would let deleting a `Task` silently detach it from a budget
line with **no `BudgetService` call, no `row_version` bump, and no audit
trail** — including a line on an already-`APPROVED`, supposedly-immutable
budget. `task_id`: plain `ForeignKey("tasks.id", ondelete="RESTRICT")`,
nullable — task/project-membership validated in the service layer (not a
composite tenant-scoped FK; `CostItem.task_id` uses the same plain-FK
shape, just with a different `ondelete` policy that doesn't apply here).
A task referenced by any budget line — even one on a DRAFT or REJECTED
budget — cannot be hard-deleted; task deactivation/archival remains
unaffected. A future phase that needs to allow task deletion while
preserving budget history would snapshot stable WBS fields onto the line
(`wbs_code`, a name snapshot) rather than relying on `SET NULL`; not
needed for this v1 slice. `CheckConstraint(amount >= 0)`.
`info={"rls_scope": "tenant_organization"}`.

Both tables call `enable_tenant_organization_rls`/
`disable_tenant_organization_rls` in `upgrade()`/`downgrade()` (from
`src.infra.persistence.migrations.helpers.postgresql_rls`), same as the
rate-card migration.

## Composition wiring

- `src/infra/composition/repositories.py`: `RepositoryBundle.
  project_budget_repo: SqlAlchemyProjectBudgetRepository`.
- `src/infra/composition/project_registry.py`: `ProjectManagementServiceBundle
  .budget_service`, construction (passing the **same shared `SystemClock()`
  instance** already built for `ResourceService`/`RateCardResolver` in this
  function's scope), needs `project_repo, cost_code_repo=
  repositories.project_cost_code_repo, task_repo, financial_profile_repo=
  repositories.project_financial_profile_repo, tenant_context_service,
  approval_service=platform_services.approval_service`, plus
  `_apply_budget_approval`/`_apply_budget_rejection` registration
  (extending whichever function currently registers `_apply_baseline`/
  `_apply_cost_*` handlers).
- `src/core/shared/events/domain_events.py`: add one new `budgets_changed`
  signal (bridge spec + field) — needed because this aggregate has an
  approval-gated apply/reject handler pair and needs a signal name for its
  `ApprovalPostCommitEvent`, same as baseline's `baseline_changed`. Do not
  reuse `costs_changed` (that means `CostItem`-specific events today).
- `application/financials/__init__.py`: export `BudgetService`.

## Test list (`src/tests/project_management/test_project_finance_budgets.py`)

- Every valid transition succeeds; every invalid one raises its specific
  code. `ensure_mutable()` raises for every non-DRAFT status individually.
- **`revision` vs `row_version` regression test**: updating a budget's
  `name`/`notes` leaves `revision` unchanged and only increments
  `row_version`; a second `create_budget` for the same project gets
  `revision = prior + 1`; DB `UniqueConstraint(..., project_id, revision)`
  exercised directly to prove no race can produce a duplicate revision.
- `add_line`/`update_line`/`delete_line`/`update_budget_header` all raise
  `PROJECT_BUDGET_IMMUTABLE` once SUBMITTED. `delete_budget` succeeds on
  DRAFT (and cascades to its lines — assert the lines are actually gone,
  not orphaned), fails on every other status (regression test specifically
  for the fix over `delete_baseline`'s status-blind delete).
- `submit_budget` on an empty budget raises `PROJECT_BUDGET_EMPTY`.
- **Ordered approve/supersede test**: `approve_budget` (ungoverned path)
  supersedes the prior approved budget in the same outer transaction; a
  forced failure between the supersede-flush and the approve-update rolls
  back both. The partial "one approved" index is exercised directly with
  two raw concurrent-style inserts, and via the service producing
  `PROJECT_BUDGET_APPROVAL_CONFLICT` (not a raw `IntegrityError`) when two
  submitted versions are approved back-to-back without an intervening
  supersede.
- **One-open-version test**: creating a second DRAFT/SUBMITTED budget
  while one is already open raises `PROJECT_BUDGET_OPEN_VERSION_EXISTS`;
  creating a new DRAFT after the existing one is REJECTED succeeds;
  creating a new DRAFT while a *different* version is APPROVED succeeds.
  A forced concurrent-insert race (two `create_budget` calls for the same
  project) surfaces `PROJECT_BUDGET_OPEN_VERSION_EXISTS`/
  `PROJECT_BUDGET_REVISION_CONFLICT` as named errors, never a raw
  `IntegrityError`.
- **Line/budget project scope test (round two)**: a direct DB-level insert
  attempt of a `BudgetLine` whose `project_id` differs from its parent
  `ProjectBudget.project_id` is rejected by the four-column composite FK
  — proves `uq_pf_budget_scope_project_id` + the composite FK actually
  enforce the invariant at the database level, not only in the service.
- **Currency immutability test (round two)**: `update_budget_header` has
  no `currency_code` parameter at all (a type-level guarantee, not just a
  runtime check); a budget's `currency_code` is unchanged after any
  `update_budget_header` call regardless of what other fields changed.
- `reject_budget` transitions SUBMITTED→REJECTED; no reopen path exists
  (assert `submit()`/`approve()` on a REJECTED budget raise).
- `close_budget` only valid from APPROVED.
- **Governed approve+reject test**: governed `approve_budget` calls
  `request_change(request_type="budget.approve", ...)` and raises
  `APPROVAL_REQUIRED`; `create_budget`/`submit_budget` are never routed
  through `ApprovalService`. The registered apply handler's mutation +
  approval decision + audit commit atomically (failure-injection test,
  same style as the A0 UoW tests). **The registered reject handler**
  actually drives `ProjectBudget.reject()` when the governance request is
  rejected — the regression test for the fix: assert the budget is
  REJECTED after `approval_service.reject(...)`, not stuck SUBMITTED.
  `approved_by`/`rejected_by` recorded on the budget match the **deciding**
  principal, not any value from the original requester's payload (test
  with two different users as requester vs. approver to prove this).
  Both the apply and reject handlers raise `PROJECT_BUDGET_ACTOR_REQUIRED`
  rather than recording an empty-string actor when no principal is present
  (round two). A governed `approve_budget` call made with a stale
  `expected_version` raises before any `ApprovalRequest` is even created
  (round two) — assert no request row exists afterward.
- `add_line` rejects: cross-org `cost_code_id`; an inactive/expired cost
  code; a cost code not in the project's restriction allow-list when the
  profile is `RESTRICTED`; a cross-project `task_id`; a mismatched
  `currency_code`. A cost code deactivated *after* being used on an
  approved budget line does not retroactively break reading that line.
- **Line-mutation aggregate-version tests (round three, blocking)**:
  `add_line`/`update_line`/`delete_line` each increment
  `ProjectBudget.row_version`, not just the line's own `row_version`; any
  of the three with a stale `expected_budget_version` raises `STALE_WRITE`
  even when the line-level version is current. **The concurrency
  regression test the fix exists for:** simulate transaction A reading a
  DRAFT budget with one line and calling `submit_budget`, concurrently
  with transaction B calling `delete_line` on that same, only, line —
  exactly one succeeds; the other raises `STALE_WRITE`; a SUBMITTED budget
  with zero lines never exists as an end state.
- **Explicit internal permission-bypass test (round three)**: a principal
  holding `approval.decide` but **not** `budget.approve` can still have
  their governance decision applied — `ApprovalService.approve_and_apply`/
  `reject` (invoked by such a principal) succeed and correctly transition
  the budget, proving `_apply_approval_decision`/`_apply_rejection_decision`
  genuinely skip the `budget.approve` check rather than relying on an
  implicit flag. Conversely, calling `approve_budget`/`reject_budget`
  *directly* (not through governance) as a principal who lacks
  `budget.approve` is rejected as usual.
- **Per-transition notes test (round three)**: submitting, approving, and
  later closing a budget with three different note strings leaves
  `submission_notes`, `approval_notes`, and `closure_notes` each holding
  their own distinct text — none overwritten by a later transition — and
  leaves the general `notes` field (set only via `update_notes()`)
  untouched by any of the three.
- Tenant A cannot read/write Tenant B's budget/line; same-tenant
  cross-organization IDs fail; optimistic concurrency on stale
  `row_version` for both budget and line updates.
- `get_totals_by_cost_code`/`get_totals_by_task` sums match a hand-computed
  Decimal-exact sum of the underlying lines.
- Migration: upgrade creates both tables with RLS; downgrade reverses
  cleanly; no data-mutating statements (unlike the rate-card migration,
  there's nothing to backfill); deleting a DRAFT budget row directly at
  the DB level cascades its lines (exercises the FK `ondelete="CASCADE"`
  independent of the service layer).
- **Transition-notes persistence round-trip (round four)**: submit with
  note A, approve with note B, close with note C, clear the session/reload
  the budget from the database — `submission_notes`, `approval_notes`, and
  `closure_notes` each still hold their own distinct text, and the general
  `notes` field is unchanged. Proves the four columns are actually
  persisted, not just present on the in-memory domain object.
- **Atomic versioned deletion (round four)**: `delete_budget`/`delete_line`
  with a stale `expected_version` raise `STALE_WRITE`, never silently
  no-op or delete the wrong generation. A forced race — read a DRAFT
  budget, concurrently submit it, then attempt the original caller's
  delete with the pre-submit version — raises `STALE_WRITE` rather than
  deleting a budget that is now SUBMITTED.
- **`task_id` RESTRICT test (round four)**: attempting to delete a `Task`
  referenced by a `BudgetLine` (on any budget status, not just APPROVED)
  is rejected at the database level; deactivating/archiving the task
  (whatever mechanism PM scheduling already uses for that) is unaffected.

## Implementation order

1. `domain/financials/budget.py` (`BudgetStatus`, transitions,
   `ProjectBudget` incl. `ensure_mutable`/lifecycle methods with explicit
   actor+timestamp params, `BudgetLine`).
2. `contracts/repositories/budget.py` (incl. `flush()`).
3. `infrastructure/persistence/orm/budget.py`.
4. `infrastructure/persistence/mappers/budget.py`.
5. `infrastructure/persistence/repositories/budget.py` (reusing
   `update_with_version_check`; `flush()` delegates to `session.flush()`).
6. Migration: both tables, all constraints incl. the two partial unique
   indexes, `uq_pf_budget_scope_project_id`, the lines' four-column
   cascade FK, RLS enable/disable, no backfill.
7. `role_permission_catalog.py`: `budget.manage`/`budget.approve`, role
   wiring, version bump.
8. `domain_events.py`: `budgets_changed` signal.
9. `application/financials/budgets/budget_service.py` — including the
   ordered supersede-before-approve flow with `IntegrityError` translation,
   and both the apply and reject handlers' actor-sourcing design (the
   handlers themselves are registered in composition, step 12, but the
   service methods they call — `approve_budget`/`reject_budget` accepting
   an explicit actor argument rather than reading the request — are built
   here).
10. `application/financials/__init__.py`: export `BudgetService`.
11. `src/infra/composition/repositories.py`: `project_budget_repo`.
12. `src/infra/composition/project_registry.py`: service construction
    (shared `Clock`), `_apply_budget_approval`/`_apply_budget_rejection`
    registration.
13. `test_project_finance_budgets.py`: full test list.
14. Full regression run (`project_management` suite, then a broader
    platform/architecture pass) compared against a clean `git stash`
    baseline, exactly as done for the rate-card cutover.

## Verification

Run `./pmenv/Scripts/python.exe -m pytest src/tests/project_management/test_project_finance_budgets.py -q`
first in isolation, then the full `src/tests/project_management` suite,
then `src/tests/architecture/test_project_finance_persistence_guardrails.py`
specifically (it directly checks every `project_finance_*` table for
tenant/org scope and RLS metadata). Compare any new failures against the
currently-known 24-failure baseline (enumerated in
`rate_card_cost_engine_cutover_plan.md`) via a `git stash`/`pytest`/
`git stash pop` cycle on the failing subset to confirm whether they're
genuine regressions or pre-existing.
