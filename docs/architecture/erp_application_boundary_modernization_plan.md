# ERP Application Boundary Modernization: Audit and Plan

Status: audit complete; implementation not started (2026-10-10).

## Executive Decision

The application has a sound domain/repository/UoW foundation and a completed
C0-C6 composition migration. The next problem is not the number of files: it
is that operation mixins obtain large, implicit `self` dependency sets from
their host services, while some outward application results still expose
domain objects. One confirmed dependency inversion runs from Platform
application into a desktop API package; several Platform application files
also import concrete infrastructure. These are distinct from harmless
stateless mixins and from adapter-local DTOs.

Use cohesive, explicitly injected application handlers only where an
operation group has a clear authorization and transaction boundary. Keep a
thin public service facade where current callers benefit from it; do not
introduce a command bus, one class per method, or a second composition root.

**DTO ownership decision:** reuse the existing
`src/core/platform/contract` and
`src/core/modules/project_management/contracts` trees. Add feature-scoped
use-case command/query/result contracts there only when an input or output is
genuinely shared by desktop and future HTTP adapters. Keep current
`contracts/reads` immutable reader facts/query specifications with their
reader ports; do not clone them into an application DTO hierarchy. Keep
desktop labels, formatting, `DesktopApiResult`, and QML view models in their
current adapter/presentation layers. Future FastAPI request/response schemas
belong to the HTTP adapter. The **neutral API is the application use-case
contract**, not a renamed desktop API or a shared transport schema.

Pre-release permits coordinated interface cutovers and deletion of obsolete
internal paths, but does not justify changing RBAC, tenant isolation,
financial authority, approval atomicity, or UoW lifetimes during a structural
move. The highest-risk pilots are Project creation/catalog, Platform Time,
and Finance query/governance; start with Projects, not Finance.

## Scope and Evidence

Only Platform and Project Management exist as implemented core capabilities;
`src/core/modules` contains no other business module. PM includes Finance,
Time/Timesheets, Resources, Scheduling, Portfolio, Collaboration, Dashboard,
Reporting, and Register. `src/core/modules/project_management/api/http` is
only a package stub. There is no live FastAPI adapter to preserve yet.

Inspected: Platform and PM application/domain/contracts/API trees; desktop
commands, DTOs and serializers; QML controller/presenter packages; owner
composition bundles/bootstraps and root `app_container.py`; repository/read
contracts and SQL reader implementations; UoW and event tests; architecture
guards; `docs/composition_architecture/README.md`. C0-C6 are closed. The
latest recorded broad Platform/PM/architecture run is 3,715 passed and 7
skipped; the dedicated PostgreSQL integration run is 250 passed. Those are
starting evidence, not tests rerun as part of this read-only audit.

### Mixin Inventory

Fifteen concrete application service/query facades use operation mixins or
business-service inheritance: three Platform, twelve PM. This count excludes
the stateless `ModuleGuardedServiceMixin`/PM module guard and infrastructure
ORM mixins. The inventory below groups inherited mixins by responsibility;
the cited service class is the actual constructor and public call surface.

| Class and current file | Inherited operation groups; implicit `self` dependencies | Target and risk | Main consumers / characterization |
| --- | --- | --- | --- |
| `AuthService`, `src/core/platform/application/security/auth/auth_service.py` | Query and validation mixins use repositories, session, canonical bindings and tenant context | Keep facade; isolate account query vs registration/auth commands only after scoped-RBAC characterization. **High** | Platform desktop auth, role administration, shell session; auth/RBAC/RLS tests |
| `TimeService`, `src/core/platform/application/time_management/time/time_service.py` | Entries, periods, query, support and financial-event mixins share allocation/time repos, event buses, UoW and callback state | Separate entry/period/query handlers around one explicit transaction/event policy. **Critical** | PM `TimesheetService`, desktop time, approved-Time outbox; Time/Finance inbox/atomicity tests |
| `ModuleCatalogService`, `src/core/platform/application/tenant/modules/module_catalog_service.py` | Mutation/query/context mixins share entitlement repo/reader, user session, audit, cache/invalidation and `read_only` state | Keep public catalog; extract only coherent entitlement mutation if needed. **Medium-high** | Runtime, guards, QML navigation, module licensing; entitlement/RLS tests |
| `ProjectService`, `src/core/modules/project_management/application/projects/service.py` | Create/update/status/delete/query mixins plus support methods reach project/task/assignment repos, Platform party/department repos, reader, UoWs, auth and audit | **A2 pilot:** creation, profile/lifecycle/deletion command groups and catalog query; thin facade. **High** | PM desktop Projects, Tasks, Finance, dashboard/global overview; project CRUD/catalog/approval tests |
| `TaskService`, `src/core/modules/project_management/application/tasks/service.py` | Eighteen task-operation mixins plus guard share repos, scheduler, Time, Approval, task UoW, participant mode and mutable warning/event sidecars | Group by lifecycle, hierarchy, assignment/dependency, schedule and query; do not split participant UoW blindly. **Critical** | Task desktop, scheduling, approval participants, Gantt; task/approval/UoW tests |
| `TimesheetService`, `src/core/modules/project_management/application/timesheets/services/service.py` | Inherits Platform `TimeService` and PM guard, adds PM readers and scope methods with `*args/**kwargs` constructor | Replace inheritance only after Time capabilities are explicit; inject narrow Platform Time port. **Critical** | PM owner/review desktop APIs; time approval/labor posting tests |
| `ResourceService`, `src/core/modules/project_management/application/resources/catalog/resource_service.py` | Resource commands/queries/context and skill/certification commands/queries share Employee reference, PM repos, readers and UoW | Resource master and capability handlers; preserve Employee-as-Platform authority. **High** | Resource desktop, assignment, dashboard, Finance rates; resource/Employee boundary tests |
| `ProjectResourceService`, `src/core/modules/project_management/application/resources/project_resources/project_resource_service.py` | Membership commands and queries share staffing/assignment repos, session and UoW | Separate bounded membership query from governed assignment command where useful. **Medium-high** | Project detail, assignments, capacity; envelope tests |
| `PortfolioService`, `src/core/modules/project_management/application/portfolio/services/portfolio_service.py` | Intake, template, scenario, dependency commands/queries and executive/support mixins share repositories, readers and mutable scenario state | Cohesive per-capability handlers; retain cross-capability orchestration facade. **High** | Portfolio desktop, Dashboard; scenario/query-scope tests |
| `DashboardService`, `src/core/modules/project_management/application/dashboard/services/dashboard_service.py` | Alerts, upcoming, burndown, EVM, register, portfolio, professional widgets reach whole Project/Task/Resource services | Keep a composition query facade; inject bounded widget read capabilities, not command facades. **Medium** | Dashboard desktop; snapshot, query-count and basis tests |
| `CollaborationService`, `src/core/modules/project_management/application/collaboration/services/collaboration_service.py` | Comment/presence commands and comment/document/inbox queries plus principal/support mixins share privacy scope, reader and UoW | Separate governed comment/presence writes from bounded reads; share explicit visibility policy. **High** | Task discussion/inbox, notifications; privacy/RLS/dedup tests |
| `ReportingService`, `src/core/modules/project_management/application/reporting/services/reporting_service.py` | Cost, baseline, profitability, variance, EVM, labor and KPI builders share canonical Finance inputs | Preserve one financial authority; split report assembly by output only, not formulas. **High** | Export/snapshot/dashboard/reporting; Finance parity tests |
| `RegisterService`, `src/core/modules/project_management/application/risk/register_service.py` | Lifecycle and query mixins plus guard share register repo/reader and scope | Small lifecycle/query split if constructor coupling warrants it. **Medium** | Register desktop, Dashboard; register CRUD/page tests |
| `ProjectFinanceWorkspaceQuery`, `src/core/modules/project_management/application/financials/workspace_query.py` | Eight configuration/cost/budget/change/forecast/rate/billing/integration query groups reach nine readers, scope, permission and Accounting capability | Keep slim finance facade; delegate per-read capability with one explicit scope/permission policy. **High** | Finance desktop, exports; R6B query/permission/RLS tests |
| `ProjectFinancePerformanceQuery`, `src/core/modules/project_management/application/financials/analytics/performance/query.py` | EVM, variance, cost-phasing and report query groups share readers and canonical EVM authorities | Preserve one Decimal calculation authority; composition-only query facade may remain. **High** | Performance/reporting/dashboard; R6E exact Decimal and basis tests |

The exact inheritance groups behind that inventory are: `AuthService`:
`AuthQueryMixin`, `AuthValidationMixin`; `TimeService`:
`TimesheetEntriesMixin`, `TimesheetPeriodsMixin`, `TimesheetQueryMixin`,
`TimesheetSupportMixin`, `TimesheetFinancialEventsMixin`;
`ModuleCatalogService`: `ModuleCatalogMutationMixin`,
`ModuleCatalogQueryMixin`, `ModuleCatalogContextMixin`; `ProjectService`:
`ProjectCreateMixin`, `ProjectUpdateMixin`, `ProjectStatusMixin`,
`ProjectDeletionMixin`, `ProjectQueryMixin`; `ResourceService`:
`ResourceCommandMixin`, `ResourceQueryMixin`, `ResourceContextQueryMixin`,
`SkillCommandMixin`, `SkillQueryMixin`; `ProjectResourceService`:
`ProjectResourceCommandMixin`, `ProjectResourceQueryMixin`; `RegisterService`:
`RegisterLifecycleMixin`, `RegisterQueryMixin`. The PM service classes in
this paragraph also inherit `ProjectManagementModuleGuardMixin` where shown
in their class declarations.

`TaskService` has the following operation mixins:
`ApprovedScheduleChangeMixin`, `TaskScheduleSyncMixin`,
`TaskHierarchySupportMixin`, `TaskHierarchyQueryMixin`, `TaskHierarchyMixin`,
`TaskIdentityMixin`, `TaskProgressMixin`, `TaskDeletionMixin`,
`TaskLifecycleMixin`, `TaskDependencyDiagnosticsMixin`, `TaskDependencyMixin`,
`TaskSchedulingConstraintMixin`, `ResourceLevelingApplyMixin`,
`TaskAssignmentMixin`, `TaskTimeEntryMixin`, `TaskAssignmentBridgeMixin`,
`TaskQueryMixin`, `TaskValidationMixin`. `TimesheetService` instead inherits
the entire Platform `TimeService`, not individual PM time operation mixins.

The remaining large read/operation aggregates are `PortfolioService`
(`PortfolioDependencyCommandMixin`, `PortfolioDependencyQueryMixin`,
`PortfolioExecutiveQueryMixin`, `PortfolioIntakeCommandMixin`,
`PortfolioIntakeQueryMixin`, `PortfolioScenarioCommandMixin`,
`PortfolioScenarioQueryMixin`, `PortfolioSupportMixin`,
`PortfolioTemplateCommandMixin`, `PortfolioTemplateQueryMixin`);
`DashboardService` (`DashboardAlertsMixin`, `DashboardUpcomingMixin`,
`DashboardBurndownMixin`, `DashboardEvmMixin`, `DashboardRegisterMixin`,
`DashboardPortfolioMixin`, `DashboardProfessionalMixin`);
`CollaborationService` (`CollaborationCommentCommandMixin`,
`CollaborationCommentQueryMixin`, `CollaborationDocumentQueryMixin`,
`CollaborationInboxQueryMixin`, `CollaborationPresenceCommandMixin`,
`CollaborationPresenceQueryMixin`, `CollaborationPrincipalMixin`,
`CollaborationSupportMixin`); and `ReportingService`
(`ReportingCostBreakdownMixin`, `ReportingBaselineCompareMixin`,
`ReportingProfitabilityMixin`, `ReportingVarianceMixin`,
`ReportingEvmMixin`, `ReportingLaborMixin`, `ReportingKpiMixin`).
`ProjectFinanceWorkspaceQuery` composes `ConfigurationWorkspaceQueries`,
`CostWorkspaceQueries`, `BudgetsWorkspaceQueries`,
`FinancialChangesWorkspaceQueries`, `ForecastsWorkspaceQueries`,
`RateCardsWorkspaceQueries`, `InvoicingWorkspaceQueries`, and
`IntegrationWorkspaceQueries`; `ProjectFinancePerformanceQuery` composes
`EvmQueries`, `VarianceQueries`, `CostPhasingQueries`, and `ReportsQueries`.
These names identify the current public operation families; extraction
boundaries must be verified against each family's actual `self` accesses,
authorization and commit behavior before an implementation gate closes.

`ProjectManagementModuleGuardMixin` itself is a small reusable policy and is
not a reason to rewrite every Finance service. Reporting builder mixins are
listed under ReportingService; private helper mixins are not counted as
additional service facades. The 15 candidates are **not** 15 mandatory
refactors: close each candidate only when a narrower dependency or explicit
boundary is demonstrably better than its current form.

### Confirmed Boundary and DTO Findings

| Evidence | Classification | Treatment |
| --- | --- | --- |
| `PlatformRuntimeApplicationService` imports `ModuleRuntimeSnapshot` and `build_module_runtime_snapshot` from `src/core/platform/api/desktop_runtime/service_resolver.py` | **Confirmed application -> desktop API inversion**; snapshot also contains domain module/entitlement objects | Move the neutral snapshot builder/contract inward; leave service-dictionary resolution and shell text in the desktop adapter. Keep existing public behavior during coordinated cutover. |
| `src/core/modules/project_management/contracts/reads/projects/models.py::ProjectCatalogReadItem.project` holds a `Project` domain entity, populated by `sqlalchemy_catalog_reader.py::project_from_orm` | **Confirmed read-contract domain leakage**; desktop project serializer consumes the entity | Project pilot replaces catalog row with immutable scalar fact fields and explicit Decimal/availability semantics; SQL reader maps columns without constructing domain aggregates for list rows. |
| `application/projects/commands/create.py::create_project` returns `Project`, while `api/desktop/projects/serializers/project_serializer.py` maps domain fields plus status/site/client/budget labels | **Outward domain leakage plus legitimate desktop formatting** | Application outward result uses neutral ID/version or immutable result when warranted. Keep display labels/formatting in desktop presenter/adapter, never in shared contract. |
| `api/desktop/projects/commands/project_commands.py::{ProjectCreateCommand, ProjectUpdateCommand}` are dataclasses in a desktop package; `api/desktop/projects/models/project.py::ProjectDesktopDto` contains formatted budget/status/site labels | First pair are candidate **shared use-case inputs**, not automatically HTTP schemas; Desktop DTO is **adapter-specific** | Move only genuinely shared command fields to `contracts` with intentional defaults/validation. Keep Desktop DTO. HTTP later maps its own Pydantic request to the same use case. |
| `application/risk/dto/register_summary.py::RegisterDashboardSnapshot.high_risks` contains `RegisterEntry` aggregates | **Confirmed application result leakage** if exposed outward | Replace aggregate with an immutable urgent/risk result when that outward path is migrated; keep domain object inside application otherwise. |
| `src/core/platform/api/desktop/{approval,master_data/party,master_data/department,notifications,history/activity}/*` imports domain entities for serialization | **Confirmed domain-to-desktop mapping**, not proof that transport leaks ORM | Review each outward service return; move use-case result only when shared web/desktop semantics justify it. Do not mass-clone every serializer. |
| `src/core/modules/project_management/contracts/reads/{projects,tasks,resources,financials}` and Platform `contract/read/*` already contain page/query facts and reader ports | **Existing reusable neutral read contracts** | Reuse. Rename or reshape only fields that embed aggregates, adapter formatting, mutable state, or permission-derived fake defaults. |
| Platform application imports concrete infrastructure in `time_management/time/{timesheet_periods,timesheet_entries}`, `security/auth/{auth_service,unit_of_work,session/context_switch_service,provisioning/registration_service}`, `security/authorization/roles/tenant_role_administration_service.py`, and `master_data/org/organization_service.py` | **Confirmed dependency-direction violations**, including SQLite write-lock/UoW helpers, concrete clock defaults, and a calendar ORM reference | Classify runtime vs type-only imports per file; inject ports/adapters or move persistence work behind UoW. Do not remove locking/transaction semantics without SQLite and PostgreSQL proof. |

The PM architecture guard currently forbids application/domain/contracts ->
infrastructure imports, but an equivalent Platform-wide guard is needed.
Domain trees showed no corresponding API/infrastructure imports in this scan.
Many API files import **domain enums/value objects**, which alone is not an
aggregate leak. Likewise, a `DesktopDto` is not automatically misplaced just
because the future HTTP adapter will show similar fields.

### Dependency and Lifetime Map

Current desktop path: QML -> UI controller/presenter -> desktop API ->
application service/query -> domain and repository/read ports -> SQL/UoW.
The root builds exactly one Platform bundle and PM bundle; module-owned
composition builds their services. Finance workers and approval participants
use fresh or caller-owned UoWs rather than the long-lived desktop session.

| Relationship | Current concern | Smallest safe target |
| --- | --- | --- |
| Dashboard -> `ProjectService`, `TaskService`, `ResourceService` (`dashboard_service.py`) | Read widgets depend on full command facades | Cohesive, permission-aware read capabilities or existing readers; no raw repository bypass |
| PM TimesheetService -> Platform TimeService by subclassing | PM inherits every Platform Time dependency and constructor | Narrow Time use-case contract supplied by Platform composition, after time transaction characterization |
| PM Collaboration -> Platform `DocumentIntegrationService` | Whole service for document evidence/link work | Existing public Platform capability/port if it covers the authorized operation; not a direct document repo shortcut |
| PM Task/Financial Change -> Platform `ApprovalService` | Governance call and participant transaction coupling | Preserve explicit approval orchestration; narrow only after decision permission and participant UoW proofs |
| Project commands -> Platform Party/Department repositories | Cross-foundation reference validation needs exact org/status checks | Keep Platform-owned authority; narrow public lookup/read capability where repository access obscures permission/scope |
| PM Finance -> project/reference readers and Platform context | Several valid read-port and scope dependencies already exist | Keep existing `contracts/reads` and source gateway boundaries; avoid speculative interfaces |

Shared policy candidates are explicit scoped context resolution, permission
checks, project access, and audit/event recording. Reuse existing
`require_permission`, `require_project_permission`, tenant context, UoW and
event machinery. Extract a new collaborator only where two or more handlers
would otherwise duplicate the **same** rule and its dependencies. Never use
a generic base handler or global dependency bag. A handler must receive only
the repositories/readers/policies required by its operations. Composition
owns handler lifetime and construction; no handler imports composition.

## Target Boundary and Package Shape

Preserve current package conventions and add folders only when a migration
actually lands there:

```text
src/core/platform/
  contract/use_cases/<feature>/       # shared input/result when needed
  contract/read/<feature>/            # existing reader facts/ports
  application/<feature>/              # service facade + cohesive handlers
  api/desktop/<feature>/              # QML-facing adapter and display DTO
  api/http/<feature>/                 # future only; own request/response schema
  infrastructure/composition/         # existing owner bootstrap/dependencies

src/core/modules/project_management/
  contracts/use_cases/<feature>/      # shared command/query/result when needed
  contracts/reads/<feature>/          # existing SQL reader contracts
  application/<feature>/              # facade + command/query handlers
  api/desktop/<feature>/              # current desktop adapter
  api/http/<feature>/                 # future only
  infrastructure/composition/         # existing owner bootstrap/dependencies

src/infra/composition/app_container.py # root module/integration assembly only
```

For the Project pilot, first add only
`contracts/use_cases/projects/{commands,results}.py` and cohesive handler
files under `application/projects/commands/` or `handlers/` after confirming
the current package's actual responsibilities. Do not create empty
`dto/commands`, `dto/queries`, `handlers` and `policies` trees together.
Existing `contracts/reads/projects` is the catalog query/read-fact home.

An application facade may remain to preserve a stable use-case surface for
multiple desktop callers and approval participants. It delegates to injected
handlers and contains no duplicate authorization, validation or transaction
logic. A same-module feature may inject a handler directly only when it needs
that exact capability and the handler's authorization contract is public.
Cross-module consumers use a public contract, not another module's private
handler class. Composition wires both desktop and future HTTP adapters to
the same application use cases; the adapters never import one another.

Reader implementations may construct immutable scalar projections in SQL,
with explicit tenant/org/project scope, deterministic order and bounded
pagination. They must not return ORM rows or mutable domain aggregates to
transport layers. Application queries may coordinate several readers and
permission checks but must not recalculate Finance authority in QML,
presenters, snapshots or exports. Commands return an ID/version or an
application result where the caller needs it; domain aggregates stay within
application/domain execution. Money remains Decimal internally; text and
locale formatting are adapter/presenter concerns. `0` remains distinct from
unavailable/restricted.

### Contract Decisions For Desktop And Future HTTP

The application owns the meaning and validation of a use case; the existing
`contract(s)` package is its neutral, importable public surface. This is a
physical package choice, not a claim that HTTP or QML owns the contract.
Existing repository/write DTOs nearest persistence should remain where they
are unless their own responsibility changes. Do not move every DTO merely
because a second adapter is planned.

| Question | Decision |
| --- | --- |
| Command handler or service? | Use a handler for a cohesive operation group with a distinct dependency/transaction set. Keep a simple service when extraction adds indirection without reducing coupling. |
| Related operations? | Group by invariant and UoW, not by UI screen or one class per method. For Projects, create/update/status/delete and catalog are candidate groups, subject to characterization. |
| Facade lifetime? | Keep a thin service where existing desktop/approval callers need a stable entry point; composition injects handlers and controls their scope. A facade must not build handlers or duplicate their rules. |
| Direct handler use? | Same-module callers may use a public narrow handler when they need exactly that capability. Cross-module callers use a public port/use-case contract, not a private handler. |
| Query collaboration? | Prefer an existing scoped reader contract for bounded projections; use a narrow capability port when another use case must enforce more than raw data access. Never replace permission-aware service calls with unrestricted repository reads. |
| Shared command/query DTOs? | Put only transport-neutral use-case inputs in feature-scoped `platform/contract/use_cases` or `project_management/contracts/use_cases`. Use business names, e.g. `CreateProjectInput` or `ProjectCatalogQuery`, not `Desktop*` or `Http*`. Avoid a second parallel DTO if an existing read query contract already fits. |
| Shared result DTOs? | Put stable use-case results in the same feature contract when desktop and HTTP need the same semantics. Existing immutable reader facts stay in `contract(s)/read(s)`; API response models stay adapter-specific. |
| Domain-to-result conversion? | The application use case maps internal aggregates to neutral results at its outward boundary; read implementations project scalar facts directly from SQL. Domain value objects may remain internal to application and mapping code. |
| API neutrality? | `api/desktop` remains a desktop adapter, not a supposedly neutral API. Future `api/http` maps HTTP schemas to the same application contract. Neither adapter imports the other. |
| Validation ownership? | Pydantic/domain invariants on existing shared write models remain authoritative for entity fields; application handlers enforce contextual eligibility, RBAC, scope and workflow state. Transport parsing stays in its adapter. Do not duplicate a CRUD validation layer. |
| Circular dependencies? | Put shared immutable use-case types and ports in `contract(s)`, not in sibling handlers. Handlers depend on contracts/domain; composition depends on handlers, never the reverse. |

For Project creation, the current `ProjectCreateCommand` has fields that may
be shared with HTTP, but moving it is not automatic: first compare desktop
defaults and application validations, then introduce a neutral input with one
coordinated caller cutover. The desktop `ProjectDesktopDto` carries display
labels and formatted values and stays adapter-local. FastAPI may use Pydantic
HTTP schemas when implemented; those schemas must not become the use-case
contract or force desktop code to depend on FastAPI.

## Migration Gates

Every gate is a coordinated cutover: characterize -> implement -> migrate all
callers -> delete superseded path -> run its checks. Never leave a permanent
old/new compatibility pair. Recovery is via the pre-gate commit/worktree
snapshot and focused rollback of that gate, not a runtime fallback.

| Gate | Exact scope and prerequisites | Implementation and closure evidence | Recovery concern |
| --- | --- | --- | --- |
| **A0 audit (this document)** | C0-C6 composition closed; inventory above | Confirm paths/consumers, DTO ownership, transaction and event invariants; team reviews this plan before source edits | Revisit classifications if a hidden consumer is found |
| **A1 contract boundary** | `platform_runtime_service.py`, `api/desktop_runtime/service_resolver.py`, Platform/PM contract trees, API command/DTO inventories | Move `ModuleRuntimeSnapshot` out of desktop import direction; define a feature contract rule and architecture tests for Platform + PM. Characterize current serialization before any command DTO move. No new HTTP implementation. | Avoid changing desktop runtime context shape or module-entitlement visibility |
| **A2 PM Project pilot** | `application/projects/{service.py,commands/*,queries/*}`, `contracts/reads/projects/*`, `infrastructure/persistence/reads/projects/sqlalchemy_catalog_reader.py`, `api/desktop/projects/*`, PM composition `dependencies/projects/*` | Create cohesive creation/profile/lifecycle/deletion/query handlers only where dependency sets differ; thin ProjectService delegates. Move shared project command input to `contracts/use_cases/projects` if both adapters will use it. Replace catalog `Project` aggregate with immutable row fact. Migrate desktop serializer/callers, remove old mixins. Verify CRUD, manager/party/department eligibility, budget redaction, page/sort/tenant scope, UoW/audit/event equivalence. | Highest pilot risk is silently changing transaction/event order or budget visibility; keep characterization tests and one cutover branch |
| **A3 complex read facades** | `financials/workspace_query.py`, `financials/analytics/performance/*`, Finance `contracts/reads`, SQL readers, desktop/report/export/snapshot consumers | Separate per-capability query collaborators only where constructor/query tests show benefit; preserve single Finance scope/permission policy and canonical EVM/Decimal authorities. Do not split by arbitrary UI tab. Keep current facade if delegation adds no value. | R6 authority, restricted-vs-unavailable semantics, cross-project basis and bounded SQL must remain identical |
| **A4 remaining operation clusters** | Platform Auth/Time/ModuleCatalog first by dependency; PM Tasks/Timesheets, Resources, Collaboration, Portfolio, Register, Dashboard/Reporting in characterized batches | Remove hidden operation-mixin dependencies incrementally, migrate same-module consumers to narrow capabilities where worthwhile. Fix Platform application->infrastructure imports through explicit ports/UoWs without altering locks, scope, worker or approval behavior. Do not rewrite simple Finance services just for symmetry. | Approved-Time/Approval participant UoWs, service principal, notification privacy and Event/Inbox one-effect semantics require PostgreSQL regression |
| **A5 interface cutover** | Remaining desktop commands/serializers, controllers/presenters, use-case contracts | Migrate only truly shared application inputs/results into `contract(s)/use_cases`; keep display-only `DesktopDto` and QML view models adapter-local. Remove domain aggregate exposure at outward use-case boundaries. Demonstrate a transport-neutral caller with tests, but do not implement FastAPI until requested. Delete superseded DTOs/imports in the same slice. | Desktop UI must preserve field defaults, errors, permission presentation and mutation refresh; no parallel compatibility API |
| **A6 enforcement/closure** | Architecture guards, full Platform/PM/UI tests, PostgreSQL integration, composition docs | Guard application->API/infrastructure, domain->outer layers, module private-handler imports, reader ORM/aggregate leakage, no duplicate DTO authority. Run focused plus broad suites, migrations/RLS/concurrency, mypy/Ruff/compile/QML checks. Close only with exact counts and clean deleted-path search. | Classify unrelated failures honestly; never relax a security guard to make the suite green |

**First implementation gate after review: A1.** A1 corrects the confirmed
Platform application -> desktop dependency and establishes DTO classification
tests before the more hazardous Project pilot. A2 should not start until A1
is accepted and its desktop runtime contract is green. A3/A4 may be batched
by capability after A2 demonstrates a safe handler/facade pattern.

## Risk and Verification Matrix

| Risk | Required proof before closing affected gate |
| --- | --- |
| RBAC/tenant/project and module guard drift | Negative permission tests, wrong-tenant/org/project tests, non-owner PostgreSQL RLS, server-side recheck for every command |
| UoW/Approval participant split | One commit owner, rollback of business/audit/event/outbox state, no duplicate subscriptions, fresh worker sessions |
| Approved-Time, financial integrations and notifications | Exact duplicate/changed duplicate behavior, outbox/inbox transaction neutrality, service identity, privacy recipient recheck, post-commit invalidation |
| Project/Resource/Employee and Party coordination | Platform remains master of Employee/Party core data; PM keeps its own Resource/Project state; IDs and eligibility validated server-side |
| Finance basis/Decimal/availability | Existing R6 Budget/Forecast/Actual/EVM/Cost Phasing/Billing/Commercial/Accounting handoff parity; no unavailable-to-zero or float regression |
| Desktop and future HTTP contract drift | Compare same use-case result through desktop serializer and a neutral contract test; HTTP schema remains independently versioned when implemented |
| Query performance | SQL-side sort/page/count, deterministic tie-breakers, bounded reader queries and no N+1 in presenters/controllers |

Definition of done is behavioral and architectural: no application import
from API or concrete infrastructure; no domain/ORM aggregates escape an
outward use-case result; each migrated operation has explicit dependencies,
one authorization rule, one transaction owner and one canonical result
contract; desktop behavior and existing permissions are unchanged; old
operation mixins/DTO paths are deleted after caller migration; all affected
focused, broad, PostgreSQL/RLS, architecture and static gates are green.

This document authorizes no implementation by itself. The team should review
A1/A2 contract naming and cutover scope before work begins.
