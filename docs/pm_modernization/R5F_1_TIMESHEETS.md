# R5F.1 Permission-Aware Resource Timesheets

## Status

**IMPLEMENTATION COMPLETE - R5H EVIDENCE GATES APPLY.** R5F remains closed and
Review Queue ownership is unchanged. R5F.1 owns one canonical `Work ->
Timesheets` workspace. R6 is outside this phase.

The earlier personal-only implementation is not a compatibility target. Its
`Owner*` contracts, reader, presenter, controller, tests, and QML type artifacts
must be renamed or deleted when the resource-centric cutover is complete. No
temporary personal-only code may remain after closure.

## Product Boundary

Timesheets prepares, inspects, corrects, and submits authoritative
`TimeEntry`/`TimesheetPeriod` records for one selected Resource and reporting
period. Review Queue approves, returns, locks, and unlocks submitted periods.
Reviewer authority never implies authority to edit another Resource's entries.

There is one Timesheets destination. `MINE`, `TEAM`, and `ALL` are query scopes,
not routes, tabs, or separate workspaces. Workload Management remains exactly
Resources and Review Queue.

## TimesheetScope

`TimesheetScope` is a typed string enum in the PM timesheet read contract:

- `MINE`: backend-resolved Resource linked to the authenticated identity.
- `TEAM`: Resources assigned to projects managed by the actor or included in
  the actor's explicit project-scoped timesheet authority.
- `ALL`: all eligible Resources in the active organization, only with explicit
  organization-wide permission.

A requested `resource_id` is always a filter after scope authorization. It
never grants access. `MINE` ignores/rejects an arbitrary target Resource.
`TEAM` and `ALL` initially require Resource selection and never auto-select the
first result.

## Permission Model

The implementation adds the minimum explicit authority separation:

| Permission | Meaning |
|---|---|
| `timesheet.read_own` | Read the actor-linked Resource's periods and entries |
| `timesheet.edit_own` | Add, edit, and delete the actor-linked Resource's open/correctable entries |
| `timesheet.submit` | Submit/resubmit the actor-linked Resource's period |
| `timesheet.read_team` | Read authorized project-team Resource timesheets |
| `timesheet.edit_team` | Prepare entries for authorized project-team Resources |
| `timesheet.read_all` | Read eligible Resource timesheets across the active organization |
| `timesheet.edit_all` | Prepare entries for eligible Resources across the active organization |
| `timesheet.submit_on_behalf` | Submit/resubmit another Resource's period |
| `timesheet.approve` | Review Queue decisions only |
| `timesheet.lock` | Review Queue lock lifecycle only |

Read-other does not imply edit-other. Edit-other does not imply delegated
submission. `timesheet.approve` and `timesheet.lock` grant none of the above
Timesheets preparation permissions.

## Mine Resolution

The service obtains the principal user ID and runtime tenant/organization IDs,
then the Reader resolves exactly one active eligible Resource through the
authoritative person-directory identity link. QML does not supply the Resource
for `MINE`. No match produces a truthful setup state; ambiguity is denied and
never resolved by choosing the first Resource.

Employee Resources require an active linked employee-directory record. External
Resources may optionally use that directory identity link for authenticated
self-service; the Resource remains `worker_type=EXTERNAL`. An external Resource
without a login has no `MINE` identity but remains available to an authorized
TEAM/ALL timekeeper.

## Team Authorization

The current schema has no generic line-manager hierarchy. R5F.1 therefore uses
the authoritative PM relationships that exist:

1. projects whose `manager_user_id` is the actor; and
2. project IDs carrying explicit project-scoped `timesheet.read_team` authority.

The Resource selector derives distinct Resources from assignments on those
projects in SQL. A target outside that set is denied. Organization-level TEAM
permission does not silently become ALL access.

## All Authorization

`ALL` requires `timesheet.read_all` in the active organization. Mutation still
requires `timesheet.edit_all`; delegated submission separately requires
`timesheet.submit_on_behalf`. Every query includes tenant and organization
predicates. ALL never crosses organizations or tenants.

## Eligible Resource Policy

One domain policy owns time-reporting eligibility. The initial authoritative
policy requires all of:

- active Resource;
- `ResourceKind.PERSON`;
- `WorkerType.EMPLOYEE` or `WorkerType.EXTERNAL`;
- labor-compatible Resource context supported by existing task assignments.

ResourceKind alone is insufficient. CREW and EQUIPMENT are denied unless a
future governed policy explicitly enables them. The policy is enforced by
selectors and the shared TimeEntry mutation path, so Task Detail -> Time and
Timesheets cannot disagree.

## Owner And Actor

The owner is the target Resource. The actor is the authenticated user. Existing
authoritative fields are retained:

- `TimeEntry.author_user_id/author_username` record entry mutation actor;
- `TimesheetPeriod.resource_id` records owner;
- `TimesheetPeriod.submitted_by_user_id/submitted_by_username` record submitter;
- period version and timestamps record lifecycle ordering.

No QML-derived owner/actor audit values are accepted.

## Delegated Workflow

Delegated entry is approved for TEAM/ALL actors with the matching edit-other
permission. Delegated submission is also approved, but only with
`timesheet.submit_on_behalf`. This enables an external Resource without a login
to complete the lifecycle while preserving owner and actor separately.

Normal status rules remain authoritative: OPEN and REJECTED may be changed when
permitted; SUBMITTED, APPROVED, and LOCKED are read-only in Timesheets. TEAM/ALL
authority never bypasses workflow state or optimistic version checks.

## Query Contract

The resource-centric query contains scope, optional authorized Resource,
period, search/project/task/date filters, page/page size, and allowlisted stable
sort. Period totals are computed over the complete authorized owner-period, not
the visible page and not only visible project labels.

Project/task identity may be redacted where project visibility is absent, while
hours remain included in truthful period totals. Redaction must not become a
filter that falsifies totals.

## Resource Selector

`TimesheetResourceSelectorReader` returns immutable lightweight facts only:
Resource ID/code/name, kind, worker type, active state, and eligibility. It
accepts typed scope, actor, search, page, and bounded page size. SQL performs
authorization, eligibility, search, stable order, count, limit, and offset.

The QML type-ahead never receives the organization Resource catalog. Query
budget per selector request is two bounded statements (count + page), with no
aggregate hydration or per-row lookups. Target is responsive bounded behavior
at 10k and 50k Resources; measurements are recorded before closure rather than
claimed from unit tests.

## UI Contract

MINE-only users see no scope or Resource selector. Privileged users see a
compact `View` selector. TEAM/ALL shows a bounded searchable Resource picker and
an explicit Select a Resource state. Once selected, period, summary, entries,
history, and commands all use that Resource context. The page never presents a
mixed all-Resource TimeEntry grid.

Backend-derived page capabilities include available scopes, selected Resource,
scope/resource selector visibility, read/history rights, entry CRUD rights,
submit/resubmit rights, and return-reason visibility. QML status strings do not
create authority.

## Implementation Map

1. Replace personal `Owner*` read DTOs/protocol with resource-centric typed
   workspace and selector contracts.
2. Add explicit permissions and role assignments without coupling reviewer and
   editor authority.
3. Add the central eligibility policy and enforce it in selectors and shared
   TimeEntry commands.
4. Replace `SqlAlchemyOwnerTimesheetReader` with a scoped reader implementing
   identity resolution, selector, period, entries, and history.
5. Refactor service methods around actor + scope + authorized target Resource;
   retain canonical TimeEntry/TimesheetPeriod commands.
6. Refactor desktop DTO/API, presenter/controller, and QML to one adaptive
   Timesheets workspace with bounded selector search/paging.
7. Delete superseded personal-only files and update QML type metadata.
8. Run targeted security/query/integration/QML tests and benchmarks; do not run
   the full suite unless separately requested.

## Mandatory Exit Gate

- [x] One Timesheets workspace exists under Work.
- [x] No My Time, Team Time, or All Timesheets top-level destination exists.
- [x] MINE/TEAM/ALL are typed query scopes.
- [x] MINE-only users see no unnecessary scope controls.
- [x] MINE Resource is resolved server-side and cannot be impersonated.
- [x] TEAM population is server-authorized; out-of-team targets are denied.
- [x] ALL requires explicit permission and never crosses tenant/organization.
- [x] Resource selection is bounded, searched, counted, paged, and sorted in SQL.
- [x] PERSON Employee and PERSON External are eligible under central policy.
- [x] External with login supports MINE; without login supports governed delegation.
- [x] CREW and EQUIPMENT are not automatically eligible.
- [x] Owner and actor remain distinct audit facts.
- [x] Read-other, edit-other, delegated submit, and review are separate permissions.
- [x] Direct target IDs never grant authorization.
- [x] Period totals remain truthful under project identity redaction.
- [x] TimeEntry and TimesheetPeriod remain authoritative.
- [x] Task Detail -> Time and Timesheets reuse the same mutation path.
- [x] On-behalf entry and submission are explicitly authorized.
- [x] Submission remains atomic and version-aware.
- [x] Review Queue refreshes through post-commit invalidation only.
- [x] History follows the selected Resource and is server-paged.
- [x] No Resource-selection N+1 query exists.
- [x] 10k selector performance is measured.
- [ ] 50k selector performance is measured where practical.
- [ ] 1024x640 TEAM/ALL layout is manually verified.
- [x] Review Queue was not redesigned by R5F.1.
- [x] Personal-only artifacts are deleted; no dead compatibility code remains.
- [x] No commit was created by Codex.

## Closure Evidence

Implementation and targeted R5F.1 contracts are complete. The optional 50k
selector run and manual 1024x640 interaction observation remain environment
evidence, not alternate implementation paths. Integrated results and the final
R5 decision are recorded in `R5H_WORKLOAD_MANAGEMENT_CLOSURE.md`.
