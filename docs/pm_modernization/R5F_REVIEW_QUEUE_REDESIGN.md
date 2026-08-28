# R5F Review Queue Redesign

## Status

R5F implementation is complete as of 2026-08-24. The PM Review Queue is a
read projection over platform-owned `TimesheetPeriod`; no queue aggregate,
generic approval engine, assignment review, or reviewer-owned submission flow
was introduced.

## Ownership And Workflow

The source states remain `OPEN`, `SUBMITTED`, `APPROVED`, `REJECTED`, and
`LOCKED`. Reviewer transitions are:

| Action | Transition | Permission | Required input |
|---|---|---|---|
| Approve | `SUBMITTED -> APPROVED` | `timesheet.approve` | period ID + expected version |
| Return | `SUBMITTED -> REJECTED` | `timesheet.approve` | period ID + expected version + reason |
| Lock | `APPROVED -> LOCKED` | `timesheet.lock` | period ID + expected version |
| Unlock | `LOCKED -> APPROVED` | `timesheet.lock` | period ID + expected version |
| Reopen correction | `APPROVED -> OPEN` | `timesheet.approve` | period ID + expected version + reason |

Submit remains an owner/time-entry operation and is absent from reviewer QML,
controller, and presenter contracts. Unsafe reviewer bulk actions were removed.

## Concurrency And Transaction

`TimesheetPeriod.version` is mandatory in the domain, ORM, mapping, repository,
read fact, desktop DTO, presenter state, and command payload. Repository writes
use one scoped conditional update over ID, tenant, organization, expected state,
and expected version, then increment the version. A zero-row stale write raises
`ConcurrencyError(code="TIMESHEET_PERIOD_STALE")`; stale state is never
overwritten.

The application transaction stages the conditional transition, append-only
enterprise audit evidence, and approved-time outbox record, flushes, and commits
once. Any failure rolls all three back. Domain invalidation and immediate outbox
dispatch occur only after commit. Audit metadata records actor, scope, reason,
old/new state, period identity, and resulting version.

The fresh pre-release baseline contains the version column directly. No
upgrade-only compatibility repair is retained.

## Authoritative Reads

`SqlAlchemyTimesheetReviewReader` implements the immutable
`TimesheetReviewQueueFact` with typed item discriminator
`TIMESHEET_PERIOD`. It preserves tenant/organization scope, server paging,
allowlisted server filtering/sorting, deterministic period-ID tie-breaking, and
a fixed count/page/project-attribution statement budget. The default filter is
`SUBMITTED`; historical states are explicit filters.

Totals include every period entry attributable to the Resource through employee
or assignment ownership. Direct-project and generic/non-task entries contribute
without fabricated Task attribution. Project-restricted visibility fails closed:
a period is visible only when its attributed projects are fully visible, and
each action capability plus command revalidates the specific permission for
every represented project.

The Inspector is independently authorized and loaded by period ID. It returns a
bounded summary/current version only; it does not hydrate or expose an unbounded
entry list. Initial queue load does not select the first row, and late Inspector
responses are ignored when selection has changed.

## Desktop And QML

The compatibility route ID remains `project_management.timesheets`, but the
visible destination and runtime controller are Review Queue only. Personal
assignment snapshots, entry models, entry mutations, Submit, and their hidden
controller/presenter state were retired. Task Detail continues to use the shared
desktop time-entry API directly and was not redesigned.

The shared `DataTable` remains in server sorting mode with single selection.
Actions render only from exact backend capabilities (`canApprove`, `canReject`,
`canLock`, `canUnlock`). Return uses a dedicated reason dialog, all mutations
carry `expectedVersion`, busy state prevents duplicate submission, and conflict
refresh preserves authoritative row/detail behavior. No lifecycle transition is
derived in QML.

## Legacy Cleanup

Removed the platform `TimesheetReviewMixin` N+1/unbounded read path, legacy
review queue/detail/entry models, the unbounded desktop review-entry DTO, PM
reviewer personal-time controller state, personal-time presenter commands, and
obsolete assignment/entry builders and table model. No compatibility shim or
temporary R5F transition code remains.

## Validation

- Transition/finance/N+1 targeted slice: `10 passed`.
- Core R5F read/UI/transaction slice: `26 passed` after stale-test corrections.
- R5F contract/presenter slice: `11 passed`.
- Fresh-baseline migration path: passed with `timesheet_periods.version` present.
- Direct touched-QML lint: clean after unused-import cleanup.
- Python targeted compilation: passed.
- One unrelated architecture test still detects the pre-existing stale
  `src/ui_qml/platform/controllers/admin` directory; it is outside R5F.
- No full test suite was run, per request.

## R5G Handoff

R5G owns integrated hardening, not Review Queue feature redesign: five-viewport
runtime geometry, keyboard/focus, popup anchoring, 100/1,000/10,000/50,000 data
measurements, PostgreSQL plans/index decisions, direct PostgreSQL tenant/org RLS
negative tests, combined Resource/Review Queue invalidation scenarios, and
memory/leak observation. These are explicitly unclaimed here.

R5F did not create a generic review framework, move Submit into reviewer UX,
change Task Detail Time, redesign Resources, begin Finance/R6, or commit changes.
