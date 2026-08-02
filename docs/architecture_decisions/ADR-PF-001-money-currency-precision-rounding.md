# ADR-PF-001: Money, Currency, Precision, and Rounding

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase A1

## Context

PM finance, Time, and Procurement currently use binary floats for amounts, hours, rates, and quantities. Currency is an optional uppercase string, several PM services independently default to `EUR`, and formatting/calculation logic is duplicated. Project Finance needs exact arithmetic without making project concepts dependencies of a shared primitive.

## Decision

- Add dependency-free platform `CurrencyCode`, signed `Money`, `DecimalQuantity`, `MonetaryRate`, and `RoundingPolicy` value objects.
- `Money` contains Decimal amount and CurrencyCode. It permits negative, zero, and positive values; aggregates enforce their own sign rules.
- `DecimalQuantity` contains Decimal quantity and normalized unit. `MonetaryRate` is Money per normalized unit. Rate-card type, precedence, and effective interval remain PM-owned.
- Money arithmetic rejects currency mismatch. Rate multiplication rejects incompatible quantity units.
- Use canonical decimal strings at JSON/desktop boundaries, not binary JSON numbers. QML displays/parses values but performs no authoritative arithmetic.
- Proposed persistence conventions are `Numeric(19,4)` for stored monetary amounts, `Numeric(19,8)` for rates, `Numeric(19,6)` for quantities, `Numeric(9,6)` for percentages, and `Numeric(24,12)` for exchange rates. Schema review must verify expected maximum values before acceptance.
- Round only at named boundaries using currency minor-unit metadata and a single policy. The proposed default is `ROUND_HALF_EVEN`; billing/tax-specific alternatives require a later explicit policy decision.
- Resolve default currency from explicit transaction input, then Project Financial Profile, then Organization base currency. Invalid or ambiguous data fails/quarantines; it never silently becomes `EUR`.

## Alternatives Rejected

- Keep floats and round for display: display rounding cannot repair calculation/storage error.
- Put Money inside PM: Procurement is already a second real consumer.
- Put rate-card behavior in platform Money: it would introduce business-specific policy into a primitive.
- Store amounts as integer cents only: currencies have varying minor units and rates require greater precision.

## Consequences

All financial adapters and persistence mappings must use one conversion convention. Money can represent reversals and adjustments, while budget/commitment policies remain non-negative. Time and Procurement adoption can be incremental but no new financial field may use float.

## Migration Impact

Legacy floats are converted through their decimal string representation, rounded under the accepted policy, and reconciled by project/currency. Unresolved currencies are quarantined. New Numeric columns/tables are additive before cutover.

## Test Impact

Add property/unit tests for arithmetic, sign, mismatch, allocation, precision, minor units, serialization, rate/unit multiplication, persistence round trips, and conversion/reconciliation edge cases.
