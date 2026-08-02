# ADR-PF-005: Rate-Card Precedence

- Status: accepted
- Date: 2026-08-02
- Implementation gate: Phase B rate cards

## Context

Current labor costing chooses a ProjectResource override or Resource current hourly rate. There are no effective dates, cost-versus-billing distinction, role/skill/department rates, unit safety, or historical snapshots. A deterministic precedence rule is required before rate cards are modeled.

## Decision

- Cost and billing rates are separate rate types and never fall back across type.
- Specificity order is: customer-contract/project resource override; project resource override; project role/skill/department line; organization resource line; organization role/skill/department line; legacy Resource default during transition; otherwise fail with no applicable rate.
- Selection filters by effective date, currency policy, unit, overtime/holiday context, and active version before applying precedence.
- Equal-specificity overlapping matches are configuration errors, not arbitrary first-match choices.
- A selected `MonetaryRate`, rate-line ID, rate-card version, basis, and effective date are snapshotted on planned/posting lines.
- Overtime/weekend/holiday multipliers are explicit modifiers applied after base-rate selection and recorded in the snapshot.

## Alternatives Rejected

- Continue current-rate lookup: retroactively changes history.
- Copy one hourly rate onto assignments: does not solve effective dates, units, or billing rates.
- Select the first database match: nondeterministic and unsafe.

## Consequences

Rate-card configuration must prevent invalid overlaps and expose explainable selection results. PM owns selection policy; platform MonetaryRate owns only amount-per-unit arithmetic.

## Migration Impact

Resource and ProjectResource rates seed transitional effective-dated lines with explicit origin and start policy. They remain fallback projections until every consumer migrates.

## Test Impact

Test every precedence level, ambiguity, effective boundaries, unit mismatch, cost/billing separation, modifier application, missing rate, and historical snapshot stability.

## Acceptance Evidence

The Phase B gate reverified that current costing has only Resource and ProjectResource current-rate defaults and no competing rate-card implementation. The accepted order is deterministic, keeps cost and billing rates separate, fails on ambiguity, and requires immutable selection snapshots. Rate-card schema and selection implementation remain a subsequent Phase B slice.
