# R6D-F Integrated Hardening

Status: COMPLETE (2026-09-12). R6D-G is not started.

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
- The live R6D-C/D/E plus R6B Rate and consolidated R6D-F PostgreSQL selection
  passed **30 tests** via non-owner `app_runtime` with forced RLS. The new
  consolidated matrix is independently runnable and exercises both legal worker
  deliveries and direct hostile SQL across all nine final R6D Finance tables.
- Focused R6D-B/C/D/E/R6C application selection passed **69 tests**. Separate
  Finance/event invalidation regression selection passed **62 tests**.
  A real pair of separately committed Procurement events with the same
  correlation ID now produces two Commitment invalidations. The former
  correlation-based handler dedupe could suppress the second; the handler now
  uses per-UoW context identity while retaining intra-commit coalescing.
- Representative seeded SQLite approved-Time worker counts: post **27** SQL
  statements, exact Finance-inbox replay **3**, correction **33**, and
  no-Rate failure dispatch **26** (different entry points are labeled in their
  tests). Procurement delivery from
  R6D-E: create **32**, revise **30**, close **30**, receipt **38**, stale **9**,
  published-outbox replay **1**. Rate write counts are characterized in the
  R6D-B test. These are observations, not arbitrary production budgets.
- The actual Commitment Reader count and page statements were captured and
  explained under `app_runtime` with 1,000 scoped synthetic lines. The count
  used a sequential scan (44 shared-buffer hits, 0.43 ms) and the `LIMIT 25`
  page used a top-N heapsort (40 kB, 44 hits, 1.16 ms), without sort spill.
  The scan is reasonable for this all-in-one-project sample; no index is
  justified by this plan alone.
- `Posting Failures` is currently the **approved-Time** diagnostic only:
  its API queries approved-Time inbox evidence, its presenter title and QML
  section identify that scope, and it must not be described as a generic
  Procurement failure queue. Unsupported changed Procurement receipt semantics
  remain quarantinable, with no Finance-side correction invented.
- The same trace-correlation invalidation defect also affected the approved-
  Time and Finance setup handlers. They now use per-UoW context identity;
  their focused fan-out/dedupe suite passed **27 tests**. Other Finance
  capability handlers still use correlation-based dedupe and require separate
  reconciliation before the broader R6D closure claim.
- Decimal money/rate/quantity remains authoritative in R6D write paths.
  QML `Number()` hits in these screens are pagination/version/display values;
  `performance_query` and EVM float paths are current analytical authority
  reserved for R6E, not R6D ledger arithmetic. No new FX provider was added.

## A. Governed Rate vs Approved-Time Posting

- Posting resolves a candidate, acquires a PostgreSQL `FOR SHARE` lock on its
  scoped Rate Line, and verifies its version before using the snapshot. A
  concurrently changed line causes bounded re-resolution, never a mixed
  amount/provenance snapshot. Governed economic edits acquire `FOR UPDATE`
  before checking historical consumption. The lock is held by the Finance UoW
  through posting commit; neither path commits inside the service.
- In the edit-first live race, the worker initially sees Rate A (42.125), the
  governed command commits B (52.125), and the worker re-resolves B. It posts
  one Actual of 123.80 for 2.375 hours with line version 2 and matching Rate
  provenance. A later economic edit is denied; a permitted future end-date
  edit leaves posting/Actual history unchanged.
- In the worker-first live race, PostgreSQL reports a governed edit waiting on
  the worker's Rate lock. The worker posts Rate A and Actual 100.05 with line
  version 1. After its commit, the blocked economic edit rejects because the
  line has historical use. Independent runtime Sessions/UoWs and the real
  Finance command boundary and approved-Time dispatcher are used.
- The existing live Rate overlap advisory-lock test and service overlap checks
  remain green. The worker uses configured Rate Card evidence, not the seeded
  Resource's intentionally different `hourly_rate=999`.

## B. Combined Runtime-Role RLS Matrix

- `test_r6d_f_combined_finance_rls.py` runs the legal governed Rate edit,
  governed Manual Actual draft, approved-Time worker posting, and Procurement
  Commitment/receipt delivery under real `app_runtime`. The role is
  `NOSUPERUSER`, `NOBYPASSRLS`, and owns none of the nine protected tables;
  every table has RLS enabled and forced.
- For Rate Card/Line, Cost Entry, Labor Posting, Commitment header/line/source
  revision/match, and Finance inbox, direct foreign-tenant and foreign-org
  `SELECT` and `DELETE` see zero rows. Direct forged foreign-scope `INSERT`
  receives SQLSTATE `42501`; mutable cross-scope `UPDATE` receives `42501`.
  Immutable ledger or envelope updates reject earlier in their trigger with
  `P0001`; a mutable Actual draft separately proves its RLS `UPDATE` denial.
- Genuine foreign-parent IDs are used for Rate Card project, Rate Line card,
  Actual project/Cost Code/Task/Resource/reversal original, Labor project/Actual,
  Commitment project/header, source revision line, Match line/Actual, and inbox
  project. In-scope forged child inserts fail scoped foreign keys with `23503`.
  These FK results are not mislabeled as RLS evidence.

## C. Authoritative Query Characterization

- Actual: a scoped 1,000-draft-row project sample with status and source-module
  filters executes **one count + one page SELECT**. The page uses deterministic
  date/created-at/ID order, `LIMIT 25`, and no row-level N+1. A representative
  runtime-role plan scans 1,000 matching rows, returns 25 using top-N heapsort
  (56 kB), 72 shared hits, about 1.65 ms. The existing desktop API regression
  proves stale-offset normalization; no separate selected-detail SQL is used
  by this list contract.
- Approved-Time: post **27**, replay **3**, correction **33** worker statements;
  no-Rate failure dispatch **26** statements. The failure path persists no
  Actual and records `RATE_CARD_NO_APPLICABLE_RATE` in retry diagnostics.
  Candidate Rate lookup uses scoped Rate Line and Card index scans (4 shared
  hits, about 0.11 ms) in a live `EXPLAIN (ANALYZE, BUFFERS)`; older R6D-B
  bounded Rate master/line plans still pass.
- Posting Failures: a scoped 1,000-retry-row inbox sample with approved-Time
  event type, project, status, server sort, ID tie-break and `LIMIT 25` executes
  **one count + one page SELECT**, with no N+1 or client-side filtering. The
  representative plan scans 1,000 matches, returns 25 with a top-N sort
  (87 kB), 201 shared hits, about 1.55 ms. The existing sensitive-permission
  regression proves redaction does not change the bounded query shape.
- Commitment: reuse the live 1,000-line scoped count/page plan above. No
  full-table client filtering or demonstrated N+1 was found in these paths.
  Sequential scans in all-in-one-project samples are not sufficient evidence
  for new indexes; **no index change is required by current plans**. Selective
  multi-project scale belongs to later R6H performance work, not this gate.

## D. Invalidation and Scope

- Multiple Finance events in one commit still coalesce. Two distinct committed
  Finance/Time or Procurement deliveries with the same correlation ID each
  invalidate once; correlation ID is not a global suppression key. Targeted
  Finance/event invalidation selection: **62 passed**. The separate Time/setup
  handler regression selection previously passed **27 tests**.
- Final targeted verification: **30 live PostgreSQL**, **69 R6D/R6C
  application**, **62 invalidation**, and **14 Time/stale-offset** tests passed.
  Python compilation and `git diff --check` passed. `ruff` is unavailable in
  `pmenv`; no QML changed, so QML lint is not applicable.
- R6D-G, R6E, Procurement correction semantics, Billing, and Accounting remain
  untouched by R6D-F. No legacy compatibility path or product functionality
  was added in this phase.

The future Procurement producer must define accepted-receipt correction,
reversal, and revision linkage. Since no such event contract exists today,
Finance rejects/quarantines changed receipt semantics rather than inventing
replacement Actual or Match history. This is a future source-contract need,
not permission to weaken the current fail-closed boundary.
