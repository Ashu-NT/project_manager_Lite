# ERP Composition Architecture

## Initial State (2026-10-09)

The ERP has one application root at `src/infra/composition/app_container.py`.
`build_service_graph()` builds a mixed Platform/PM `RepositoryBundle`, then the
Platform bundle, PM bundle, Global Overview, and cross-module dispatchers. It
also replays durable Approved-Time and Procurement work during startup. The
desktop shell and test fixtures consume `build_service_dict()`; several tests
and Global Overview import the existing bundle types/builders directly.

| Current file | Size / responsibility | Target owner |
| --- | --- | --- |
| `modules/platform_registry.py` | 1,287 lines: tenant/auth bootstrap, Platform repositories/services, event subscriptions, approval, calendars, notification delivery | `core/platform/infrastructure/composition/{bootstrap,dependencies,events,registrations}` |
| `modules/project_registry.py` | 1,891 lines: PM access registration, all PM services/UoWs, Finance governance/workers, event subscriptions, approval handlers | `core/modules/project_management/infrastructure/composition/{bootstrap,dependencies,events,registrations}` |
| `persistence/repositories.py` | 321 lines: mixed Platform/PM repository bundle and construction | Platform/PM-owned repository bundles, assembled explicitly by root |
| `notifications.py` (retired) | Platform Approval policy plus PM assignment/mention policy and PM delivery-time recipient recheck | Split between Platform events and PM registrations; root injects PM delivery policy |
| `approval_apply_dependencies/*` (retired) | Seven PM approval dependency factories, some rebuilding scoped repositories | PM `registrations/approvals`, with Finance factories under `approvals/finance` |
| `integration/accounting/*` | External Accounting transport/outcome composition | Root integration composition; PM handoff stays destination-neutral |
| `global_overview_registry.py`, `global_overview_invalidation.py` | Cross-module read and invalidation assembly | Root/global-overview composition (not Platform or PM business authority) |
| `app_container.py` | 546 lines: service graph projection, ordered assembly, cross-module dispatch and startup replay | Small root `app_container.py` plus explicit `platform.py`, `modules.py`, `integrations/` |

Only Project Management exists under `src/core/modules` today. No empty
composition packages should be created for hypothetical modules. At baseline,
neither Platform nor PM infrastructure had a composition package; C1 created
both for the first extracted responsibilities.

## Dependency and Lifetime Rules

1. Root constructs one shared session-bound repository graph, Platform bundle,
   PM bundle, Global Overview, and then integration dispatchers. Cross-module
   dispatchers must not be built before the PM Finance worker UoW factories.
2. Platform bootstrap must not import PM ORM, events, services or policies.
   Root may inject a PM-provided extension/port into Platform notification
   delivery before PM service construction. PM registers its transactional
   handlers once against the shared Platform dispatcher during PM bootstrap.
3. The existing long-lived desktop Session, fresh command UoW sessionmakers,
   shared transactional dispatcher, post-commit bus, and scoped view channel
   must retain identity/lifetime. No duplicate subscriptions or service graphs.
4. PM Finance creates raw services, then a fresh-session governance UoW and
   governed ports; workers use explicit service principals. Do not reorder
   this construction or convert it to a global locator.
5. Current composition mutates shared services after construction: Platform
   injects tenant context into repositories; PM registers access/auth scope
   resolvers and approval handlers; root sets the Approved-Time dispatcher
   on Time and performs bounded startup replay. These are sequencing risks to
   make explicit, not a license to change behavior during structural moves.
6. Notification and Approval transactional handlers access `uow._session`.
   Keep this fact visible during migration; replacing it requires a separate
   scoped UoW-port design and atomicity proof, not an opportunistic rename.

## Public Import Migration

`app_container.build_service_graph/build_service_dict` are public root entry
points and remain stable. `PlatformServiceBundle` and
`ProjectManagementServiceBundle` are consumed by Global Overview and tests;
their field contracts remain stable while imports move with the implementation.
The `src/infra/composition/modules/*_registry.py` modules are internal root
imports but have test consumers; migrate those tests with each cutover and
delete superseded files rather than keeping production compatibility shims.
Direct test imports of `notifications.py` and
`approval_apply_dependencies/*` moved with their owning phases. The shared mixed
`RepositoryBundle` cannot be deleted until Platform, PM, root and all approval
factory callers have been migrated together.

## Incremental Execution Map

| Gate | Change | Verification / deletion condition | Status |
| --- | --- | --- | --- |
| C0 | Baseline inventory, public-import and lifecycle map | Composition/architecture tests run; no source changes | Complete |
| C1 | Split Platform Approval vs PM notification registration and PM recipient recheck; inject policy from root | Same transactional subscription counts, recipient/privacy/RLS and startup tests; delete mixed `notifications.py` | Complete |
| C2 | Move PM access/scope registrations and approval registrations/dependency factories into PM composition | Service identity, reviewer permissions, handler counts, transaction/UoW tests; delete root approval factory package | Complete; mixed repository-bundle dependency remains until C5 |
| C3 | Extract PM Projects, Tasks, Resources, Scheduling, Timesheets, Collaboration, Portfolio and Risk dependency/event groups | Per-group focused tests; no duplicated factories/subscriptions; preserve PM bundle | Complete; Finance remains C4 |
| C4 | Extract Finance core/governance/workers last, preserving fresh sessions, governed ports and service-principal factories | Finance integration, atomicity, concurrency, RLS and startup replay tests | Structural cutover complete; broad regression gate remains open on classified, non-Finance baseline failures |
| C5 | Move Platform services/events and split repository bundle by owner | Platform auth/tenancy/calendar/approval suites; root remains sole assembler | In progress: Platform post-commit registrations extracted; service/repository ownership remains |
| C6 | Slim root and move only cross-module integrations/global overview wiring under root | Desktop startup, full PM/Platform, PostgreSQL and architecture guards; delete both central registries and obsolete imports | PM bootstrap ownership cut over early; root/Platform slimming remains |

Do not blindly mirror the proposed folder tree. Add a feature subfolder only
when an extraction has an actual responsibility and test boundary. No business
rules, schema, authorization semantics or domain behavior change is permitted.

## Current Migration Evidence

- C1: Platform Approval notification subscriptions now live under Platform
  composition; PM assignment/mention subscriptions and recipient recheck live
  under PM composition. The root injects the PM recheck into the single
  Platform notification dispatcher. The mixed root `notifications.py` was
  deleted, and no import of its old path remains. A service-graph test asserts
  the shared transactional dispatcher and exactly one handler per event type.
- C2 access slice: PM owns project scope policy and the Access, Auth, and Role
  Governance resolver registrations. The call remains at the original PM
  startup position. A service-graph test checks that Access and Auth share the
  same resolver and Role Governance has its two resolvers.
- C2 approval slice: PM owns all approval-handler registration and seven scoped
  dependency factories. Budget, Forecast, Project Cost, Financial Change and
  Billing Preparation composition is grouped under `approvals/finance`; Task
  and Baseline stay outside that Finance subfolder. The PM builder calls the
  registration function at the original point. The root approval factory
  package and all old imports were removed. Factory session construction and
  reviewer-permission mapping are unchanged. The factories still import the
  mixed root `RepositoryBundle`; remove that inward-to-root dependency at C5,
  not through a speculative bundle rewrite in C2.
- Verification: focused composition/Platform notification/architecture tests:
  20 passed; focused access/composition/architecture tests: 12 passed;
  PostgreSQL R7B governance and R7D notification/RLS tests: 51 passed. Scoped
  Ruff F/I, targeted mypy for new registration files, Python compilation, and
  `git diff --check` passed. C1 earlier focused notification checks also passed
  (17, 40, and 24 tests in separate targeted runs). These counts are not a full
  ERP regression run; broad validation remains a C4/C6 closure gate.
- C2 approval verification: 55 focused approval/factory/composition tests and
  54 live PostgreSQL governance, Billing rate-snapshot and Finance governance
  tests passed. A later composition/guard run passed 16 tests and the corrected
  ownership guard passed. The broader architecture run was 175 passed, 3
  failed: one stale scope-registration path guard was corrected; two unrelated
  failures remain in the repository (Platform/UI files over the size limit and
  a guard targeting the already-moved procurement consumer). Scoped Ruff F/I,
  compilation and `git diff --check` pass. Targeted mypy on the moved factory
  package reports two existing contract mismatches carried unchanged from the
  original files: `approval_service=None` in Billing Preparation and the
  `TaskService` schedule-apply protocol signature in Financial Change. Neither
  was masked or altered by this structural move.
- C3 Projects and Register: PM-owned `dependencies/{projects,register}.py`
  construct fresh-session command UoWs and services; PM-owned
  `events/{projects,register}.py` subscribe the existing post-commit invalidation
  handlers. Calls remain in the same order in the central builder. Composition
  tests prove one shared bus, one handler per affected event, and fresh UoW
  sessions bound to the same engine. Project-focused tests: 31 passed;
  Register-focused tests: 12 passed. The four new modules pass targeted mypy
  and Ruff F/I. They temporarily depend on the mixed root repository and
  Platform bundles; C5 must remove that dependency when bundles split.
- C3 Tasks and Timesheets: PM-owned dependency builders construct the Task
  fresh-session UoW and the single Timesheet service from existing shared
  inputs. PM-owned event registrars preserve the Task transactional notification
  registration, nine Task post-commit invalidation subscriptions, and the
  Timesheet period-status subscription. The Task service still receives the
  exact Timesheet instance exposed as `time_service`. Composition tests cover
  handler identity/counts, shared bus, and fresh Task UoW session. Task-focused
  tests: 51 passed; Timesheet-focused tests: 19 passed. All four new modules
  pass targeted mypy and Ruff F/I. This was an intermediate C3 checkpoint;
  the later Resources and Scheduling slices are recorded below.
- C3 Resources and Scheduling: PM-owned Resource construction preserves one
  catalog reader across catalog/inspector/summary, one context reader across
  projects/assignments/activity/capability, a fresh-session Resource UoW, and
  the Finance-shared clock. Its three existing post-commit subscriptions retain
  their types and order. Resource-focused tests: 14 passed. Scheduling now
  constructs its calendar adapter and engine early for Task use, while Baseline
  construction remains later after Portfolio. The adapter is reused by
  Scheduling and Portfolio, and the Baseline UoW intentionally remains bound
  to the ambient session. Its five post-commit subscriptions retain one shared
  handler. Scheduling/Baseline-focused tests: 37 passed. All four new files
  pass targeted mypy and Ruff F/I.
- C3 Collaboration and Portfolio: their fresh-session UoWs, services and
  post-commit subscriptions moved to PM-owned builders/registrars without
  changing registration order. Collaboration retains its attachment hooks,
  local clock and one handler shared by three comment events. Portfolio retains
  the Scheduling calendar adapter, Finance rate resolver and one handler
  shared by four Portfolio events. Focused tests: 19 and 16 passed.
- C3 Reporting, Dashboard and remaining Resources: Reporting and Dashboard
  builders reuse the existing Scheduling, Finance-rate and PM service instances;
  no calculation or event authority moved. Project Resource retains the shared
  ambient-session UoW. Skill/availability foundation, capacity/workload
  services, Portfolio resource pool and Data Import facade are now PM-owned
  builders called at their original positions. Combined non-Finance composition
  and adjacent feature tests: 40 passed; live PostgreSQL R7B governance/security:
  44 passed. Targeted Ruff F/I, mypy (21 dependency/event source files), Python
  compilation and `git diff --check` passed. A scan of the central PM builder
  finds only Finance service constructors. The PM and Platform bundle types
  remain imported by these builders until C5 splits their ownership; the PM
  builder now lives at its module-owned bootstrap path (see C6 evidence).
- C4 Finance event slice: Forecast, Financial Change, Planned Cost,
  Commitment, Cost Entry, Budget, Billing, Configuration and Rate Card
  post-commit invalidation subscriptions moved into PM-owned
  `events/finance/` files. Calls remain at their original relative positions
  in the PM builder. A composition test checks every moved event type has
  exactly one handler and each family shares one handler instance. Focused
  Budget/Forecast checks: 62 passed; combined Finance invalidation, Budget,
  Rate and Cost Entry checks: 71 passed. Targeted Ruff F/I and mypy pass for
  all eight Finance event source files. No Finance service construction,
  governed port, UoW factory or worker principal was changed in this slice.
  This was an event-only checkpoint before dependency and worker migration.
- C4 Finance dependency slice: PM-owned `dependencies/finance/` builders now
  construct Configuration, Rate Card/Resolver, Budget, Cost Entry, Commitment,
  Planned Cost, and Forecast Version/Generation at their original positions.
  The existing ambient session, shared clock, rate resolver, and later governed
  service ports remain unchanged. Composition tests assert service identity and
  lifetime; focused Cost Entry/Commitment/Planned Cost tests passed (28), and
  composition/Forecast tests passed (18). The prior Configuration/Rate/Budget
  slice passed 111 focused tests. Targeted Ruff F/I and mypy pass for the six
  Finance dependency files. Finance read composition now owns Workspace Query,
  Performance Reader and Finance Service construction; the workspace query
  remains before Reporting and Performance remains after it. Reader/session
  identity checks and workspace tests passed (6 and 4); targeted mypy passes
  for all seven Finance dependency files. This checkpoint did not yet migrate
  the fresh-session Finance UoW, worker principal factories, governed ports,
  Billing or other query composition.
- C4 Finance worker and remaining raw-service slice: PM-owned
  `dependencies/finance/workers.py` builds the fresh-session Finance UoW and
  explicit-principal Approved-Time/Procurement consumer factories. Both
  dispatchers and the governed command boundary still share one UoW factory;
  the worker session is distinct from the ambient UI session but bound to the
  same engine. Worker composition and consumer tests: 35 passed. Ambient
  Financial Change and Billing Profile/Preparation constructors moved to
  `finance/{changes,billing}.py` without moving their governed mutation ports;
  composition and command tests: 34 passed. The schedule-change port's unused
  `commit` parameter was removed to match its sole TaskService implementation
  and caller; focused participant/schedule tests: 19 passed. Targeted mypy now
  passes for all ten Finance dependency source files. At that checkpoint,
  governed operations, command ports, and remaining Finance query wiring
  still required migration and integrated proof.
- C4 governed-operations slice: the fresh-UoW operations factory moved from the
  central PM registry into `dependencies/finance/governance_operations.py`.
  Construction remains per command; no service or repository commits were
  introduced. Governed Planned Cost, Cost Entry and Billing Preparation now
  share a rate resolver bound to the command UoW; Billing's cost/labor source
  readers and financial-period service also use that UoW instead of ambient UI
  repositories. A composition regression asserts one fresh session across the
  governed services, repositories, rate reader and period service. The UoW
  event callback checks the existing DomainEvent protocol before forwarding;
  Billing's optional approval repository now declares the Platform repository
  contract. Composition checks: 9 passed; affected governance/Billing/Cost
  command tests: 38 passed; targeted mypy passed for the new factory and
  Billing service. At that checkpoint, command-port extraction, remaining
  Finance query wiring, and broad PostgreSQL/atomicity/regression evidence
  remained open.
  A further Budget/Forecast/Setup/Rate/Billing command regression passed
  (144 tests), including the moved event callback in those command families.
- C4 governed-port and final read assembly: the ten existing Finance mutation
  families and their method sets live in PM-owned `finance/governed_ports.py`;
  a composition test confirms every port shares the one command boundary.
  Performance Query construction moved to `finance/reads.py` at its original
  point after Reporting and Baseline, reusing their instances and the existing
  Performance Reader. The SQLite command-preparation helper and boundary
  constructor moved to `finance/governance_boundary.py`; the concrete UoW is
  checked before command operations are built. The Baseline read protocol now
  declares read-only `Sequence` results so its real service satisfies the
  contract. Focused port/boundary and performance checks: 15 and 23 passed.
  Targeted Finance dependency mypy passes (14 source files).
- C4 live PostgreSQL evidence: governance commands and Billing rate/concurrency
  tests passed (24); combined Finance RLS, Approved-Time posting, Procurement
  commitment projection and worker tests passed (14). The latter run exposed
  stale Party seed columns and test-order-dependent whole-project assertions;
  the seed now uses Party `status`/`roles`, and the assertions scope to the
  tested receipt/commitment and foreign tenant. The same live set was rerun
  green. A composition regression also proves both durable Finance startup
  dispatchers are called in order with the existing bound (12 tests in the
  final composition file run). The complete PM/Platform suite was subsequently
  run from commit `9589133d1`: 3,482 passed, 26 failed, 7 skipped in 23m45s.
  All 26 failures reproduce under `pytest --lf` (26 failed). The failures are
  outside the Finance composition changes: three PM/Platform boundary tests
  cover a retired Employee contract path, Employee-to-Resource mutation
  expectations, and calendar permission setup; the other 23 are Platform
  approval eligibility/event shape, invitation-event expectations, desktop
  DTO/reference data/catalog expectations, overview labels, persistence layout,
  and mapper fixture setup. One Employee-to-Resource failure may represent a
  genuine stale-resource defect; it must not be dismissed as a test-only issue.
  None of the failed production paths was changed in the C4 Finance cutover.
  This is a classified red baseline, not a passing broad gate; C4 is not
  formally closed. Re-run the full suite after resolving these failures.
- C5 first Platform event slice: master-data post-commit subscriptions now live
  under Platform composition in `events/master_data.py`, called at their
  original position. A composition check confirms exactly one Platform handler
  per event and shared handler identity per family; the PM handler for
  `EmployeeProfileUpdated` remains a separate legitimate subscriber. An
  architecture guard was updated from the retired Platform registry import to
  the live root registry and new registrar. Combined architecture, UI event
  guard, and composition checks passed (41); targeted mypy and Ruff F/I
  passed, and compilation passed. A broader Platform headcount test remains red
  on the pre-existing overview-label mismatch described above. No Platform
  service factory, repository bundle, domain behavior, or root entry point
  changed in this slice.
- C5 remaining Platform event slice: organization, entitlement and membership
  registrations moved to `events/tenancy.py`; role-binding, account-security
  and authorization-context registrations moved to `events/security.py`;
  Approval read invalidation moved to `events/approvals.py`. Root calls each
  registrar in the original subscription order before master-data registration.
  The original event families still share one handler instance per family;
  a composition test checks exactly one Platform application handler per event.
  Focused composition tests: 14 passed; affected Qt adapter/approval registration
  tests: 127 passed; architecture and Platform event tests: 91 passed. Targeted
  Ruff F/I, mypy on the three new registrars, and compilation passed. The
  Platform service constructors and mixed root `RepositoryBundle` are still
  active; the next ownership slice must split that bundle rather than moving
  another dependency builder that imports it from the root.
- PM bootstrap entry-point correction (early C6 slice): the central builder
  moved from `src/infra/composition/modules/project_registry.py` to
  `src/core/modules/project_management/infrastructure/composition/bootstrap.py`.
  The obsolete file was removed, not retained as a compatibility shim.
  `app_container.py` now imports only PM composition `bootstrap.py`, which
  supplies both the builder and notification recipient policy; Global Overview
  imports the bundle type from that PM-owned file. Source guards now point at
  the actual dependency builders instead of expecting their Reader constructors
  in the retired central registry. Focused composition/architecture tests:
  83 passed; the known unrelated Platform 1,200-line guard was deselected
  (admin controller 1,275 lines; calendar repository 1,215 lines). Targeted
  Ruff F/I, compilation and `git diff --check` passed. The follow-up typing
  slice below resolves the moved bootstrap's 11 mypy mismatches.
  No empty `shared.py` was created: there is not yet a distinct shared PM
  dependency to own. The PM bootstrap/dependency files still type against the
  mixed root `RepositoryBundle` and root Platform bundle; C5 must replace
  those inward references while preserving repository/session identity.
- PM bootstrap typing follow-up: Task event registration now asks for the
  transactional/post-commit subscriber protocols it uses. The Platform bundle
  advertises its actual subscribe-and-dispatch concrete transactional bus,
  rather than the dispatch-only protocol. `wrap_finance_service` preserves the
  delegated service interface through one explicit cast at the adapter
  boundary; a composition test verifies every declared governed mutation
  exists and remains callable on both the underlying service and port.
  Bootstrap, task-event and governed-port mypy: 3 source files clean; focused
  Finance/PM composition: 28 passed; targeted Ruff F/I passed. Checking the
  broader Platform registry still reports four existing calendar assignment
  repository/port generic-type mismatches, not caused by this dispatcher
  annotation change. Do not claim Platform registry mypy green yet.

## Closure Gates

For each gate: focused tests, composition/service identity, UoW/session
ownership, transactional vs post-commit behavior, scope and permission checks,
static imports/typing/lint and `git diff --check`. At C4/C6 run broad PM and
Platform suites plus PostgreSQL integration. All old production paths are
removed after their consumers migrate; no duplicate service construction,
event subscription or dynamic-import discovery remains. C6 alone closes this
architecture migration.
