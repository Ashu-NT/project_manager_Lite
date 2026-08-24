# R5B Resource Catalog Read Architecture

## 1. Status

R5B implementation and targeted validation are complete as of 2026-08-24. The Resource catalog, Inspector, and Resource summary/detail foundation now use independently authorized, tenant- and organization-scoped scalar readers. R5C, R5D, R5E, Review Queue, and Finance work were not started.

All 63 technical exit-gate conditions pass. Gate 63 is interpreted as "the implementing agent did not commit": the user created commits `dde3c85e`, `0303e21f`, and `c5e7c703` during the work; the agent did not create, amend, or rewrite a commit.

Validation summary:

- Targeted R5B/Resource compatibility suite: 27 passed, 22 deselected.
- R5B architecture/runtime file: 15 passed, including all five required viewports and an additional compact viewport.
- Performance/query-plan suite: 6 passed.
- Targeted `qmllint`: exit 0 with no diagnostics.
- Python compilation and final diff checks are recorded in the final execution report.

## 2. Scope

R5B owns only the Resource read side and Resource catalog/Inspector/detail-shell presentation:

- immutable catalog, Inspector, and summary facts;
- scoped SQL readers and query-service authorization;
- typed desktop DTOs;
- controller-owned catalog query state and selected Resource ID;
- ID-driven Inspector and Resource summary;
- responsive catalog/Inspector presentation;
- authoritative Overview and truthful lazy placeholders for later sections.

Resource master writes, ResourceKind, capability writes, capacity authority, full Projects/Assignments/Activity readers, Review Queue, and Finance are outside R5B.

## 3. R5A Decisions Applied

- Resource remains a tenant- and organization-owned provider of schedulable PM delivery capacity.
- No `PERSON`/`CREW`/`EQUIPMENT` classification is inferred before R5C.
- The UX is Catalog -> lightweight Inspector -> Open Resource -> canonical detail.
- Detail navigation is exactly Overview, Capability, Availability, Projects, Assignments, Activity.
- The shared server-mode `DataTable` remains the catalog surface.
- Reader contracts are not repositories and return immutable scalar facts.
- Resource detail is ID-driven and never hydrated from a current-page row.
- No new utilization, capability, certification, conflict, or workload truth was invented.

## 4. Final Catalog Read Flow

```text
ResourcesWorkspacePage.qml
  -> ProjectManagementResourcesWorkspaceController
  -> ResourcesWorkspacePresenter
  -> ProjectManagementResourcesDesktopApi.list_resource_page
  -> ResourceQueryMixin.query_catalog_page
  -> SqlAlchemyResourceCatalogReader.read_page
  -> scoped SQL summary/count/page projections
  -> ResourceCatalogReadPage[ResourceCatalogReadItem]
  -> ResourceCatalogPageDesktopDto
  -> ResourceRecordViewModel/QAbstractListModel
  -> shared DataTable (one server page)
```

The read path performs no aggregate repository hydration, Python sorting/filtering, or per-row lookup.

## 5. Immutable Catalog Fact

`ResourceCatalogReadItem` is `@dataclass(frozen=True, slots=True)` and contains only scalar/value facts: Resource ID/code/name/role, worker and cost types, active state, capacity modifier, organization/department/site/employee identifiers and labels, and version. It embeds neither the mutable `Resource` aggregate nor an ORM instance or mutable collection.

`ResourceCatalogReadPage` carries an immutable item tuple, filtered count, page state, scope summary, and normalized `ReadSort`. `ResourceCatalogItemDesktopDto` is the typed desktop transport projection.

## 6. Search/Filter/Sort Contract

Search is case-insensitive and limited to operational fields: Resource code, Resource name, and role. Contact, address, phone, email, employee PII, department, and site are not broad-search inputs.

Current explicit filters are active status and cost category. Tenant and organization are mandatory implicit scope, not optional client filters. Department, site, and worker-type filters are not claimed as implemented. Search/filter/page-size/sort changes reset page to 1; no page-local filter exists.

Allowed server sort keys are `title`, `resourceCode`, `statusLabel`, `department`, `site`, `role`, `workerTypeLabel`, and `capacityPercent`. `catalog` is the default active-first/name ordering. Unsupported keys fail safely to the documented default. Every ordering has Resource ID as deterministic tie-breaker.

## 7. Count Semantics

- `total` is the entire active tenant/organization Resource scope before search, active, or category filters.
- `filtered_total` is the count after all current catalog filters/search and is the pagination authority.
- `active`, `employees`, `external`, and `average_capacity` are scope-wide overview values, not filtered-page metrics.
- `items` contains only the requested bounded page.

These meanings are preserved through `ResourceCatalogPageDesktopDto` and presenter/controller serialization.

## 8. Selection Authority

`ProjectManagementResourcesWorkspaceController.selectedResourceId` is the single contextual selection authority. Initial selection is empty and no first-row auto-selection occurs. Selection is O(1) against the current table model and triggers only the Inspector read, never a catalog reload.

Refresh preserves query state and retains/reloads a selected ID only while it remains in the authoritative current result page. Filter/search changes that remove it clear the ID, Inspector, and activated summary safely. Bulk-selection IDs remain a separate table concern and are not detail authority.

## 9. Inspector Architecture

```text
selected Resource ID
  -> controller.loadResourceInspector
  -> presenter.build_resource_inspector
  -> desktop API.get_resource_inspector
  -> ResourceQueryMixin.get_resource_inspector
  -> ResourceInspectorReader.read_inspector
  -> one bounded scoped SQL projection
  -> ResourceInspectorFact -> typed DTO -> Inspector view model
```

The Inspector has independent loading/error state. Monotonic request IDs plus selected-ID comparison prevent a late response for Resource A from overwriting Resource B. Selecting successive rows does not rebuild the catalog.

At workspace widths below `Theme.AppTheme.inspectorWidth + 720`, the Inspector uses a bounded contextual popup. At or above that threshold, it uses a fixed-width side Inspector.

## 10. Inspector Fact

`ResourceInspectorFact` is frozen and slotted. It contains stable identity, role/engagement, active state, capacity modifier, organization/department/site/employee labels, version, and bounded active-project/assignment counts. It carries deny-safe `can_read`, `can_manage`, `can_deactivate`, and `can_reactivate` flags derived after authorization.

It contains no Resource aggregate, ORM object, full Project collection, full Assignment collection, skill list, certification list, workload series, or inferred ResourceKind.

## 11. Resource Summary Architecture

Open Resource passes only the selected Resource ID. `get_resource_summary` independently requires `resource.read`, resolves active tenant/organization IDs, executes a bounded scalar projection, and returns `ResourceSummaryFact`; it does not depend on the catalog page or Inspector DTO.

The typed `ResourceSummaryDesktopDto` and `ResourceDetailViewModel` are built only after this independent read. Tests prove that a Resource not present on catalog page 1 can be opened correctly by ID and that wrong-organization IDs fail as not found.

## 12. Detail Shell

```text
SectionDetailPage
  -> fixed ContextualActionToolbar
  -> section-scoped fixed inline messages
  -> ResourcesDetailPanel
       -> Overview (authoritative summary)
       -> Capability (existing Skills + Certifications reads)
       -> Availability (truthful R5D placeholder)
       -> Projects (truthful R5E placeholder)
       -> Assignments (truthful R5E placeholder)
       -> Activity (truthful R5E placeholder)
```

The header contains stable Resource identity/status and deny-safe actions. Overview uses the independently loaded summary. The shell does not seed fields from a catalog row and does not render pseudo-history or legacy workload formulas.

## 13. Lazy Section Ownership

- Overview: R5B, authoritative Resource summary.
- Capability: existing read presentation retained; write authorization/concurrency/audit hardening belongs to R5D.
- Availability: R5D owns calendar/workload authority reconciliation and the final reader.
- Projects: R5E owns the scoped, paged Resource-to-Projects reader.
- Assignments: R5E owns the scoped, paged Resource-to-Assignments reader.
- Activity: R5E owns authoritative audit/activity history.

Only the active section is instantiated through `LazySectionLoader`. Deferred sections state their ownership and show no fabricated data.

## 14. Permissions

Catalog, Inspector, and summary each independently require `resource.read`; a successful catalog read does not authorize either later read. Management presentation derives from `resource.manage` through the canonical authorization engine and fails closed. Inspector lifecycle flags are state-aware: deactivate only for active Resources, reactivate only for inactive Resources, and both require management permission.

R5B did not relocate RBAC into readers or QML. Readers receive already authorized scope IDs and QML consumes backend-derived capability facts.

## 15. Tenant/Organization Scope

Every new reader call receives explicit active `tenant_id` and `organization_id`. Catalog rows and joined labels are constrained to both scope IDs. Inspector and summary select by Resource ID plus both scope IDs. Wrong-tenant or wrong-organization access returns the same not-found boundary as a missing Resource.

Context changes clear Resource read state and invalidate prior Inspector/detail request generations so old-scope data cannot remain authoritative.

## 16. PII Search Decision

Default catalog search intentionally excludes Resource contact/address and employee email/phone/address. Catalog columns expose operational identity and placement only. The summary contract retains existing contact/address values for current Resource write/detail compatibility, but they are not catalog search inputs or default catalog columns. Any future contact search requires an explicit product requirement, permission decision, and indexed PostgreSQL design.

## 17. DataTable Contract

The Resource catalog retains the shared `DataTable` with `sortingMode: "server"`. `sortKey` and `sortDirection` bind to controller query state; `sortRequested` calls `setResourceSort`. The table receives one page through `resourcesTableModel`; pagination uses `resourcePage`, `resourcePageSize`, and filtered `resourceTotalCount`.

Final columns are Code, Resource, Engagement, Role, Organization (optional/hidden by default), Department, Site (optional/hidden by default), Status, and Capacity Modifier. There is no client-side global-sort/filter illusion and no unbounded Resource payload.

## 18. Responsive Matrix

Offscreen runtime creation and geometry checks passed with no layout-managed-anchor or missing-type messages:

| Viewport | Result | Inspector mode |
|---|---:|---|
| 800 x 640 (additional compact proof) | Pass | Contextual popup |
| 1024 x 640 | Pass | Side Inspector; 736 px catalog minimum is preserved |
| 1280 x 720 | Pass | Side Inspector |
| 1366 x 768 | Pass | Side Inspector |
| 1440 x 900 | Pass | Side Inspector |
| 1920 x 1080 | Pass | Side Inspector |

The breakpoint is based on actual workspace width, never global `Window.width`. `ResourcesListPage` is sized only by its parent `RowLayout`; its former conflicting root anchor was removed.

## 19. SQL Statement Budgets

Measured at the service boundary, including runtime-session scope lease:

- Catalog page: 4 statements (scope lease, scope summary, filtered count, page projection).
- Inspector: 2 statements (scope lease plus one projection with correlated counts).
- Resource summary: 2 statements (scope lease plus one projection).

Counts remain constant as page cardinality grows. There are no employee, department, site, Project, or Assignment per-row queries.

## 20. Query Plans

No PostgreSQL database URL is declared in the current development environment, so PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` evidence was not fabricated. Reproducible SQLite `EXPLAIN QUERY PLAN` coverage records default page, name search, code search, status filter, role sort, and capacity sort.

SQLite uses `idx_resources_tenant` for scoped lookup and a temporary B-tree for each ordered page. This confirms bounded indexed scope lookup but also shows that current expression ordering is not covered by a SQLite index. No speculative cross-database index was added. Before production, R5G/deployment validation must run the actual PostgreSQL projections, compare organization/tenant composite and functional-index candidates, and add only indexes justified by PostgreSQL plans and measured workload.

## 21. 100/1k/10k Measurements

Warm SQLite development fixture, seven samples per size, page size 25, search plus ascending title sort:

| Resource count | p50 | p95 | Statements | Target |
|---:|---:|---:|---:|---:|
| 100 | 4.14 ms | 8.08 ms | 4 | <= 200 ms / <= 4 |
| 1,000 | 6.78 ms | 12.50 ms | 4 | <= 200 ms / <= 4 |
| 10,000 | 40.48 ms | 41.29 ms | 4 | <= 200 ms / <= 4 |

Inspector measured p50 2.20 ms, warm p95 3.60 ms, cold 5.64 ms, and 2 statements. Summary measured p50/p95 1.88 ms and 2 statements. These are local SQLite engineering measurements, not production PostgreSQL latency claims. A 50,000-Resource fixture remains optional R5G evidence.

## 22. Legacy Paths Removed

Removed after reference count reached zero:

- mutable Resource aggregate leakage from `ResourceCatalogReadItem`;
- page-row seeded selected detail/availability state;
- first-row automatic selection;
- service-fan-out availability presenter helper;
- obsolete Capacity, Calendar, Cost Rates, Availability, Assignments, and Activity QML section implementations plus `qmldir` registrations;
- pseudo activity/history and attractive but non-authoritative capacity/utilization presentation;
- stale detail-panel signals and stale workspace view-model fields;
- catalog contact/address PII search.

Existing enterprise availability, assignment, skill/certification, and Resource write services were not deleted: they have real non-R5B consumers or explicit R5C/R5D/R5E ownership.

## 23. Explicit Deferred Scope

- R5C: ResourceKind and all Resource master write/lifecycle/concurrency/transaction/dialog hardening.
- R5D: capability writes and permission/audit/concurrency hardening; capacity/calendar/workload authority reconciliation and authoritative Availability reader.
- R5E: paged Projects and Assignments readers plus authoritative Activity/audit history.
- R5F: Review Queue redesign and workflow/concurrency behavior.
- R5G/deployment: PostgreSQL query-plan/index validation and optional 50,000-row scale evidence.

The retained controller/API availability and assignment paths are temporary handoff surfaces owned by R5D/R5E; they must be replaced or retired when those authoritative sections land. They are not used to manufacture R5B catalog or Overview facts.

## 24. R5C Handoff

R5C starts from the independent Resource summary/detail foundation and owns Resource Master Write UX only:

1. Introduce explicit `ResourceKind` without inferring it from cost type, employee linkage, or worker type.
2. Redesign Create/Edit around the final kind-aware contract.
3. Fix capacity preservation so unrelated edits cannot reset authoritative values.
4. Add scoped deactivate/reactivate lifecycle dialogs and deny-safe actions.
5. Require version on updates/lifecycle commands and surface optimistic conflicts locally.
6. Enforce caller/UoW transaction ownership for touched Resource writes.
7. Validate responsive write dialogs and tenant/organization selectors where the command contract requires them.
8. Remove superseded write compatibility code once references reach zero; no permanent adapter or dead code remains.

R5C must preserve the R5B read facts/readers and Accounting/PM module boundaries, must not redesign Review Queue, and must not replace the scoped SQL catalog with aggregate hydration.
