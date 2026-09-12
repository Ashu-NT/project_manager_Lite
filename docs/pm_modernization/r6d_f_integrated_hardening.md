# R6D-F Integrated Hardening

Status: IN PROGRESS, NOT CLOSED (2026-09-12)

R6D-F is an integrated proof phase, not a new Finance feature. R6C stays closed;
R6D-E remains closed only for its current neutral Procurement contract. Do not
start R6D-G or R6E from this checkpoint.

## Verified So Far

- Authority remains Rate Card/Line for configured rates, `ProjectCostEntry` for
  posted managerial Actual, Time for approved work, Procurement for PO/receipt
  source truth, Commitment/Match for Finance projection/evidence, and Finance
  Inbox for worker dedupe. No Accounting authority or Procurement producer was
  introduced.
- Interactive Rate/Manual Actual writes enter the fresh Finance governance UoW.
  Approved-Time and Procurement dispatchers own separate fresh worker UoWs.
  Inner R6D services do not commit or roll back. Worker dispatcher source-outbox
  claim/ack commits and the Finance UoW commit are separate, intentional owners.
  `begin_nested()` in Commitment and Actual services translates local source
  identity/revision/reversal uniqueness races, not an outer commit.
- The live R6D-C/D/E plus R6B Rate PostgreSQL selection passed **24 tests** via
  non-owner `app_runtime` with RLS. Those tests include supported parent/child
  negative paths, legal workers, duplicate deliveries, source revision races,
  and Rate Reader/overlap coverage. They are not yet the complete combined
  hostile-parent matrix requested for R6D-F.
- Focused R6D-B/C/D/E/R6C application selection passed **71 tests**. Separate
  Rate/Actual/Commitment invalidation regression selection passed **54 tests**.
  A real pair of separately committed Procurement events with the same
  correlation ID now produces two Commitment invalidations. The former
  correlation-based handler dedupe could suppress the second; the handler now
  uses per-UoW context identity while retaining intra-commit coalescing.
- Representative seeded SQLite worker counts: approved-Time post **26** SQL
  statements and exact Finance-inbox replay **3**. Procurement delivery from
  R6D-E: create **32**, revise **30**, close **30**, receipt **38**, stale **9**,
  published-outbox replay **1**. Rate write counts are characterized in the
  R6D-B test. These are observations, not arbitrary production budgets.
- `Posting Failures` is currently the **approved-Time** diagnostic only:
  its API queries approved-Time inbox evidence, its presenter title and QML
  section identify that scope, and it must not be described as a generic
  Procurement failure queue. Unsupported changed Procurement receipt semantics
  remain quarantinable, with no Finance-side correction invented.
- Decimal money/rate/quantity remains authoritative in R6D write paths.
  QML `Number()` hits in these screens are pagination/version/display values;
  `performance_query` and EVM float paths are current analytical authority
  reserved for R6E, not R6D ledger arithmetic. No new FX provider was added.

## Remaining R6D-F Exit Gates

1. Prove the governed Rate-change versus approved-Time-post race and two
   concurrent overlapping Rate Line mutations under PostgreSQL; inspect whether
   a consumed Rate Line can be changed between rate resolution and worker commit.
2. Run the integrated Actual submit/approve/post/reverse and Time correction
   races under the runtime role, including commit-ack replay and staged-failure
   interactions. Existing single-family tests are not a substitute for every
   cross-workflow concurrency assertion.
3. Extend the forced-RLS hostile matrix across Rate, Actual dimensions and
   reversal parent, labor posting, Commitment children, inbox, and both source
   outboxes in one documented runtime-role execution. Direct foreign parent
   INSERT/UPDATE/DELETE coverage must be enumerated, not inferred from SELECT.
4. Record Actual create/submit/approve/reject/post/reverse, Time correction and
   no-Rate failure SQL counts. Run `EXPLAIN (ANALYZE, BUFFERS)` on current
   effective-Rate, Actual, Commitment, Posting Failures, revision lookup and
   open-Commitment queries with representative scoped volume. Only add indexes
   if a real plan establishes need. Check batch N+1 and lock order/scope.
5. Finish targeted invalidation, sensitive-redaction/project-isolation,
   Platform Approval, Time contract, Procurement neutral contract, R6B Reader,
   and R6C UoW regressions; then run compilation, lint if QML changed, and
   `git diff --check`. R6D-G cleanup inventory must classify possible dead
   R6D paths separately from valid R6E analytical authority.

The future Procurement producer must define accepted-receipt correction,
reversal, and revision linkage. Since no such event contract exists today,
Finance rejects/quarantines changed receipt semantics rather than inventing
replacement Actual or Match history. This is a future source-contract need,
not permission to weaken the current fail-closed boundary.
