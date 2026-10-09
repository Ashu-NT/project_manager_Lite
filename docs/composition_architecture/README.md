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
| `approval_apply_dependencies/*` | Seven PM approval dependency factories, some rebuilding scoped repositories | PM `registrations/approvals` after lifetime/transaction characterization |
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
Likewise move direct test imports of `notifications.py` and
`approval_apply_dependencies/*` with their owning phase. The shared mixed
`RepositoryBundle` cannot be deleted until Platform, PM, root and all approval
factory callers have been migrated together.

## Incremental Execution Map

| Gate | Change | Verification / deletion condition | Status |
| --- | --- | --- | --- |
| C0 | Baseline inventory, public-import and lifecycle map | Composition/architecture tests run; no source changes | Complete |
| C1 | Split Platform Approval vs PM notification registration and PM recipient recheck; inject policy from root | Same transactional subscription counts, recipient/privacy/RLS and startup tests; delete mixed `notifications.py` | Complete |
| C2 | Move PM access/scope registrations and approval registrations/dependency factories into PM composition | Service identity, reviewer permissions, handler counts, transaction/UoW tests; delete root approval factory package | In progress: access registration extracted; approvals remain |
| C3 | Extract PM Projects, Tasks, Resources, Scheduling, Timesheets, Collaboration, Portfolio and Risk dependency/event groups | Per-group focused tests; no duplicated factories/subscriptions; preserve PM bundle | Not started |
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
  same resolver and Role Governance has its two resolvers. Approval registration
  and dependency factories remain in the central PM registry until separately
  characterized and moved.
- Verification: focused composition/Platform notification/architecture tests:
  20 passed; focused access/composition/architecture tests: 12 passed;
  PostgreSQL R7B governance and R7D notification/RLS tests: 51 passed. Scoped
  Ruff F/I, targeted mypy for new registration files, Python compilation, and
  `git diff --check` passed. C1 earlier focused notification checks also passed
  (17, 40, and 24 tests in separate targeted runs). These counts are not a full
  ERP regression run; broad validation remains a C4/C6 closure gate.

## Closure Gates

For each gate: focused tests, composition/service identity, UoW/session
ownership, transactional vs post-commit behavior, scope and permission checks,
static imports/typing/lint and `git diff --check`. At C4/C6 run broad PM and
Platform suites plus PostgreSQL integration. All old production paths are
removed after their consumers migrate; no duplicate service construction,
event subscription or dynamic-import discovery remains. C6 alone closes this
architecture migration.
