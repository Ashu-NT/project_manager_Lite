# ERP Application Boundary Modernization: Audit and Plan

Status: A0-A3 complete; A4 application DTO boundary cutover current (2026-10-16).
A5-A6 are not yet certified. Earlier closure counts below describe their
recorded worktrees, not final evidence for this subsequent DTO cutover.

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

**Current DTO ownership decision (supersedes the original contracts/use_cases
proposal):** feature-owned application use-case inputs and outputs live under
`application/<feature>/dto/commands/`, `dto/queries/`, and `dto/responses/`.
Related operations share meaningful feature files; there is no flat `dto.py`
or compatibility re-export. Finance keeps its existing subfeature ownership.
Desktop and future HTTP adapters map their payloads into these typed inputs;
handlers accept the inputs and return application results. Adapter-specific
labels, formatting, `DesktopApiResult`, and QML models remain outside the
application. Future FastAPI schemas remain adapter-owned, not core contracts.

Immutable SQL Reader facts and query specifications remain in
`contracts/reads`, alongside the Reader interfaces. Query handlers map those
facts into application responses when the use-case shape differs; do not
create duplicate types solely to rename the same data. A neutral cross-module
port must not depend outward on application or adapter implementation packages.
The **neutral API is the application use-case contract**, not a renamed desktop
API or a shared transport schema.

**Output boundary clarification (2026-10-16):** outward application handlers
and queries return immutable transport-neutral DTOs, not mutable domain
aggregates. A Reader already returning a suitable immutable DTO does not need
an identical application response class. Return that canonical Reader DTO
unchanged. Application feature mappers convert domain entities into DTOs, or
assemble a genuinely different use-case projection; do not create mappers or
response types solely to satisfy a folder layout. An API importing an
application mapper to convert a returned domain aggregate is not a completed
cutover. Superseded API domain-to-response serializers must be deleted, not
retained as forwarding wrappers. Desktop-only presentation may remain outside
application, but it consumes DTOs rather than domain aggregates. Keep
normalized/derived local values when useful;
read unchanged command fields directly instead of mechanically unpacking
whole DTOs into local aliases. New boundaries require explicit typing.

**Thin API clarification (2026-10-16):** application handlers own domain-to-DTO
mapping, and adapters consume/return those DTOs directly. Do not clone an
application response into another desktop record just to attach display
labels. QML presenters build labels and view models from the same application
result. A serializer is justified for actual transport encoding, not as a
mandatory second business-data mapping stage. Earlier output cuts retaining
API presentation copies are not evidence that this final boundary is complete.

**Redundant-model audit (2026-10-16):** removed the parallel Project catalog
and detail response copies and the Resource catalog/item/summary/inspector,
capability-item/page, activity, usage and sort copies. Readers retain their
canonical immutable records. Also consolidated equivalent Platform overview
rollups, employee breakdown rows, runtime module/capability records and shared
working-calendar result records. Removed identity-only conversion helpers.
Different business meanings are not merged merely because fields coincide
(for example Department and Party summaries, or distinct Finance metrics).
Domain aggregates and immutable DTOs remain legitimately separate types.

`mappers/` is this repository's organizational convention, not a mandatory
enterprise standard. Pure mapping/assembly functions need no handler facade,
registry or injected mapper service. Fowler's DTO pattern calls this role an
assembler; the separate Data Mapper persistence pattern is not what these
application DTO functions implement. The CQRS read path may return a typed
SQL projection directly without rebuilding domain objects or duplicate DTOs.

Redundancy-cleanup verification: 229 architecture/composition tests and 32
focused Project/Resource/Platform runtime/headcount tests passed. Mypy passed
for 1,297 application/API files; repository Ruff F/I, compilation and
`git diff --check` passed. The final PM/Platform response-schema scan (including
two-field rollups and field-order-independent comparisons) found no remaining
exact Reader/API-versus-application response copies. This is evidence for the
redundancy cleanup, not certification of the entire command/output migration
or a replacement for its broader behavioral/RLS gates. The workspace `.tmp`
directory was removed. No commit was made.

**Notification output cutover (2026-10-16):** moved the single neutral
`NotificationDto` from the desktop adapter to the Notification application's
`dto/responses` package. Authenticated query and read-state command handlers
now return that response; domain mapping lives in the feature's `mappers`
package, with nested metadata detached from the domain object. The desktop
adapter consumes results directly and no longer imports or serializes the
Notification aggregate. Shell consumers use the same response, not a copy.
The two adapter-only command/query protocols were removed after verifying
their sole production consumer; composition still injects the existing
handler instances. Shared notification delivery ports remain unchanged.
No contract-to-application dependency or compatibility export was introduced.
Recipient/tenant/org checks, bounded reads, commit ownership, delivery draining,
and desktop error handling are unchanged. Delivery-internal source identity
is verified against persistence rather than leaked into the public response.

Verification: 280 notification/durable-delivery/shell UI/architecture/composition
tests passed; scoped Mypy passed for 16 source files. This closes the
Notification result boundary only. Desktop labels, formatted dates/money, icons and chart/table
descriptors are not neutral application results and must not be moved merely
to empty API folders. Full A4-A6 certification remains outstanding.

**Actual Cost output cutover (2026-10-16):** the feature now owns
`dto/responses/cost_entry.py` and `mappers/cost_entry.py`. The frozen, slotted
`CostEntryResponse` carries detached scalar cost/source/version evidence,
Decimal money, optional posting evidence and server-authored action
capabilities. There is no existing equivalent Reader DTO to duplicate.
Create/replay/update/submit/reject/post/reverse and get/list now return that
response; approval keeps its existing distinct governed-decision result.
Private approval-participant operations and trusted approved-Time/Procurement
posting retain their existing domain/transaction contracts. Repositories,
savepoints, UoW commit ownership, audits and events are unchanged.

The desktop cost serializer now performs presentation only on the response;
it neither receives the aggregate nor rebuilds capabilities. Removed the
redundant API serialization and query-requirement wrappers and the query's
aggregate-taking capability facade. Renamed generic `mappers/responses.py`
to content-specific `mappers/approval.py`. No compatibility wrappers or
duplicate handler/session graphs were introduced. Tests verify frozen
snapshots across lifecycle changes, replay, Decimal/None preservation,
desktop capabilities and stable query counts as page size increases.

Final targeted verification: 309 tests passed across cost lifecycle/output,
desktop Finance, approved-Time labor, allocation N+1, neutral Procurement
delivery, architecture and composition. Ten live PostgreSQL Actual Cost
tests passed through the existing dedicated integration environment,
including runtime-role RLS, hostile scope, stale writes and concurrency.
Previously stale test callers were updated to the existing command DTOs and
required version tokens; no production business rules were loosened.
Mypy passed for 1,302 PM/Platform application/API source files; repository
Ruff F/I, compilation and diff checks passed. Full suites were not run and
the wider boundary migration is not certified. No commit was made.

**Portfolio Intake/Templates direct-result correction (2026-10-16):** added
feature-owned `dto/responses/intake.py` and `mappers/intake.py` for domain
Intake results; no full Intake Reader result already exists. The existing
five-field `PortfolioScenarioIntakeFact` is a distinct bounded analytics
projection and is not expanded or copied into a competing read authority.
Command results snapshot the domain-calculated composite score; no scoring
formula was duplicated. Paginated queries map only the selected page and
return the frozen application page with canonical sort metadata.

Removed `PortfolioIntakeDesktopDto`, `PortfolioTemplateDesktopDto`, their
two API model files and their two serializers, including obsolete exports.
Intake, Intake page and Template operations now pass application results
through the API without serializing/reconstructing their business fields.
Template results reuse the existing application DTO. Intake status/budget/
capacity labels and template weight summaries are built in QML presenters;
no labels were moved into the application. The existing command/UoW,
authorization, organization scope, SQL pagination and scoring authorities
remain intact. Tests assert adapter result identity, immutable snapshots,
exact zero budget/score, normalized page sorting, rollback and UI consumption.

Verification: 309 targeted Portfolio/boundary/SQL-pagination/rollback/UI/
architecture/composition tests passed. Mypy passed for 1,318 PM/Platform
application/API and Portfolio presenter source files; Ruff F/I, compilation,
retired-symbol search and diff checks passed. Other Portfolio destinations
and other API serializers remain to be reconciled with the clarified thin-API
target; the whole migration is not certified. No full suite or PostgreSQL
rerun was claimed for this cut. No commit was made; `.tmp` remains absent.

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

At audit baseline, `TaskService` had the following operation mixins (see the
cutover log below for the current class declaration):
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

### Implementation Evidence (2026-10-10)

**A1 complete.** `ModuleRuntimeSnapshot` and immutable scalar runtime facts
now live under `platform/contract/use_cases/platform_runtime`; the builder
lives in Platform application, and desktop service-dictionary resolution stays
in the desktop adapter. The application no longer imports that adapter.
The new architecture test guards Platform and PM application/contract imports
from API adapters and checks that the runtime snapshot contains no domain
module or entitlement aggregates. Focused Platform runtime/boundary tests:
36 passed (including PM desktop architecture guards). No HTTP adapter was
added.

**A0/A1 composition recheck (2026-10-11).** A0 is the approved inventory and
authority map; A1 owns transport-neutral runtime contracts, not handler
construction. The A1 Platform application/desktop runtime and application
boundary tests were rerun with the current A4 composition work and passed.
The A2 Project pilot remains the canonical pattern: PM composition builds
handlers and injects them into a guarded facade. The recheck identified A4
drift in Register, Resource, Project Resource, and Task; those corrections
are recorded below. No A0/A1 contract or desktop runtime behavior changed.

**A2 complete.** PM composition now injects explicit Project create, update,
status, deletion and query handlers into a thin guarded `ProjectService`.
The five operation mixins were retired; `ProjectSupportMixin` remains as a
feature-specific shared write-policy helper used by create/update handlers,
both of which declare their dependencies explicitly. The catalog read item
contains an immutable `ProjectCatalogProjectFact` rather than a domain
`Project`. SQL reader mapping no longer calls `project_from_orm` for catalog
rows. Shared Project create/update commands moved from the desktop commands
file to `contracts/use_cases/projects`; the old command file was deleted.
The desktop API still exposes its own presentation DTOs and works with the
neutral input classes. Project CRUD, audit/rollback, tenant isolation, budget
redaction, sort/page and desktop tests passed: 71 targeted; the broader PM
application suite passed 1,238 with 2 skipped. Dedicated PostgreSQL runtime
role/RLS tests passed 14. Targeted Project mypy and scoped Ruff F/I passed.
No broad Platform/PM suite or full PostgreSQL suite has run yet; those remain
mandatory A6 gates. A2 did not alter any financial calculation or schema.

**A3 complete by deliberate retention.** Finance workspace's eight query
mixins are already feature-grouped but share a single permission-aware
lookup/scope path; Performance's four query mixins share canonical EVM and
basis authorities. Neither facade owns mutable write state or transaction
commit. Splitting them now would introduce eight-plus handler objects,
delegating wrappers and a new shared policy object, while their sole current
production caller remains the Finance desktop read facade. That increases
coupling and risks duplicating finance permissions/basis without a demonstrated
narrow consumer. Per the approved gate rule, retain these read-only query
aggregators as justified mixins. R6B destination, Performance, canonical
read-model and variance regression: 77 passed. This is an explicit A3
decision, not accidental unfinished migration. Revisit only if a real second
consumer or measured constructor/query problem emerges. A4-A6 remain open.

**A4 in progress: Organization default-calendar persistence inversion.** The
Organization application service no longer imports calendar ORM classes or
seeds rows directly. A Platform contract writer is injected by Platform
composition; its SQLAlchemy implementation writes the organization-scoped
GLOBAL calendar and rules inside the same creation UoW transaction. The
writer is a required constructor dependency, not an optional runtime fallback.
Its explicit scope preserves the just-created organization rather than the
caller's active organization. Rollback, calendar contents, cross-tenant
creation and desktop invalidation passed in the final 56-test
organization/architecture run. The two small existing
Organization typing defects were repaired: bulk updates now select only the
two supported fields explicitly, and the event helper accepts the declared
Organization UoW protocol. AuthService no longer constructs an infrastructure
clock; Platform composition injects the shared `Clock` contract, and 101
focused Auth/RBAC tests passed. The eight touched production files passed Mypy;
scoped production Ruff F/I passed. Narrow architecture guards now prevent
the migrated services from reintroducing concrete infrastructure imports.
Tenant-role administration also receives `Clock` from Platform composition
instead of constructing `SystemClock`; its final role-governance/architecture
suite passed 54 tests with 2 skipped. Its update operation now reuses one
non-null timestamp for persistence, session revocation and the event.
The remaining Platform Auth/Time persistence dependencies, PM A4 clusters,
A5 and A6 remain open. Finance's feature-folder structure and canonical
financial authorities were not changed.

**A4 Auth transaction boundary in progress.** The application-owned
`auth/unit_of_work.py` helper was retired. AuthService, tenant custom-role
administration and role-policy reconciliation now receive the same explicit
`AuthUnitOfWorkFactory` contract; the Platform persistence implementation still
wraps the caller's existing Session in `SqlAlchemyUnitOfWorkBase`, uses a fresh
operation correlation context, rejects absent dispatchers/bus, and retains the
existing commit, transactional-dispatch, post-commit and SQLite lock behavior.
Registration helpers now type their UoW as the shared contract rather than the
concrete SQLAlchemy class. Context switching receives a separate
`SessionWriteLock` port; its concrete adapter still delegates to the same
`sqlite_write_lock` immediately around the shared-session commit. No Finance
folders or financial authorities changed. The Auth/role/reconciliation focused
run passed 163 tests with 2 skipped; context-switch/architecture follow-up
passed 55; PostgreSQL runtime security passed 14. Targeted Mypy is clean.
Time's concrete UoW references were the next A4 batch below; remaining
operation clusters are not yet migrated, so A4 as a whole is not closed.

**A4 Time transaction boundary in progress.** Platform TimeService now receives
an explicit `TimeUnitOfWorkFactory`. TimeEntry mutation and TimesheetPeriod
transition use that factory instead of importing `SqlAlchemyUnitOfWorkBase`
inside application code. The concrete factory still uses the caller's shared
Session, the same dispatchers and bus, and each caller's fresh
`DomainEventContext`; TimeEntry's missing-dispatcher fail-closed check remains.
PM composition supplies the factory without changing Finance ownership or
folders. Focused TimeEntry/TimesheetPeriod/approved-time/architecture tests:
42 passed. Live PostgreSQL approved-time labor posting: 7 passed. Standalone
Mypy for the existing Timesheet mixin files remains noisy because the mixins
declare neither host attributes nor a typed self contract; factory, concrete
adapter and TimeService typing must be checked separately until that larger
handler/mixin migration is completed. A4 is still open.

**A4 Platform UoW package organization complete.** The contract and concrete
persistence UoW packages now mirror Platform capability ownership:
`master_data` (organization, site, department, employee, party, documents),
`security` (Auth, role governance, Auth session write lock), `tenancy`
(membership, module entitlement), `approval`, `time_management`, and
`provisioning` (the cross-cutting organization/entitlement bootstrap UoW).
The existing `integration` folders remain. All production and test consumers
were migrated directly; no old-path compatibility modules were retained.
Focused UoW/transaction suites passed 78 plus 94 tests, the Organization
contract correction passed 27 tests, and the architecture/tenant-membership
adapter suite passed 194. Broad Platform/PM/Platform-UI collection found
3,974 tests without import errors. The 47 UoW contract/implementation files
pass Mypy, and all 76 migrated import consumers pass scoped Ruff F/I. A stale
Project architecture guard was updated to test the approved thin-facade
delegation rather than requiring every handler to inherit the create/update
policy mixin. Finance's PM package structure and business semantics remain
unchanged. This package reorganization does not close the broader A4 gate.

**A4 Register lifecycle boundary in progress.** Register writes now delegate
through the guarded `RegisterService` facade to an explicitly injected
`RegisterLifecycleHandler`. The handler owns only the lifecycle repositories,
tenant/user scope and Register UoW; it retains the existing single-transaction
audit/activity/event behavior. Catalog reads remain on the existing query
mixin because they already have a distinct read dependency and no demonstrated
second consumer requiring another facade. The Register-focused suite passed 20
tests, including bulk status's one-UoW proof; module-guard, entitlement and
architecture tests passed 31. Targeted Mypy passed. Platform application is
now protected by an AST import guard against concrete infrastructure imports.
ModuleCatalog's entitlement transition/provisioning mixin is retained for now:
it represents one governed transaction boundary, and a mechanical split would
add constructor coupling without a proven benefit. The final Register and
dependency-guard rerun passed 29 tests, including a disabled-module denial
before handler entry. A4 remains open for Time and the larger PM operation
clusters.

**A4 Project Resource read boundary in progress.** The Project Resource
query mixin was replaced by an explicitly injected query handler. The existing
guarded service remains the sole public facade; its six read methods delegate
to the handler. Membership writes now delegate to an explicitly injected
`ProjectResourceCommandHandler`; the guarded facade no longer retains duplicate
repositories, session or UoW state. The handler keeps the established single
transaction, authorization, envelope, audit and event path, and validates
Decimal inputs through the existing ProjectResource write model. The old
command mixin and its stale references were removed. Disabled-module regressions
verify both read and write delegation cannot bypass the PM module gate. The
expanded Project Resource/resource transaction suite passed 80 tests; targeted
Mypy passed on the command handler and facade. TimeService's unused `_assignment_repo`
and `_task_repo` aliases were removed after confirming that the actual
`_work_allocation_repo`/`_work_owner_repo` fields serve all consumers; Time,
TimesheetPeriod and approved-time regressions passed 37 tests. The larger Time
handler split remains open because query/support/period transitions share
authorization, UoW and approved-time event policy; it must not be forced as a
mechanical move that risks one-effect or transaction semantics.

**A4 Resource capability/context/master cutover complete (2026-10-11).** Resource
skill and certification page queries now use an explicitly injected scoped
`ResourceCapabilityQueryHandler`; their governed writes use a separate
`ResourceCapabilityCommandHandler` with explicit repositories, tenant/user
scope and the existing Resource UoW. Resource Projects, Assignments and
Activity server-paged reads use a `ResourceContextQueryHandler`. Resource
master create/update/lifecycle/purge now use a `ResourceMasterCommandHandler`
with explicit Employee, Department, Site, tenant, authorization and UoW
dependencies. `ResourceService` remains the single guarded public facade; the
same Resource UoW, audit/activity/event staging and optimistic-version checks
remain. No Finance authority or folder structure changed. All old Resource
capability/context/master mixin symbols were removed. A 65-test
resource-context/capability/composition rerun passed after updating stale test
probes of private ProjectService fields to the approved Project handlers and
using the session fixture. The final integrated Resource, directory,
capability, context, architecture and composition run passed 90 tests. Targeted
Mypy passes on the five changed Resource application files. The live R5H
PostgreSQL runtime-role/RLS matrix passed 14 tests against the dedicated
non-owner test database, covering Resource scope and parent/child bypass.
This closes the
Resource master/capability/context batch, not A4 overall; Time, Task,
Collaboration, Portfolio and other characterized clusters remain.

**A4 handler construction correction and Task Detail read slice
(2026-10-11).** PM composition now constructs Register lifecycle, Project
Resource command/query, and Resource master/capability/context handlers and
injects them into their guarded facades. ResourceService no longer retains an
unused write UoW, clock, or duplicate write-only dependencies. Task Detail
lookup and its server-paged Assignment, Dependency, and Activity reads moved
from the broad Task query mixin into a read-only
`TaskDetailPageQueryHandler`; the normal Task builder and both approval
participant builders inject it. The Reader calls now use explicit typed
parameters rather than heterogeneous `**kwargs`, with the same scope,
permissions, sort and normalized-page retry behavior. An AST architecture
guard prevents the A2/A4 PM facades from constructing handlers. The A0/A1,
Resource, Register, Task Detail, composition and architecture matrix passed
138 tests; approval participant regressions passed 11. Targeted Mypy and
Ruff F/I passed. This corrects handler ownership without closing all of A4.

**A4 Task read continuation (2026-10-11).** Task Detail's four read methods
have dedicated behavior tests for assignment ascending/descending page order,
out-of-range normalization, predecessor/successor filtering, activity page
size, and denial before Reader access. The Task workspace's authoritative
server-page method now delegates to a composition-injected
`TaskWorkspacePageQueryHandler` with explicit Reader, calendar, session and
tenant dependencies. The normal Task service and both approval-participant
compositions inject the handler; there is no service-side construction or
fallback. Task Detail and workspace handlers share the composed Reader.
Task workspace pagination/sort, detail, approval participant, architecture
and composition regression passed 48 tests;
targeted Mypy and Ruff F/I passed. Task command/participant UoW behavior was
not changed. A4 remains open for the larger command, Time, Collaboration and
Portfolio clusters.

**A4 Task lookup cutover (2026-10-11).** The remaining `TaskQueryMixin`
became a composition-injected `TaskLookupQueryHandler` for project/resource
Task lookups, Assignment lookups, Timesheet assignment contexts, and scoped
task queries. The guarded `TaskService` delegates all seven public methods;
the normal Task composition and both approval-participant compositions inject
the handler. The old mixin file, export, and stale test-path mapping were
deleted rather than kept as a compatibility layer. Resource/task Assignment
lookups now use `TaskRepository.list_by_ids()` once per operation instead of
`get()` inside a loop; project permission filtering and input order are
preserved. A direct regression makes per-task `get()` fail and verifies the
batch call and denied-project filtering. Focused Task, Timesheet, leveling,
desktop, approval-participant and architecture tests passed 65 cases;
composition/handler/architecture tests passed 16 cases; and the PM service
tenant-isolation regression passed 3 cases. Targeted Mypy, Ruff F/I, Python
compilation and `git diff --check` passed. This closes the Task read-query
mixin, not the larger Task command or A4 gate.

**A4 Task WBS read-query cutover (2026-10-11).** The four hierarchy and
rollup reads now delegate from `TaskService` to a composition-injected
`TaskHierarchyQueryHandler`; the normal Task builder and both approval
participant builders supply its explicit repository, calendar and session
dependencies. Ordered child grouping moved to the Task domain hierarchy
module so command and query paths retain one rule without a query-to-command
mixin dependency. The hierarchy command, scheduling and UoW paths were not
changed. Focused WBS, scheduling, desktop API and architecture tests passed
22 cases; targeted Mypy passed. A4 remains open for the Task command and
other characterized clusters.

**A4 Task dependency diagnostics read cutover (2026-10-11).** The dependency
impact and removal previews now use a composition-injected
`TaskDependencyDiagnosticsQueryHandler`; the Task facade keeps typed public
methods, and dependency commands continue to invoke those methods before
their existing write/UoW path. The normal builder and both approval
participant builders supply the task/dependency repositories, calendar,
scheduling engine and session explicitly. The old diagnostics mixin/export
was retired. Dependency preview, authorization, concurrency and WBS tests
passed 29 cases; the broader business-rule, dependency math/performance and
architecture matrix passed 67 cases. Targeted Mypy and Ruff F/I passed.
Task command mixins and A4 overall remain open.

**A4 Task code and validation policies (2026-10-11).** `TaskIdentityMixin`
and `TaskValidationMixin` were retired. PM composition now constructs and
injects `TaskCodePolicy` and `TaskValidationPolicy` at the normal Task service
and both approval-participant sites. Lifecycle/assignment commands still use
the facade's private helpers and the same Task UoW; code generation, duplicate
mapping, project-date validation, capacity rules, warning consumption and
strict/warn policy are preserved. Capacity conflict-name resolution now uses
one `list_by_ids()` batch instead of `get()` inside a loop, with a direct
regression forbidding per-task reads. The focused Task/capacity/approval/
tenant-isolation/architecture matrix passed 60 tests; targeted Mypy passed.
The larger Task command mixins and A4 overall remain open.

**A4 Task schedule-sync extraction (2026-10-11).** `TaskScheduleSyncMixin`
was retired. PM composition injects a `TaskScheduleSynchronizer` with the
existing SchedulingEngine and TaskRepository into all three TaskService
construction paths. Dependency, constraint, leveling and approved-schedule
commands still own their UoW and call the facade helper with explicit
`commit=False`; the synchronizer only computes before/after task-date IDs.
The `commit` argument is now required, preventing an accidental implicit
scheduler commit in a future UoW caller. A direct test proves changed-ID
selection, primary-task exclusion and commit-flag forwarding. The focused
scheduling/approval matrix passed 37 tests; a post-signature Task/
architecture rerun passed 24; targeted Mypy and Ruff F/I passed.

The remaining `TaskAssignmentBridgeMixin` is **not** a safe rename: when it
auto-provisions `ProjectResource`, it calls `session.commit()` before
delegating to the assignment command. A4 must characterize and replace that
split transaction with one operation-owned UoW before retiring the mixin;
do not preserve its early commit in a new handler. This risk is separate
from the completed schedule-sync extraction.

**A4 Task assignment atomicity prerequisite (2026-10-11).** The Task UoW
now includes the scoped ProjectResource repository. `assign_resource` stages
an auto-provisioned ProjectResource and its TaskAssignment in the same Task
UoW; the old `session.commit()` before assignment has been removed. The
public `assign_project_resource` no longer accepts private UoW/object
overrides; a private shared-UoW helper handles the bridge and direct command
paths. Rollback tests inject failure before assignment and after assignment
staging and verify neither record persists. The focused assignment, capacity,
approval-participant and architecture matrix passed 61 tests. Scoped Ruff
F/I and Python compilation passed; targeted Mypy passed on the UoW contract,
implementation, participant scope and Task facade. Existing direct Mypy
errors in the legacy Assignment/Bridge mixins remain part of the pending
handler migration. This removes the split transaction but does **not**
retire the remaining Task command mixins or close A4. PostgreSQL runtime-role
RLS/concurrency proof is still required before the full Task cutover closes.

**A4 Task WBS support-policy cutover (2026-10-11).**
`TaskHierarchySupportMixin` became a composition-injected
`TaskHierarchyPolicy` with explicit Task, Assignment and Dependency
repositories. `TaskService` retains private delegates for existing hierarchy,
lifecycle and assignment commands while their transaction ownership remains
unchanged. The WBS policy no longer relies on facade inheritance; the
parent-walk also explicitly terminates at a missing parent ID. WBS,
resource-flow and architecture regression passed 35 tests; targeted Mypy,
Ruff F/I and compilation passed. A4 remains open for the larger Task command
groups.

**A4 Task deletion transaction boundary (2026-10-11).** Task deletion now uses
the Task UoW session for TimeEntry, Assignment, Dependency and Task writes;
the outer-session flush is gone. The UoW also exposes TimeEntry cleanup to
resource unassignment. Bulk deletion resolves selected Tasks and Assignments
in batches, and the production TimeEntry repository deletes the selected
allocations in one scoped SQL statement. The approval participant uses its
caller-owned TimeEntry repository, preserving its single transaction owner.
Focused Task/Time tests passed 36 cases, including injected Task-delete
failure proving Task, Assignment and TimeEntry rollback. `TaskDeletionMixin`
was then retired: composition now injects `TaskDeletionCommandHandler` and a
shared `TaskUowScope` into `TaskService`. The latter preserves normal fresh
UoWs and approval-participant event collection without hidden facade state.
Approval-participant regression passed 22 cases; targeted Mypy passed.
A combined Task/approval/architecture run passed 50 cases; scoped Ruff F/I,
Python compilation and `git diff --check` passed.
A4 remains open for the other Task command mixins, audit/event rollback and
PostgreSQL runtime-role RLS proof.

**A4 Task progress command cutover (2026-10-11).** `TaskProgressMixin` was
retired. A composition-injected `TaskProgressCommandHandler` now receives the
Task repository, user/tenant context, the existing WBS/date policies and the
same TaskUowScope used by the facade. Bulk status changes fetch selected Tasks
in one batched repository read rather than a per-ID loop. Public TaskService
methods remain thin delegates; permission, project-scope, leaf, date,
activity and event behavior is unchanged. Focused Task/desktop/architecture
tests passed 38 cases, progress/domain tests passed 21 cases, and an injected
second-write failure proved bulk status rollback. Targeted Mypy passed.
A4 remains open for the remaining Task command mixins and integrated
PostgreSQL/security/event proofs.

**A4 Task/Time bridge cutover (2026-10-11).** `TaskTimeEntryMixin` was
retired. Composition injects a `TaskTimeEntryHandler` with the existing
TimesheetService, Task/Assignment repositories and user context. TaskService
retains explicit public delegates; Time remains the sole owner of TimeEntry
and period writes, authorization, and transactions. The Task-scoped entries
page preserves the same task/project permission check and one batched
allocation lookup. The legacy mixin export and unused TaskService timesheet
repository/service constructor state were removed. Focused Task/Time tests
passed 42 cases; approved-time labor and concurrency tests passed 36 cases;
targeted Mypy passed. The Task-scoped page still materializes the task's
entries before in-memory pagination, so this cutover does not close the
separate SQL pagination/performance concern. A4 remains open.

**A4 approved Task schedule-change cutover (2026-10-11).**
`ApprovedScheduleChangeMixin` was retired. Composition now injects an
`ApprovedScheduleChangeHandler` with explicit Task repository, tenant scope,
calendar/scheduler, schedule synchronizer, date validation policy and shared
TaskUowScope. The TaskService facade preserves the Financial Change port's
validation/apply methods and participant event collection. Validation batches
target Task and project-hierarchy reads rather than querying per target.
Persisted result dates are checked fail-closed before audit/activity and
`AppliedTaskScheduleChange` evidence. Financial Change and schedule-impact
regressions passed 38 cases, end-to-end Financial Change orders passed 19
cases, and a targeted test proves approval validation does not use per-target
`get()` calls; targeted Mypy passed. A4 remains open for the
other Task command mixins and integrated security/concurrency/RLS proofs.

**A4 Task WBS move/recode command cutover (2026-10-11).**
`TaskHierarchyMixin` was retired. Composition now injects a
`TaskHierarchyCommandHandler` with explicit Task repository, user/tenant
context, existing WBS policy and shared TaskUowScope. `TaskService.move_task`
and `recode_task` remain thin public delegates. The original WBS conflict,
cycle, descendant recode, activity and event behavior is preserved. Focused
WBS/desktop/approval/architecture tests passed 27 cases; an injected second-write failure
proved full subtree rollback; targeted Mypy passed. A4 remains open for the
remaining Task command mixins and PostgreSQL RLS/concurrency proof.

**A4 Task scheduling-constraint command cutover (2026-10-11).**
`TaskSchedulingConstraintMixin` was replaced by an explicitly injected
`TaskSchedulingConstraintHandler`. Its permission/governance decision,
apply-time version and calendar checks, schedule recalculation, audit/activity,
and event recording remain on one operation-owned UoW path. `TaskService`
retains thin public and approval-participant delegates; Task creation delegates
the shared calendar policy to the handler. Main and approval composition now
construct the handler directly. Focused constraint, persistence, desktop and
approval-participant tests passed 26 cases; a recalculation-failure rollback
test passed with the constraint unchanged. Targeted Mypy and Ruff F/I passed.
A4 remains open for the other Task command mixins and wider integration gates.

**A4 Task resource-leveling command cutover (2026-10-11).**
`ResourceLevelingApplyMixin` was replaced by composition-injected
`ResourceLevelingCommandHandler`, covering the shared preview/fingerprint and
governed apply workflow. Main and approval composition pass explicit repository,
calendar, session, tenant, scheduler and UoW dependencies; `TaskService` keeps
thin desktop and approval-participant delegates. Fingerprint rejection,
per-task audit/activity/events and one operation-owned transaction remain in
place. A new injected recalculation-failure test proves all proposed task floors
roll back. Focused leveling/desktop/approval tests passed 28 cases; neighboring
constraint/WBS and architecture tests passed 37 cases. Targeted Mypy passed.
The remaining Task dependency and assignment mixins still need A4 review or
cutover; A4 is not closed.

**A4 Task lifecycle command cutover (2026-10-11).**
`TaskLifecycleMixin` was replaced by `TaskLifecycleCommandHandler`, built by
main and approval composition with explicit Task repository, user/tenant
context, calendar, existing Task code/WBS/date/constraint policies and shared
Task UoW scope. `TaskService.create_task` and `update_task` are thin delegates;
the commands package no longer exports the retired mixin. Two new
failure-injection tests prove Task create/update and activity recording roll
back together. Focused lifecycle/WBS/constraint/leveling/approval tests passed
45 cases; desktop CRUD and architecture tests passed 25; rollback tests passed
2. Targeted Mypy and Ruff F/I passed. At this cutover,
`TaskDependencyMixin`, `TaskAssignmentMixin` and
`TaskAssignmentBridgeMixin` remained inherited; PostgreSQL and broad A4/A6
validation remained open.

**A4 Task dependency command/read cutover (2026-10-11).**
`TaskDependencyMixin` was retired. `TaskDependencyCommandHandler` now owns
governed add/update/remove and approval apply, with explicit repositories,
authorization context, WBS policy, diagnostics reader, schedule synchronizer
and Task UoW scope. `TaskDependencyQueryHandler` owns permission-scoped get/list
reads, retaining the single project-wide dependency query rather than an N+1
task loop. PM main/approval composition builds both; `TaskService` retains
thin public and approval-participant delegates. Dependency governance,
concurrency, diagnostics, read-performance and approval tests passed 24 cases;
two injected schedule-failure tests proved add/update rollback. Targeted Mypy
passed; adjacent dependency/scheduling, desktop CRUD and architecture tests
passed 79 cases. Only `TaskAssignmentMixin` and `TaskAssignmentBridgeMixin` remain as
TaskService operation mixins; A4's broader integration gates remain open.

**A4 Task assignment command cutover (2026-10-11).** The final two operation
mixins were retired. Composition injects one `TaskAssignmentCommandHandler`
into the guarded `TaskService` facade for normal PM requests and both approval
participants. The handler owns assignment writes, reads, response actions,
capacity warnings and the auto-provision bridge. Auto-provisioning a
`ProjectResource` and creating its `TaskAssignment` still use one Task UoW;
the old bridge implementation and dead TaskService policy/UoW wrappers were
removed. The facade retains the pending-event hook used by approval/Finance.
Focused assignment and approval-participant tests passed 42 cases; targeted
Mypy and Ruff F/I passed. TaskService now inherits no operation mixins, but
A4 remains open for the other service clusters and broad PostgreSQL/security,
desktop and integration closure gates.

**A4 TaskService facade simplification audit (2026-10-11).** The current
facade is smaller than the older line-count estimate but still forwarding-heavy.
The method/consumer map and capability/lifetime design are in
[`task_service_facade_a4_inventory.md`](task_service_facade_a4_inventory.md).
The first verified cut removes four unused facade constructor inputs and an
uncalled private constraint-validation delegate. Approval/Financial Change
participant forwarding remains until outer transaction and event-drain parity
can be demonstrated; no direct handler injection may bypass module entitlement.
This is an A4 continuation, not A4 closure.

**A4 Task capability consumer cutover (2026-10-11).** PM composition now
returns one typed, session-scoped Task result exposing the existing lookup,
assignment, lifecycle, hierarchy and progress handlers alongside the current
facade. Dashboard consumes only lookup/assignment, and CSV import consumes
only lookup/lifecycle/hierarchy/progress. Their own module guards remain in
place; the handlers still enforce task/project permissions and own the same
UoWs. Focused Dashboard/composition/WBS, import, and architecture suites passed
31, 44, and 26 cases respectively. The desktop adapters and approval/Finance
participants still depend on TaskService; no facade method used by them was
retired. The full facade refactor therefore remains open.

**A4 narrow-consumer cleanup verification (2026-10-11).** The only facade
delegate made unused by the Dashboard/import cutover,
`list_assignments_for_tasks`, is removed. Dashboard batching instrumentation
now observes the real lookup handler and passed 2 tests. Dashboard and CSV
module-entitlement regression tests passed with the existing guards; focused
permission/lookup tests passed 45; live PostgreSQL runtime-role security/RLS
passed 14. TaskService is 795 lines, 75 methods including `__init__`, and 27
constructor inputs versus 816/77/31 at the audit start. Remaining desktop and
transaction-scoped callers are deliberately unchanged; the broader facade
refactor and A4 overall remain open.

**A4 Dashboard desktop read cut (2026-10-11).** The delayed-tasks adapter
now uses the same composed Task workspace query handler directly, with an
explicit module-entitlement check at the desktop boundary before handler
permission and scope checks. No second handler/session was built. Tasks desktop
still uses the facade workspace-page delegate, so it remains active. Focused
Dashboard/composition/module-guard/architecture tests passed 49 cases; A4
remains open for the other desktop and transaction-participant callers.
Desktop-registry and Finance invalidation regressions passed 22 cases with
one skip; scoped Ruff F/I, compilation and diff check passed.

**A4 Timesheets desktop read cut (2026-10-11).** The Timesheets adapter now
receives the composed Task lookup and assignment handlers rather than
TaskService. Its assignment selectors and snapshot retain module-entitlement
checks; handlers retain task/project permissions and the Timesheet write path
is unchanged. Two context-only TaskService forwarding methods with no
remaining production callers were removed. TaskService is now 782 lines,
73 methods and 27 constructor inputs. Focused Timesheets, composition,
module-guard, measurement and registry tests passed 54 cases. The remaining
Tasks/Scheduling desktop and approval/Financial Change participants still
need separate safe migrations; A4 remains open. Live PostgreSQL runtime-role
security/RLS regression passed 14 cases after this cut.

**A4 Tasks workspace-page cut (2026-10-12).** Tasks desktop now calls the
existing composed Task workspace page handler directly, with the same
module-entitlement check before the handler's task/project and tenant/org
checks. Dashboard already used that handler. The last production facade caller
was migrated, so `TaskService.query_workspace_page` and its constructor input
were deleted; approval and Financial Change participant compositions also
stopped constructing unused workspace handlers. The guarded desktop query
budget remains four statements. TaskService is now 745 lines, 72 methods and
26 constructor inputs. Focused page/serialization/composition tests passed 45;
approval/Financial Change/Tasks API/Dashboard/architecture tests passed 41.
QML task presenter/controller regressions passed 20; live PostgreSQL
security/RLS passed 14. Scoped Ruff F/I, Mypy, compilation and diff checks
passed. A4 remains open for remaining Task facade consumers and participant
contracts.

**A4 Task Detail page cut (2026-10-12).** Tasks desktop now receives the
composed Task detail query handler directly for assignment, dependency and
activity pages. The adapter retains PM module-entitlement checks, and the
handler retains task/project and tenant/org checks. The three page-query
facade delegates were deleted; its detail handler remains required by the
active `get_task` facade method. TaskService is now 709 lines, 69 methods and
26 constructor inputs. Focused detail/composition passed 46; API/guard/
architecture passed 28; QML/approval/Financial Change passed 40; live
PostgreSQL security/RLS passed 14. A4 remains open for other facade callers and
transaction-scoped participant contracts.
The desktop architecture guard now distinguishes the explicit
`require_module_enabled` policy call from application-object construction;
its negative construction regression and the affected API suite passed 27.

**A4 dependency-preview read cut (2026-10-12).** Tasks desktop now receives
the same composed diagnostics handler used by dependency commands and guards
module entitlement before the read. Two unused TaskService preview delegates
and their constructor input were deleted. Approval/Financial Change
participant transactions remain unchanged. The facade is now 682 lines, 67
methods and 25 constructor inputs. Focused regressions passed 71;
architecture/API/composition passed 37; live PostgreSQL RLS/security passed
14. Scoped Ruff F/I, Mypy, compilation and diff checks passed. A4 is still
open for remaining real consumers and participant-scoped boundaries.

**A4 dead lookup cleanup (2026-10-12).** Three facade methods with no
production callers were deleted: `list_tasks_for_resource`,
`list_assignments_for_resource`, and `query_tasks`. The first two remain
available on the composed lookup handler; its unused in-memory `query_tasks`
path was retired in favor of the existing paged workspace query. TaskService
is now 656 lines, 64 methods and 25 constructor inputs. Focused lookup,
resource and adapter tests passed 31; the combined Task/API/approval/
architecture slice passed 100 and live PostgreSQL security/RLS passed 14.
Scoped Ruff F/I, Mypy, compilation, and diff checks passed. A4 remains open.

**A4 Task Detail time-read cut (2026-10-12).** Tasks desktop now injects the
composed assignment and time-entry handlers for time summary and entry-page
reads. Adapter entitlement and handler task/project scope checks remain in
place. The two superseded TaskService delegates were deleted; the facade is
now 628 lines, 62 methods and 25 constructor inputs. Task/UI/composition/
architecture tests passed 77; live PostgreSQL security/RLS passed 14.
Scoped Ruff F/I, Mypy, compilation and diff checks passed. A4 remains open.

**A4 unused read-delegate cleanup (2026-10-12).** Removed test-only
`get_assignment`, `list_time_entries_for_assignment`, and `get_time_entry`
from TaskService. Tests now use the existing assignment handler or
TimesheetService. The facade is 619 lines, 59 methods and 25 constructor
inputs. Migrated tests passed 21; combined Task/API/UI/composition/
architecture tests passed 94 and live PostgreSQL security/RLS passed 14.
Scoped Ruff F/I, Mypy, compilation, and diff checks passed. A4 remains open.

**A4 Timesheet period authority cut (2026-10-12).** Nine TaskService
period/read forwards with no production caller were retired; tests now use
TimesheetService for governed period transitions. Dead TaskTimeEntryHandler
pass-throughs were deleted while its live task-page query and entry operations
remain. TaskService is 559 lines, 50 methods and 25 constructor inputs.
Focused Time/permissions tests passed 69; combined Task/Timesheets/approval/
desktop/architecture tests passed 123; live PostgreSQL security/RLS passed
14. Scoped Ruff F/I, Mypy, compilation and diff checks passed. A4 remains open.

**A4 TaskService constructor cleanup (2026-10-12).** Removed eight
stored-but-unused constructor inputs from TaskService and all three PM-owned
builders. Approval and Financial Change transaction tests now assert supplied
session and service identity on the real UoW and handlers, rather than on
facade aliases. The guard retains its user session and module catalog. The
facade is 528 lines, 50 methods and 17 constructor inputs. Combined focused
regressions passed 134; live PostgreSQL security/RLS passed 14. Scoped Ruff
F/I, Mypy, compilation and diff checks passed. A4 remains open.

**A4 assignment-hours capability cut (2026-10-12).** Tasks desktop now
calls the existing composed assignment command handler directly for manual
assignment hours, retaining its module guard and the handler's permission,
scope, and UoW rules. Tests use the owning handler. The obsolete TaskService
forwarder was removed. TaskService is 525 lines, 49 methods and 17
constructor inputs. The TimeEntry authority and approval-participant
transactions are unchanged. A4 remains open.
Focused Task/Time/permissions tests passed 47; desktop/composition tests
passed 29 with 1 skipped; desktop entitlement regression passed (14 in its
slice); live PostgreSQL security/RLS passed 14. Scoped Ruff F/I, Mypy and
compilation passed. A repository-wide Ruff invocation reported 78 findings;
the touched Python files pass scoped F/I checks.

**A4 timesheet initialization delegate removal (2026-10-12).** Test-only
initialization forwards were removed from TaskService and TaskTimeEntryHandler;
tests now call the owning TimesheetService. The focused Time/collaboration/
desktop slice passed 32 tests. TaskService is 522 lines, 48 methods and 17
constructor inputs. Other time-entry write forwards and approval transaction
contracts remain for later verified migration; A4 remains open.

**A4 TimeEntry write ownership cut (2026-10-12).** Tests now call the
authoritative TimesheetService for TimeEntry creation, correction, and
deletion. Removed three TaskService forwards, three duplicate
TaskTimeEntryHandler forwards, one facade constructor input, and two unused
approval-only handler constructions. The Task Detail time page retains its
read-only handler. TaskService is 489 lines, 45 methods and 16 constructor
inputs. Approval participant transaction paths are unchanged. A4 remains open.
The affected Task/Time/Approval/UI/composition slice passed 178 tests;
live PostgreSQL security/RLS passed 14. Scoped Ruff F/I, Mypy, compilation,
and diff checks passed. A stale composition import of PM worker principal
names was also corrected to resolve directly from their application owners.

**A4 Project read capability cut (2026-10-12).** PM-owned composition now
exposes the existing `ProjectQueryHandler` alongside `ProjectService` in a
typed `ProjectComposition`; the application root and desktop resolver pass
that same instance to Projects desktop. The adapter checks the PM entitlement
before read calls, while the query handler keeps project permission and scope
checks. Projects desktop no longer uses service query forwards or the old
detail fallback. Seven now-unconsumed ProjectService query forwards were
removed after test callers migrated to the composed handler. Project command
operations and the still-used `get_project`/`list_projects` facade reads remain.
No duplicate handler or session graph was introduced. Portfolio already has
feature command/query packages; Resource already has master/capability command
and capability/context query handlers. Those consumers require separate
guard/transaction characterization before direct injection, not duplicate
handler creation.

**A4 Resource detail-query capability cut (2026-10-12).** PM-owned
composition exposes the existing `ResourceCapabilityQueryHandler` and
`ResourceContextQueryHandler` beside `ResourceService` in a typed
`ResourceComposition`. The application root and desktop resolver reuse the
same instances. Resources desktop checks the PM module entitlement before
calling either handler; the handlers retain permission and tenant/project
scope enforcement. Skills, certifications, projects, assignments, and
activity detail pages no longer pass through five ResourceService query
forwards. The forwards and their two facade constructor dependencies were
deleted after test callers migrated. ResourceService remains for active
catalog reads and commands. The focused Resource/context/composition slice
passed 52 tests; the guard/domain/desktop slice passed 26 tests. Scoped
Mypy and Ruff F/I passed. Pylance/Pyright CLI is not installed in the
environment, so editor diagnostics were not independently run. At this checkpoint A4 remained
open: TaskService still had 45 methods and 16 constructor inputs, and
Portfolio/other consumers have not yet been migrated to narrow capabilities.
The PostgreSQL security slice was invoked but all 14 tests skipped because
the required live test database was not configured for this run; it is not
claimed as fresh RLS evidence for this cut.

**A4 PM application-service disposition (2026-10-12).** This inventory covers
the PM-owned application service families, not Platform services consumed by
PM. A service is not a defect merely because it remains a service: retain
actual orchestration, policy, calculation, and transaction coordination.
This is a historical checkpoint, superseded by the completed PM named-service
inventory and final verification below. Its open rows described implementation
work at that time, not the current production architecture.

| PM family | Boundary at this checkpoint | Disposition at this checkpoint |
| --- | --- | --- |
| Projects | `ProjectService` commands and two still-used lookups; `ProjectQueryHandler` directly exposed | Keep guarded command facade while active callers need it; migrate remaining lookups only with their scope/module checks, then remove dead forwards. |
| Tasks | `TaskService` remains 45 methods/16 constructor inputs; composed command/query capabilities are already separately exposed | Continue caller-by-caller removal of ordinary delegates. Keep approval-participant, scheduling-constraint, resource-leveling, and pending-event/UoW operations until shared-transaction equivalence is proven. |
| Resources | `ResourceService` still owns active command delegates and catalog reads; capability/context detail query handlers are direct | Move command consumers to the already composed master/capability handlers only with equivalent module, permission, event, and UoW checks. Retain read methods that are not forwarding to those handlers. |
| Project resources | `ProjectResourceService` forwards command and query handlers | Candidate for direct capability injection; Projects and Tasks desktop plus assignment builders must migrate together before retiring the facade. |
| Register | `RegisterQueryHandler` and `RegisterLifecycleHandler` are independently composed and injected | Complete: all production read/write consumers migrated; `RegisterService` deleted. Both handlers retain module, permission, tenant/project, and UoW boundaries. |
| Portfolio | `PortfolioIntakeQueryHandler` now owns scoped Intake browse; `PortfolioService` still owns Intake writes and template/scenario/dependency/executive mixins over one UoW | Continue cohesive command/query cuts only after shared scope, scoring, and UoW policy is characterized; do not instantiate one service per mixin or duplicate sessions. |
| Collaboration | `CollaborationService` coordinates comment/mention/evidence operations and a shared collaboration UoW | Split only independently transactional capabilities after privacy, recipient, audit, and event proofs. |
| Timesheets | `TimesheetService` owns owner/reviewer authorization, period/entry workflows, and approval interactions | Retain as workflow authority; split read capabilities only if they remove a measured dependency without bypassing period/UoW policy. |
| Dashboard and Reporting | Dashboard assembles cross-feature read facts; Reporting owns guarded analytical/report queries | Retain current read orchestration. Narrow upstream dependencies where safe; do not duplicate EVM or Finance calculations in new handlers. |
| Scheduling and baselines | `SchedulingEngine`, `BaselineService`, comparison and impact services own scheduling/baseline rules | Retain domain/workflow services. Any caller cut must preserve project scope, baseline approval and schedule transaction ownership. |
| Resource planning | availability, capacity, workload, and portfolio pool services own distinct calculations/read rules | Retain; they are not forwarding facades. |
| Data import | PM importer coordinates schema, validation, and Project/Task writes through existing capabilities | Retain as an infrastructure adapter/orchestrator; do not bypass feature commands or their module guards. |
| Finance | Budget, Forecast, Changes, Configuration, Rates, Actuals, Commitments, Planned Cost, Billing, handoff, Finance read/performance/workspace services | Retain separate canonical business authorities and existing governed command/read boundaries. No blanket handler rewrite or second financial formula path. |

At that checkpoint, the immediate A4 migration backlog was Task ordinary delegates,
Resource command delegates, Project Resource, Portfolio, and Collaboration.
Register migration is complete. Closure requires migrated production consumers and removal of
superseded paths, not just constructing handlers in composition. The other
families above were explicitly reviewed and initially retained. Their final
disposition is recorded in the completed inventory below.

**A4 Register command cut (2026-10-13).** PM composition constructs one
`RegisterLifecycleHandler`, exposes it in a typed `RegisterComposition`, and
injects it directly into Register desktop writes. The handler itself now
enforces the PM module entitlement in addition to its existing command
permission, project scope, and UoW checks; desktop also checks entitlement.
`RegisterService` no longer accepts the handler or forwards create, update,
delete, or bulk-status commands. Subsequently, its read methods were moved to
`RegisterQueryHandler`, which is directly injected into Register desktop and
Dashboard. The now-empty `RegisterService` file was deleted, and the composition
graph exposes `register_query` plus `register_lifecycle_commands`, not a
compatibility service key. The query handler retains read permission, project
scope, tenant scope, and module entitlement checks.
Register/domain/composition tests passed 30; the broader Register, pagination,
presenter, and composition slice passed 47; Portfolio/Scheduling/Timesheets/
Finance/architecture regressions passed 62. Scoped Mypy and Ruff F/I passed.
This is a completed Register command cut, not A4 overall closure.

**A4 Register read cut (2026-10-13).** Dashboard and Register desktop now
receive the same composition-built `RegisterQueryHandler`. The old service
class/file, its graph key, and stale service-facing assertions were removed.
Register query/lifecycle, desktop, Dashboard, tenant-hardening, pagination,
composition, and architecture matrix: 95 passed. An earlier wider slice found
three stale tests accessing repositories on `TaskService`; those tests now
address the owning Task lookup/dependency handlers, and the affected slice
passed 46. Scoped Mypy (five entrypoints), Ruff F/I, and diff check passed.
`PortfolioService` remains active shared scoring/UoW policy across command and
query mixins, and `FinanceService` remains active snapshot/reconciliation
calculation authority; neither is an empty forwarding facade. Finance's
governed command port has one dynamic `*args, **kwargs` relay into a fresh
operation UoW; removing it requires a separately proven transaction-preserving
typed boundary, not a cosmetic mass replacement.
Portfolio's `update_intake_item` and `update_scenario` now expose explicit
keyword parameters instead of accepting untyped `**changes`. The update
semantics distinguish omitted fields from explicit `None` for target dates and
optional limits; unknown field names fail immediately. Portfolio domain,
modernization, and rollback slice: 49 passed. This is command-contract cleanup,
not a claim that Portfolio mixins have become handlers. The next structural
Portfolio cut should compose cohesive command/query handlers with explicit
dependencies and a shared scoring/scope policy, migrate consumers, then delete
superseded mixins and the service only when no orchestration remains. Current
independent Mypy checking reports pre-existing hidden-state mixin attribute
errors; these require the handler migration rather than blanket suppression.

**A4 Portfolio Intake read cut (2026-10-13).** PM composition constructs one
`PortfolioIntakeQueryHandler` from the existing scoped Intake repository,
tenant context, user session, and module catalog. It injects this handler into
the desktop Portfolio adapter; the two Intake browse methods and their mixin
were removed from `PortfolioService`. Authorization, module entitlement,
organization scoping, SQL pagination, and sort behavior remain at the handler.
The same repository instance is used; no second session or UoW was created.
Portfolio/desktop/composition/architecture regression: 105 passed. Scoped
Mypy on the new handler, desktop API, composition, and graph: clean. This is
one completed read-capability cut, not Portfolio or A4 closure.

## A4 Platform Capability Cutover (2026-10-14)

This continuation applies the approved direction to the remaining named
Platform boundaries: composition constructs cohesive handlers and injects
them directly into desktop adapters, workers, CLI operations, and module
consumers. No replacement forwarding service or compatibility alias is kept.
The supplied backlog labels this group as 22, but names 20 service types plus
the Platform runtime facade (21 named types). The map below covers every
named item; it does not invent an additional migration target.

| Former boundary | Active application capabilities | Composition and consumers |
| --- | --- | --- |
| ApprovalService | ApprovalCommandHandler, ApprovalQueryHandler, ApprovalParticipantRegistry | Platform approvals composition shares the registry with PM registrations; desktop receives commands/queries; PM participants keep the deciding UoW session. |
| FinancialPeriodService | FinancialPeriodCommandHandler, FinancialPeriodQueryHandler | Platform finance composition creates both; desktop receives both; PM costing/Billing receives only period queries. |
| NotificationService | NotificationCommandHandler, NotificationQueryHandler, NotificationDeliveryHandler | Notification composition supplies scoped commands, pure reads, and explicit durable delivery; desktop drains committed work before reading. |
| ServicePrincipalService | ServicePrincipalCommandHandler, ServicePrincipalQueryHandler, ApiKeyAuthenticationHandler | Security composition supplies management to desktop, scoped worker lookup to integration runtimes, and credential authentication separately. |
| RuntimeExecutionService | RuntimeExecutionCommandHandler, RuntimeExecutionQueryHandler | Composition reuses one scoped execution repository; import/export/report runtimes receive lifecycle commands, history consumers receive reads. |
| MasterDataExchangeService | SiteImportHandler, SiteExportHandler, PartyImportHandler, PartyExportHandler | Master-data composition registers entity-owned handlers and constructs the existing import/export runtimes; the aggregate service and callback wrappers are removed. |
| AccountingConnectorConfigurationService | AccountingConnectorConfigurationCommandHandler | Application command retains caller-owned participant semantics or operation UoW ownership; no nested handler is constructed in a command. |
| AccountingIntegrationCapabilityService | AccountingIntegrationCapabilityQueryHandler | External integration composition injects the adapter-installation/configuration capability query without introducing Accounting operations. |
| RoleGovernanceService | RoleGovernanceCommandHandler | Security composition injects scoped role governance into assignment, access, and module registration consumers. |
| RolePolicyReconciliationService | RolePolicyReconciliationCommandHandler, RolePolicyReconciliationQueryHandler | Reconciliation preview and mutation are separate capabilities with explicit authorization/transaction dependencies. |
| ScopeDelegationProvisioningService | ScopeDelegationProvisioningCommandHandler, ScopeDelegationProvisioningQueryHandler | Delegation planning and application retain their existing scope and privilege checks. |
| TenantRoleAdministrationService | TenantRoleCommandHandler, TenantRoleQueryHandler | Tenant-role reads and commands share composition-owned authorization policy and repository lifetimes. |
| TenantAdminService | TenantLifecycleCommandHandler, TenantAdminQueryHandler | Tenancy composition exposes catalog reads and tenant lifecycle writes separately. |
| TenantMembershipService | TenantInvitationCommandHandler, TenantMembershipLifecycleCommandHandler, TenantMembershipQueryHandler | Tenancy composition shares membership support/UoW dependencies; invitation acceptance, membership state, and personal invitation reads are separate. |
| PlatformCalendarService | PlatformCalendarCommandHandler, PlatformCalendarQueryHandler | Calendar composition supplies catalog writes/reads separately. |
| WorkingRuleService | WorkingRuleCommandHandler, WorkingRuleQueryHandler | Existing rule transactions and resolver invalidation are preserved. |
| CalendarExceptionService | CalendarExceptionCommandHandler, CalendarExceptionQueryHandler | Exception mutations and reads are directly injected. |
| RecurringEventService | RecurringEventCommandHandler, RecurringEventQueryHandler | Recurrence mutations and reads are directly injected. |
| ShiftPatternService | ShiftPatternCommandHandler, ShiftPatternQueryHandler | Pattern/day writes and scoped pattern reads are directly injected. |
| CalendarAssignmentService | CalendarAssignmentCommandHandler, CalendarAssignmentQueryHandler | External module assignment ports remain neutral and generic; both handlers share the composed repositories. |
| PlatformRuntimeApplicationService | PlatformRuntimeQueryHandler plus existing Organization handlers and OrganizationProvisioningCommandHandler | Runtime orchestration retains permissions/accessibility/snapshot policy; organization forwarding methods and the resolver that built a hidden runtime graph are removed. |

Handler implementations remain in their feature application packages.
Reusable immutable application DTOs remain beside the relevant feature
handlers. Cross-module Approval and Notification capabilities live under
`src/core/platform/contract/port/approval` and `.../notifications`; the retired
`application/notifications/public.py` is not a public cross-module dependency.
Platform and PM composition remain separate, with the existing application
composition root assembling their typed results.

Transaction distinctions remain explicit: Approval participants run in the
deciding UoW; connector configuration uses the supplied transaction repository
and audit owner; API-key authentication atomically writes use/audit evidence;
runtime tracking remains transaction-neutral. Notification reads do not drain
the outbox; the desktop adapter invokes the delivery capability explicitly.
Calendar writes keep the existing resolver cache/invalidation relationships.

Retired service production paths and runtime forwarding/resolver paths are
removed. Tests address the handler/repository/UoW that owns the behavior.
The scoped baseline application lookup is classified as a Scheduling port,
not a SQL Reader fact contract. Architecture size checks exclude third-party
temporary caches rather than treating cached dependencies as repository code.

Validation status: the named Platform capability cutover is COMPLETE.

| Final verification slice | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Affected Platform application/API/auth/infrastructure feature matrix | 524 | 0 | 5 |
| PM Approval participants, approved-Time/Commitment integration, Scheduling, and affected desktop/QML adapters/presenters | 159 | 0 | 0 |
| Architecture guards, including schema/migration and read/port boundaries | 188 | 0 | 0 |
| Composition lifetime/event registration guards | 34 | 0 | 0 |
| Live PostgreSQL runtime-role RLS/notifications/Accounting handoff | 31 | 0 | 0 |
| Live PostgreSQL governance/Finance commands/approved-Time integration | 60 | 0 | 0 |

The five Platform skips are existing storeroom ownership-resolver tests for
the absent Inventory module. They are not substituted for the live RLS runs.
Supplemental Accounting command/transaction and application boundary tests
passed 25 cases; supplemental notification/overview/desktop tests passed 24.
These reruns overlap the matrix above and are not added to a unique-test total.
All 5,972 repository tests collected successfully; the full repository test
suite was not executed for this focused migration.

Scoped Ruff F/I, Python compilation, retired production-symbol searches, and
`git diff --check` pass. Mypy reports no issues in 144 scoped source files
with `--follow-imports=silent --ignore-missing-imports`. Standalone
Pyright/Pylance is unavailable in this environment and is not claimed as run.
The only corrected production guard issue found during validation was a
nested connector-command handler construction; it now uses the operation's
repository/audit owner directly. Tests also prove notification queries do not
deliver work and the desktop adapter retains explicit restart recovery.

This closes the named Platform backlog, not unrelated PM/A4/A5/A6 work.
No future Accounting/Procurement/Inventory operations or transport framework
were introduced, and no commit was made by the agent.

## PM Named-Service Capability Cutover: Complete

The requested PM inventory contains 22 boundaries: Projects and Tasks (2),
Finance (13 when Forecast generation/versions and Billing profile/preparation
are counted separately), Resources (4), and Scheduling/baselines (3).
All named production facades below have been retired. Final integrated
verification passed on 2026-10-15. This closes the named PM handler cutover,
its Finance DTO regrouping, and the module-owned graph follow-up; it does not
claim unrelated repository-wide lint-policy cleanup or new product capabilities.

| Existing boundary | Current migration status |
| --- | --- |
| ProjectService | Deleted. Composition injects the existing query/create/update/status/deletion handlers directly into desktop, import and internal consumers. |
| TaskService | Deleted. Typed Task composition exposes lifecycle, progress, hierarchy, dependency, assignment, time-entry, scheduling and read capabilities. Approval participants receive only their supplied-session decision handlers and TaskUowScope; Financial Change receives the trusted scheduling port. |
| BudgetService | Deleted. budgets/commands separates lifecycle, lines and approval/successor authority; budgets/queries separates catalog and workspace reads. |
| ProjectCommitmentService | Deleted. commitments/commands/projection.py owns neutral financial-fact projection/matching; commitments/queries owns read-only catalog access. |
| FinancialConfigurationService | Deleted. configuration/commands separates financial profile and cost-code operations; configuration/queries owns catalog/workspace reads. |
| ProjectCostEntryService | Deleted. cost/entries/commands separates manual lifecycle, review, posting, approved-Time and neutral Procurement receipt consumption. Queries cannot mutate or revalue Actuals. |
| FinancialChangeService | Deleted. financial_changes/commands separates draft/impact, submission and approval/successor application. Impact commands return their changed parent and impact together from the same transaction. |
| ForecastGenerationService | Deleted. forecasts/commands/generation.py owns the existing authoritative draft-generation operation inside the fresh governance UoW. |
| ForecastVersionService | Deleted. forecasts/commands separates lifecycle, lines and approval/successor operations; forecasts/queries owns catalog/workspace reads. |
| ProjectBillingProfileService | Deleted. invoicing/commands separates profile and schedule operations; invoicing/queries owns profile/schedule reads. |
| ProjectBillingPreparationService | Deleted. invoicing/commands separates preparation lifecycle, sources, submission and participant approval. Accounting handoff requests no longer reach through private preparation state. |
| PlannedCostService | Deleted. planned_costs/commands/snapshot.py owns snapshot creation; planned_costs/queries owns read-only access. |
| ProjectRateCardService | Deleted. rate_cards/commands separates cards from rate-line governance; rate_cards/queries owns catalog/workspace reads. Historical selection remains RateCardResolver-owned. |
| FinanceService | Single read authority moved to financials/queries/snapshot.py as FinanceSnapshotQueryHandler; composition, desktop, reporting/export and test consumers migrated; former production file deleted. Financial calculation semantics unchanged. |
| AccountingHandoffRequestService | Deleted. accounting/commands/request.py injects repositories, evidence builder, permission context, clock, audit/event sink and enqueue capability explicitly. Immutable handoff, outbox and Billing transition remain atomic; the enqueue clock is pinned to the evidence timestamp. |
| EnterpriseResourceAvailabilityService | ResourceAvailabilityQueryHandler under resources/capacity/queries/availability.py; composed instance reused by capacity/assignment consumers; old production file deleted. |
| ResourceWorkloadService | ResourceWorkloadQueryHandler under resources/capacity/queries/workload.py; scoped workload consumers migrated; old production file deleted. |
| PortfolioResourcePoolService | PortfolioResourcePoolQueryHandler under resources/portfolio/queries/resource_pool.py; Portfolio/composition consumers migrated; old production file deleted. |
| ProjectResourceService | Facade deleted. Composition exposes ProjectResourceCommandHandler and ProjectResourceQueryHandler directly, with the existing scoped repository and shared UoW; both enforce module entitlement before operation. |
| BaselineService | Deleted. scheduling/baselines/commands/lifecycle.py owns the governed lifecycle; queries/catalog.py owns reads. The approval participant retains its supplied session and never opens or commits another UoW. |
| BaselineComparisonService | Standalone comparison implementation moved to scheduling/baselines/queries/comparison.py as BaselineComparisonQueryHandler; old file deleted. Existing callers are tests, not an active production destination; production integration is not claimed. Do not conflate baseline-to-baseline comparison with current-schedule reporting. |
| ScheduleChangeImpactService | ScheduleChangeImpactQueryHandler under scheduling/forecasting/queries/change_impact.py. Module composition constructs it from scoped repositories/calendar/approved-baseline port and injects the same instance into Tasks and Scheduling desktop adapters. Old service and API-owned construction helper deleted. |

The schedule-impact cutover also repaired a real composition defect: the old
desktop helper looked for repository attributes retired from TaskService and
silently failed to construct the query. Construction now belongs exclusively
to Scheduling composition. The approved-baseline lookup port exposes its
actual immutable ID requirement rather than an opaque object.

Project handlers preserve explicit project permission checks and their
existing fresh Project UoWs/shared deletion transaction. Entitlement guards
now reside on all directly consumed Project handlers, not solely on the
former aggregate facade. Regression tests verify exact composed-instance
identity and disabled-module rejection before repositories/UoWs execute.
Resource tests similarly verify command/query repository identity without
asserting an obsolete forwarding facade's source text.

The temporary Project and Task facade files and their graph exposures are
deleted. Test helpers inspect the actual owning handlers/repositories rather
than requiring compatibility attributes on a query handler.

Finance writes retain the operation-scoped governance UoW. The dynamic
FinanceGovernedServicePort, mutation registry and wrapping composition module
are deleted. Explicit, typed governance callbacks select cohesive command
handlers on the fresh UoW; outward reads receive query handlers directly.
This is real transaction orchestration, not a replacement forwarding facade.
Participant/caller-owned transactions, immutable handoff/outbox atomicity,
Decimal authorities and permission/scope checks remain required gates.

Verification so far (overlapping slices, not a unique-test sum): scheduling
and entitlement 55 passed; resource/Finance-read/desktop 57 passed;
Project command/identity/desktop/composition 73 passed; architecture,
composition, contracts and desktop matrix 356 passed; final importer,
permission, tenant-isolation and Project composition slice 46 passed.
Live PostgreSQL RLS/Finance-read/governance/approved-Time/history slice:
37 passed, 0 failed, 0 skipped, using the existing Docker PostgreSQL and its
non-owner runtime role. Scoped Mypy: all 78 changed production source files clean with
`--follow-imports=silent --ignore-missing-imports`. Scoped Ruff F/I, changed
Python compilation and diff checks pass. Standalone Pylance/Pyright is not
available and is not claimed as run.

The expanded affected-file run initially found four failures: a stale Approval
query fixture attribute, two repository-scope tests inadvertently invoking
ProjectResource commands, and duplicate desktop/handler Project entitlement
queries. All were corrected and the affected 115-test slice passes. The
Project handler remains the entitlement authority; the obsolete desktop
entitlement dependency is removed, restoring the existing four-statement
Project catalog page budget. Mypy-driven API cleanup also replaces untyped
Project import/Finance cost-code keyword dictionaries with explicit arguments
and represents an absent portfolio summary as unavailable, not zero.
The combined matrix was rerun after these corrections from the final source
worktree:

| Earlier seven-boundary checkpoint (not current final verification) | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| All affected test files, architecture/schema guards, composition, Project/Resource/Scheduling/Finance contracts and desktop/UI regressions | 672 | 0 | 0 |
| Live PostgreSQL runtime-role RLS, Finance performance Reader, governed commands, approved-Time posting and activity/history scope | 37 | 0 | 0 |

At that earlier checkpoint, all 5,982 repository tests collected successfully.
The full repository suite was not executed. Scoped Ruff F/I and compilation covered all changed Python files;
Mypy covers all 78 changed production Python files; `git diff --check` is green.
Standalone Pylance/Pyright remains unavailable. Those earlier checks certified
the initial seven retired paths only. Their then-open 15 boundaries have now
been migrated as described in the current inventory; final verification of
the combined implementation must not reuse the earlier counts as evidence.

PM named-service/A4 cutover is COMPLETE. No Finance business-semantic change,
future Accounting/Procurement/Inventory operation, additional session/handler
graph or agent commit was introduced.

### Final Closure Evidence (2026-10-15)

| Final verification scope | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Entire PM backend suite, four isolated file shards plus serial timing files | 1,923 | 0 | 1 |
| Entire Platform backend suite, four isolated file shards | 1,832 | 0 | 5 |
| Entire PM QML/controller/presenter/context/route suite | 792 | 0 | 0 |
| Shared QML primitives and application shell | 367 | 0 | 0 |
| Architecture and application/module composition | 227 | 0 | 0 |
| Live PostgreSQL integration, RLS, concurrency, recovery and performance | 250 | 0 | 0 |

Shard coverage was reconciled against collection: all 1,924 PM and 1,837
Platform cases were included exactly once. The PM skip is the explicitly
opt-in large-scale workflow (PM_RUN_PERF_TESTS); the five Platform skips
require the intentionally absent Inventory-owned storeroom scope resolver.
They are not implemented by PM to make tests pass. Separate PostgreSQL
10k/50k performance fixtures passed with their original thresholds.

Earlier broad runs exposed obsolete query/session probes, participant facade
attribute names, desktop fixtures missing governed command injection, an
incorrect Task lookup capability, and builtin-exception expectations. These
were migrated to the actual handler/UoW owners without adding compatibility
attributes or bypassing transactions/authorization. Whitespace-sensitive
invitation event guards now inspect AST event calls; the Forecast generation
test has real input evidence rather than skipping any BusinessRuleError.

Two later source-inspection failures were traced to cached line numbers while
source formatting was in progress. Fresh focused tests passed, and the complete
frozen-source shard rerun above is green. PostgreSQL and Gantt timing thresholds
also failed under competing test load; isolated final reruns passed without
raising limits or changing financial/authorization behavior.

PostgreSQL uses the existing reproducible Docker environment, fresh Alembic
schema, and the non-owner app_runtime role with NOSUPERUSER/NOBYPASSRLS and real
tenant/organization session context. SQLite remains the fast unit-test backend.
No PostgreSQL installation, production schema reset, or new module was added.

Mypy passed 729 application/API/composition source files using
--follow-imports=silent --ignore-missing-imports. Repository-wide Ruff F/I,
changed-file full configured Ruff rules, Python compilation, changed shared
QML control lint and git diff --check passed. Standalone Pylance/Pyright was
not available and is not claimed. The broader repository Ruff caveat is
recorded below; the full repository test suite was not run.

Production retired-symbol/path searches are clean. TaskService and its
forwarding facade are gone, rather than reduced to another forwarding layer.
The module guard and shared Project create/update validation support remain
intentional mixins; typed CQRS query partitions remain query composition,
not old operation services. Domain calculators, policies, transaction/UoW
orchestration and infrastructure import adapters retain their distinct roles.
No generic command bus, global service locator, dynamic forwarding or second
financial authority was introduced. Existing user work/commits were preserved;
the agent made no commit.

### Current Integration Corrections

- Finance features use real commands/ and queries/ packages. Lifecycle,
  line/source editing, submission, review and posting are separated where
  their dependencies/invariants differ; a large service was not simply renamed.
- Source cost analytics lives at
  application/financials/analytics/costs/source_breakdown.py. Its former
  reporting/analytics.py path and reporting re-export are removed.
- Task assignment-preview conflict labels use one scoped batched task lookup,
  not get_task inside a per-conflict query loop.
- Baseline events use the existing ID-only active-scope contract. Project
  invalidation drops and logs a tenantless event instead of constructing an
  unscoped presentation hint.
- The finite Accounting handoff evidence builder remains destination-neutral.
  Delivery infrastructure is injected at composition, never inferred from a
  Billing facade's private state.

### Finance Application DTO Ownership

The former application/financials/models/finance_models.py combined unrelated
application result types. It is deleted, along with the generic models package
and unused services re-export. Existing fields, calculations, Decimal values,
availability states and dataclass semantics are preserved at these owners:

| Application owner | Types |
| --- | --- |
| financials/dto.py | FinanceSnapshot, FinanceReconciliation, FinancePeriodRow, FinanceAnalyticsRow |
| financials/cost/dto.py | ProjectFinanceLedgerRow, cost breakdown/source rows and labor result types |
| financials/revenue/dto.py | ProjectCommercialProjection |
| financials/earned_value/dto.py | EarnedValueMetrics, EvmSeriesPoint |
| financials/governance/successors/dto.py | ApprovedFinancialLineAdjustment, ApprovedFinancialSuccessorResult |

Successor contracts are shared only by Budget, Forecast and Financial Change
approval workflows, not general read models. The former shared/successor_models.py
is deleted. Reader facts stay under contracts/reads; desktop formatting stays
under api/desktop. No duplicate DTO definitions or old-path compatibility
modules are retained.

Governance's package initializer no longer eagerly imports command handlers:
application DTO imports must not build the governance command graph. Command
boundary consumers import command_boundary directly. Dashboard's internal
query capability protocols remain under contracts/ports/dashboard, like other
contracts between PM capabilities/submodules. Cross-module synchronous
integration boundaries use the existing module-level gateway package, not
internal ports. Canonical event payloads remain distinct from synchronous
gateway capabilities; this grouping does not create a second fact-delivery path.

### Module-Owned Composition Graph

The central ServiceGraph no longer repeats the complete Platform and PM
dependency inventories. It aggregates the already-built PlatformServiceBundle,
ProjectManagementServiceBundle, GlobalOverviewServiceBundle and the
application-owned IntegrationRuntimeBundle, plus the shared Session reference.
ServiceGraph is reduced from 690 lines/168 fields to 43 lines/5 fields.

Each owner explicitly exports its existing runtime bindings: Platform 82,
PM 89, integration runtime 7 and Overview 4, plus the application's Session
binding: the same 183 public runtime dependency names. No handler, repository,
SQLAlchemy session or graph is reconstructed during export. The existing
desktop runtime dictionary remains an active adapter input, not a second
application dependency graph or a handler-owned service locator.

The application container assembles these bundles and cross-module runtimes;
module-owned bootstrap remains responsible for constructing module handlers.
There are no flat forwarding properties, dynamic __getattr__, compatibility
facades or duplicate module graph types. Duplicate exported dependency names
raise ConfigurationError with code DUPLICATE_RUNTIME_DEPENDENCY instead of
silently replacing another owner's instance. Regression tests prove identity,
database-free export and collision rejection.

Quality scope: repository-wide Ruff F/I is clean. The broader configured Ruff
profile was also run and reports 748 remaining findings (predominantly unused
unpacked test variables, broad exception handling and date/time policy).
It is not reported as globally clean. Newly moved DTO exports and empty
type-checking blocks were corrected; changed files pass the full configured
rules. Broad historical lint-policy remediation is not a business-handler
or composition-cutover change.

### Transport-Neutral Error Contract

Core exceptions remain under core/platform/common/exceptions.py and contain
no HTTP status, FastAPI dependency or transport response. Every expected
failure carries a stable code, safe message and its original cause when
translated. The application/API adapters use the shared validation,
not-found, business-rule, concurrency, authentication, authorization,
configuration and unsupported-operation vocabulary. Missing runtime wiring
is a configuration failure, not a missing business record or a fake zero.

The future HTTP adapter should use specific-before-general type dispatch:

| Application failure | Future HTTP mapping |
| --- | --- |
| AuthenticationError | 401; adapter supplies authentication headers when appropriate. |
| AuthorizationError | 403; preserve the permission-denial code. |
| NotFoundError | 404; retain scoped not-found behavior without revealing foreign records. |
| ConcurrencyError | 409; an adapter may use 412 only for an explicit HTTP conditional-write contract. |
| BusinessRuleError | 409 for a rejected state transition or workflow prerequisite. |
| OperationNotPermittedError | 409 for an operation forbidden by entity structure/immutability; caller permission denial uses AuthorizationError instead. |
| ValidationError | 422 for validly parsed but invalid application input; malformed transport syntax is the adapter's 400 responsibility. |
| Named ingress payload-size validation error | 413, checked before general ValidationError. |
| UnsupportedOperationError | 501 for a genuinely unsupported server operation; invalid format/selection input remains ValidationError, not this type. |
| ConfigurationError, otherwise-unclassified DomainError, or unexpected internal failure | 500 with a safe response; log technical details/cause privately. |

Successful 200 reads, 201 creation, 202 accepted asynchronous work and 204
no-content writes are selected by endpoint semantics, not by exceptions.
A valid read model with unavailable/restricted metrics remains a truthful
successful result; metric availability is not an HTTP error classifier.

Pydantic validators retain the internal exceptions their validation machinery
requires. Public boundaries translate expected failures or quarantine finite
integration rejection reasons; programmer errors and injected infrastructure
failures are not mislabeled as successful business results. No FastAPI
implementation, HTTP schema hierarchy or generic catch-and-swallow layer is
introduced by this contract.

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

The user approved implementation of the migration gates and the recorded
follow-up decisions. Completed scope and its verification are recorded above;
this does not authorize speculative business-semantic changes, a FastAPI
implementation or future Accounting/Procurement/Inventory operations.
