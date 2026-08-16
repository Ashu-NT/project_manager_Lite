# ADR-PF-010: Billing and Accounting Boundary

- Status: accepted
- Date: 2026-08-02
- Accepted: 2026-08-11
- Implementation gate: Phase E

## Context

PM invoicing/revenue packages and QML invoice views are placeholders. The repository has no official customer invoice, payment, tax, revenue-recognition, or general-ledger aggregate. Project Finance still needs billable-source selection, billing preparation, project revenue projections, profitability, and external reconciliation.

## Decision

> Project Finance owns the commercial and managerial financial view of project execution. Accounting owns statutory and receivables truth. PM may prepare, project, reconcile, and display external accounting outcomes, but it may never manufacture those authoritative accounting records itself.

- PM owns Project billing configuration/schedules, billable source eligibility, `ProjectBillingPreparation`, approval, duplicate-selection prevention, contract-value projections, and project profitability read models.
- A future Billing/Accounting module or external system owns official invoice numbers/documents, tax, receivables, payments, statutory revenue recognition, and GL posting.
- PM sends approved billing preparations through an idempotent contract and stores external acknowledgement, invoice reference, status snapshot, and reconciliation reference.
- External invoice/payment updates are projections in PM and cannot be edited as authoritative records.
- Only billing methods explicitly accepted by product are implemented; placeholder QML does not define scope.

## Accepted First-Release Scope

- PM prepares billing for `time_and_materials`, `fixed_price`, and `cost_plus` projects. Unit and recurring billing are deferred until a separate product decision adds their source and schedule semantics.
- PM never issues the official invoice. It owns billing schedules, preparation numbers, eligible-source selection, approval state, source locks, contract-value projections, and profitability read models.
- Fixed-price billing uses PM-owned billing schedule lines. A schedule line may reference a Project milestone/Task, but the billing amount and due/acceptance state remain finance-owned facts.
- Time-and-materials preparation selects approved-time billing facts with snapshotted billing rates. Cost-plus preparation selects posted cost facts and snapshots the approved markup policy. Expense-claim capture is deferred to a future Expenses owner; externally sourced posted expenses may participate through the canonical financial-source contract.
- PM exposes contract, billable, externally invoiced, externally paid, and margin projections only. Statutory revenue recognition remains external.
- The first accounting boundary is vendor-neutral contract version `project_billing_preparation.v1`, delivered through the platform durable integration mechanism. It carries tenant, organization, project, preparation, currency, immutable line, idempotency, and correlation identifiers. External acknowledgement supplies external system, invoice/reference, status, acknowledgement time, and reconciliation reference.
- Closed financial periods reject new billing preparation for sources in that period. Corrections are reversal/replacement preparations in an open period and retain the original preparation reference; PM does not reopen an external accounting period.
- Billing preparations, source locks, approvals, acknowledgements, reconciliation evidence, and audit exports are immutable or append-only after approval. Tenant retention policy is configurable with a seven-year default; legal hold prevents deletion. Phase E introduces no hard-delete workflow.

## Alternatives Rejected

- Build a full accounting application inside PM: violates scope and ownership.
- Let external accounting read PM tables directly: bypasses contracts, tenancy, and idempotency.
- Treat vendor commitment status `INVOICED`/`PAID` as customer billing: these are unrelated semantics.

## Consequences

Phase E may now proceed. The integration contract is vendor-neutral so an ERP-specific adapter can be selected later without changing PM ownership or aggregate semantics. QML presents preparation and integration status, not unsupported official accounting behavior.

## Migration Impact

No existing invoice data is available to migrate. Legacy vendor references remain procurement/cost source snapshots and are not reclassified as customer invoices.

## Test Impact

Test billable-source eligibility and locking, retry idempotency, approval, external acknowledgement/reconciliation, tenant isolation, sensitive profitability permission, and prevention of duplicate billing.

## Implementation Decisions — Phase E item 5 (locked 2026-08-12, margin formula revised after evidence-based investigation)

This section records the remaining implementation-level decisions needed to build the "contract, billable, externally invoiced, externally paid, and margin projections" this ADR already scopes (line 28) and the "sensitive profitability permission" this ADR already requires (Test Impact). It does not reopen or change anything else decided above.

**Profitability permission.** A dedicated `finance.read_profitability` permission is added, distinct from `finance.read_sensitive` (which protects individually-identified labor rates/costs — a different kind of sensitivity). Redaction mapping for the five ADR projections:

| Projection | Authority | Gate |
| --- | --- | --- |
| `contract_value` | `ProjectBillingProfile.contract_value` | `finance.read` |
| `billable_amount` | Sum of governed billing preparations | `finance.read` |
| `externally_invoiced_amount` | Derived from `ProjectBillingExternalEvent` | `finance.read` |
| `externally_paid_amount` | Derived from `ProjectBillingExternalEvent` | `finance.read` |
| `forecast_revenue_at_completion` / `revenue_basis` / `projected_margin_amount` / `projected_margin_percent` | Billing-method-aware revenue vs. canonical forecast cost at completion | `finance.read_profitability` |

Only the margin-family figures carry the extra tier — ADR-PF-010 does not classify the other four as more sensitive than ordinary Project Finance data, and least-privilege favors letting a caller see billing progress without also seeing commercial margin. Granted by default to `finance_controller` and `auditor`, mirroring `finance.read_sensitive`'s existing distribution.

**Margin definition — fixed-price only; T&M and cost-plus explicitly unavailable, not approximated.** Investigation found no `forecast_revenue_at_completion` concept anywhere in the codebase. Three specific questions were checked against the actual domain before adopting a formula, and the conclusion is deliberately conservative: **only fixed-price produces a projected margin today.**

- **Cost-plus EAC recoverability (checked, rejected)**: `add_cost_plus_source` (`preparation_service.py:253-294`) selects billable cost one posted `ProjectCostEntry` at a time with no cost-code/category filter, and no recoverable/non-recoverable cost distinction exists anywhere in the domain (the only `is_billable` flag is project-level, not per-entry or per-cost-code). `CostControlTotals.estimate_at_completion` is whole-project forecast cost. Applying `× (1 + cost_plus_markup_percent / 100)` to unfiltered EAC would silently overstate revenue for any project with non-recoverable cost mixed in — nothing in the domain proves 100% of EAC is recoverable. **Profitability is explicitly unavailable for cost-plus** (`revenue_basis = "unavailable_cost_plus_recoverability"`) until the domain can identify a recoverable-cost basis. This is a named, deferred limitation, not an oversight.
- **Time-and-materials `contract_value` semantics (checked, rejected as a revenue stand-in)**: `contract_value` is one flat field, required positive to activate *any* billing method, with zero method-specific validation, documentation, or "not-to-exceed" concept found anywhere (grepped). Using it as a stand-in forecast revenue for T&M would present an unproven number as if it were a real forecast. **Profitability is explicitly unavailable for time-and-materials** (`revenue_basis = "unavailable_time_and_materials_forecast_billing"`) until a forecast-billing-volume concept is built — `contract_value` itself remains visible under the ordinary `contract_value` projection (`finance.read`), just not repurposed as revenue.
- **Fixed-price**: the agreed `contract_value` does not move with cost, so it already *is* the forecast revenue at completion — exact, not an estimate. This is the only method where the projection is safe today.

```text
if billing_method != fixed_price:
    forecast_revenue_at_completion = None
    projected_margin_amount        = None
    projected_margin_percent       = None
    revenue_basis                  = "unavailable_time_and_materials_forecast_billing" | "unavailable_cost_plus_recoverability"
else:
    forecast_revenue_at_completion = contract_value                                     [revenue_basis = "contract_value"]
    projected_margin_amount        = forecast_revenue_at_completion - forecast_cost_at_completion
                                      (None if forecast_cost_at_completion is unavailable)
    projected_margin_percent       = projected_margin_amount / forecast_revenue_at_completion
                                      (None if the denominator is 0 -- never a fabricated percentage)
```

`revenue_basis` always names why a figure is present or absent, so no consumer has to guess. `forecast_cost_at_completion` is always the existing canonical `CostPolicyEngine`/`CostControlTotals.estimate_at_completion` — no new cost aggregation is introduced, and its own ETC generation already nets commitment exposure, so profitability cannot double-count commitments against actuals. This is a *projection*, not a billing-progress metric: `externally_invoiced`/`externally_paid` remain semantically independent commercial/billing-progress figures and are never substituted into the margin formula (invoiced-to-date minus cost-to-date answers a collections question, not a project-profitability question). T&M and cost-plus projects still receive their full `contract_value`/`billable_amount`/`externally_invoiced_amount`/`externally_paid_amount` projections under ordinary `finance.read` — only the margin family is unavailable for them.

**Externally invoiced/paid — checked against reversal/correction handling.** `ProjectBillingExternalEvent` carries no monetary field; invoicing/payment status is binary per preparation (has/doesn't have an `external_invoice_reference`; latest event `event_type == reconciled` is the closest available "paid" signal). Reversal/correction is modeled at the **preparation** level, not the event level: a negative-`total_amount` preparation must carry `correction_of_preparation_id` (`billing_preparation.py:185-193`) and goes through its own independent approval/delivery/external-event lifecycle. Summing `total_amount` per-preparation, gated by that preparation's own latest external event, therefore nets a confirmed correction against the original once both are independently confirmed — consistent with the domain's own validation rules, though no existing test exercises `correction_of_preparation_id` (a gap in existing coverage, not introduced by this work; a regression test for it is added alongside this feature). `externally_invoiced_amount`/`externally_paid_amount` carry an `external_accounting_data_available` flag rather than defaulting to a bare `0`, since no accounting integration exists yet (item 4) and a true zero must stay distinguishable from "no integration has reported anything." No `recognized_revenue` field is introduced — statutory revenue recognition remains external per this ADR's existing decision.
