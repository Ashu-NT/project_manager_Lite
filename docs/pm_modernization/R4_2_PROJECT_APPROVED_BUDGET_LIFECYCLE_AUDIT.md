# R4.2 Project Approved Budget Lifecycle Audit

Status: READ-ONLY AUDIT COMPLETE  
Date: 2026-08-20  
Scope: Project Approved Budget from persistence through CQRS, desktop API, presenter/controller, and PM QML  
Constraint: R4.2 remains closed. This report does not authorize implementation or visual redesign.

## 1. Executive Summary

`Approved Budget` is not a mutable `Project` field. It is the exact `SUM(project_finance_budget_lines.amount)` for the one `ProjectBudget` whose status is `approved` in the active tenant, organization, and project. Project Finance owns that authorization lifecycle. A budget is drafted as versioned lines, submitted, and approved or rejected; approval can be direct or routed through the platform approval workflow. The Project catalog consumes the result as a cross-aggregate CQRS projection.

The absence of an Approved Budget input in `ProjectEditorDialog.qml` is therefore intentional and architecturally correct. Adding that field would create a second source of truth and bypass budget permissions, approval, audit, immutability, and optimistic concurrency. The actual product gap is that the Finance QML and desktop API expose Budget Versions and Budget Lines as read-only data and provide no budget create/edit/submit/approve workflow.

Four integration defects must be corrected before adding a budget management entry point: the Project catalog discloses Finance totals under only `project.read`; the single-project detail API does not hydrate Approved Budget or Finance currency; the catalog formats the total with Financial Profile currency rather than the approved Budget's own currency; and the Projects controller does not refresh on `project_budget` events. The table column is also configured without `sortable: true`, making its implemented server sort unreachable from QML.

## 2. Observed Product Gap

The Projects catalog, inspector, and detail design all present a field called `Approved Budget`, while Project Create/Edit has no matching input. This is not a missing-field defect in isolation. The displayed value belongs to a governed Finance aggregate and is intentionally absent from Project commands and persistence.

The user-visible gap is workflow reachability: users can see existing approved budget facts, but the current desktop application cannot create or approve a budget through Finance. The backend lifecycle exists and is tested; its desktop/QML command adapter does not.

## 3. Terminology

| Repository term | Current meaning |
|---|---|
| `ProjectFinancialProfile` | One finance configuration record per project; owns project Finance currency and policy, not an amount. |
| `ProjectBudget` | One immutable-after-submission budget authorization revision. |
| `BudgetLine` | A cost-code/task amount belonging to a ProjectBudget. |
| Approved Budget | Sum of lines belonging to the ProjectBudget currently in `approved` status. |
| `revision` | Immutable business revision number within a project: v1, v2, and so on. |
| `row_version` / ORM `version` | Optimistic concurrency token incremented on header and line-driven aggregate changes. |
| Planned cost | A disposable, computed labor-cost snapshot; not an approved authorization. |
| Forecast / EAC | A versioned estimate-to-complete control; distinct from budget authorization. |
| BAC | Finance snapshot `budget`, sourced from the approved budget total. |
| Funding | `ProjectFinancialProfile.is_funded`, currently a Boolean, not a funding amount. |
| Baseline | Scheduling/control baseline; not the authoritative ProjectBudget amount. |

## 4. Projects Approved Budget Column

| Attribute | Current implementation |
|---|---|
| QML configuration | `src/ui_qml/modules/project_management/qml/workspaces/projects/ProjectsColumnConfig.js` |
| Table | `ProjectsListPage.qml`, `AppWidgets.DataTable { id: projectsTable }` |
| Table persistence ID | `pm.projects.table` in `ProjectsWorkspaceState.qml` |
| Column key and raw row property | `approvedBudgetLabel` |
| Label | `Approved Budget` |
| Formatter | None in QML; the backend sends a preformatted string. |
| Server sort key | `approvedBudgetLabel` is allowed and mapped by the QueryService/Reader. |
| Effective QML sorting | Disabled because the column omits `sortable: true`, despite `sortingMode: "server"`. |
| Currency | Embedded in `approvedBudgetLabel`, for example `EUR 250,000.00`. |
| Null behavior | Desktop `format_budget(None, currency)` returns `Not set`. |
| Default visibility | `visibleByDefault: true`. |
| Customization persistence | Yes. Column order and hidden state are stored through `loadTableColumnState` / `saveTableColumnState`. |
| Export | Included when visible through the current visible-column export state. |

The DataTable does not calculate or format money. Its model row receives `approvedBudgetLabel` from the Projects presenter serialization.

## 5. Project Read Path

The live catalog path is:

1. `ProjectsListPage.qml` reads model property `approvedBudgetLabel`.
2. `ProjectManagementProjectsWorkspaceController.refresh()` asks `ProjectProjectsWorkspacePresenter.build_workspace_state()` for a page.
3. `workspace_builder.build_workspace_state()` calls `ProjectManagementProjectsDesktopApi.list_project_page()`.
4. The desktop API calls `ProjectService.query_catalog_page()` and serializes every `ProjectCatalogReadItem` with `serialize_project()`.
5. `ProjectQueryMixin.query_catalog_page()` validates query state, tenant/org context, and project access before invoking `SqlAlchemyProjectCatalogReader.read_page()`.
6. The reader executes one paginated SQL statement containing the approved-line aggregate.
7. `serialize_project()` produces exact decimal text plus `approved_budget_label`.
8. `project_mapper.build_project_state()` maps it to `approvedBudget` and `approvedBudgetLabel`.
9. `serialize_project_record_view_models()` supplies the row to `DynamicTableModel` and QML.

Files:

- `src/core/modules/project_management/application/projects/queries/project_query.py`
- `src/core/modules/project_management/infrastructure/persistence/reads/projects/sqlalchemy_catalog_reader.py`
- `src/core/modules/project_management/contracts/reads/projects/models.py`
- `src/core/modules/project_management/api/desktop/projects/api.py`
- `src/core/modules/project_management/api/desktop/projects/serializers/project_serializer.py`
- `src/ui_qml/modules/project_management/presenters/projects/workspace_builder.py`
- `src/ui_qml/modules/project_management/presenters/projects/project_mapper.py`
- `src/ui_qml/modules/project_management/controllers/projects/projects_workspace_controller.py`

## 6. Authoritative Persistence Source

Approved Budget is derived from two canonical tables:

| Table | Relevant columns | Nullability / type |
|---|---|---|
| `project_finance_budgets` | `tenant_id`, `organization_id`, `project_id`, `id`, `currency_code`, `status`, `revision`, `version`, approval metadata | Scope, project, currency, status, revision, and version are non-null. |
| `project_finance_budget_lines` | `tenant_id`, `organization_id`, `project_id`, `budget_id`, `amount`, `currency_code`, `version` | `amount` is non-null `Numeric(19,4)` and must be nonnegative. |

ORM models are `ProjectBudgetORM` and `BudgetLineORM` in `infrastructure/persistence/orm/budget.py`. The budget has scoped FKs to Organization and Project. A line has a four-column scoped FK to its budget and scoped FKs to Project and Cost Code. Project deletion cascades to budgets and lines; cost-code and task references are restricted where history must be preserved.

The derivation is exactly:

```sql
SELECT SUM(project_finance_budget_lines.amount)
FROM project_finance_budget_lines
JOIN project_finance_budgets
  ON matching tenant_id, organization_id, project_id, and budget_id
WHERE project_finance_budgets.tenant_id = projects.tenant_id
  AND project_finance_budgets.organization_id = projects.organization_id
  AND project_finance_budgets.project_id = projects.id
  AND project_finance_budgets.status = 'approved'
```

There is no `COALESCE`; absence of an approved budget or approved lines yields SQL `NULL`, then DTO `None`, then `Not set`.

## 7. Project Domain

`Project` in `domain/projects/project.py` owns:

`id`, `name`, `code`, `description`, `start_date`, `end_date`, `status`, `client_name`, `client_contact`, `organization_id`, `site_id`, `department_id`, `client_party_id`, `manager_user_id`, and `version`.

It has no `budget`, `planned_budget`, `approved_budget`, `budget_amount`, or currency field. `Project.create()` therefore accepts no financial amount. Project optimistic concurrency protects only Project-owned fields. Budget mutations do not and should not increment `Project.version`; they use `ProjectBudget.row_version` and `BudgetLine.row_version`.

Project emits `project_changed` after Project writes. Budget lifecycle operations emit `budgets_changed` independently.

## 8. Project ORM / Mapper / Repository

`ProjectORM` has no budget or currency column. The removed legacy `planned_budget` is absent. The Project mapper neither omits nor fabricates a budget value because no Project-owned value exists. `SqlAlchemyProjectRepository.add()` and `update()` persist only Project fields, and its version-checked update has no Finance column.

Layer proof:

| Layer | Budget field present? | Finding |
|---|---:|---|
| `ProjectORM` | No | No persistence omission. |
| `Project` domain | No | Intentional Finance ownership. |
| Project mapper | No | Correctly maps only Project state. |
| Project repository add/update | No | Correctly avoids a duplicate source of truth. |
| Project CQRS read item | Yes, derived | `approved_budget: Decimal | None`. |
| Desktop Project DTO | Yes, read-only | Decimal text and display label. |

## 9. Project Create Path

Create flow:

`ProjectEditorDialog.buildPayload()` -> `ProjectsDialogHost` -> controller `createProject()` -> presenter `project_command_handler.create_project()` -> `ProjectCreateCommand` -> `ProjectManagementProjectsDesktopApi.create_project()` -> `ProjectService.create_project()` -> `Project.create()` -> Project repository + new `ProjectFinancialProfile` -> commit -> `project_changed`.

The Project and its one-to-one Financial Profile are created atomically. Currency establishes Finance configuration; no Budget or BudgetLine is created.

| Field | QML create | Desktop request | Application service | Project domain | Repository / ORM |
|---|---:|---:|---:|---:|---:|
| `name` | Yes | Yes | Yes | Yes | Yes |
| `code` / `projectCode` | Yes | Yes | Yes | Yes | Yes |
| `description` | Yes | Yes | Yes | Yes | Yes |
| `status` | Yes | Yes | Yes | Yes | Yes |
| `client_name` | Yes | Yes | Yes | Yes | Yes |
| `client_contact` | Yes | Yes | Yes | Yes | Yes |
| `start_date` | Yes | Yes | Yes | Yes | Yes |
| `end_date` | Yes | Yes | Yes | Yes | Yes |
| `site_id` | Yes | Yes | Yes | Yes | Yes |
| `department_id` | Yes | Yes | Yes | Yes | Yes |
| `financial_currency_code` | Yes | Yes | Yes | No | Financial Profile only |
| `organization_id` | Context-derived in current QML | Supported | Yes | Yes | Yes |
| `client_party_id` | No | Supported | Yes | Yes | Yes |
| `manager_user_id` | No | Supported | Yes | Yes | Yes |
| Approved Budget | No | No | No | No | Finance Budget only |

## 10. Project Update Path

Update flow mirrors create through `ProjectUpdateCommand` and `ProjectService.update_project()`. It accepts Project identity/profile fields and `expected_version`; it accepts neither Finance currency nor a budget amount.

Approved Budget cannot be changed programmatically through the Projects desktop API, Project commands, Project service, Project aggregate, or Project repository. The Project write path ends before Finance. It can only change through `BudgetService` or an approved `FinancialChangeService` successor operation.

## 11. Current Project Editor

`ProjectEditorDialog.qml` contains:

- Project code
- Project name
- Status
- Site
- Department
- Client
- Client contact
- Financial currency, visible only during Create
- Start date
- Finish date
- Description

There is no Approved Budget field, hidden budget input, advanced section, Finance section, conditional permission-gated budget field, or budget mutation payload. Currency on Create configures the Financial Profile; it does not authorize spending.

## 12. Legacy/Dead Project Budget UI

| Finding | Classification | Evidence |
|---|---|---|
| Current Projects QML only displays `approvedBudgetLabel` | LIVE | Column, inspector, and Overview. |
| `Project.planned_budget` and its database column | LEGACY, REMOVED | C.9 documentation records clean-break removal; absent from current domain/ORM. |
| `FinancialsBudgetSection.qml` | DEAD, DELETED | `test_finance_workspace_phase_b8.py` asserts it does not exist. |
| `FinancialsBudgetVersionsSection.qml` | LIVE, READ-ONLY | Displays budget revision records. |
| `FinancialsBudgetLinesSection.qml` | LIVE, READ-ONLY | Displays paginated lines. |
| Project budget editor dialog | NOT PRESENT | Repository-wide QML search finds none. |
| Presenter tests using synthetic approved amounts | TEST-ONLY | They prove mapping, not persistence or write reachability. |

No orphaned live Project budget editor was found.

## 13. Finance Budget Domain

`ProjectBudget` is the Finance-owned aggregate root for one project's budget authorization revision. `project_id` links it to Project. One project may have many historical revisions, but database partial unique indexes allow at most one open revision (`draft` or `submitted`) and at most one `approved` revision at a time.

Statuses are `draft`, `submitted`, `approved`, `rejected`, `superseded`, and `closed`. `revision` is the immutable business version. `row_version` is the optimistic token. Only `draft` is mutable; `submitted` is frozen pending decision.

The budget header has no total column. The total is always the sum of its lines. Approval authorizes the complete frozen line set at that revision.

## 14. Budget Write Lifecycle

Primary backend methods in `BudgetService`:

| Operation | Method | Permission | Key rule |
|---|---|---|---|
| Create revision | `create_budget()` | `budget.manage` | Requires Project and Financial Profile; only one open revision. |
| Edit header | `update_budget_header()` | `budget.manage` | Draft only; currency deliberately immutable. |
| Add line | `add_line()` | `budget.manage` | Draft only; cost code/task scoped; currency must match budget. |
| Update line | `update_line()` | `budget.manage` | Draft only; checks both budget and line versions. |
| Delete line | `delete_line()` | `budget.manage` | Draft only; checks both versions. |
| Submit | `submit_budget()` | `budget.manage` | Requires at least one line; Draft -> Submitted. |
| Approve | `approve_budget()` | `budget.approve` or governed `approval.request` | Submitted -> Approved. |
| Reject | `reject_budget()` | `budget.approve` | Submitted -> Rejected. |
| Close | `close_budget()` | `budget.approve` | Approved -> Closed. |
| Delete | `delete_budget()` | `budget.manage` | Draft only. |

Actual lifecycle:

```text
                         +-> Rejected [terminal]
                         |
Draft -> Submitted ------+
                         |
                         +-> Approved -> Closed [terminal]
                                      |
                                      +-> Superseded [terminal]
                                          when a successor is approved
```

There is no archive status and no reopen transition. A rejected, closed, or superseded revision is replaced by a new revision, never edited back into service.

## 15. Approval Lifecycle

Direct mode:

`BudgetService.approve_budget()` requires global and project-scoped `budget.approve`, checks `expected_version`, supersedes the previous approved row in the same nested transaction, approves the submitted candidate, commits, audits, and emits `budgets_changed`.

Governed mode:

1. Requester requires global and project-scoped `approval.request`.
2. `approve_budget()` creates a platform `ApprovalRequest` of type `budget.approve`; the Budget stays submitted.
3. A decision principal requires `approval.decide` in the platform Approval service.
4. The composition-registered budget handler calls `_apply_approval_decision()` or `_apply_rejection_decision()`.
5. The approval transaction returns `budgets_changed` as its domain result and applies the decision actor from the authenticated principal.

`FinancialChangeService` is a second governed backend path for an already-approved change request. It can atomically supersede the current approved budget and create an approved successor revision with adjusted lines. It is not a direct Project edit.

## 16. Meaning of Approved Budget

The exact rule is:

> The sum of all `BudgetLine.amount` values belonging to the one `ProjectBudget` for the same tenant, organization, and project whose status is exactly `approved`.

It is not a Project field, header total, Financial Profile value, latest revision regardless of status, planned-cost snapshot, schedule baseline, funding amount, or cached summary. Database uniqueness prevents selection ambiguity by allowing at most one approved row per project.

## 17. Currency Semantics

Canonical ownership is split correctly in the Finance domain but incorrectly combined in the Projects projection:

- `ProjectFinancialProfile.currency_code` is project Finance configuration.
- `ProjectBudget.currency_code` is immutable after budget creation.
- Every `BudgetLine.currency_code` must equal its parent Budget currency.
- Amounts are serialized without float conversion through `canonical_decimal_text()`.
- Labels use ISO minor units through `CurrencyCode` and `format_money()`.
- No FX conversion is performed by the Project catalog.

Current defect: `SqlAlchemyProjectCatalogReader` selects the approved amount but not the approved Budget currency. `serialize_project()` formats that amount using `ProjectFinancialProfile.currency_code`. `BudgetService.create_budget()` accepts an explicit currency different from the profile, and `FinancialConfigurationService.configure_profile()` can change profile currency without checking existing budget facts. The current catalog can therefore mislabel an approved amount with the wrong currency.

The authoritative display currency for the existing approved amount must be `ProjectBudget.currency_code`, unless a future explicit conversion contract returns both source and display currency plus rate evidence.

## 18. Governance / Authorization

Budget reads require global and project-scoped `finance.read`. Budget planning requires `budget.manage`. Direct decisions require `budget.approve`; governed requests and decisions use `approval.request` and `approval.decide`. Every service mutation records a fail-closed, high-severity, `financial` audit entry.

Critical query-policy defect: `ProjectQueryMixin.query_catalog_page()` requires only `project.read`, while its Reader always selects Approved Budget and Financial Profile currency. The Viewer and Resource Manager role sets demonstrate that `project.read` does not imply `finance.read`. The Projects catalog can therefore disclose Finance data to a principal who cannot use `BudgetService.get_approved_budget()`.

A normal Project editor cannot legitimately set Approved Budget. Project editing and budget authorization use different permissions, workflows, audit semantics, and aggregate owners.

## 19. Concurrency

Protection is layered:

- `Project.version` protects Project edits only.
- `ProjectBudget.revision` identifies the immutable business revision.
- `ProjectBudget.row_version` maps to ORM `version` and protects header, line-driven aggregate, submit, approve, reject, close, and delete operations.
- `BudgetLine.row_version` protects individual line updates/deletes.
- Adding/updating/deleting a line also advances the parent Budget row version, preventing submit-versus-line races.
- Partial unique indexes protect one open and one approved revision under concurrent transactions.
- Approval translates unique-index collisions to `PROJECT_BUDGET_APPROVAL_CONFLICT`.

Direct Project editing of Approved Budget would bypass every Budget-specific protection above.

## 20. Project <-> Finance Boundary

The actual relationship is:

```text
Project aggregate
  -> ProjectFinancialProfile (one finance configuration per project)
  -> ProjectBudget revisions (finance-owned authorization)
      -> BudgetLine amounts
  -> Project catalog CQRS projection (read-only approved total)
```

Projects and Finance are subdomains inside the same `project_management` module package, not separate top-level modules. The CQRS Reader imports PM Finance ORM models directly to build a cross-aggregate read model; this does not introduce a PM-to-Inventory or other module-package dependency. The application boundary is represented by `ProjectCatalogReader` / `ProjectCatalogReadItem` and `budgets_changed`, not by adding Finance state to `Project`.

## 21. Project Read Projection

The Project catalog uses a correlated scalar SQL subquery for approved line sum and a left join for Financial Profile currency. It is a disposable read projection, not a source of truth. It is rebuilt for each catalog query and stores no denormalized amount.

There is no Python N+1 budget lookup. The aggregate is calculated within the one paginated rows query. The status summary and filtered count are separate bounded SQL queries, as expected for pagination.

Defects in this projection are permission policy and currency selection, not amount ownership.

## 22. Project Catalog Query

- Approved Budget selection: correlated `SUM(BudgetLineORM.amount)` restricted to status `approved` and matching tenant/org/project.
- Filtering: project text, status, project name, client name, site, department, manager, and date ranges. No Approved Budget filter exists.
- Sorting: Reader supports `approvedBudgetLabel` as an allowed server key and orders by the numeric aggregate with project ID tie-breaker.
- QML sorting reachability: disabled because the column lacks `sortable: true`.
- Pagination: filtered count is calculated before offset/limit; page normalization re-queries when needed.
- Determinism: `stable_order_by()` appends `ProjectORM.id`.
- Join behavior: Financial Profile is a left join so projects without a profile remain visible.
- Performance: no N+1; correlated aggregate cost should be validated with PostgreSQL query plans at scale. Existing budget project/status and line budget indexes support the path, but there is no recorded scale-plan test.

The amount is not inherently always null or zero. Once a backend-created Budget reaches `approved`, the catalog SQL can populate it. The desktop app currently lacks the write workflow that would create such data.

## 23. Project Inspector

The inspector displays Client, Site, Department, Start, Finish, Approved Budget, and Contact. It reads the already-loaded catalog row's `state.approvedBudgetLabel`; it performs no extra query. Therefore its value matches the table exactly, including the catalog's current Finance authorization and currency defects.

It does not display budget status, revision, approved actor/time, variance, commitments, actuals, forecast, or full Financial Profile.

## 24. Project Detail

The Project Overview section displays Budget and Currency. Its data path differs from the inspector: `activateProject()` calls `build_project_detail_state()`, which calls `ProjectManagementProjectsDesktopApi.get_project()`.

`get_project()` serializes the Project without passing `approved_budget` or `financial_currency_code`, so serializer defaults produce `approvedBudgetLabel = "Not set"` and empty currency. A project with a real approved budget can therefore show the correct catalog/inspector value and an incorrect full-detail value. This is a confirmed read-model integration defect.

The prior Project-detail Financials section was correctly removed because it duplicated these two facts and otherwise only directed users elsewhere. This audit does not reopen that IA decision.

## 25. Current Finance Budget UI

Route: `project_management.financials`. The canonical PM shell currently reaches `FinancialsWorkspacePage.qml`, which includes an explicit Project selector and grouped sections.

Current budget UI:

- `FinancialsBudgetVersionsSection.qml` displays version/status/total/approval metadata.
- `FinancialsBudgetLinesSection.qml` displays paginated line facts.
- `ProjectFinanceWorkspaceQuery.get()` reads Finance Profile, budget versions, and lines.
- `serialize_finance_configuration_workspace()` exposes revision, status, total, line count, row version, currency, approved actor, and approved time.

Current command UI:

- `FinancialsDialogHost.qml` contains only Manual Actual and Actual Lifecycle dialogs.
- `FinancialsMutationMixin` exposes actual-entry and export mutations, not budget mutations.
- `ProjectManagementFinancialsDesktopApi` has no BudgetService dependency, budget commands, or create/edit/submit/approve methods.
- Budget section contextual actions are empty.

Therefore a desktop user cannot currently set or approve a Project budget through Finance. The valid backend service exists but has no desktop/QML adapter.

## 26. Approved Budget Column Truthfulness

Classification: **TRUTHFUL BUT CURRENTLY UNPOPULATED THROUGH THE DESKTOP UI**, with three integration qualifications.

The name and amount derivation are truthful when data is valid: only the currently approved budget's lines contribute. It is not legacy or placeholder data. However:

1. Desktop users cannot create the underlying approved budget.
2. The amount may be labeled with the wrong currency.
3. The value is exposed without `finance.read` and can remain stale after budget events.

The full Project detail is separately derived incorrectly because it never loads the Finance facts.

## 27. Estimated vs Planned vs Approved Budget

The current domain distinguishes several concepts:

| Concept | Current source | Approval meaning |
|---|---|---|
| Initial estimate/request | No dedicated model or field | Not implemented. |
| Planned labor cost | `ProjectPlannedCostVersion` + lines | Computed current snapshot; explicitly not approved. |
| Approved Budget | `ProjectBudget` + lines | Governed authorization. |
| Cost baseline | Scheduling/control baseline and EVM facts | Distinct from budget authority. |
| Forecast / ETC / EAC | Versioned `ProjectForecast` | Estimate, not authorization. |
| Funding envelope | Only `ProjectFinancialProfile.is_funded` Boolean | No amount currently modeled. |

The removed `Project.planned_budget` must not be reintroduced as Approved Budget. If an initial estimate is desired, it needs an explicit product name, owner, lifecycle, and conversion rule into a draft budget.

## 28. Project Create Implications

Project Create should not accept `Approved Budget`. The current transaction correctly creates Project plus Financial Profile only. Creating an approved amount at the same time would skip lines, cost-code/WBS classification, submit/review, approval actor/time, and Budget revision evidence.

A future optional Create field is viable only as a distinct concept such as `Initial budget request` or `Preliminary estimate`. No such canonical domain concept currently exists, so adding it now would create ambiguity and likely another source of truth.

## 29. Project Edit Implications

Project Edit should not directly change any approved financial amount. Direct editing would:

- bypass `budget.manage`, `budget.approve`, and governed approval permissions;
- mutate an approved authorization that the domain makes immutable;
- create disagreement between Project and Finance;
- bypass fail-closed financial audit records;
- bypass Budget and line optimistic concurrency;
- bypass revision and supersession history;
- potentially invalidate cost-code/task line reconciliation.

Finance configuration changes also belong to `FinancialConfigurationService`, not Project update. The current Project Edit omission is correct.

## 30. Available Budget Metadata

The backend already exposes or can derive:

- Budget ID, name, status, business revision, row version, and currency
- Line count and total amount
- Submitted actor/time and notes
- Approved actor/time and notes
- Rejected actor/time and notes
- Superseded actor/time
- Closed actor/time and notes
- Cost-code, task/WBS, description, and amount per line
- Finance snapshot Approved Budget ID/revision
- Posted actual, commitments, approved forecast, ETC, EAC, VAC, and budget utilization/variance facts

Projects currently consumes only amount and profile currency. Finance already reads richer lifecycle metadata. This report does not authorize adding that metadata to Project QML.

## 31. Events / Refresh / Invalidation

Every successful BudgetService mutation emits `domain_events.budgets_changed(project_id)`. The shared event hub bridges it to a `DomainChangeEvent` with entity type `project_budget`. Governed Financial Change application emits `budgets_changed` when it creates an approved successor.

`FinancialsRefreshMixin` subscribes to `project_budget`, so an active Finance workspace requests a refresh. `bind_project_domain_events()` subscribes Projects only to `project` and `portfolio_entity`; it does not subscribe to `project_budget`.

Result: the Projects table and inspector can remain stale after budget create/line/lifecycle changes until manual refresh, navigation reload, or another subscribed event. The full detail remains wrong even after refresh because its single-project API omits Finance facts.

No durable cache or materialized read model must be invalidated; the issue is controller refresh subscription and consistent query use.

## 32. Archive / Replacement / Revocation Behavior

| Scenario | Actual behavior in Projects projection |
|---|---|
| Approved budget archived | No archive operation/status exists. |
| Approval revoked | No revoke transition exists. Approved can be closed or superseded. |
| Approved budget closed | No row remains in `approved`; projection becomes `NULL` -> `Not set` after refresh. |
| Replacement approved | Previous approved becomes `superseded`; successor becomes sole approved; projection switches atomically after refresh. |
| Draft deleted | No effect on Approved Budget. |
| Submitted/approved/rejected/superseded/closed deleted | Service rejects deletion; only Draft is deletable. |
| Project deleted | Scoped DB cascades delete Finance Profile, budgets, and lines. |
| Financial Profile currency changed | Approved amount is unchanged, but current catalog may relabel it with the new profile currency. This is a defect. |

Whether a closed project budget should display `Not set` or the last historical authorized amount is a product decision; current semantics are `Not set` because only status `approved` qualifies.

## 33. Tenant / Organization Scope

Budget service reads/writes require active tenant and organization context plus global and project-scoped permission checks. `SqlAlchemyProjectBudgetRepository` rejects entity scope mismatches and filters every direct budget/line access by tenant and organization. Composite FKs enforce tenant/org/project consistency at the database layer.

The Project catalog Reader correlates budgets to Project using tenant, organization, and project, and starts from a Project page already restricted to the active tenant/org and authorized project IDs. A cross-tenant or cross-organization budget cannot satisfy that projection.

Both Finance tables declare `rls_scope: tenant_organization`. The fresh Alembic baseline classifies `project_finance_budgets` and `project_finance_budget_lines` in `TENANT_AND_ORGANIZATION_TABLES`, and `enable_baseline_rls()` is called after schema creation. PostgreSQL RLS is therefore part of fresh-schema installation in addition to application predicates and scoped FKs.

## 34. Current Test Coverage

Strong existing coverage:

- Budget domain transitions and terminal states
- Create, line add/update/delete, submit, approve, reject, close, and draft delete
- Empty-budget rejection and immutable submitted/approved data
- Header/line/aggregate stale writes and race cases
- One-open and one-approved uniqueness/conflict translation
- Direct and governed approval permissions and decision actor
- Audit-oriented lifecycle behavior
- Cross-organization cost-code/task/reference guards
- Repository tenant/organization isolation
- Canonical Finance snapshot reconciliation with approved budget/forecast/actual
- Project desktop serializer null label
- Presenter mapping of a synthetic approved amount
- Project server pagination/sorting for ordinary project keys
- Finance read sections and Project selector
- PM domain-event refresh behavior for other capabilities

Important gaps:

- No database-backed Project catalog test proves an approved budget total reaches `ProjectCatalogReadItem`.
- No ascending/descending cross-page test for `approvedBudgetLabel`.
- No test detects that the QML column lacks `sortable: true`.
- No test asserts `finance.read` redaction/denial in Project catalog.
- No test covers approved Budget currency differing from Financial Profile currency.
- No test proves single-project detail returns the same budget facts as catalog.
- No Projects event test expects `project_budget` to refresh the catalog.
- No Finance desktop/controller/QML tests exist for budget commands because those adapters do not exist.
- No QML test explicitly asserts Approved Budget is absent from Project Create/Edit for governance reasons.
- PostgreSQL query-plan/scale coverage for the correlated aggregate is absent.

Verification on 2026-08-20 with Conda environment `pmenv`:

- Final approved-budget targeted suite: `88 passed` in 62.35 seconds.
- Fresh-baseline migration/domain regression: `32 passed` in 34.81 seconds.
- The stale budget migration test was rewritten to upgrade the fresh single baseline at `head`, use the current Project schema, create its own tenant/organization fixture rows, and downgrade to `base`.
- All direct Alembic test callers now use only `head` and `base`; deleted pre-squash revision IDs and historical backfill assumptions were removed. Fresh-schema tests preserve current constraints, triggers, scoped relationships, explicit milestone state, and clean downgrade/re-upgrade behavior.
- Baseline lifecycle tests now assert the canonical `ValidationError` contract and strict rejection of negative duration/cost rather than obsolete `ValueError` and silent-clamping behavior.
- Three Platform event tests now activate their intentionally lazy workspaces before asserting domain-event refresh, consistent with `test_secondary_workspace_lazy_loading.py`.

## 35. Exact READ Trace

```text
project_finance_budgets(status='approved', currency_code, tenant/org/project)
  + project_finance_budget_lines(amount Numeric(19,4), same scope)
  -> SqlAlchemyProjectCatalogReader.read_page()
     correlated SUM(BudgetLineORM.amount), no COALESCE
  -> ProjectCatalogReadItem.approved_budget: Decimal | None
  -> ProjectQueryMixin.query_catalog_page()
  -> ProjectManagementProjectsDesktopApi.list_project_page()
  -> serialize_project()
     canonical_decimal_text()
     format_budget(amount, currently profile currency)
  -> ProjectDesktopDto.approved_budget / approved_budget_label
  -> ProjectProjectsWorkspacePresenter + project_mapper.build_project_state()
  -> ProjectsWorkspaceController.projectsTableModel
  -> ProjectsListPage.projectsTable
  -> ProjectsColumnConfig key approvedBudgetLabel
  -> Approved Budget cell
```

Inspector branch:

```text
same loaded catalog row -> ProjectsWorkspacePage._inspectorItem
  -> state.approvedBudgetLabel -> Approved Budget inspector field
```

Detail defect branch:

```text
activateProject()
  -> build_project_detail_state()
  -> ProjectManagementProjectsDesktopApi.get_project()
  -> serialize_project(project) with default approved_budget=None/currency=''
  -> ProjectsOverviewSection -> Not set / no currency
```

## 36. Exact WRITE Trace

Canonical backend lifecycle:

```text
BudgetService.create_budget(project_id, name, currency)
  -> ProjectBudget revision N, status Draft
  -> SqlAlchemyProjectBudgetRepository.add()
  -> project_finance_budgets

BudgetService.add_line/update_line/delete_line(... expected versions ...)
  -> BudgetLine amounts + parent Budget row_version advance
  -> project_finance_budget_lines / project_finance_budgets.version

BudgetService.submit_budget(...)
  -> Draft -> Submitted, frozen

BudgetService.approve_budget(...)
  -> direct budget.approve
     OR approval.request -> ApprovalService -> approval.decide handler
  -> previous Approved -> Superseded, candidate Submitted -> Approved
  -> commit + fail-closed audit + budgets_changed(project_id)

next Project catalog refresh
  -> SUM(lines for sole status='approved' Budget)
  -> Approved Budget
```

Current desktop reachability:

```text
Finance QML Budget Versions / Budget Lines
  -> READ ONLY
  -> no budget dialog
  -> no controller mutation
  -> no desktop budget command/API
  -X-> BudgetService create/edit/submit/approve
```

Governed successor path:

```text
approved FinancialChangeRequest with Budget impacts
  -> FinancialChangeService._apply_budget_successor()
  -> old Approved -> Superseded
  -> new submitted+approved ProjectBudget revision and copied/adjusted lines
  -> audit + budgets_changed
  -> same Project catalog projection
```

## 37. Field Coverage Matrix

| Concept / field | Project ORM | Project domain | Project create DTO | Project update DTO | Budget ORM | Budget domain | Budget commands/services | Project read model | Projects table | Project Editor | Finance UI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Approved budget | No | No | No | No | Derived from approved header + lines | Derived | Approve lifecycle | `approved_budget` | `approvedBudgetLabel` | No | Read-only total |
| Budget total | No | No | No | No | No header total; line `amount` | Sum of lines | Line mutations | Aggregate Decimal | Preformatted | No | Version total shown |
| Currency | No | No | Profile currency on create | No | Header and line `currency_code` | Immutable Budget currency | Create only; lines must match | Profile currency currently | Embedded label | Create-only Profile currency | Profile/Budget/line shown |
| Budget status | No | No | No | No | `status` | Six-state lifecycle | Submit/approve/reject/close | Not in Project item | No | No | Yes |
| Budget version | No | No | No | No | `revision`, `version` | `revision`, `row_version` | Expected versions required | Not in Project item | No | No | Yes |
| Financial profile | Separate table | Separate aggregate | Currency creates profile | No | `project_finance_profiles` | `ProjectFinancialProfile` | Configuration service | Currency joined | Currency only in state/detail | Currency on create | Profile section |
| Planned cost | No | No | No | No | Separate version/line tables | Computed snapshot | PlannedCostService | No | No | No | Read-only section |
| Forecast/EAC | No | No | No | No | Separate version/line tables | Forecast aggregate | Forecast services | No | No | No | Read-only/analytics facts |

There are no desktop Budget command DTOs in the current Finance API. The matrix's Budget command column refers to application service methods.

## 38. Actual Gap Classification

| Code | Applies? | Finding |
|---|---:|---|
| A. QML-only omission | No for Project editor; Yes for Finance workflow | Project omission is correct; Finance lacks command UI. |
| B. Desktop DTO omission | Yes | Finance desktop API has no Budget command DTOs; single-Project DTO hydration omits Finance facts. |
| C. Command/application omission | Partial | Application service exists; desktop command/application adapter does not. |
| D. Repository persistence omission | No | Canonical Budget persistence is complete. |
| E. Project domain omission | Intentional | Project must not own Approved Budget. |
| F. Finance workflow owns field intentionally | Yes, primary classification | Canonical ownership. |
| G. Finance UI omission | Yes, primary product gap | Read-only Budget sections. |
| H. Projection/read-model defect | Yes | Detail hydration and currency source are wrong. |
| I. Naming problem | No for Approved Budget | Label matches approved-line sum; `Not set` wording may be refined. |
| J. Product-model ambiguity | Yes | Initial estimate/request and closed-budget display have no decision/model. |
| K. Synchronization/invalidation defect | Yes | Projects does not subscribe to `project_budget`. |

Additional critical classification: authorization leakage in the Project catalog because `project.read` currently exposes `finance.read` facts.

## 39. Design Option A

**Direct Project field: REJECT.**

This is domain-incorrect and has the highest duplicate-source risk. It would require either mirroring Finance truth into Project or bypassing the Budget aggregate. It conflicts with approval, audit, revision history, line classification, optimistic concurrency, and permissions. Lower UI complexity does not justify corrupting ownership.

## 40. Design Option B

**Initial/Estimated Budget in Project editor: DEFER pending a product model.**

This could improve project intake only if it is explicitly not Approved Budget. It needs a named concept, owner, permissions, persistence, lifecycle, and a rule for creating or comparing a draft ProjectBudget. The current domain has no such field. Reusing `planned_budget` or silently creating an approved budget is unacceptable.

## 41. Design Option C

**Approved Budget read-only in Projects plus Manage Budget navigation: APPROVE.**

This preserves one source of truth, makes Projects informative, and routes authorized users to the canonical Finance workspace with explicit project context. It has low duplicate-source risk and aligns with the approved PM-local navigation model. The action must be deny-safe and available only when the principal has the required Finance capability.

Option C alone does not solve the missing Finance write workflow; it needs the narrow command rollout in Option D at the authoritative destination.

## 42. Design Option D

**Governed Budget workflow in Finance, reachable from Projects: APPROVE as the implementation target.**

Implement Budget command DTOs and methods in the Finance desktop API, controller capability state, contextual actions, and Finance-local dialogs for draft header/lines, submit, approve/request approval, reject, close, and draft delete. These must call `BudgetService`; no QML-side status mutation or Project write is allowed.

The Project-side action should navigate to Finance and pin the selected project. An inline Project dialog is not recommended initially because it duplicates a substantial Finance workflow and its concurrency state. A future launcher dialog is acceptable only if it remains an adapter to the same BudgetService and lifecycle.

## 43. Recommended Design Direction

Adopt **Option C + authoritative Option D**:

1. Keep Approved Budget read-only in Projects.
2. Do not add Approved Budget to Project Create or Edit.
3. Correct authorization, currency, detail-query, and invalidation defects first.
4. Add a deny-safe `Manage Budget` action that opens Finance with explicit project context.
5. Build the budget lifecycle UI in Finance against `BudgetService` and platform ApprovalService.
6. Keep the Approved Budget column, but hide/redact it without Finance read authority.
7. Add Budget status near the Finance workflow, not automatically to the Projects catalog until product approves it.
8. Treat a future initial estimate as a separate product/domain feature.

This is the lowest-risk enterprise SaaS design because it preserves authorization evidence, auditability, concurrency, and a single financial source of truth.

## 44. Backend Corrections Required Before UI

Priority order:

1. **Critical: enforce Finance read policy in the Project catalog.** Decide whether `finance.read` gates the entire field or whether a new `finance.read_summary` permission is required. Query and DTO must redact/omit, and QML must hide deny-safe.
2. **High: select and serialize the approved Budget's currency.** Do not label its amount with mutable Financial Profile currency. Define and enforce the supported single-currency invariant or an explicit conversion contract.
3. **High: make single-project detail use a scoped read model that hydrates the same authorized Approved Budget and currency facts as catalog.** Do not add a Python list-and-filter path.
4. **High: subscribe Projects to `project_budget` events.** Preserve queued refresh behavior while busy/loading.
5. **Medium: add `sortable: true` to the Approved Budget column only if product wants exposed sorting; backend server sorting already exists.** Add cross-page tests.
6. **Medium: introduce Finance desktop Budget command DTO/API/controller adapters with capability presentation and expected-version fields.** The application service remains the sole writer.
7. **Medium: add a live PostgreSQL migration/RLS test for Approved Budget.** Fresh-baseline SQLite coverage is current, but it cannot prove PostgreSQL policy creation, forced RLS behavior, or cross-scope denial under database roles.
8. **Test gates:** add permission, currency mismatch, catalog/detail parity, event refresh, real approved-total projection, lifecycle adapter, and QML capability tests before UI rollout.

No Project ORM column, Project domain field, or Project repository write is required.

## 45. Final Decision Questions

1. Should users with `project.read` but without `finance.read` see no column, a redacted value, or a newly authorized summary through `finance.read_summary`? Recommended default: hide the column and value unless explicitly authorized.
2. Is Project Finance strictly single-currency per project? Recommended default: yes; Budget currency must equal Financial Profile currency, and profile currency becomes immutable after financial facts exist.
3. Should closing an approved budget make Projects show `Not set`, or should Projects show the last closed authorized amount with status? Current behavior is `Not set`; this requires product confirmation.
4. Is an initial `Estimated Budget` or `Budget Request` needed during Project Create? If yes, define it as a separate intake concept rather than Approved Budget.
5. Should `Manage Budget` be shown in Project inspector, Project Overview contextual actions, or both? Recommended initial location: Overview contextual action plus Finance navigation, capability-gated.
6. Should Approved Budget be user-sortable in Projects? Backend support exists, but current QML disables it.
7. Which roles may create/submit versus approve budgets in the first desktop rollout? Existing permission split is `budget.manage`, `budget.approve`, `approval.request`, and `approval.decide`.

Until these decisions and backend corrections are resolved, no Approved Budget input should be added to `ProjectEditorDialog.qml`.

## 46. Implementation Decision - R4.2 Read Correctness Patch

Status: **implemented and closed**. This is a read-only correctness and security
follow-up to the closed R4.2 Projects redesign. It does not begin Finance budget
management, R4.5, R5, or R6.

### Ownership and write boundary

- Approved Budget remains owned by Finance as the sum of `BudgetLine.amount`
  for the one `ProjectBudget` whose current status is `approved`.
- Project domain, Project ORM, Project repository writes, Project create/update
  commands, and `ProjectEditorDialog.qml` remain free of Approved Budget and
  `planned_budget` fields.
- The Projects capability consumes this value only through an immutable CQRS
  read projection. No second financial source of truth was introduced.

### Authorization decision

- The existing `finance.read` permission governs the Approved Budget fact.
- `project.read` plus authorized `finance.read` returns the amount and its
  approved Budget currency.
- `project.read` without `finance.read` returns `approved_budget=None`, an empty
  approved-budget currency and label, and `approved_budget_visible=False` at
  the read/desktop DTO boundary.
- Project-scoped Finance grants are applied per row. A principal may see an
  authorized project's amount while another visible project's amount remains
  redacted.
- QML removes the catalog column when no Finance access is available and hides
  the Inspector and Overview budget surfaces from redacted project rows. QML
  never receives a hidden amount and is not the security boundary.

### Projection correctness and parity

- The SQL reader obtains the approved amount and `ProjectBudget.currency_code`
  under the same tenant, organization, project, approved-status, and Finance
  scope predicates.
- Financial Profile currency remains a separate configuration fact; it is no
  longer used to label Approved Budget.
- `ProjectCatalogReader.read_one()` provides a bounded single-project SQL read.
  `ProjectManagementProjectsDesktopApi.get_project()` uses it instead of
  list-then-filter or a Finance-service N+1 call.
- Catalog, Inspector and Project detail now share the same amount, currency and
  authorization visibility semantics.
- If no budget is currently approved, authorized readers see
  `No approved budget`; closed and superseded amounts are not presented as
  current authorization and absence is not rendered as zero.

### Invalidation and sorting

- Projects now subscribes to `project_budget` domain changes through its
  existing domain-event invalidation path. Existing busy/loading queuing,
  selected-project state, lazy loading and tenant/organization context behavior
  are preserved.
- The Approved Budget column declares `sortable: true` and remains server-owned.
  SQL orders by the Numeric/Decimal aggregate, not formatted text, with the
  existing ascending project-ID tie-breaker for deterministic pagination.
- Null/currently-unapproved rows remain null facts; no client-side money sort
  was added.

### Verification

Focused regression coverage proves:

- real database-backed multi-line sums;
- approved Budget currency differing from Financial Profile currency;
- authorized catalog, Inspector and detail parity;
- deny-safe catalog DTO, detail DTO, presenter state and QML behavior;
- project-scoped Finance authorization and project correlation;
- tenant and organization isolation on the bounded detail reader;
- no-approved, approved, superseded, closed and successor-approved lifecycle
  projection behavior;
- ascending/descending numeric sorting across pages, null rows, and stable
  equal-value project-ID ordering;
- `project_budget` refresh plus queued refresh while busy;
- unchanged Project write models and editor inputs;
- constant query budgets, shared Portfolio-reader compatibility, QML route
  loading, and CQRS reader architecture guardrails.

### Explicit deferral and next stage

No Budget create/edit/line, submit, approve, reject, close, successor, Manage
Budget, initial estimate, or Budget Request UI was added. Those workflows remain
R6 Finance scope. No Gantt work was included in this patch.

### Exit gate

| # | Gate | Result |
|---:|---|---|
| 1 | Approved Budget absent from Project domain | PASS |
| 2 | Approved Budget absent from Project ORM | PASS |
| 3 | Approved Budget absent from Project Create | PASS |
| 4 | Approved Budget absent from Project Edit | PASS |
| 5 | `finance.read` protects the fact | PASS |
| 6 | `project.read` alone does not disclose totals | PASS |
| 7 | QML does not leak unauthorized values | PASS |
| 8 | Currency comes from approved `ProjectBudget` | PASS |
| 9 | Catalog amount/currency pair is authoritative | PASS |
| 10 | Single-project detail matches catalog | PASS |
| 11 | Inspector matches catalog | PASS |
| 12 | No Python N+1 introduced | PASS |
| 13 | `project_budget` refreshes Projects | PASS |
| 14 | Busy/loading queued refresh preserved | PASS |
| 15 | Approved Budget sorting reachable in QML | PASS |
| 16 | Sorting numeric and server-side | PASS |
| 17 | Null/currently-unapproved wording truthful | PASS |
| 18 | Tenant isolation preserved | PASS |
| 19 | Organization isolation preserved | PASS |
| 20 | Relevant backend tests pass | PASS |
| 21 | Relevant QML tests pass | PASS |
| 22 | Relevant architecture guardrails pass | PASS |
| 23 | No Finance Budget write UI started | PASS |
| 24 | No Manage Budget action added | PASS |
| 25 | No Initial/Estimated Budget feature added | PASS |
| 26 | No R4.5 work started | PASS |
| 27 | No R5/R6 work started | PASS |
| 28 | No assistant commit | PASS; external team commit `cfd1ff4f` landed during validation |

Approved sequence after this closure:

`R4.2 Approved Budget correctness patch -> CLOSED -> R4.5 Gantt modernization`
