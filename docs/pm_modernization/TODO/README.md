# PM Modernization — Consolidated Pending Work

Generated 2026-08-06 by reading every file in `docs/pm_modernization/` and separating
done/partial/pending. This is the single place to look for what's left; the other docs
in this folder describe what already exists and why. Three fully-superseded implementation
logs were deleted as part of the cleanup; their disposition is recorded at the bottom.

Updated 2026-08-08 after completing the numbered CQRS plan and reconciling the subsequent
Desktop Adapter Responsibility Audit. CQRS Phases 0A-0C and 1-6 are complete. The
Session/Unit-of-Work investigation remains a separate future architecture decision; it is
not an unfinished CQRS phase.

## 0. Desktop adapter responsibility hardening (in progress)

Source: `../CQRS/project_management_cqrs_existing_state_audit.md`, "Desktop Adapter
Responsibility Audit." This work was identified after the original consolidated TODO was
generated and therefore takes priority over starting the much larger Finance Phase C.

- **DA0 - Guardrails and characterization (in progress):** architecture guardrails are
  implemented and all six P0 behavior themes are characterized. The nine P1 findings still
  require characterization before DA0 closes.
- **DA1 - Composition leaks (not started):** Resources first as the low-risk migration,
  followed immediately by Projects and Tasks because their findings are tenant/RBAC
  sensitive.
- **DA2 - Application orchestration (not started):** move assignment previews, task/project
  access resolution, dashboard partial-failure behavior, and other application decisions out
  of presentation builders.
- **DA3 - Domain policy (not started):** remove lifecycle, certification, scheduling, and
  financial policy calculations from serializers/builders.
- **DA4 - Read orchestration and cleanup (not started):** consolidate only measured duplicate
  reads, remove dead procurement helpers, and preserve desktop DTO contracts.

### DA0/DA1 exception deletion register

These are verified pre-existing violations, not permanent exemptions. The architecture suite
holds the exact set so both additions and removals require an explicit update. Delete each test
exception in the same change that removes its runtime violation.

| Exception group | Current locations | Removal gate | Status |
| --- | --- | --- | --- |
| Repository contracts imported by desktop Resources | `resources/api.py`, `resources/factories/resources_api_factory.py`, `resources/services/availability_resolution_service.py` | DA1 injects public application collaborators from composition | OPEN |
| Private collaborator access | Resources availability/assignment builders; Projects access/resource builders and API; Tasks access/resource lookup builders | DA1 replaces every private fallback with a public application method or injected collaborator | OPEN |
| Application objects constructed in desktop code | `ResourceAvailabilityService`, `ConstraintValidator` | DA1/composition migration provides constructed collaborators | OPEN |
| Private platform module imports | `common/financial_formatting.py` imports `finance.money._decimal`; Dashboard imports `approval._approval_labels` | Expose and consume public platform contracts | OPEN |

**DA0 exit gate:** all P0/P1 behaviors have characterization coverage; architecture scanners
reject synthetic violations; every remaining exception above has a named DA1 removal owner.

Implementation checkpoint (2026-08-08):

- `test_pm_desktop_adapter_architecture.py` pins the exact repository-import, private-access,
  application-construction, and private-module exception sets; it also blocks reverse
  application/domain imports and proves the scanners detect synthetic violations.
- `test_pm_desktop_adapter_da0_characterization.py` pins the schedule-impact baseline
  divergence, Projects tenant-context fallback, both Tasks authorization fallbacks, and the
  Scheduling placeholder-success behavior.
- Dashboard authorization/infrastructure error propagation was already corrected and remains
  covered by `test_phase0a4_other_safety_corrections.py`.
- Focused checkpoint: 20 tests passed. DA0 remains open only for P1 characterization.

## 1. Finance — Phase B, remaining

Source: `../project_finance_existing_state_and_implementation_plan.md` §19 Phase B, items 7-8.

- **Item 7, second half (not done):** `CostPolicyEngine`/`LaborCostEngine`'s own "planned"
  figures (feeding KPIs/dashboards/`FinanceSnapshot.planned`) still read
  `ProjectResource.planned_hours` directly instead of `ProjectPlannedCostVersion`. A full
  cutover was investigated and explicitly rejected for now — see the doc's Phase B item 7
  sub-section — because of a granularity mismatch (envelope-level vs allocated-to-task),
  three call sites that would disagree, and no freshness/recalculation-trigger mechanism.
  Before revisiting: decide whether unallocated envelope hours should still count as
  "planned," and build an assignment-change-triggered recalculation mechanism.
- Baseline provenance (which exact rate-card line/version valued each baseline task) is not
  recorded — would need a baseline financial-snapshot extension.
- **Item 8 (not started):** replace the QML combined "Budget" cost-line section with
  separate Profile, Budget Versions, Budget Lines, Rate Cards, and Planned Costs views.

## 2. Finance — Phase C: actual ledger, commitments, time, procurement, periods (not started)

Source: same doc, §19 Phase C. All 8 items are unstarted; only the prerequisite
`TRANSITION(PF-A0-UOW-BRIDGE)` cleanup that items 2/6 depend on is done (governed
commands now own their own Unit of Work). ADR gate: ADR-PF-004/006/007/008 already
ACCEPTED, so the ADR gate itself is not blocking.

1. Organization financial periods + closure/lock policy (separate from scheduling calendars).
2. `ProjectCostEntry` draft/approval/post/reversal lifecycle with Money/base-Money/FX
   snapshot, source, period, dimensions, actor/timestamps, scoped idempotency.
3. PM commitment projections/lines, matching, cancellation/closure, remaining-balance policy.
4. Approved-Time contract/event + idempotent labor-cost consumer (snapshot rate,
   reverse/replace on corrected approvals).
5. Typed Procurement project-source queries/events (PO lines, changes, cancellation,
   receipts, supplier invoice references).
6. Replace manual combined `CostItem` writes with distinct planned/commitment/manual-actual
   commands; posted actuals never editable/deletable.
7. Backfill/split legacy `CostItem` rows, dual-read for reports, reconcile totals, quarantine
   unresolved currency/source cases.
8. Redesign QML Actuals/Commitments as ledgers (status, source, period, matching, approval,
   posting, reversal); remove generic edit/delete on posted rows.

## 3. Finance — Phase D and E (future, not started)

- **Phase D** (forecasts/ETC/change control/reporting): forecast versions+lines, ETC source
  precedence, typed financial change requests, rebuilt read models off canonical Money,
  export metadata (as-of/basis/period/pagination/reconciliation), remove desktop forecast
  fallback formulas, redesign QML Forecast/ETC/Change/Variance tabs.
- **Phase E** (billing/revenue/external accounting): blocked on ADR-PF-010 (currently
  PROPOSED, not accepted) and the product decisions in §24 items 10-15 of the master doc.

## 4. Finance — open transition-code register items

Source: same doc §20 "Transition-code deletion register." `OPEN`/`NOT CREATED` rows only
(everything else is `CLOSED`):

| Component | Removal gate |
| --- | --- |
| `cost.manage` umbrella/alias | Target command permissions active across desktop/services |
| Legacy combined `CostItem` write API | Phase C distinct commands + QML cutover |
| Legacy `CostItem` reader/projection | Phase D ledger/report reconciliation complete |
| `Project.planned_budget` compatibility projection | Budget read cutover + reconciliation complete |
| `Project.currency` compatibility projection | Profile currency cutover, all consumers migrated |
| Profile/Project currency dual-write (`PF-B1-CURRENCY-DUAL-WRITE`) | Desktop/presenters/reports/imports read profile currency exclusively; parity test passes |
| Float monetary/rate/quantity persistence | Numeric backfill + read cutover + reconciliation complete |
| Planned dual-read comparison (Phase C) | Phase D canonical report reconciliation complete — not created yet |
| Planned dual-write adapter (Phase C, only if required) | not created yet |
| Client-side fixed-limit Procurement lookup | Phase C typed project-source contract |
| Legacy financial permission aliases/feature flags | Phase E final role/API/controller inventory — not created yet |
| `Money.from_legacy_float` / `decimal_from_legacy_float` (`PF-A1-LEGACY-FLOAT`) | Phase D legacy reconciliation + float retirement complete |
| PM desktop formatter legacy-float branch (`PF-A1-DESKTOP-FLOAT`) | Phase D canonical decimal-string read DTO cutover |

## 5. Finance — open product decisions blocking later phases

Source: same doc §24. Unresolved (items already resolved by an accepted ADR are omitted):

- Which budget dimensions are mandatory in the first release beyond cost code/WBS (department,
  period, funding source)?
- Are projects single-currency, multi-currency-with-one-reporting-currency, or unrestricted
  multi-currency?
- Monetary precision, rounding mode, and line-vs-total rounding rules?
- Are manual actual costs allowed, and who may post/reverse them?
- Approval thresholds and separation-of-duties rules by tenant/org/department/project/amount/currency?
- Are expense claims in-product, a future Expenses module, or external-only?
- Which billing methods are in first PM scope — does PM only prepare billing or issue invoices?
- Is revenue recognition required, or are contract/billable/invoiced projections enough?
- Target external accounting/ERP system, identifiers, export format, acknowledgement/reconciliation workflow?
- Period-close authority and late-adjustment policy?
- Retention/export rules for financial audit, approval, source documents, reversals?
- ADR-PF-010 (billing vs. external-accounting boundary) needs to move from PROPOSED to ACCEPTED
  before any Phase E work.

## 6. PM Enterprise UI/UX — pending items

Source: `../README.md`, "PM UI/UX Inspection & Improvement Plan" section (Phases 1-11) and
the audit's "Known Limitations."

- **Phase 3 — Resource Assignment Visibility (⬜ not started):** wire
  `ResourceAvailabilityService`/`AssignmentValidationResult` into the Assign Resource dialog
  so selecting a resource shows overallocation %, conflicting projects, skill/cert match
  inline before the user clicks Assign.
- **Phase 4 — Lazy Loading Feedback (⬜ not started):** every `LazySectionLoader` section
  needs a `LoadingOverlay` while busy, an `EmptyState` when empty, and an `InlineMessage`
  danger + Retry button on load failure (pattern is written out in the source doc).
- **Phase 10 — Permission and Capability Handling (⬜ not started):** RBAC-gated buttons
  (Submit Baseline, Approve/Reject, Apply Leveling, Import) are always visible regardless of
  role. Add `can*` bool Q_PROPERTYs to each workspace controller, computed from
  `AuthorizationEngine.has_permission()` (table of required properties is in the source doc).
- **Phase 11 — Tests and Verification (⬜ not started):** add/extend tests for Phase 2, 3, 5,
  7, 10 behaviors listed in the source doc (presenter row-mapping tests, `previewAssignment`
  mapping test, `addTimeEntry` not triggering a full refresh, DataTable height regression
  check, `can*` property tests against a mock `AuthorizationEngine`).
- **No export infrastructure**: `infrastructure/exporters/` is empty. All export actions must
  stay disabled with a tooltip until Excel/PDF/Gantt renderers exist behind an adapter — do
  not ship empty stubs.
- **No tree-table component**: WBS hierarchy in Tasks uses a flat filtered list with
  on-demand children. Functional, but a dedicated tree-table component may be needed for deep
  WBS hierarchies later.
- **Async progress UX not wired**: `AsyncThresholdGuard` exists in the backend but no
  controller currently calls `classify_*`/`should_run_async()` before dispatching a LARGE+
  operation (recalculate schedule, leveling, forecast, schedule-impact preview, portfolio
  demand, report renders).

## 7. Team Collaboration — pending items

Source: `../TEAM_COLLABORATION_UPGRADE_PLAN.md` and `../TEAM_COLLABORATION_AUDIT_FINDINGS.md`
(2026-08-02 ground truth; supersedes README's collaboration claims wherever they disagree).

- **Phase 2 — cross-session delivery (open decision, not started):** notification
  persistence exists but nothing delivers a notification across sessions/users in real time.
  Needs a product decision between the Tier A/B/C options in the upgrade plan before any
  implementation starts.
- **Phase 3 — real notification channels (not started):** blocked on Phase 2.
- **Deferred, no committed timeline:** document version history; the "Delegate" approval
  quick-action.
- Notification persistence itself (Phase 1) is implemented but explicitly **not a shipped
  user-facing feature** — it has zero desktop consumer today; don't assume it's live.

## Deleted docs (2026-08-06 cleanup)

These were fully-superseded, no-longer-accurate, or complete-with-no-pending-work. Their
content is preserved in git history if a future reconciliation needs the detailed rationale
(rate precedence edge cases, budget concurrency proofs, etc.):

- `rate_card_cost_engine_cutover_plan.md` — status was "implemented and tested," zero pending
  items; substance is already captured in the master doc's §11.4 and Phase B item 4.
- `project_budget_lifecycle_plan.md` — status was "implementation complete and verified,"
  zero pending items; substance already captured in §11.5 and Phase B item 5.
- `project_planned_cost_snapshot_plan.md` — worse than merely done: its design (field name
  `planned_hours`, a single `is_complete` flag, optional non-authoritative
  `assignment_id` with `SET NULL`, no dual-version-token reconciliation) does **not** match
  what was actually built (`allocated_planned_hours`, three completeness flags
  `rates_complete`/`allocations_complete`/`cost_codes_complete`, required
  `source_assignment_id` with no live FK, dual optimistic-concurrency tokens on
  `TaskAssignment` and `ProjectResource`). Keeping it risked misleading a future reader about
  the real implementation; the accurate description lives in the master doc's §11.6.
