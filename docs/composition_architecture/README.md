# ERP Composition Architecture

## Current State (2026-10-09)

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
| C3 | Extract PM Projects, Tasks, Resources, Scheduling, Timesheets, Collaboration, Portfolio and Risk dependency/event groups | Per-group focused tests; no duplicated factories/subscriptions; preserve PM bundle | In progress: Projects, Register, Tasks, Timesheets, Resources and Scheduling extracted |
| C4 | Extract Finance core/governance/workers last, preserving fresh sessions, governed ports and service-principal factories | Finance integration, atomicity, concurrency, RLS and startup replay tests | Not started |
| C5 | Move Platform services/events and split repository bundle by owner | Platform auth/tenancy/calendar/approval suites; root remains sole assembler | Not started |
| C6 | Slim root and move only cross-module integrations/global overview wiring under root | Desktop startup, full PM/Platform, PostgreSQL and architecture guards; delete both central registries and obsolete imports | Not started |

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
  pass targeted mypy and Ruff F/I. Collaboration, Portfolio, Reporting and
  Dashboard construction/event wiring still remain in the central PM builder.

## Closure Gates

For each gate: focused tests, composition/service identity, UoW/session
ownership, transactional vs post-commit behavior, scope and permission checks,
static imports/typing/lint and `git diff --check`. At C4/C6 run broad PM and
Platform suites plus PostgreSQL integration. All old production paths are
removed after their consumers migrate; no duplicate service construction,
event subscription or dynamic-import discovery remains. C6 alone closes this
architecture migration.
