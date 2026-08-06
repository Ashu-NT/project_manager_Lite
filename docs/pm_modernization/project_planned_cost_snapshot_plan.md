# Versioned Planned-Cost Snapshot Plan

- Status: **design finalized, implementation starting** (2026-08-06).
- Companion to [project_finance_existing_state_and_implementation_plan.md](project_finance_existing_state_and_implementation_plan.md)
  (Phase B item 6, "Add versioned planned-cost calculation/snapshots from
  assignments and other planned inputs. Link dimensions to budget lines and
  retain source lineage.") and [project_budget_lifecycle_plan.md](project_budget_lifecycle_plan.md)
  (the immediately preceding slice, whose conventions this plan reuses:
  tenant/org-scoped aggregates, optimistic concurrency via
  `update_with_version_check`/`delete_with_version_check`, partial unique
  indexes for "at most one X" invariants, the shared `Clock` abstraction,
  `record_audit_entry`/`require_permission`/`require_project_permission`
  call shapes).

## Context

Section 11.6 of the audit doc rates Planned Costing **PARTIAL**: "Manual
`planned_amount`, ProjectResource planned hours, current rates, and baseline
task planned cost provide useful sources. They are mixed between persisted
and dynamically recalculated values, are not connected to budget lines, and
silently skip some currency mismatches." The target: "Introduce versioned
planned-cost snapshots sourced from assignments/material/manual inputs with
source IDs, quantity, snapshotted rate/Money, WBS, cost code, and plan
version. A recalculation creates a new snapshot/version rather than rewriting
the approved baseline."

## Scope boundary — read this first

**In scope**, per user decision this session: assignment-sourced labor
planned cost only (not material/manual inputs — those stay deferred), with
lines dimensioned by cost code + WBS/task, exactly like `BudgetLine`.

**Out of scope, explicitly deferred:**
- Manual/material planned-cost lines (audit doc mentions them as a future
  source; this slice is labor-from-assignments only, mirroring how Rate
  Cards and Budget were each scoped to one clear mechanism first).
- Baseline (`BaselineTask.baseline_planned_cost`) as a comparison source —
  not merged into this snapshot; a future reconciliation pass may compare
  the two independently.
- Any `CostPolicyEngine` cutover onto this new snapshot.
  `CostPolicyEngine._resolve_planned_labor_map` keeps computing its own
  transient project-resource-level planned labor total exactly as today;
  this new aggregate is a separate, persisted, versioned view, not a
  replacement. A future cutover plan (mirroring
  `rate_card_cost_engine_cutover_plan.md`) would do that separately, and
  would need to resolve the granularity mismatch noted below first.
- Any lifecycle beyond CURRENT/SUPERSEDED. There is no DRAFT/SUBMIT/APPROVE
  step — a snapshot is either the current calculation for a project or it
  has been superseded by a newer one. Nothing about "planned cost" is
  something a user proposes and another user approves; it is a computed
  fact about current assignments, recalculated on demand.
- A structural `budget_line_id` foreign key from a planned-cost line to a
  budget line. "Link dimensions to budget lines" is read as: **planned-cost
  lines and budget lines share the same dimension keys (`cost_code_id`,
  `task_id`)**, so a report can reconcile them by matching keys. A hard FK
  would wrongly assume a 1:1 relationship between two independently
  versioned aggregates (a budget line drawn up before any assignment exists
  yet, or a planned-cost snapshot recalculated many times against one
  unchanged budget line) — matching by dimension key at the read layer is
  the correct level of coupling, not a stored reference.
- QML section replacement.

## A real gap found during design: no per-task planned hours exists today

`ProjectResource.planned_hours` (`domain/projects/project.py`) — the only
planned-hours source `CostPolicyEngine` reads today — is **project+resource**
level; it has no `task_id`, so it cannot dimension a line by WBS.
`TaskAssignment` (`domain/tasks/task.py`) is the actual project↔task↔resource
link, but its only quantity fields are `allocation_percent` (a %, not hours)
and `hours_logged` (actual, not planned). Neither `ProjectResource` nor
`TaskAssignment` carries a `cost_code_id`.

Resolved by user decision this session:

1. **Add `planned_hours: float = 0.0` to `TaskAssignment`** — a new,
   genuinely per-task planned-hours field, validated exactly like
   `hours_logged` (`>= 0`, no upper bound — unlike `allocation_percent`,
   which is capped at 100). This becomes the authoritative source for this
   new aggregate. It does **not** replace or feed back into
   `ProjectResource.planned_hours`; the two are independent inputs used by
   two independent consumers (`CostPolicyEngine`'s existing project-level
   total vs. this new per-task snapshot), consistent with "no
   `CostPolicyEngine` cutover this phase" above. Assignments with
   `planned_hours == 0` (the default, so every existing row) are simply
   excluded from snapshot calculation — nothing breaks for projects that
   never set it.
2. **Cost code comes from `ProjectFinancialProfile.default_cost_code_id`**,
   applied uniformly to every line in a snapshot (there is no per-assignment
   or per-resource cost-code field to draw a finer-grained value from). If
   the profile has no default set, or the default cost code is inactive/not
   effective on the snapshot's `as_of` date, `calculate_snapshot` fails
   closed with `PLANNED_COST_NO_DEFAULT_COST_CODE` /
   `PLANNED_COST_DEFAULT_COST_CODE_INACTIVE` rather than snapshotting with
   an ambiguous or stale code. This is a coarser cost-code dimension than
   `BudgetLine` (which lets each line pick its own code) — a real, stated
   limitation of assignment-sourced data, not something this slice papers
   over.

## Domain model — `domain/financials/planned_cost.py` (new)

Two states only — no DRAFT/SUBMIT/APPROVE, since nothing here is proposed
for review:

```python
class PlannedCostVersionStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
```

### `ProjectPlannedCostVersion`

```python
@validated_dataclass
class ProjectPlannedCostVersion:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    revision: int                       # business version: 1, 2, 3... never reused
    status: PlannedCostVersionStatus = PlannedCostVersionStatus.CURRENT
    currency_code: str = ""             # project's financial-profile currency at calc time
    as_of: date = ...                   # rate-resolution date used for this snapshot
    calculated_by: str = ""
    calculated_at: datetime = ...
    is_complete: bool = True            # False if any assignment's resource rate was unresolved
    unresolved_resource_count: int = 0
    superseded_by: str | None = None
    superseded_at: datetime | None = None
    row_version: int = 1                # optimistic-concurrency token, distinct from `revision`
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
```

Same `revision`-vs-`row_version` split as `ProjectBudget`, for the same
reason: `revision` is which calculation this is (never changes once
written); `row_version` is the plain concurrency token that only ever
changes once, when this version is superseded by the next calculation.

Only two domain methods, mirroring `ProjectBudget.supersede`:

```python
def supersede(self, *, superseded_by: str, superseded_at: datetime) -> None:
    if self.status != PlannedCostVersionStatus.CURRENT:
        raise BusinessRuleError(
            "Only the current planned-cost version can be superseded.",
            code="PLANNED_COST_VERSION_SUPERSEDE_STATUS_INVALID",
        )
    self.status = PlannedCostVersionStatus.SUPERSEDED
    self.superseded_by = superseded_by
    self.superseded_at = superseded_at
    self.updated_at = superseded_at
```

No `ensure_mutable()` — there is no mutation path for a version's own header
fields once created (unlike `ProjectBudget`, nothing here is ever renamed or
annotated after the fact). The only two things that ever happen to an
existing row are: it stays `CURRENT`, or it transitions to `SUPERSEDED`
exactly once.

### `ProjectPlannedCostLine`

```python
@validated_dataclass
class ProjectPlannedCostLine:
    id: str
    tenant_id: str
    organization_id: str
    version_id: str
    project_id: str              # denormalized, defense-in-depth (mirrors BudgetLine)
    task_id: str                 # required — WBS dimension, from the source assignment
    resource_id: str
    cost_code_id: str            # the profile's default_cost_code_id at calc time
    assignment_id: str | None = None   # source lineage; nullable (see FK note below)
    planned_hours: float = 0.0
    rate_amount: Decimal = Decimal("0")   # snapshotted resolved rate, RateSelectionSnapshot.monetary_rate.money.amount
    amount: Decimal = Decimal("0")        # planned_hours * rate_amount
    currency_code: str = ""
    rate_card_id: str = ""        # source lineage
    rate_line_id: str = ""        # source lineage
    rate_card_version: int = 1    # source lineage
    created_at: datetime = field(default_factory=_utc_now)
```

No `row_version` on the line — lines are write-once as part of one
snapshot's calculation; there is no `update_line`/`delete_line` the way
`BudgetLine` has, since editing a snapshot line would contradict what a
snapshot is. Validators: `planned_hours >= 0`, `rate_amount >= 0`,
`amount >= 0`, `currency_code` via the same `CurrencyCode(...)
.minor_unit_quantum()` pattern as `BudgetLine`/`RateCardLine`, identifiers via
the same `_required_identifier` helper. `task_id`/`resource_id`/
`cost_code_id` required; `assignment_id` optional at the **domain**
validation level even though the calculation always supplies it — the field
exists to survive the assignment being deleted later (see the migration
section's `SET NULL` decision), not to be omitted at creation time.

## Contracts (`contracts/repositories/planned_cost.py`, new file)

```python
class ProjectPlannedCostVersionRepository(ABC):
    def add(self, version: ProjectPlannedCostVersion) -> None: ...
    def get(self, version_id: str) -> ProjectPlannedCostVersion | None: ...
    def list_for_project(self, project_id: str) -> list[ProjectPlannedCostVersion]: ...
    def get_current_for_project(self, project_id: str) -> ProjectPlannedCostVersion | None: ...
    def update(self, version: ProjectPlannedCostVersion, *, expected_row_version: int) -> None: ...
    def add_lines(self, lines: list[ProjectPlannedCostLine]) -> None: ...
    def list_lines(self, version_id: str) -> list[ProjectPlannedCostLine]: ...
    def flush(self) -> None: ...
```

No `delete`/`update_line`/`delete_line` — nothing in this design ever
mutates or removes an individual line or an existing version's header once
persisted; `update()` exists solely to flip `status`/`superseded_by`/
`superseded_at` on the previously-current row. `add_lines` takes a batch
(not one-at-a-time `add_line`, unlike `BudgetLine`) since a snapshot's lines
are always created together, in one calculation call.

`infrastructure/persistence/repositories/planned_cost.py` —
`SqlAlchemyProjectPlannedCostVersionRepository`, mirroring
`SqlAlchemyProjectBudgetRepository`: a `_context()` helper requiring
`TenantContextService`, `_require_entity_scope()` before every `add`/
`update`, every query filtered by `tenant_id`/`organization_id`, `update()`
via `update_with_version_check`.

## Application service (`application/financials/planned_costs/planned_cost_service.py`)

New package (the placeholder `application/financials/budgets/__init__.py`
pattern had no counterpart to reuse here — `planned_costs/` did not exist as
even an empty package before this slice).

### The one write operation: `calculate_snapshot`

```python
def calculate_snapshot(
    self, project_id: str, *, calculated_by: str, as_of: date | None = None
) -> ProjectPlannedCostVersion:
    require_permission(self._user_session, "plannedcost.manage", operation_label="calculate planned-cost snapshot")
    require_project_permission(self._user_session, project_id, "plannedcost.manage", operation_label="calculate planned-cost snapshot")
    context = self._require_context("calculate planned-cost snapshot")
    self._require_project(project_id)

    profile = self._financial_profile_repo.get_by_project(project_id)
    if profile is None:
        raise NotFoundError("Project financial profile not found.", code="PLANNED_COST_PROFILE_NOT_FOUND")
    if not profile.default_cost_code_id:
        raise BusinessRuleError(
            "Project has no default cost code configured.",
            code="PLANNED_COST_NO_DEFAULT_COST_CODE",
        )
    cost_code = self._cost_code_repo.get(profile.default_cost_code_id)
    resolved_as_of = as_of or self._clock.today()
    if cost_code is None or not cost_code.is_effective_on(resolved_as_of):
        raise BusinessRuleError(
            "Project's default cost code is inactive or not effective.",
            code="PLANNED_COST_DEFAULT_COST_CODE_INACTIVE",
        )

    tasks = self._task_repo.list_by_project(project_id)
    task_ids = [task.id for task in tasks]
    assignments = self._assignment_repo.list_by_tasks(task_ids) if task_ids else []
    eligible = [a for a in assignments if a.planned_hours > 0]

    resource_ids = tuple(sorted({a.resource_id for a in eligible}))
    batch = None
    if resource_ids:
        batch = self._rate_resolver.resolve_many(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            resource_ids=resource_ids,
            rate_type=RateType.COST,
            as_of=resolved_as_of,
            unit="HOUR",
        )

    now = self._clock.now()
    previous = self._planned_cost_repo.get_current_for_project(project_id)
    revision = (previous.revision + 1) if previous is not None else 1
    version = ProjectPlannedCostVersion.create(
        tenant_id=context.tenant_id, organization_id=context.organization_id,
        project_id=project_id, revision=revision, currency_code=profile.currency_code,
        as_of=resolved_as_of, calculated_by=calculated_by, calculated_at=now,
        created_at=now, updated_at=now,
    )  # version.id is generated client-side (generate_id()) — known before persisting,
       # so lines below can reference it directly with no second pass.

    lines: list[ProjectPlannedCostLine] = []
    unresolved_count = 0
    for assignment in eligible:
        snapshot = batch.snapshot_for(assignment.resource_id) if batch is not None else None
        if snapshot is None:
            unresolved_count += 1
            continue
        rate_amount = snapshot.monetary_rate.money.amount
        currency = snapshot.monetary_rate.money.currency.code
        planned_hours = Decimal(str(assignment.planned_hours))
        lines.append(ProjectPlannedCostLine.create(
            tenant_id=context.tenant_id, organization_id=context.organization_id,
            version_id=version.id, project_id=project_id,
            task_id=assignment.task_id, resource_id=assignment.resource_id,
            cost_code_id=profile.default_cost_code_id, assignment_id=assignment.id,
            planned_hours=assignment.planned_hours, rate_amount=rate_amount,
            amount=planned_hours * rate_amount, currency_code=currency,
            rate_card_id=snapshot.rate_card_id, rate_line_id=snapshot.rate_line_id,
            rate_card_version=snapshot.rate_card_version, created_at=now,
        ))
    version.is_complete = unresolved_count == 0
    version.unresolved_resource_count = unresolved_count

    try:
        with self._session.begin_nested():
            if previous is not None:
                previous_expected_version = previous.row_version
                previous.supersede(superseded_by=calculated_by, superseded_at=now)
                self._planned_cost_repo.update(previous, expected_row_version=previous_expected_version)
                self._planned_cost_repo.flush()
            self._planned_cost_repo.add(version)
            self._planned_cost_repo.flush()
            if lines:
                self._planned_cost_repo.add_lines(lines)
                self._planned_cost_repo.flush()
    except IntegrityError as exc:
        if self._is_revision_conflict(exc):
            raise ConcurrencyError(
                "Another planned-cost snapshot was calculated for this project concurrently.",
                code="PLANNED_COST_REVISION_CONFLICT",
            ) from exc
        raise

    self._record_version_audit(operation="calculate", version=version)
    self._commit()
    domain_events.planned_costs_changed.emit(project_id)
    return version
```

Notes on this shape, each answering a question the budget slice had to
answer explicitly:

- **Ordered supersede-before-add, same reasoning as budget's
  supersede-before-approve.** A partial unique index enforces "at most one
  CURRENT version per project" (below); superseding the old row and
  flushing before inserting the new one avoids a mid-transaction moment
  where two rows are simultaneously `CURRENT`. Unlike budget, there is no
  separate governed-approval branch to reconcile this against — this method
  has exactly one caller-facing entry point, no internal/bypass split needed.
- **Currency is the project's financial-profile currency, not a per-line
  choice.** Every resolved rate is normalized into that one currency before
  computing `amount`; a rate resolved in a different currency than the
  profile's is treated as unresolved for this snapshot (recorded in
  `unresolved_resource_count`) rather than silently mixed — same "excluded,
  not zeroed" policy `CostPolicyEngine`/EVM already use elsewhere in this
  codebase, not a new invented behavior. (Implementation detail: the
  resolver's `snapshot_for` already returns a specific resolved currency per
  resource per the ADR-PF-005 precedence chain; cross-currency normalization
  logic is the same `_normalize_currency`-style helper `CostPolicyEngine`
  already has, reused rather than re-derived.)
- **A snapshot with zero eligible assignments is not an error.** Unlike
  `submit_budget`'s `PROJECT_BUDGET_EMPTY` guard, a project with no
  positive-`planned_hours` assignments yet produces a valid, empty, CURRENT
  version (`is_complete=True`, `unresolved_resource_count=0`, no lines) —
  recalculating is a routine, frequent operation (unlike submitting a
  budget for approval), and failing it merely because nothing is planned yet
  would make "no plan yet" indistinguishable from "a real calculation
  error."
- **No governed-approval path.** Nothing here is submitted for review by a
  different principal; `calculate_snapshot`'s only permission check is
  `plannedcost.manage`, checked once, directly.

### Reads

- `get_current_snapshot(project_id)`, `list_versions(project_id)`,
  `get_version(version_id)`, `list_lines(version_id)`,
  `get_totals_by_task(version_id)`, `get_totals_by_cost_code(version_id)` —
  all gated by `finance.read` (+ `require_project_permission`), computed in
  Python from `list_lines()`, same pattern as
  `BudgetService.get_totals_by_cost_code`/`get_totals_by_task`. Because both
  services key their per-dimension totals by the same `(cost_code_id)`/
  `(task_id)` values, a report/reconciliation caller can directly compare
  `PlannedCostService.get_totals_by_task(current_version.id)` against
  `BudgetService.get_totals_by_task(approved_budget.id)` without any new
  linking table — this is the concrete mechanism behind "link dimensions to
  budget lines."

Constructor: `session, planned_cost_repo, project_repo, financial_profile_repo,
cost_code_repo, task_repo, assignment_repo, rate_resolver, clock,
user_session=None, enterprise_audit_service=None, module_catalog_service=None,
tenant_context_service=None` — no `approval_service` (nothing here is
governed). `rate_resolver: LaborRateResolver` — the same `RateCardResolver`
instance already shared with `CostPolicyEngine`/`BudgetService`'s
sibling services, not a second one.

**New permission**: `plannedcost.manage` only (reads reuse the existing
`finance.read`) — granted alongside `budget.manage` wherever that already
is (`_PLANNER`, `_PROJECT_LEAD`). Bump `SYSTEM_ROLE_POLICY_VERSION` to `9`.

## Migration (new revision after `m1n2o3p4q5r6`)

Revision `n1o2p3q4r5s6`, `down_revision = "m1n2o3p4q5r6"` (confirmed current
head of this chain — no later migration references it). Bundles two
independent, additive changes in one migration, following the precedent set
by the rate-card migration (`l0m1n2o3p4q5`), which added `resources.
department_id` alongside its two new tables in the same file:

### 1. `task_assignments.planned_hours`

```python
op.add_column(
    "task_assignments",
    sa.Column("planned_hours", sa.Float(), nullable=False, server_default="0"),
)
```

Purely additive; every existing assignment defaults to `0.0`, which is
already the "excluded from calculation" value — no backfill logic needed
beyond the column default itself.

### 2. `project_finance_planned_cost_versions`

Columns: `id, tenant_id, organization_id, project_id, revision, status,
currency_code, as_of, calculated_by, calculated_at, is_complete,
unresolved_resource_count, superseded_by, superseded_at, row_version
(mapped column name "version", same "version" ↔ "row_version" translation
`budget.py`'s mapper already uses), created_at, updated_at`.

Composite FKs to `tenants`/`organizations`/`projects` (same shape as
budgets). `UniqueConstraint(tenant_id, organization_id, id, name=
"uq_pf_planned_cost_versions_scoped_id")`. `UniqueConstraint(tenant_id,
organization_id, project_id, id, name="uq_pf_planned_cost_versions_scope_project_id")`
— enables the line's four-column composite FK below, same reasoning as
budget's `uq_pf_budget_scope_project_id`. `UniqueConstraint(tenant_id,
organization_id, project_id, revision, name=
"uq_pf_planned_cost_versions_project_revision")`. `CheckConstraint(status IN
('current', 'superseded'))`. `CheckConstraint(revision >= 1)`.
`CheckConstraint(unresolved_resource_count >= 0)`.

Partial unique index, same technique as budget's "one approved" index:

```sql
CREATE UNIQUE INDEX uq_pf_planned_cost_versions_one_current_per_project
ON project_finance_planned_cost_versions(tenant_id, organization_id, project_id)
WHERE status='current';
```

`info={"rls_scope": "tenant_organization"}`.

### 3. `project_finance_planned_cost_lines`

Columns: `id, tenant_id, organization_id, version_id, project_id, task_id,
resource_id, cost_code_id, assignment_id, planned_hours, rate_amount,
amount, currency_code, rate_card_id, rate_line_id, rate_card_version,
created_at`.

Four-column composite FK to the version, same shape/reasoning as
`BudgetLine`'s FK to `ProjectBudget` (guarantees
`ProjectPlannedCostLine.project_id == ProjectPlannedCostVersion.project_id`
at the database level, not just by service convention):

```python
ForeignKeyConstraint(
    ["tenant_id", "organization_id", "project_id", "version_id"],
    [
        "project_finance_planned_cost_versions.tenant_id",
        "project_finance_planned_cost_versions.organization_id",
        "project_finance_planned_cost_versions.project_id",
        "project_finance_planned_cost_versions.id",
    ],
    ondelete="CASCADE",
)
```

`task_id`: `ForeignKey("tasks.id", ondelete="RESTRICT")`, **not nullable** —
same reasoning as `BudgetLine.task_id`'s `RESTRICT` (a task referenced by
any snapshot line, even a superseded one, must remain queryable for
historical comparison; deleting it must not silently corrupt a persisted
snapshot). `resource_id`: `ForeignKey("resources.id", ondelete="RESTRICT")`
— same reasoning; a snapshot line's resource dimension is structural, not
mere provenance. `cost_code_id`: composite FK to
`project_finance_cost_codes(tenant_id, organization_id, id)`,
`ondelete="RESTRICT"` (mirrors `BudgetLine`).

**`assignment_id` uses `ondelete="SET NULL"`, nullable — deliberately
different from `task_id`/`resource_id`.** Unlike the task/resource/cost-code
dimensions, `assignment_id` carries no independent financial meaning once
the line exists — `planned_hours`, `rate_amount`, `amount`, and
`currency_code` are already fully snapshotted onto the line at calculation
time. Making it `RESTRICT` like a dimension would mean that after even one
snapshot calculation ever ran, an ordinary, unrelated PM operation —
removing a resource's assignment from a task, part of normal scheduling
work, not a financial action — would become permanently blocked. `SET NULL`
here preserves the line's amount/hours/rate/dimensions intact and only loses
the (optional) "which exact assignment produced this" drill-down link,
which is a defensible trade for not freezing ordinary scheduling operations
indefinitely. `ForeignKey("task_assignments.id", ondelete="SET NULL")`.

`rate_amount`: `financial_numeric(FinancialNumericKind.RATE)` (per-hour
rate, not a budget total — matches how `RateCardLine.rate_amount` is typed,
not `BudgetLine.amount`'s `MONEY` kind), with
`info=financial_numeric_info(FinancialNumericKind.RATE)` for the A1
architecture guardrail. `amount`: `financial_numeric(FinancialNumericKind.
MONEY)`, `info=financial_numeric_info(FinancialNumericKind.MONEY)` — this is
the guardrail gap found and fixed during the budget slice's own
verification (`rate_cards.py`'s Numeric columns had never actually declared
this marker); this migration's ORM file declares it correctly from the
start, not as a follow-up fix. `CheckConstraint(planned_hours >= 0)`.
`CheckConstraint(rate_amount >= 0)`. `CheckConstraint(amount >= 0)`.
`rate_card_version`: plain `Integer`, no FK (source-lineage metadata, same
treatment as `RateSelectionSnapshot.rate_card_version` itself, which is a
snapshotted int, not a live reference). `info={"rls_scope":
"tenant_organization"}`.

Both new tables call `enable_tenant_organization_rls`/
`disable_tenant_organization_rls` in `upgrade()`/`downgrade()`. `downgrade()`
drops the two new tables (reverse order) and the `task_assignments.
planned_hours` column.

## Composition wiring

- `src/infra/composition/repositories.py`: `RepositoryBundle.
  planned_cost_repo: SqlAlchemyProjectPlannedCostVersionRepository`,
  constructed alongside `project_budget_repo`.
- `src/infra/composition/project_registry.py`:
  `ProjectManagementServiceBundle.planned_cost_service`, constructed after
  `budget_service` (needs `project_repo, financial_profile_repo=
  repositories.project_financial_profile_repo, cost_code_repo=
  repositories.project_cost_code_repo, task_repo, assignment_repo=
  repositories.assignment_repo, rate_resolver=rate_card_resolver` — the same
  shared instance already built for `cost_policy_engine`/`budget_service`'s
  sibling wiring in this function — `clock=system_clock,
  tenant_context_service=platform_services.tenant_context_service`). No
  approval-handler registration (nothing governed).
- `src/core/shared/events/domain_events.py`: add `planned_costs_changed`
  signal (catalog-tuple entry + `Signal[str]` field), same shape as
  `budgets_changed`, keyed on entity type `"project_planned_cost"`.
- `application/financials/__init__.py`: export `PlannedCostService`.
- `TaskAssignment`-touching files that need the new field threaded through:
  `domain/tasks/task.py` (`TaskAssignment.planned_hours` +
  `_validate_planned_hours` validator + `create()` gains a
  `planned_hours: float = 0.0` parameter),
  `infrastructure/persistence/orm/task.py` (`TaskAssignmentORM.
  planned_hours` column), `infrastructure/persistence/mappers/task.py`
  (both `assignment_to_orm`/`assignment_from_orm`), and the assignment
  repository's `update()` method (`row.planned_hours = assignment.
  planned_hours`).

## Test list (`src/tests/project_management/test_project_finance_planned_costs.py`)

- **`TaskAssignment.planned_hours` unit tests**: defaults to `0.0`;
  negative values rejected (`ASSIGNMENT_PLANNED_HOURS_INVALID`); no upper
  bound (mirrors `hours_logged`, unlike `allocation_percent`); persists and
  round-trips through the ORM/mapper/repository `update()` path.
- **Empty-project snapshot**: a project with a financial profile, a default
  cost code, but zero assignments (or all with `planned_hours == 0`)
  produces a valid `CURRENT` version with zero lines, `is_complete=True`,
  `unresolved_resource_count=0` — not an error.
- **Missing/inactive default cost code**: `calculate_snapshot` raises
  `PLANNED_COST_NO_DEFAULT_COST_CODE` when the profile has none set, and
  `PLANNED_COST_DEFAULT_COST_CODE_INACTIVE` when the configured default
  exists but fails `is_effective_on(as_of)`.
- **Basic calculation correctness**: two tasks, two resources with distinct
  resolved rate-card rates, `planned_hours` set on their assignments — the
  resulting lines' `amount` values equal `planned_hours * resolved rate`
  exactly (`Decimal`, no float drift), each line's `task_id`/`resource_id`
  match its source assignment, `cost_code_id` equals the profile's default
  on every line, and `rate_card_id`/`rate_line_id`/`rate_card_version` match
  the resolver's snapshot for that resource.
- **Unresolved-rate exclusion**: one assignment's resource has no
  resolvable rate-card line for the snapshot's `as_of` date — that
  assignment produces no line, `unresolved_resource_count == 1`,
  `is_complete == False`, and the other (resolvable) assignments' lines are
  still produced normally — "excluded, not zeroed," matching
  `CostPolicyEngine`'s existing convention.
- **Versioning/supersede correctness**: calculating a second snapshot for
  the same project supersedes the first (`status == SUPERSEDED`,
  `superseded_by`/`superseded_at` set) in the same transaction as the new
  version's insert; `revision` increments (`prior + 1`); `row_version` on
  the newly superseded row increments by exactly one; the partial "one
  current" unique index is exercised directly (two raw concurrent-style
  inserts both claiming `status='current'` for the same project are
  rejected at the DB level) and via the service producing
  `PLANNED_COST_REVISION_CONFLICT` (not a raw `IntegrityError`) under a
  forced concurrent-calculation race.
- **Line/version project-scope test**: a direct DB-level insert of a
  `ProjectPlannedCostLine` whose `project_id` differs from its parent
  `ProjectPlannedCostVersion.project_id` is rejected by the four-column
  composite FK.
- **`task_id`/`resource_id` RESTRICT tests**: deleting a `Task` or
  `Resource` referenced by any planned-cost line (current or superseded) is
  rejected at the database level.
- **`assignment_id` SET NULL test (the deliberate asymmetry with
  task/resource)**: deleting the source `TaskAssignment` after a snapshot
  referencing it exists succeeds and sets the line's `assignment_id` to
  `NULL`; the line's `planned_hours`/`rate_amount`/`amount`/
  `currency_code`/`task_id`/`resource_id`/`cost_code_id` are all unchanged —
  proving the snapshot survived intact.
- **Dimension parity with `BudgetLine`**: given a `ProjectBudget` with lines
  on `(cost_code_id=X, task_id=T1)` and `(cost_code_id=X, task_id=T2)`, and a
  planned-cost snapshot whose lines land on the same `(X, T1)`/`(X, T2)`
  keys, `PlannedCostService.get_totals_by_task(version_id)` and
  `BudgetService.get_totals_by_task(budget_id)` expose directly comparable
  dict keys — the concrete proof of "link dimensions to budget lines."
- **Financial-numeric guardrail**: `rate_amount`/`amount` both declare
  `info['financial_numeric']` on the ORM columns; the A1 guardrail test
  (`test_project_finance_persistence_guardrails.py`) passes against the new
  table with no follow-up fix needed (the gap found during the budget
  slice's own verification does not recur here).
- Tenant A cannot read/write Tenant B's version/line; same-tenant
  cross-organization IDs fail; optimistic concurrency on a stale
  `row_version` for the supersede path.
- `get_totals_by_task`/`get_totals_by_cost_code` sums match a hand-computed
  Decimal-exact sum of the underlying lines.
- Migration: upgrade creates both tables with RLS and the new
  `task_assignments.planned_hours` column with its `0` default; downgrade
  reverses cleanly (drops both tables, then the column); deleting a
  superseded version's row directly at the DB level cascades its lines
  (exercises the FK `ondelete="CASCADE"` independent of the service layer).

## Implementation order

1. `domain/tasks/task.py`: `TaskAssignment.planned_hours` field + validator
   + `create()` parameter.
2. `infrastructure/persistence/orm/task.py`,
   `infrastructure/persistence/mappers/task.py`, assignment repository
   `update()` — thread `planned_hours` through.
3. `domain/financials/planned_cost.py`
   (`PlannedCostVersionStatus`, `ProjectPlannedCostVersion` incl.
   `supersede()`, `ProjectPlannedCostLine`).
4. `contracts/repositories/planned_cost.py` (incl. `flush()`).
5. `infrastructure/persistence/orm/planned_cost.py`.
6. `infrastructure/persistence/mappers/planned_cost.py`.
7. `infrastructure/persistence/repositories/planned_cost.py`.
8. Migration `n1o2p3q4r5s6`: `task_assignments.planned_hours` column, both
   new tables, all constraints incl. the partial unique index, the
   scope-enabling unique constraint, the lines' four-column cascade FK, RLS
   enable/disable.
9. `role_permission_catalog.py`: `plannedcost.manage`, role wiring
   (`_PLANNER`, `_PROJECT_LEAD`, wherever `budget.manage` already is),
   version bump to 9.
10. `domain_events.py`: `planned_costs_changed` signal.
11. `application/financials/planned_costs/planned_cost_service.py`.
12. `application/financials/planned_costs/__init__.py`,
    `application/financials/__init__.py`: export `PlannedCostService`.
13. `src/infra/composition/repositories.py`: `planned_cost_repo`.
14. `src/infra/composition/project_registry.py`: service construction
    (shared `RateCardResolver`/`Clock`), bundle field.
15. `test_project_finance_planned_costs.py`: full test list.
16. Full regression run (`project_management` suite, then
    `src/tests/architecture` guardrails specifically) compared against a
    clean `git stash` baseline, exactly as done for the rate-card and
    budget slices.

## Verification

Run
`./pmenv/Scripts/python.exe -m pytest src/tests/project_management/test_project_finance_planned_costs.py -q`
first in isolation, then the full `src/tests/project_management` suite,
then `src/tests/architecture/test_project_finance_persistence_guardrails.py`
specifically. Compare any new failures against the currently-known
pre-existing-failure baseline (last enumerated at 24 failures in
[project_budget_lifecycle_plan.md](project_budget_lifecycle_plan.md)) via a
`git stash`/`pytest`/`git stash pop` cycle on the failing subset to confirm
whether they're genuine regressions or pre-existing.
