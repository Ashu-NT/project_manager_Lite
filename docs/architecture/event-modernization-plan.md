# Event Modernization Plan

Living implementation roadmap for converging every capability's mutation-notification path onto
the canonical `DomainEvent` + `ViewInvalidation` pipeline and retiring the legacy `Signal[str]`
fields on `DomainEvents` (`src/core/shared/events/domain_events.py`).

This document tracks **status and sequencing**. It does not restate architectural rationale —
see [ADR-005: Domain Events](../architecture_decisions/ADR-005-domain-events.md) for the
canonical contracts, decision history, and alternatives rejected. See the top-level
[`README.md`](../../README.md#event-architecture) for a one-page developer orientation.

## 1. Objective

- Replace coarse legacy `DomainEvents` `Signal[str]` fields with typed, per-capability
  `DomainEvent`s.
- Converge each capability's mutations onto one canonical `UnitOfWork` (one physical
  transaction, one commit, one `DomainEvent` lifecycle).
- Emit typed business `DomainEvent`s from that UnitOfWork (`uow.record_event(...)` or an
  aggregate that records its own).
- Map each typed event to a scoped `ViewInvalidationHint` (`PlatformScope`/`TenantScope`/
  `OrganizationScope`/`ResourceScope`), never a bare string signal.
- Narrow UI refreshes from "reload the whole workspace" to "reload exactly what went stale."
- Delete each legacy `Signal` once its replacement is live and observably equivalent — no
  compatibility bridge, no alias.
- Reach legacy `Signal` count = 0.

## 2. Canonical Target Architecture

```
Application command/service
    v
Canonical UnitOfWork
    v
repository mutation + audit staging
    v
uow.record_event(...)
    v
transactional DomainEvent handlers        [FAIL_FAST]
    v
database commit
    v
postcommit DomainEvent bus                [ISOLATE_AND_CONTINUE]
    v
ViewInvalidation handler
    v
ViewInvalidationChannel
    v
scoped UI adapter/controller
    v
narrow read-model refresh
```

Full contracts, rationale, and the closed `EventScope`/`ScopeFilter` unions are defined in
ADR-005 §1 (Event Taxonomy), §9 (UnitOfWork Semantics), §12 (View Invalidation). This document
does not duplicate them — read ADR-005 before implementing a phase below.

## 3. Phase Completion Ledger

| Phase | Capability | Transaction ownership | Typed DomainEvents | ViewInvalidation | Legacy Signal status |
|---|---|---|---|---|---|
| P0-P8 | Foundational infrastructure (UnitOfWork/dispatcher/bus/channel contracts, taxonomy, scope model) | N/A - infrastructure only | N/A | N/A | N/A |
| P9-P10D | Organization, Module Entitlements, Role Binding / Scoped Access, Tenant Membership, Approval (5 capabilities) | Canonical, per-capability UnitOfWork | 15 classes: `OrganizationCreated`; `OrganizationProfileUpdated`/`OrganizationEnabled`/`OrganizationDisabled`; `ModuleLicensed`/`ModuleLicenseRevoked`/`ModuleEnabled`/`ModuleDisabled`/`ModuleLifecycleTransitioned`; `RoleBindingAssigned`/`RoleBindingRevoked`; `TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed`; `ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected` | Narrow, scoped adapters (`ScopedViewInvalidationSubscription`-based) | `organizations_changed` deleted (P10D closed the last gap - `update_organization`/`enable`/`disable`) |
| P12 (A/B) | Employee | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `employees_changed` deleted |
| P13 (A/B) | Department | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `departments_changed` deleted |
| P14 (A/B) | Site | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `sites_changed` deleted |
| P15 (A/B) | Party | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `parties_changed` deleted |
| P16 (A/B/C/D, D-FIX) | Document + DocumentStructure + DocumentLink | Canonical `DocumentUnitOfWork` (`.documents`/`.structures`/`.links`, shared by `DocumentService` + `DocumentIntegrationService`) | `DocumentCreated`, `DocumentProfileUpdated`, `DocumentStructureCreated`, `DocumentStructureProfileUpdated`, `DocumentReferenceLinked`, `DocumentReferenceUnlinked` | Narrow, incl. the generic `ResourceScope` `EventScope` kind (P16D-FIX) for DocumentLink's cross-module target identity | `documents_changed` deleted |
| P18 (A/B) | Project Resource (Master + Capability) | Canonical `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` (`.resources`/`.skills`/`.certifications`, shared for the same reason `DocumentUnitOfWork` is) | `ResourceMasterChanged` (CREATED/UPDATED/DEACTIVATED/REACTIVATED/PURGED), `ResourceCapabilityChanged` (ADDED/UPDATED/REMOVED) — existing vocabulary, retained unchanged | Narrow: `resource_list` (`OrganizationScope`) for Master, `resource_capabilities` (`ResourceScope`, exact-resource) for Capability | `resources_changed` deleted |
| P19 (+ P19-FIX) | Finance Forecast | Canonical `FinanceGovernanceUnitOfWork` (already existed) — `ForecastVersionService`/`ForecastGenerationService` gained `record_event` wired to `uow.record_event`; the second, hidden `financial_change.apply` successor producer now reports through a new generic `ApprovalHandlerResult.domain_events` seam, `ApprovalService` recording it on its own real UoW | `ForecastVersionChanged` (CREATED/SUBMITTED/APPROVED/REJECTED/DELETED), `ForecastLineChanged` (ADDED/UPDATED/REMOVED), `ForecastDraftGenerated` | Narrow: `forecast_planning` (project-scoped `ResourceScope`) for everything except approval, `forecast_approved_basis` (same scope kind) for `ForecastVersionChanged(APPROVED)` — P19-FIX corrected APPROVED to notify **both** targets (the version's own status change is visible in `forecast_planning`'s list too), never one alone | `forecasts_changed` deleted |
| P20 | Inventory Storeroom + Storage Location | New canonical `InventoryFoundationUnitOfWork`/`InventoryFoundationUnitOfWorkFactory` (`.storerooms`/`.locations`, `src/core/modules/inventory_procurement/{contracts,infrastructure/persistence}/uow/inventory/inventory_foundation_unit_of_work.py`) — replaced raw `self._session.commit()` mutation in `InventoryService`/`InventoryFoundationService`; also fixed a real pre-existing bug where activity recording was silently dead code (never wired with an `_activity_service`) | `StoreroomCreated`, `StoreroomProfileUpdated`, `StoreroomStatusChanged` (a genuine 4-state DRAFT/ACTIVE/INACTIVE/CLOSED lifecycle, not a boolean); `LocationCreated`, `LocationProfileUpdated` (Location's `is_active` has no derived consequences, so it stays a plain profile field, unlike Site's) | Narrow: `storeroom_list` (`OrganizationScope`) — one target shared by the master list AND the `storeroom_options` reference selector (proven the same underlying projection); `location_list` (`OrganizationScope`) | `inventory_storerooms_changed`/`inventory_locations_changed` both deleted |

**Platform / Shared Master Data is fully modernized** as of P16D-FIX: Organization, Tenant
Membership, Module Entitlements, Role Binding / Scoped Access, Approval, Employee, Department,
Site, Party, Document, DocumentStructure, DocumentLink. Zero Platform-owned legacy `Signal`
fields remain on `DomainEvents`.

**Project Resource is fully modernized** as of P18B.

| Aspect | Status |
|---|---|
| Resource Master transaction ownership | MODERNIZED — canonical `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` (`src/core/modules/project_management/{contracts,infrastructure/persistence}/uow/resources/resource_unit_of_work.py`), fresh `Session` per operation |
| Resource Capability transaction ownership | MODERNIZED — same `ResourceUnitOfWork` (`.skills`/`.certifications` accessors) |
| Resource typed event transport | CANONICALIZED — `ResourceMasterChanged`/`ResourceCapabilityChanged` recorded via `uow.record_event(...)`, dispatched through the shared transactional/post-commit pipeline; the bespoke module-level `Signal[T]` publishers are DELETED |
| Resource audit / activity | ATOMIC — `record_audit_entry(uow, ...)` inside the same transaction as the mutation; activity-feed staging also rides the same fresh UoW `Session` (a real regression found and fixed mid-P18A: activity staged on the old process-lifetime shared session was never committed once the mutation itself moved to a fresh session) |
| No-op discipline | `update_resource`, `update_resource_skill`, `update_resource_certification` produce zero write/audit/event on a true no-op |
| Employee-driven Resource sync | CASE A (real Resource mutation) — `sync_linked_employee_resources` writes real `name`/`role`/`contact` columns atomically inside Employee's own canonical UoW, and now also records a typed `ResourceMasterChanged(UPDATED)` there via a `ResourceMasterEventFactory` Protocol Platform owns and PM's composition satisfies (`build_resource_master_changed_for_employee_sync`, wired only in `platform_registry.py`) — Platform's `employee_service.py` never imports PM's concrete event class |
| Resource ViewInvalidation | MODERNIZED — two targets: `resource_list` (`OrganizationScope`, every `ResourceMasterChanged`) and `resource_capabilities` (`ResourceScope`, exact-resource, every `ResourceCapabilityChanged`); proven from source that list/options projections never embed skill/certification data, so a capability change never triggers a list-scoped refresh |
| UI consumers | CUT OVER — all 8 original consumers re-audited from source (not assumed): the main Resources workspace controller narrows to `refresh()` (list) + `reload_skills_and_certs()`/activity-reload (capability/detail, entity-id-gated to the selected resource); Dashboard/Portfolio/Scheduling/Tasks/`ResourceTimesheetsController`/`TimesheetsWorkspaceController` (review queue) all react to `resource_list` only, via one `ResourceViewInvalidationAdapter` instance each (none had a genuine `resource_capabilities` dependency — proven from their own presenter/query source); Platform's Control workspace subscription was removed entirely with no replacement (no real Resource dependency found) |
| `resources_changed` | DELETED — field, all 3 producers (Resource Master, Resource Capability, Employee sync), and all 8 consumers. Legacy Signal count: 28 (29 → 28, confirmed via source) |

Only one full refresh remains genuinely coarse: the 6 non-Resources-workspace consumers
(Dashboard/Portfolio/Scheduling/Tasks/2x Timesheets) call their own existing `refresh()` on any
Resource Master change rather than a narrower, capability-specific reload — none had an existing
narrower seam, and building one would mean redesigning each of those *other* capabilities' own
presenter/query shape (explicitly out of P18B's scope: "refactor unrelated PM capabilities").
This is still a real improvement over pre-P18B behavior: none of the 6 fire on
`ResourceCapabilityChanged` any more (a skill/certification edit no longer triggers any of their
refreshes at all), and the Resources workspace itself no longer double-reacts (a coarse full
refresh plus a redundant narrow "activity" reload on every event, regardless of relevance) the
way it did before.

**Finance Forecast is fully modernized** as of P19.

| Aspect | Status |
|---|---|
| Forecast transaction ownership | Already canonical (`FinanceGovernanceUnitOfWork`, pre-existing) |
| Forecast typed event transport | CANONICALIZED — `ForecastVersionChanged`/`ForecastLineChanged`/`ForecastDraftGenerated` recorded via `uow.record_event(...)` from `ForecastVersionService`/`ForecastGenerationService` |
| Financial-change-apply forecast successor | CANONICALIZED via a new generic seam — `ApprovalHandlerResult.domain_events`, recorded by `ApprovalService` on its own real `UnitOfWork` before `uow.commit()`; the participant never receives the `UnitOfWork` (ADR-005 §24 invariant preserved) |
| No-op discipline | `update_line` produces zero write/audit/event/synthetic version bump on a true no-op (a real, newly-added guard — not present pre-P19) |
| Forecast ViewInvalidation | MODERNIZED — two project-scoped targets: `forecast_planning` (every fact except approval) and `forecast_approved_basis` (`ForecastVersionChanged(APPROVED)` only) — a real correction over legacy behavior, which invalidated `{overview, planning, performance}` for every event and never invalidated `commercial` at all |
| UI consumers | CUT OVER — the sole consumer (`FinancialsRefreshMixin`'s destination-based model) now reacts via one `ForecastViewInvalidationAdapter` on `ProjectManagementFinancialsWorkspaceController`, filtered by selected project |
| `forecasts_changed` | DELETED — field, both producers, the one consumer. Legacy Signal count: 27 (28 → 27, confirmed via source) |

See ADR-005 §26.16 for the full design (including why the financial-change-apply producer needed
a new generic Approval reporting seam rather than widening `dependencies_factory`).

**Inventory Storeroom + Storage Location is fully modernized** as of P20.

| Aspect | Status |
|---|---|
| Storeroom transaction ownership | MODERNIZED — canonical `InventoryFoundationUnitOfWork`, fresh `Session` per operation (was raw `self._session.commit()`) |
| Storage Location transaction ownership | MODERNIZED — same `InventoryFoundationUnitOfWork` (`.locations` accessor) |
| Typed event transport | CANONICALIZED — `StoreroomCreated`/`StoreroomProfileUpdated`/`StoreroomStatusChanged`/`LocationCreated`/`LocationProfileUpdated` recorded via `uow.record_event(...)` |
| Audit | ADDED — `record_audit_entry(uow, ...)` inside the same transaction (Inventory had no governance audit trail for these two capabilities before; mirrors the canonical pattern already used by this module's own `PurchaseOrderSubmissionUnitOfWork`) |
| Activity | FIXED — `record_activity` was silent dead code pre-P20 (`InventoryService`/`InventoryFoundationService` were never wired with an `_activity_service`); now atomic with the mutation via a fresh, transaction-bound `ActivityService` |
| No-op discipline | `update_storeroom`/`update_storage_location` produce zero write/audit/event/synthetic version bump on a true no-op (real, newly-added guards — not present pre-P20) |
| Cross-org / parent integrity | Audited, no bug found: a Location's `storeroom_id` is immutable after creation (no "move between storerooms" operation exists), a Storeroom must belong to the active organization to be referenced (already enforced pre-P20), parent-location cycles are already rejected. Storeroom status transitions do not cascade to child Locations (no cascade existed pre-P20 either; out of scope to add one) |
| ViewInvalidation | MODERNIZED — two org-scoped targets: `storeroom_list` (every Storeroom fact) and `location_list` (every Location fact); proven from source that `storeroom_list` is the *same* projection backing both the Inventory workspace's master list and the `storeroom_options` selector used by Pricing/Procurement/Reservations — one target, not two |
| UI consumers | CUT OVER — 6 workspaces re-audited from source (not assumed): Inventory (owner, full `refresh()` on either target — no narrower seam exists in its own monolithic `build_workspace_state`), Dashboard (KPI rollup, full `refresh()` on either target — legitimate, no seam), Pricing/Procurement (`storeroom_options` selector only, reuse the existing narrow `refresh_site_options` seam), Reservations (`storeroom_options` selector only, P20 additively extracted a new narrow `refresh_storeroom_options` seam mirroring Pricing/Procurement's), Catalog (zero real dependency — proven no Catalog presenter references Storeroom or Location at all — subscription removed with no replacement) |
| `inventory_storerooms_changed` / `inventory_locations_changed` | DELETED — both fields, all producers, all consumers. Legacy Signal count: 25 (27 → 25, confirmed via source) |
| P21 | Finance Financial Setup | Already canonical `FinanceGovernanceUnitOfWork` — `FinancialConfigurationService` gained `record_event` wired to `uow.record_event`; no new UoW | `ProjectFinancialProfileUpdated`, `ProjectFinancialProfileTransitioned` (project-scoped); `CostCodeCreated`, `CostCodeProfileUpdated`, `CostCodeActivated`, `CostCodeDeactivated` (organization-scoped — `ProjectCostCode` is a global catalog, not project-owned); `ProjectCostCodeRestrictionAdded`, `ProjectCostCodeRestrictionRemoved` (project-scoped join) — 8 events for 8 audited operations | Narrow: `financial_profile` (project-scoped `ResourceScope`) fed only by the two Profile events — proven the *sole* current Financial Setup projection (no destination in the Financials workspace ever caches Cost Code data; every cost-code picker is a live, on-demand query). Cost Code / Restriction events are recorded as canonical typed facts with deliberately zero ViewInvalidation subscription | `financial_setup_changed` deleted |

**Finance Financial Setup is fully modernized** as of P21. A significant re-audit finding: only
`create_cost_code` has a live production caller today (via a direct `commands.financial_setup(...)`
call in the desktop API) — `configure_profile`/`transition_profile`/`update_cost_code`/
`deactivate_cost_code`/`activate_cost_code`/`add_project_cost_code`/`remove_project_cost_code` are
all reachable through the governed `FinanceGovernedServicePort` (registered mutations) but have
zero current UI/API callers. All 8 still received full typed-event coverage (they are real,
complete, governed-surface operations, not dead code to delete), but this explains why P21's
ViewInvalidation retirement changes essentially nothing about today's visible behavior: the legacy
`financial_setup_changed → {planning, costs, controls}` blanket invalidation was already pure
waste for the one live producer (`create_cost_code` — no cost-code list is ever cached anywhere in
the Financials workspace), and the one destination it should invalidate (`controls`, for
`financial_profile`) has no live producer yet either. See ADR-005 §26.18 for the full design.
| P22 | Finance Rate Card | NEW: `FinanceGovernanceUnitOfWork` gained a `rate_cards` named repository accessor (Option A convergence — Rate Card is governed exactly like Budget/Forecast/Setup, same `finance.manage`/`finance.read` permission model, same audit conventions; no separate UoW); `ProjectRateCardService` moved off raw `self._session.commit()` onto `record_event` wired to `uow.record_event`, with the outer `FinanceGovernanceCommandBoundary.rate_card` family now owning commit/rollback | `RateCardCreated`, `RateCardDeactivated` (Rate Card itself has only create+one-way-deactivate — no rename/update, no reactivate); `RateCardLineAdded`, `RateCardLineUpdated`, `RateCardLineDeactivated` | Narrow: `rate_card_list` — `OrganizationScope` for an organization-wide card (`project_id is None`), or a project-keyed `ResourceScope` (`entity_type="project"`) for a project-specific card (P22-FIX; dual-shape, chosen per event's own persisted `project_id`); `rate_card_detail` (exact-card `ResourceScope`) — the selected card's own detail + its lines, proven the same combined projection. `RateCardDeactivated` notifies BOTH (mirroring the P19-FIX dual-notification correction) | `rates_changed` deleted |

**Finance Rate Card is fully modernized** as of P22. Confirmed the *narrowest* Finance capability
audited so far: exactly one producer file, one legacy field, one UI consumer, matching P17's own
characterization. `create_rate_card`/`deactivate_rate_card`/`create_line`/`update_line`/
`deactivate_line` were already comparatively well-guarded (audit already atomic with the mutation,
via `record_audit_entry(..., commit=False)` before the old `self._session.commit()`) — but the
capability had never been added to the canonical `FinanceGovernanceCommandBoundary`/
`FinanceGovernedServicePort` wiring at all (a raw, ungoverned service instance, confirmed from
source), unlike Budget/Forecast/Setup which already routed through it. `update_line` had no no-op
detection (fixed); `deactivate_rate_card`/`deactivate_line` already had correct existence guards.
A dead, never-populated `duplicate_message`/IntegrityError→`ValidationError` conversion path was
removed (confirmed: no unique constraint on Rate Card name exists at the DB level, and no call
site ever passed `duplicate_message` — the conversion never fired; simplification, not a
regression). See ADR-005 §26.19 for the full design.

**P22-FIX**: `rate_card_list`'s original `OrganizationScope`-only scope was corrected to a
dual-shape scope that mirrors the read model's own dual-ownership query
(`SqlAlchemyFinanceRateReader._card_conditions`: `project_id IS NULL OR project_id ==
:project_id`) — an organization-wide card (`project_id is None`) still invalidates
`OrganizationScope`; a project-specific card invalidates only a project-keyed `ResourceScope`
(`entity_type="project"`, `entity_id=project_id`), so a Project A-specific card change no longer
spuriously invalidates Project B's "costs" view. Project identity travels only via the hint's own
`scope`/`entity_id` — never a new field. The UI consumer (`RateCardViewInvalidationAdapter`)
routes the two shapes to distinct signals (`rateCardListStale` for org-wide, unconditional;
`rateCardListStaleForProject` for project-specific, gated by the controller's currently selected
project — mirroring `on_forecast_planning_stale`'s established pattern). See ADR-005 §26.19 for
the full corrected design.

| P23 | PM Baseline Approval | NEW: `SqlAlchemyBaselineUnitOfWork` — `BaselineService`'s Session is the long-lived, process-shared one many other PM services also use (its repositories and its `SchedulingEngine` collaborator are bound to it), never a fresh per-request one, so this UoW variant reuses the canonical transactional-dispatch/postcommit-publish machinery but overrides `commit()`/rollback to never close that shared Session; the approval-mediated create path needed no new transaction plumbing at all (already fully session-parameterized since P4-PRE, reuses `ApprovalHandlerResult.domain_events` directly) | `ProjectBaselineCreated`, `ProjectBaselineSubmitted`, `ProjectBaselineApproved` (carries `superseded_baseline_id` — a data fact of the same approval decision, not a separate event), `ProjectBaselineRejected`, `ProjectBaselineDeleted` — the full DRAFT→SUBMITTED→APPROVED/REJECTED lifecycle plus deletion, re-audited from source (P17 had only seen the approval-gated create producer) | Narrow: one target, `project_baseline` (project-scoped `ResourceScope`) — every current consumer (Scheduling's baseline register/compare/variance rows, Dashboard's baseline selector) rebuilds from the same projection via a single coarse workspace refresh; source does not justify splitting a `baseline_schedule`/`baseline_variance` target out separately | `baseline_changed` deleted |

**PM Baseline Approval is fully modernized** as of P23. Re-audit found a materially richer
capability than P17's own characterization ("approved request created/applied a baseline"): a
full DRAFT→SUBMITTED→APPROVED/REJECTED status lifecycle (`submit_baseline`/`approve_baseline`/
`reject_baseline`) plus `delete_baseline`, all real, UI-reachable desktop-API operations that
NEVER emitted `baseline_changed` (or anything else) even before this phase — a previously silent
gap, now fully covered by typed events. `approve_baseline` is the richest fact: it supersedes the
project's previous approved baseline (if any) and builds per-task variance records in the same
transaction; represented as one `ProjectBaselineApproved` event carrying `superseded_baseline_id`,
not two events, since no source path ever supersedes a baseline independently of approving
another one. The Control workspace's `baseline_changed` subscription was removed with no
replacement (P18B-class finding: its overview/queue presenters — approval queue + audit feed —
never referenced Baseline business data at all). See ADR-005 §26.20 for the full design, including
why a dedicated fresh-per-request UoW (the pattern every other capability uses) was rejected in
favor of the shared-Session-preserving variant.

| P24 | Inventory Item Catalog + Item Category | NEW: `InventoryCatalogUnitOfWork`/`Factory` (Option A convergence — Item + Category share one UoW, mirroring `InventoryFoundationUnitOfWork`'s storerooms/locations, since Items reference Categories by code within the same organization boundary) — `ItemMasterService`/`ItemCategoryService` moved off raw `self._session.commit()` onto this fresh-per-request UoW, and gained real compliance audit entries for the first time (previously only an activity-feed entry, never `record_audit_entry`, for either capability) | `InventoryItemCreated`, `InventoryItemProfileUpdated`, `InventoryItemStatusChanged` (mirrors `StoreroomProfileUpdated`/`StoreroomStatusChanged`'s exact split — Item shares Storeroom's own DRAFT/ACTIVE/INACTIVE/OBSOLETE-shaped status lifecycle); `InventoryItemCategoryCreated`, `InventoryItemCategoryProfileUpdated` (Category has no status-transition lifecycle of its own — `is_active` is a plain profile flag, folded into ProfileUpdated) | Narrow: `item_list` (`OrganizationScope`) — one org-wide projection feeding Catalog's own Item master list, Dashboard's low-stock row item labels, and every `item_options` selector (Inventory/Procurement/Reservations), proven from source to be the exact same underlying rows with no separately cached detail; `item_category_list` (`OrganizationScope`) — Catalog's own Category list/options, proven never to also stale `item_list` since `search_items`'s category label/equipment/project-usage flags are computed live at read time, never cached on the Item row | `inventory_items_changed`/`inventory_item_categories_changed` both deleted |

**Inventory Item Catalog + Item Category are fully modernized** as of P24. The redundant
`inventory_items_changed` publication inside `item_document_service.py`'s `link_document`/
`unlink_document` — which never mutated the Item row at all, only ever calling P16D's
`document_integration_service.link_existing_document`/`unlink_existing_document` (already typed,
already driving the canonical `document_links` ViewInvalidation target) — was removed entirely,
with no replacement Item DomainEvent, confirming P17's own finding. Re-audit of all six Inventory
workspace binders found: Catalog (owner, full `refresh()` on either target — no narrower seam
exists in its own monolithic `build_workspace_state`, the same class of acceptance P20 already
established for Storeroom/Location); Dashboard (`item_list` only, full `refresh()` — its low-stock
rows' item labels are a real, source-proven dependency, no narrower seam); Inventory/Procurement/
Reservations (`item_list` only, narrow `refresh_item_options()` — newly extracted in this phase,
mirroring the `refresh_site_options`/`refresh_storeroom_options` pattern P20 already established);
Pricing (zero dependency on Item or Category anywhere in its own presenter/state builders —
subscription removed with no replacement, the same class of finding as P18B's Control-workspace
`resources_changed` removal). See ADR-005 §26.21 for the full design.

| P25 | Inventory Reorder Policy | Option A convergence — added a `reorder_policies` named repository accessor to the EXISTING `InventoryFoundationUnitOfWork` (shared with Storeroom/Location, P20), rather than a new UoW: `ReorderPolicy` is validated against the same Item/Storeroom/Location repositories, uses the same `storeroom`-scoped permission model, and is owned by the same `InventoryFoundationService` class that already held Storeroom/Location's own commands — `upsert_reorder_policy` moved off raw `self._session.commit()` onto this shared UoW, and gained a real compliance audit entry for the first time (previously only an activity-feed entry) | `InventoryReorderPolicyConfigured` — one semantic event for the single `upsert_reorder_policy` business operation (the desktop command is itself literally named `InventoryReorderPolicyUpsertCommand`): the caller never distinguishes create vs. update, so this is not split into Created/Updated | Narrow: `reorder_policy_list` (`OrganizationScope`) — one org-wide projection feeding only the Inventory workspace's own "Foundation" panel (`build_foundation_snapshot`); proven that no other Inventory/Procurement workspace references the `ReorderPolicy` entity at all — Dashboard/Pricing's "reorder required" low-stock signal is computed entirely from `StockItem`'s own embedded `reorder_point`/`min_qty` fields (P24), never from this table | `inventory_reorder_policies_changed` deleted |
| P28B | Purchase Order | `PurchaseOrderSubmissionUnitOfWork` broadened (name kept, mirrors `InventoryFoundationUnitOfWork`'s own P20→P25 precedent of keeping its name across a widened scope) from submit-only to ALL of create/add-line/update/submit/cancel/send/close, gaining `purchase_order_lines`/`balances`/`_activity_service` accessors; approve/reject stay `ApprovalService`-owned (its own `PlatformUnitOfWork`), converted off the legacy `ApprovalPostCommitEvent` bridge onto `ApprovalHandlerResult.domain_events`; `post_receipt` also converges onto the same PO UoW, with Receipt/Balance/`StockControlService` collaborators constructed fresh per-transaction via an injected, composition-owned factory (never a named UoW accessor, and never an application-layer→infrastructure import — a real circular import was found and fixed this way) | `InventoryPurchaseOrderCreated`, `LineAdded`, `ProfileUpdated`, `Submitted`, `Approved`, `Rejected`, `Cancelled`, `Sent`, `Closed`, `ReceivingAdvanced` (10 events for 10 confirmed PO-owned facts — document link/unlink get zero PO event, P28B §2); plus the Requisition-owned `InventoryRequisitionSourcingAdvanced` (`requisition_events.py`), returned alongside `PurchaseOrderApproved` in the same `domain_events` tuple (Option A, P28A/ADR-005 §26.23), one per touched Requisition | Narrow: `purchase_order_list`/`purchase_order_detail` (`OrganizationScope`/`ResourceScope`, every PO fact notifies both — P19-FIX/P22-FIX precedent); `requisition_list`/`requisition_detail` (same scope shapes P27A already proposed, reused by P29) for the Requisition-sourcing fact | `inventory_purchase_orders_changed` deleted |
| P29 | Inventory Requisition | Option A extension of the existing `RequisitionSubmissionUnitOfWork` (name kept, already had every accessor create/add-line/update/cancel needed) — moved create/add-line/update/cancel off raw `self._session.commit()`; approve/reject stay `ApprovalService`-owned, converted off the legacy `ApprovalPostCommitEvent` bridge onto `ApprovalHandlerResult.domain_events` | `InventoryRequisitionCreated`, `LineAdded`, `ProfileUpdated`, `Submitted`, `Approved`, `Rejected`, `Cancelled` (7 events for the 7 facts P27A identified) — `InventoryRequisitionSourcingAdvanced` (P28B) unchanged | Narrow: `requisition_list`/`requisition_detail` (`OrganizationScope`/`ResourceScope`, every event notifies both — same targets P28B already established, one generalized handler covering all 8 event types); Dashboard newly wired (Submitted/Approved/Rejected/Cancelled move its "Awaiting Approval" KPI count) | `inventory_requisitions_changed` deleted |

**Inventory Reorder Policy is fully modernized** as of P25. Re-audit resolved P17's own semantic
uncertainty ("create/update may be combined into one service operation"): confirmed `upsert_reorder_policy`
is a genuine upsert (natural key = organization + Item + Storeroom + optional Location, looked up
via `get_for_scope`), not two business actions disguised as one — the desktop API command's own
name (`InventoryReorderPolicyUpsertCommand`) already documents this. True no-op detection added
to the update-via-scope-lookup path (candidate-vs-current comparison before any timestamp bump —
previously always wrote/audited/emitted on identical input). All six Inventory workspace binders'
`inventory_reorder_policies_changed` subscriptions re-audited: only the owning Inventory workspace
had a real dependency (full `refresh()`, no narrower seam exists in the same monolithic
`build_workspace_state` that already justifies full refresh for Storeroom/Location); Catalog/
Dashboard/Pricing/Procurement/Reservations all had zero real dependency on the `ReorderPolicy`
entity — all five subscriptions removed with no replacement. See ADR-005 §26.22 for the full
design.

**Purchase Order is fully modernized** as of P28B — implementing P28A's audit/design exactly as
recommended (Option A cross-capability event return, no deviation).

| Aspect | Status |
|---|---|
| PO transaction ownership | MODERNIZED — `PurchaseOrderSubmissionUnitOfWork` (name kept from its original submit-only P4-PRE scope, mirroring `InventoryFoundationUnitOfWork`'s own precedent of keeping its name across a widened scope) now covers create/add-line/update/submit/cancel/send/close, each a fresh Session |
| Approve/reject transaction ownership | Unchanged, already canonical — `ApprovalService`'s own `PlatformUnitOfWork`; the participant still never receives a `UnitOfWork` or a `record_event` callback (only `ApprovalHandlerResult.domain_events`, drained by `ApprovalService` itself) |
| `post_receipt` transaction ownership | MODERNIZED — same PO UoW; Receipt/Balance/`StockControlService` collaborators are constructed fresh per-transaction via a composition-owned factory (`_build_purchase_order_receiving_collaborators`, injected as `receiving_collaborators_factory`), not named UoW accessors — no ownership claim over Receipt/Balance, whose own facts remain on their existing legacy Signals |
| Typed DomainEvents | CANONICALIZED — 10 PO-owned events (`InventoryPurchaseOrderCreated`/`LineAdded`/`ProfileUpdated`/`Submitted`/`Approved`/`Rejected`/`Cancelled`/`Sent`/`Closed`/`ReceivingAdvanced`) plus the Requisition-owned `InventoryRequisitionSourcingAdvanced` (new `requisition_events.py`), all recorded via `uow.record_event(...)` |
| PO approval → Requisition sourcing | CANONICAL (Option A) — `apply_submitted_purchase_order_approval` returns both `InventoryPurchaseOrderApproved` and one `InventoryRequisitionSourcingAdvanced` per touched Requisition in the same `domain_events` tuple; `ApprovalService.approve_and_apply`'s pre-existing (previously unused for this family) `for domain_event in handler_result.domain_events: uow.record_event(domain_event)` loop drains it on the same transaction — no new plumbing |
| Requisition-sourcing concurrency gap | RESOLVED — `PurchaseRequisitionLine` gained a real `version` column (migration `c3f6a1b8d9e0`, ORM + domain + mapper), and its repository `update()` now uses the same atomic conditional `UPDATE ... WHERE version = :expected` (rowcount-verified, `update_with_version_check`) already used by `PurchaseOrder`/`PurchaseRequisition`. Two POs approved concurrently against the same Requisition line can no longer silently lose one another's `quantity_sourced` increment — the loser's `ApprovalService.approve_and_apply` transaction raises `ConcurrencyError` and rolls back entirely (zero postcommit events), proven by a genuine two-Session regression test |
| Document link/unlink | RESOLVED (P28B §2) — `link_document`/`unlink_document` no longer emit `inventory_purchase_orders_changed` (PO's own row was never mutated by this path; P16D's typed `DocumentReferenceLinked`/`Unlinked` was already the canonical record). **Real, pre-existing bug found while testing this, NOT fixed here (out of scope)**: both methods call `DocumentIntegrationService.link_existing_document`/`unlink_existing_document` with a `module=...` keyword neither method accepts — confirmed via `git show HEAD` to predate this phase; these two `PurchasingService` methods have never worked in production. Flagged for a future, unrelated fix |
| Cross-org integrity | Closed one gap P27A/P28A both flagged as open — PO approval now explicitly verifies the sourced `PurchaseRequisitionLine`'s parent Requisition belongs to the PO's own organization before sourcing it (previously relied only on the requisition-line repository's ambient tenant-scoped query) |
| No-op discipline | `update_purchase_order` now has a true no-op guard (zero write/audit/event/version-bump on an identical payload), matching every prior phase's first-audit finding |
| Enterprise audit | ADDED — `record_audit_entry(uow, ..., commit=False, fail_closed=True)` now runs atomically with every PO mutation (create/add-line/update/cancel/send/close/receiving); previously these paths had zero enterprise audit (best-effort activity-feed only, P28A finding) |
| PO ViewInvalidation | MODERNIZED — `purchase_order_list` (`OrganizationScope`) + `purchase_order_detail` (`ResourceScope`, exact PO), every PO fact notifies both (P19-FIX/P22-FIX "notify both" precedent — Procurement's own detail read is field-richer than its list row, and both go stale together on most facts). No separate `purchase_order_receiving` target — no distinct receiving-queue projection exists in source |
| Requisition ViewInvalidation (from PO sourcing) | MODERNIZED — `requisition_list`/`requisition_detail`, same scope shapes P27A already proposed for Requisition's own eventual events, reused here so P29 inherits a working target rather than inventing a second one |
| Consumers | Re-wired onto the new typed events via `platform_post_commit_bus` subscriptions in `inventory_registry.py`; the underlying consumer classification (Procurement + Dashboard real, Reservations/Pricing/Inventory/Catalog incidental) is unchanged from P28A's audit. **P28B's own QML cutover covered PO scope codes only** — `PurchaseOrderViewInvalidationAdapter` was wired to Procurement's and Dashboard's `_request_domain_refresh`/`refresh`, and the 4 incidental binders' legacy subscriptions were removed. It did **not** wire anything for the Requisition-sourcing scope codes (`requisition_list`/`requisition_detail`) — the domain-event handler correctly produced those hints and they reached `platform_view_invalidation_channel`, but no QML adapter consumed them, so a PO approval that sourced a Requisition produced zero UI reactivity for that Requisition (a real regression versus the pre-P28B legacy `inventory_requisitions_changed` re-emission this replaced). **Closed by P28B-FIX** (see below) with a new `RequisitionViewInvalidationAdapter`, wired to Procurement only (Dashboard has no real dependency — confirmed by re-reading `dashboard.py::build_snapshot`, whose only Requisition filter is `{SUBMITTED, UNDER_REVIEW}`, never touched by sourcing transitions) |
| `inventory_purchase_orders_changed` | DELETED — field, all 12 producer sites, zero remaining consumers of the raw signal itself (QML binders still exist but now receive nothing since the Signal no longer fires; their own migration onto `ViewInvalidationHandler`-based subscriptions is the UI follow-up above) |

Test coverage added: `src/tests/inventory_procurement/test_p28b_purchase_order_modernization.py` —
a genuine two-Session concurrency regression (not merely sequential `expected_version` calls),
`update_purchase_order` true no-op, document link/unlink zero-PO-signal (isolated from the
pre-existing `DocumentIntegrationService` bug above via a fake collaborator), the full
create/add-line/update/cancel lifecycle emitting zero legacy signals, and `post_receipt` emitting
the typed `InventoryPurchaseOrderReceivingAdvanced` while Receipt's own legacy signal fires
unchanged. `test_purchasing_apply_participant.py`'s two approve/reject tests were updated from
asserting the legacy `post_commit_events` shape to the new `domain_events` shape. Full
`src/tests/inventory_procurement/` suite: 183 passed, 3 pre-existing failures confirmed unrelated
(verified against `HEAD` before this phase — Reservation `source_reference_type` validation and
two unrelated import/reporting tests, none touching Purchase Order code).

Cross-capability note: constructing `post_receipt`'s Receipt/Balance/`StockControlService`
collaborators via a direct application-layer import of SQLAlchemy repositories caused a real
circular import (`application.procurement` → `infrastructure.persistence.repositories` →
`infrastructure.importers.service` → `application.procurement`) — fixed by injecting a
composition-owned `receiving_collaborators_factory: Callable[[Session], tuple[...]]` into
`PurchasingService`, mirroring the existing `ApprovalService.dependencies_factory` seam, so the
application layer only depends on the callable's shape, never on `sqlalchemy`/`src.infra` directly.

See ADR-005 §26.23 for the full design.

**P28B-FIX — Requisition sourcing ViewInvalidation: production wiring verified, one real gap
found and closed (no backend change).** P28B's backend (typed events, UoW convergence, concurrency
fix, legacy-signal deletion) was approved and out of scope for re-verification. This follow-up
inspected only the event → ViewInvalidation → UI-consumer chain for
`InventoryRequisitionSourcingAdvanced`, per its own explicit request not to assume production
wiring from the event existing or from tests.

- **Domain-event handler**: `build_requisition_sourcing_view_invalidation_handler`
  (`event_handlers/view_invalidation.py`) was already correct and already wired — subscribed to
  `InventoryRequisitionSourcingAdvanced` on `platform_post_commit_bus` in `inventory_registry.py`.
  It maps to `requisition_list` (`OrganizationScope`) and `requisition_detail` (`ResourceScope`,
  `entity_type="purchase_requisition"`), with correct per-correlation-id, per-target dedupe: a PO
  sourcing multiple lines of the same Requisition still produces exactly one list hint and one
  detail hint; a PO sourcing two different Requisitions produces one list hint (org-wide, no
  `requisition_id` in its dedupe key) plus one detail hint per Requisition.
- **The real gap**: no QML adapter consumed `requisition_list`/`requisition_detail` hints at all.
  `PurchaseOrderViewInvalidationAdapter` (the only adapter wired against
  `PROCUREMENT_CATEGORY` hints) filters strictly on the two PO scope codes — a Requisition-sourcing
  hint reached it and was silently dropped. Confirmed via source, not inferred: no
  `RequisitionViewInvalidationAdapter`-shaped class existed anywhere under `src/ui_qml/`, and no
  `requisitionListStale`/`requisitionDetailStale`-shaped signal existed anywhere. Net effect before
  this fix: a PO approval that sourced a Requisition correctly stopped emitting the legacy
  `inventory_requisitions_changed` (P28B's intended change) but nothing typed replaced it in the
  UI — Procurement's cached Requisition list/detail could go stale with **zero** reactivity, a real
  regression the P28B backend work introduced without a corresponding UI fix.
- **Fix**: added `RequisitionViewInvalidationAdapter`
  (`src/ui_qml/platform/adapters/requisition_view_invalidation_adapter.py`, structurally identical
  to `PurchaseOrderViewInvalidationAdapter`), wired in `context.py` for Procurement only —
  `requisitionListStale`/`requisitionDetailStale` both connect to
  `self._procurement_workspace._request_domain_refresh` (same full-refresh breadth already
  accepted for PO hints on the same monolithic `build_workspace_state`; the two adapters are
  independent subscriptions, so a PO event and a Requisition event from the same approval each
  independently trigger a refresh call — neither suppresses the other). Also added to the
  `refreshCapabilities` tenant/org re-scoping sweep. **Dashboard was deliberately NOT wired** —
  re-read `dashboard.py::build_snapshot` directly: its sole Requisition filter is status ∈
  `{SUBMITTED, UNDER_REVIEW}` for the "Awaiting Approval" KPI/section, never touched by sourcing
  transitions (which only occur once a Requisition is already `APPROVED`); no other KPI/section
  references `quantity_sourced` or a sourcing status. A `test_dashboard_workspace_has_no_
  requisition_view_invalidation_adapter` regression test locks this in.
- **Concurrency-losing approval**: confirmed structurally and by test — `ApprovalService.
  approve_and_apply` only drains `handler_result.domain_events` into postcommit dispatch *after*
  its `with uow:` block succeeds; a `ConcurrencyError` raised mid-handler (the P28B fix's own
  guard) propagates out of that block, so `uow.commit()` never runs and postcommit dispatch never
  fires — zero ViewInvalidation hints reach the channel, proven by a real (not merely simulated)
  failing `approve_and_apply` call.
- **Legacy signal count reconfirmed unchanged by this fix**: 18 (`inventory_purchase_orders_changed`
  still deleted; `inventory_requisitions_changed` still present with exactly its 7 Requisition-owned
  producers — recomputed via source grep, unchanged from P28B).
- No backend/domain/transaction code was touched — this was a UI-consumer gap only. Test coverage
  added to `test_p28b_purchase_order_modernization.py` (handler dedupe/mapping, end-to-end
  production-path hint assertions, the concurrency-losing-approval zero-invalidation case, the
  Procurement wiring test, the Dashboard no-adapter test) and
  `test_purchasing_apply_participant.py` (multi-line-same-Requisition batches to one event,
  multi-Requisition batches to one event per Requisition, rejection never sources).

**Inventory Requisition is fully modernized as of P29**, implementing P27A's audit exactly as
recommended (Option A extension of the existing `RequisitionSubmissionUnitOfWork`, name kept per
P28B's own precedent for the identical situation).

| Aspect | Status |
|---|---|
| Requisition transaction ownership | MODERNIZED — `RequisitionSubmissionUnitOfWork` (name kept, already had `requisitions`/`requisition_lines`/`approvals`/`_enterprise_audit_service` from its pre-P29 submit-only scope — no new accessors were needed, unlike PO's own broadening) now also covers create/add-line/update/cancel, each a fresh Session |
| Approve/reject transaction ownership | Unchanged, already canonical — `ApprovalService`'s own `PlatformUnitOfWork`; the participant (`ProcurementApprovalParticipant`) still never receives a `UnitOfWork` or a `record_event` callback |
| Typed DomainEvents | CANONICALIZED — 7 new Requisition-owned events (`InventoryRequisitionCreated`/`LineAdded`/`ProfileUpdated`/`Submitted`/`Approved`/`Rejected`/`Cancelled`) added to the existing `requisition_events.py`, alongside the unmodified `InventoryRequisitionSourcingAdvanced` (P28B) — all recorded via `uow.record_event(...)` |
| ViewInvalidation handler | GENERALIZED — `build_requisition_sourcing_view_invalidation_handler` (which only ever handled the one PO-triggered event) was renamed `build_requisition_view_invalidation_handler` and its type union widened to all 8 Requisition event types, mirroring `build_purchase_order_view_invalidation_handler`'s own single-handler shape for its 10 PO events. **Superseded by P29-FIX** (see below) — per-event precision replaced the original "every event notifies both targets" symmetry |
| Approval event return | CANONICAL (Option A pattern, same as PO) — `apply_submitted_requisition_approval`/`_rejection` now return `ApprovalHandlerResult(domain_events=(...))` instead of the legacy `ApprovalPostCommitEvent("inventory_requisitions_changed", ...)` bridge |
| No-op discipline | `update_requisition` gained a true no-op guard (zero write/audit/event/version bump on an identical payload) — P27A's own finding was that this guard never existed |
| Enterprise audit | ADDED — `record_audit_entry(uow, ..., commit=False, fail_closed=True)` now runs atomically with create/add-line/update/cancel; previously these paths had zero enterprise audit (best-effort activity-feed only, P27A finding). Proven atomic by a real audit-failure-rollback regression test (representative of all four, which share one transaction boundary) |
| Supplier same-organization integrity | **Re-investigated, found NOT a real gap** — P27A/P28A/P28B all characterized `_ensure_business_supplier_scope` as never checking organization membership, based on reading that method in isolation. Tracing its sole caller one line up shows `PartyService.get_party` already scopes its own lookup to the active organization and raises `NotFoundError` for a cross-org party — confirmed by a real regression test, not inferred. No code change was made (a second check would have been unreachable dead code); this corrects the prior phases' characterization rather than fixing a bug that doesn't exist |
| Consumer cutover | CUT OVER — the existing `RequisitionViewInvalidationAdapter` (P28B-FIX) is reused unchanged for all 8 event types (no second/parallel adapter). Procurement's wiring is unchanged (already existed). Dashboard's original wiring (both `requisitionListStale`/`requisitionDetailStale`) was **corrected by P29-FIX** to a dedicated precise target — see below. Catalog/Reservations/Pricing/Inventory(Foundation) subscriptions removed, no replacement (confirmed zero real dependency, unchanged from P27A) |
| Unreachable `FULLY_SOURCED → CLOSED` transition | Confirmed still unreachable — no producer performs it. Recorded as pre-existing product/domain debt, not addressed (no close-Requisition command was invented, per explicit scope boundary) |
| `inventory_requisitions_changed` | DELETED — field, all 7 remaining producer sites (5 in `procurement_lifecycle.py` + 2 in `procurement_approval.py`), all 6 legacy consumer subscriptions. Legacy Signal count: 17 (18 → 17, confirmed via `dataclasses.fields(DomainEvents)`) |

Test coverage added: `src/tests/inventory_procurement/test_p29_requisition_full_modernization.py`
(every new event's list+detail mapping, cross-event-type dedupe within one transaction, real
create/add-line/update/cancel producer paths including a true no-op and a stale-version rejection,
an audit-failure-rollback proof for the new UoW boundary, approve/reject end-to-end through
`ApprovalService`, the supplier-organization-scoping finding above, a legacy-reference grep sweep,
and UI wiring for both Procurement and the incidental workspaces). `test_procurement_apply_
participant.py`'s two approve/reject tests were updated from the legacy `post_commit_events` shape
to `domain_events`. Full `src/tests/inventory_procurement/` suite: 196 passed (223 including this
phase's own new file), 3 pre-existing failures confirmed unrelated (unchanged from P28B/P28B-FIX's
own baseline — Reservation `source_reference_type` validation and two unrelated import/reporting
tests).

See ADR-005 §26.25 for the full design.

**P29-FIX — Requisition invalidation precision + UI refresh coalescing: two real gaps found and
closed (no backend/event-vocabulary change).** P29's typed events, UoW convergence, audit
convergence, approval event return, and legacy-signal deletion were approved and out of scope for
re-verification. This follow-up re-audited only the event → ViewInvalidation → UI-consumer chain,
per its own explicit instruction not to accept "every event notifies both targets, matching broad
codebase precedent" as sufficient justification without re-proving each event against the actual
persisted read models.

- **Gap 1 — imprecise event → target mapping.** Re-reading `to_requisition_record_view_model`
  (the `requisition_list` row) and `build_requisition_detail` (the `requisition_detail`
  projection) directly showed the original "every event → both targets" design was wrong in two
  directions: `InventoryRequisitionCreated` can never make an existing `requisition_detail`
  projection stale (no client can hold a cached detail view for an id that did not exist before
  the transaction) — corrected to `requisition_list` only. `InventoryRequisitionLineAdded`
  touches no field that appears on the list row (line data only reaches `requisition_lines` and
  the detail's derived `hasLines`/`canSubmit` flags) — corrected to `requisition_detail` only.
  `ProfileUpdated`/`Submitted`/`Approved`/`Rejected`/`Cancelled`/`SourcingAdvanced` do genuinely
  touch both (status and/or site/storeroom/priority/purpose all appear on both the list row and
  detail) — left unchanged, now for a proven reason rather than a default. The handler functions
  (`_requisition_event_notifies_list`/`_notifies_detail`/`_notifies_pending_approval` in
  `event_handlers/view_invalidation.py`) encode this explicitly, each with the source citation for
  its rule, rather than the prior unconditional "notify both" body.
- **Gap 2 — Dashboard was over-wired, not "harmlessly" so.** P29's own Dashboard wiring reused the
  broad `requisitionListStale`/`requisitionDetailStale` signals — re-reading
  `dashboard.py::build_snapshot` directly confirmed its *sole* Requisition dependency is the
  "Awaiting Approval" KPI/section, filtered to `status ∈ {SUBMITTED, UNDER_REVIEW}`; Created/
  LineAdded/ProfileUpdated are DRAFT-only (never touch that set) and `SourcingAdvanced` only ever
  fires once a Requisition is already past `APPROVED` (already established in P28B-FIX). A new,
  dedicated org-scoped target, `requisition_pending_approval`, is now notified only for
  Submitted/Approved/Rejected/Cancelled (`REQUISITION_PENDING_APPROVAL_SCOPE_CODE`) — the same
  "distinct approval-summary projection, not a screen-specific one" class of target P19-FIX
  already established for Finance Forecast's `forecast_approved_basis`. `RequisitionViewInvalidationAdapter`
  gained a third signal, `requisitionPendingApprovalStale`, on the SAME adapter class (no second/
  parallel adapter) — Dashboard is now wired to that signal exclusively; `Cancelled` is still
  notified unconditionally despite only *sometimes* leaving the pending set, since the event
  carries no prior-status field to filter that specific case — documented as a deliberate,
  narrowly-scoped exception, not a return to blanket over-inclusion.
- **Gap 3 (found during investigation, not in the original ask) — genuine double full-refresh.**
  Tracing `_request_domain_refresh()` showed it executed `refresh()` fully synchronously on every
  call, with no coalescing beyond "already mid-refresh right now" — so any transaction producing
  2+ Procurement-relevant hints (e.g. `InventoryRequisitionApproved`'s `requisition_list` +
  `requisition_detail`, or equally PO's own pre-existing `purchase_order_list` +
  `purchase_order_detail` pair from P28B) rebuilt the entire monolithic Procurement workspace
  twice. `project_management`'s own `ProjectManagementWorkspaceControllerBase` already solves
  exactly this with a `QTimer(0)`-coalesced scheduling mechanism, gated on the app-wide
  `pmEventLoopRunning` property set in `src/ui_qml/shell/app.py`'s real entrypoint (falling back to
  immediate synchronous execution when no Qt event loop is running, e.g. in most of this test
  suite) — ported verbatim into `InventoryProcurementWorkspaceControllerBase`
  (`_schedule_domain_refresh`/`_execute_scheduled_domain_refresh`), not reinvented. This is a
  pre-existing generic UI scheduling primitive being reused across modules, not a new bespoke
  debounce service; it benefits PO's own list+detail pair identically, at no extra cost.
- **What did NOT change**: `requisition_detail`'s scope stays the exact `ResourceScope`
  (`entity_type="purchase_requisition"`, exact `entity_id`) — never widened to an org-wide
  refresh. Procurement's own consumption of both targets remains one full, monolithic `refresh()`
  (its `build_workspace_state` rebuilds list+detail+lines together in one call regardless of which
  hint triggered it — no narrower seam exists, matching the same acceptance class already used for
  every other Inventory capability); P29-FIX's coalescing fix ensures that full refresh happens
  *once* per transaction, not that it becomes narrower. No typed event, UoW, audit, concurrency,
  or approval-architecture behavior from P29 was touched.
- Legacy Signal count unchanged: 17. `inventory_requisitions_changed`/`inventory_purchase_orders_changed`
  both remain deleted; producers/consumers remain 0 for both.

See ADR-005 §26.26 for the full design, including the final source-derived event → target matrix.

**P26A — Auth Credential & Session: semantic + transaction audit complete (design only, no
migration yet).** Full source re-audit of all 10 raw-Session producer files
(`authentication_transactions.py`, `password_service.py`, `mfa_service.py`,
`federated_identity_service.py`, `session_service.py`, `user_admin_service.py`,
`bootstrap_service.py`, `registration_service.py`, `tenant_role_administration_service.py`,
`role_policy_reconciliation_service.py`) and both consumers (`admin_console/domain_event_binder.py`,
`access_workspace_controller.py`), performed directly by the main agent from current source
(re-verified after a workspace-integrity recovery: an earlier draft of this audit was produced
unintentionally by an unauthorized research subagent and was discarded before this entry was
written). Confirms 19 exact `auth_changed.emit(...)` call sites, no reflective/generic dispatch,
decomposing into far more distinct facts than a single signal name suggests:

- **Durable Auth-owned DomainEvent candidates** (mutate `UserAccount`/`AuthSession`, atomic
  same-transaction audit already in place for every one): password changed (self-service/admin
  reset/force-reset-required), MFA provisioned/enabled/disabled, federated identity linked,
  session policy changed, all-sessions revoked, account enabled/disabled, account unlocked,
  profile updated, login success, failed login recorded (`register_failed_login` — one emit site
  per failed attempt regardless of whether it crosses the lockout threshold on that call; lockout
  is a data state on the same row, not a separate emit), user registered / bootstrap admin
  created.
- **Already-correct session/application-context transitions, never routed through `auth_changed`**
  (confirmed via `context_switch_service.py::commit_context_switch`): active organization/tenant
  switch. `UserSessionContext` (`domain/security/auth/session.py`) already has its own
  `_notify_context_changed()` hook, wired today only to `auth_service.persist_session_context`
  (a persistence side-effect, not yet any UI reactivity path) — the existing proof that a
  non-`DomainEvent` session-context mechanism already coexists correctly alongside the legacy
  signal.
- **Misrouted — belong to Authorization, not Auth** (`tenant_role_administration_service.py`,
  `role_policy_reconciliation_service.py`): custom-role permission update, custom-role retirement,
  policy-reconciliation apply — each loops `auth_changed.emit(user_id)` per affected user for a
  fact that is semantically Authorization/RoleBinding, not Auth. `retire_custom_role`'s cascading
  revocation (`revoke_active_for_role`, a raw bulk-SQL `UPDATE` at
  `infrastructure/persistence/repositories/security/auth/auth.py:583`) bypasses the domain layer
  entirely — the already-existing typed `RoleBindingRevoked` event does not fire for this path, so
  `auth_changed` is currently the *sole* notification for it, not a redundant duplicate.
- **Under-instrumented, not over-instrumented**: `registration_service.py::_create_user` (shared
  by `register_user`/`onboard_tenant_user`/bootstrap's own user creation) constructs
  `UserTenantMembership` and `RoleBinding` directly via their repositories inside its own
  `session.begin_nested()`, bypassing the typed `TenantMembershipActivated`/`RoleBindingAssigned`
  events entirely. Registration produces zero typed Membership/RoleBinding events for a brand-new
  user today.
- **Security-correctness finding** (not exploitable under normal operation): in
  `authentication_transactions.py`, `complete_successful_authentication` re-raises (fail-closed) if
  its atomic audit persistence fails; `register_failed_login` swallows the identical exception
  class without re-raising (fail-open) — a failed login whose audit persistence fails silently
  leaves no lockout-counter increment and no record. Every other producer's audit staging is
  correctly atomic (same transaction, before commit).
- **Consumers are narrower than their wiring suggests**: `access_workspace_controller.py` already
  performs its own narrow `_refresh_after_security_change()` from every admin action it triggers
  itself — its `auth_changed` subscription is only load-bearing for *other*-originated changes.
  `admin_console/domain_event_binder.py` still triggers a full `_request_domain_refresh()`.
- **No canonical UnitOfWork exists anywhere on this surface** — all 19 producers mutate a shared,
  manually-committed `AuthService._session` directly; typed-event work here cannot simply add
  `uow.record_event(...)` the way prior phases did, since no UoW abstraction is in place yet. This
  is itself a prerequisite design decision for whichever phase migrates this surface first.
- **Recommended migration slicing**: **P26B** — Credentials + Account Security + Session
  Persistence (password, MFA, federated identity, enable/disable/lock/unlock, profile, session
  policy/revocation) — one cohesive transactional surface, the single largest and cleanest slice,
  no open security question. **P26C** — Login/Registration/Provisioning — must resolve the
  fail-open/fail-closed audit asymmetry and the registration Membership/RoleBinding conflation
  (reusing the existing typed Membership/RoleBinding vocabulary, not inventing an Auth-owned
  substitute) as part of the slice, not deferred further. **Not an Auth phase** — the
  custom-role/policy-reconciliation cleanup (extending `revoke_active_for_role` to emit the
  already-existing `RoleBindingRevoked`) belongs to Authorization's own backlog.
- `auth_changed` **cannot be safely deleted in one phase**: no UoW convergence yet, the
  RoleBinding-bulk-SQL-bypass gap, and the registration Membership/RoleBinding conflation each need
  their own fix first.

No source was changed by this audit. Legacy Signal count unchanged at 19.

**P27A — Inventory Requisition: semantic + transaction audit complete (design only, no migration
yet).** Full source re-audit of `procurement_lifecycle.py` (5 direct producers), `procurement_
approval.py` (2 approval-bridge producers), and `purchasing_receiving.py` (1 cross-capability
re-emission from Purchase Order's own approval participant), plus all 6 consumer binders. Confirms
7 exact `inventory_requisitions_changed` producer sites genuinely owned by Requisition, no
reflective/generic dispatch, decomposing into more distinct facts than P17's rough "~5" estimate:

- **7 Requisition-owned facts**: header created, line added (the *only* line-mutation command —
  no update-line/remove-line exists anywhere), header profile updated (DRAFT only), submitted,
  approved, rejected, cancelled.
- **An 8th, mis-attributed fact**: `purchasing_receiving.py`'s Purchase-Order-approval participant
  mutates the referenced Requisition Line's sourced quantity/status and derives the header status
  (`APPROVED → PARTIALLY_SOURCED → FULLY_SOURCED`), then re-emits `inventory_requisitions_changed`
  for every touched requisition. This is a Purchase-Order-owned business fact bleeding into
  Requisition's signal, not a genuine Requisition action — its correct event ownership is an open
  question for whichever phase modernizes Purchase Orders, not resolved here.
- **Aggregate**: `PurchaseRequisition` (has `version`, optimistic concurrency) + child
  `PurchaseRequisitionLine` (no own version field). Header status is direct for the early
  transitions, line-derived for the sourcing transitions. `FULLY_SOURCED → CLOSED` is defined in
  the transition table but unreachable — no producer transitions to it.
- **Transaction ownership**: create/add-line/update/cancel are raw-Session, service-owned commit,
  with **no atomic audit at all** (only a best-effort activity-feed entry committed in a *separate*
  transaction after the mutation already committed — the same gap class P22-P25 each closed for
  their own capability). `submit_requisition` already uses a canonical UoW
  (`RequisitionSubmissionUnitOfWork`, with `requisitions`/`requisition_lines`/`approvals`/atomic
  `EnterpriseAuditService` already wired) — the natural Option A extension target for the other
  four operations, not a new UoW. Approve/reject are ApprovalService-owned, still on the legacy
  string-keyed `ApprovalPostCommitEvent` bridge rather than P23's typed
  `ApprovalHandlerResult(domain_events=(...))` pattern.
- **Scope**: `PurchaseRequisition` has `organization_id` only, no `tenant_id` field --
  `OrganizationScope` is correct (list/KPI targets), `ResourceScope` for a cached detail view --
  matching every other Inventory capability's precedent, not an Auth-style `TenantScope`.
- **Consumers**: all 6 workspace binders subscribe identically to all 6 remaining raw Inventory
  signals. Re-audit found Procurement (owner: list + detail + lines) and Dashboard (declared
  blanket KPI-rollup policy) have real dependencies; Catalog, Reservations, Pricing, and
  Inventory(Foundation) have **zero** "requisition" reference anywhere in their own
  presenter/state-builder trees -- the same incidental-subscription pattern P24/P25 already found
  and removed for Item/Category/ReorderPolicy in these exact same workspaces.
- **No-op**: `update_requisition` has no no-op detection -- always writes/activity-logs/emits even
  for an identical payload, the same gap class found and fixed in every prior modernized phase.
- **ReorderPolicy**: zero relationship anywhere in requisition creation -- the same pre-existing
  replenishment-architecture gap P25 already documented, not fixed here.
- **Recommended P27B shape**: one phase, for the 7 Requisition-owned facts, converging onto the
  existing `RequisitionSubmissionUnitOfWork` extended to also own create/add-line/update/cancel
  (Option A). The 8th, PO-triggered fact is explicitly out of P27B's scope.
- `inventory_requisitions_changed` **cannot be fully deleted in P27B** -- the PO-sourcing
  side-effect will keep emitting it until Purchase Orders' own modernization phase resolves that
  boundary; producers CAN converge from 7 to that single remaining PO-triggered site.

No source was changed by this audit. Legacy Signal count unchanged at 19.

**P28A — Purchase Order: semantic + transaction audit complete (design only, no migration yet).**
Full source re-audit of `purchasing_lifecycle.py` (7 direct producers: create/add-line/update/
cancel/send/close/submit), `purchasing_service.py` (2 direct producers: link/unlink document),
`purchasing_receiving.py` (1 direct producer — `post_receipt` — plus 2 producers via the legacy
`ApprovalPostCommitEvent` bridge — approve/reject), the shared `ApprovalService` approve/reject
machinery, and all 6 consumer binders. Confirms 12 exact `inventory_purchase_orders_changed`
producer sites (10 direct `.emit()` + 2 reflective via `getattr(domain_events, signal_name)`
dispatch in `approval_service.py`), no PO-specific reflective/generic helper beyond that one
shared Approval bridge, decomposing into 9 distinct PO-owned facts (more than P17's rough "six"):

- **9 PO-owned facts** (all confirmed in source, none assumed from naming): header created, line
  added (the *only* line-mutation command — no update-line/remove-line exists, mirroring P27A's
  identical Requisition finding), header profile updated (DRAFT only), submitted, approved,
  rejected, cancelled, sent, closed. (Document link/unlink is a minor 10th fact family, arguably
  owned by the already-modernized Document capability rather than PO itself.)
- **Aggregate**: `PurchaseOrder` (has `version`, optimistic concurrency — but enforced only on
  `update`/`cancel`, NOT on `submit`/`send`/`close`, a real gap) + child `PurchaseOrderLine` (no
  own version field, additive-only mutation).
- **Lifecycle**: `DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, SENT, PARTIALLY_RECEIVED,
  FULLY_RECEIVED, CLOSED, CANCELLED`, exact transition table confirmed in
  `application/common/support.py`; terminal states `REJECTED`/`CANCELLED`/`CLOSED`.
  Receiving-driven `→PARTIALLY_RECEIVED/FULLY_RECEIVED` and approval-driven `→APPROVED/REJECTED`
  are both real, source-confirmed transitions.
- **Transaction ownership — three distinct patterns coexist**: (1) raw process-lifetime `Session`,
  best-effort separate-transaction audit — create/add-line/update/cancel/send/close/
  link/unlink-document; (2) canonical `PurchaseOrderSubmissionUnitOfWork` (fresh Session per call)
  — submit only, ATOMIC audit, but its legacy activity-feed entry is still separately committed
  after `uow.commit()`; (3) `ApprovalService`'s own fresh `PlatformUnitOfWork` — approve/reject,
  ATOMIC, and uniquely the same transaction also atomically covers `PurchaseOrderLine`,
  `StockBalance.on_order_qty`, and (on approve) `PurchaseRequisitionLine`/`PurchaseRequisition`
  sourcing state, all four aggregates committed together with the `ApprovalRequest` decision
  itself. `post_receipt` is a fourth, separate raw-`Session` pattern, not the
  ApprovalService-mediated flow.
- **CRITICAL — PO approval mutates Requisition sourcing state in the identical transaction as PO's
  own status change**: confirmed via `purchasing_receiving.py::apply_submitted_purchase_order_
  approval`. Gated per-line (`if line.source_requisition_line_id:` — not every PO approval touches
  a Requisition), additive (`quantity_sourced += sourced_qty`) with an explicit over-sourcing guard
  (`INVENTORY_REQUISITION_LINE_OVERSOURCED`) plus a second domain-layer range guard, correctly
  deduplicated to one header-status refresh and one legacy-signal emission per distinct touched
  Requisition even when several PO lines source different lines of the same Requisition. One PO
  can source multiple Requisitions; one Requisition can be sourced by multiple POs over time
  (nothing scopes a Requisition line to a single PO). PO's own status flips to `APPROVED` before
  the Requisition-sourcing loop runs, same method, same `uow._session`, one `uow.commit()` —
  proven atomic by a test that monkeypatches `Session.commit`/`rollback` to assert the participant
  itself never calls either. **A genuine, previously-undocumented concurrency gap**:
  `PurchaseRequisitionLine` has no `version` column read/compared/incremented anywhere (unlike
  `PurchaseRequisition` and `PurchaseOrder`, which do have one) — two POs approved concurrently
  against the same Requisition line, in two separate `ApprovalService` transactions, could each
  read the same stale `quantity_sourced`, both pass the over-sourcing guard against stale data, and
  both commit an additive update: a real cross-transaction lost-update race, not merely a
  documentation gap.
- **PO → Stock Balance is a real mutation, not over-notification**: `on_order_qty` is genuinely
  incremented on approval and reversed on cancel (`_adjust_on_order_balance`); `on_hand_qty` is
  untouched by approval, changing only via `post_receipt`.
- **PO → Receipt**: `ReceiptHeader` references `purchase_order_id` (one-directional); no Receipt is
  auto-created at PO create/approve; `post_receipt` is a wholly separate, later, manually-triggered
  operation that mutates PO line/header status (`PARTIALLY_RECEIVED`/`FULLY_RECEIVED`) and is
  itself a 12th `inventory_purchase_orders_changed` producer, on its own raw-`Session` transaction
  pattern — distinct from the ApprovalService-mediated approve/reject flow.
- **PO creation from Requisition**: manual line selection, never auto-generated;
  `source_requisition_id` (header, advisory) and `source_requisition_line_id` (per-line, optional)
  allow a single PO to mix requisition-sourced and direct/catalog lines; creation and line-add only
  *read* the Requisition to validate remaining quantity/org — only **approval** mutates it,
  confirmed from both the PO and (via P27A) the Requisition side.
- **Approval architecture**: no formal `ApprovalParticipant` protocol exists — a structural
  duck-typed convention (`.apply()`/`.reject()`). `PurchasingApprovalParticipant` delegates to a
  fresh `PurchasingService` bound to `ApprovalService`'s own fresh UoW Session (never the app's
  shared session). Still reports through the **legacy** `ApprovalHandlerResult(post_commit_events=
  (ApprovalPostCommitEvent(...), ...))` string-keyed bridge — same as Requisition's own approval
  participant — never the P19/P23 typed `domain_events` tuple, even though
  `ApprovalService.approve_and_apply` already unconditionally drains `handler_result.domain_events`
  into `uow.record_event(...)` inside the same transaction today; that seam sits ready and unused
  for this exact boundary.
- **Cross-org integrity**: PO creation explicitly checks site/supplier/requisition organization.
  Line-add and approval do not independently re-verify the sourced Requisition line's organization
  against the PO's own — approval relies only on the requisition-line repository's ambient
  tenant-scoped query (fail-closed on lookup, but not an explicit assertion). Confirms and sharpens
  P27A's flagged gap: `PurchaseRequisitionLine.suggested_supplier_party_id` is validated for
  active/business-party-type only, never for same-organization membership.
- **No-op/idempotency**: `update_purchase_order` has no no-op guard (same gap class as every prior
  phase's first audit). Duplicate submit is hard-rejected by the DRAFT-only guard, not silently
  no-op'd. Approval-level replay is blocked by `ApprovalRequest`'s own "already decided" guard once
  committed, but the Requisition-sourcing race above is a genuine cross-transaction gap, not
  covered by that guard.
- **Recommended event ownership (Option A, evaluated against B/C)**: the PO approval participant
  should return **both** `PurchaseOrderApproved` and a batched, per-Requisition sourcing event (one
  event per touched Requisition, not per line or per PO-line-touch — mirroring the existing
  `touched_requisition_ids` dedup) in the same `ApprovalHandlerResult.domain_events` tuple,
  recorded by `ApprovalService` on its own already-atomic UoW. This requires no new transactional
  machinery (the `domain_events` → `uow.record_event` seam already runs unconditionally today),
  preserves the exact atomicity already relied upon, and the participant already holds direct,
  same-Session access to every Requisition object it would need. Option B (a separate transactional
  handler reacting to `PurchaseOrderApproved` alone) was rejected: it would either collapse back
  into Option A (if run pre-commit on the same Session) or reintroduce a dual-write/
  eventual-consistency window that does not exist today, worsening the already-identified
  `PurchaseRequisitionLine` version gap rather than fixing it. No cleaner Option C seam was found.
- **Proposed cross-capability event**: a Requisition-owned, PO-caused event (not
  `InventoryRequisitionChanged`) — e.g. `RequisitionSourcingAdvancedByPurchaseOrder` — one per
  touched Requisition per approval, carrying the set of `(requisition_line_id,
  quantity_sourced_delta, resulting_line_status)` plus resulting header status (only if it actually
  changed) and causal `purchase_order_id`/`approval_request_id` metadata, so a future consumer can
  distinguish this from a genuine Requisition self-action.
- **Consumers**: 6 workspace binders subscribe identically to all 6 remaining raw Inventory signals
  (same fan-out pattern P24/P25/P27A already found for their own signals). Re-audit found only
  Procurement (owner — PO list/detail/lines, monolithically entangled with Requisition list/detail
  in the same `build_workspace_state`) and Dashboard (3 of 8 KPIs plus 2 of 3 dashboard sections
  genuinely PO/Requisition/Balance-driven, org-wide `purchase_order_list` shape only, no detail
  dependency) have real dependencies; Reservations, Pricing, Inventory(Foundation), and Catalog
  have **zero** real PO reference anywhere in their own presenter/state-builder trees — the same
  incidental-subscription pattern already found and removed for other Inventory signals in
  P24/P25/P27A.
- **Proposed ViewInvalidation targets**: `purchase_order_list` (`OrganizationScope`) and
  `purchase_order_detail` (exact `ResourceScope`, `entity_type="purchase_order"`) — no separate
  `purchase_order_receiving` target is justified (no distinct receiving-queue projection exists;
  it's the same detail read). On the Requisition side: `requisition_list` (`OrganizationScope`) and
  `requisition_detail` (`ResourceScope`, `entity_type="purchase_requisition"`) both go stale on a
  PO-triggered sourcing event — a genuine two-capability fan-out from one PO approval, not
  expressible by `inventory_requisitions_changed` alone once retired.
- **Recommended sequencing**: **OPTION A** — P28B (Purchase Order's own 9 facts, including
  converting `purchasing_receiving.py`'s three producer sites — approve/reject/post_receipt's
  PO-status consequence — off the legacy bridge, AND introducing the one Requisition-owned
  `RequisitionSourcingAdvancedByPurchaseOrder` event as part of PO's own transaction) fully retires
  `inventory_purchase_orders_changed` in one phase; **P29** (Requisition's own 7 already-audited
  facts from P27A, Option A extension of `RequisitionSubmissionUnitOfWork`) then fully retires
  `inventory_requisitions_changed`, since P28B will have eliminated the sole non-Requisition-owned
  producer. Combining PO and Requisition into one phase (roadmap Option B) is not required —
  Requisition's other 7 facts run on entirely separate transaction paths untouched by PO's approval
  mutation.
- `inventory_purchase_orders_changed` **can be deleted in P28B**, provided P28B's scope explicitly
  includes all 12 producer sites (not just `purchasing_lifecycle.py`'s 7) — the 2
  `purchasing_service.py` document-link sites and all 3 `purchasing_receiving.py` sites
  (post_receipt, approve, reject) must convert too, or the signal survives with a residual
  producer.
- P28B **will unblock full P29 Requisition modernization** — once the PO-approval-triggered
  Requisition mutation reports through a typed event instead of the legacy
  `ApprovalPostCommitEvent("inventory_requisitions_changed", ...)` loop, zero non-Requisition-owned
  producers remain. Recommend fixing the `PurchaseRequisitionLine` version-field/locking gap as
  part of P28B (it's what makes the new sourcing event trustworthy) even though the field belongs
  to Requisition's own aggregate; the Requisition supplier same-organization validation gap is
  lower urgency and can wait for P29.

No source was changed by this audit. Legacy Signal count unchanged at 19.

**P30A — Inventory Reservation: semantic + transaction audit complete (design only, no migration
yet).** Full source re-audit of `reservation_service.py` (5 direct producers: create/issue/
link-document/unlink-document/close, the last shared by release and cancel),
`stock_control_adjustments.py` (`hold_reservation`/`release_reservation`, invoked with
`commit=False` so their own internal audit/emit branch never runs — the caller owns the commit),
`stock_control_movements.py::issue_stock` (the `release_reserved_qty` path), and all 6 consumer
binders. Confirms exactly 5 exact `inventory_reservations_changed.emit(...)` call sites, all
Reservation-owned, no reflective/generic dispatch, no `ApprovalPostCommitEvent` usage (Reservation
has no approval step at all — created directly `ACTIVE`), decomposing into fewer distinct facts
than P17's rough "~5" estimate once document-link churn is set aside:

- **3 Reservation-owned facts, not 5**: created (`create_reservation`), released/cancelled (one
  shared `_close_reservation` producing either terminal status), consumption advanced
  (`issue_reserved_stock` — partial and full issue are the same fact, distinguished only by the
  server-derived resulting status, not a separate business action). **No profile/quantity-update
  operation exists anywhere** (once created, a reservation's item/storeroom/quantity are
  immutable — only status-transition fields ever change), **no separate activation/approval
  step** (status starts at `ACTIVE` on create), and **no expiry**: `need_by_date` is stored but
  never read by any status transition, scheduled job, or query filter anywhere in the module —
  purely informational, not enforced. P17's classes B, C, F, and G (profile-changed,
  activated/approved, expired, allocation-changed) do not exist as real facts for this aggregate.
- **A 4th and 5th producer that are not business facts**: `link_document`/`unlink_document` mutate
  only a `DocumentLink` association, never the reservation's own quantity/status fields, Balance,
  or a ledger row — yet both still call `domain_events.inventory_reservations_changed.emit(...)`.
  The closest sibling precedent, Purchase Order's own `link_document`/`unlink_document`
  (`purchasing_service.py:142-176`), emits **no** legacy signal at all for the equivalent
  operation. Recommend following that precedent: do not model document link/unlink as
  `InventoryReservation*` DomainEvents in P30B — the existing activity/audit trail is sufficient,
  matching P28A's own note that PO document link/unlink is "arguably owned by the already-
  modernized Document capability rather than PO itself."
- **Aggregate**: `StockReservation` — a single flat row per item/storeroom position (no child
  `ReservationLine`; one reservation = one item = one storeroom), `version` field, optimistic
  concurrency. No `location_id` field exists anywhere on the aggregate (Storeroom-level
  granularity only). `requested_by_user_id`/`requested_by_username` are a snapshot of the
  creating principal, not a validated Employee FK.
- **Lifecycle** (`RESERVATION_STATUS_TRANSITIONS`, `application/common/support.py:71-77`):
  `ACTIVE → {PARTIALLY_ISSUED, FULLY_ISSUED, RELEASED, CANCELLED}`,
  `PARTIALLY_ISSUED → {FULLY_ISSUED, RELEASED}`; `FULLY_ISSUED`/`RELEASED`/`CANCELLED` are all
  terminal, confirmed exhaustively from source, not inferred from method names.
- **CRITICAL — Reservation → Stock Balance is a real, persisted mutation, not a derived read**:
  `StockBalance.reserved_qty`/`available_qty` are maintained columns (with a `model_validator`
  invariant, `available_qty == on_hand_qty - reserved_qty`, enforced on every load). `create`
  increments `reserved_qty` via `_post_reservation_transaction` (`RESERVATION_HOLD`); `close`
  (release/cancel) decrements it (`RESERVATION_RELEASE`); `issue_reserved_stock` decrements it via
  `_post_movement_transaction`'s `release_reserved_qty` parameter alongside the on-hand decrease.
  All three run inside the *same* commit as the Reservation row's own write (shared raw `Session`,
  `commit=False` on every internal call, one `self._session.commit()` owned by
  `ReservationService`) — genuine same-transaction cross-aggregate atomicity already exists today,
  just not wrapped in a canonical UoW. `inventory_balances_changed` is correctly co-emitted on
  create/issue/close (not on link/unlink-document, which never touches Balance) — classification
  **B** (real mutation), not **D** (over-notification); Balance itself is explicitly out of P30B
  scope per this phase's own brief and needs no change.
- **Reservation → Ledger**: no separate `InventoryLedger` entity exists anywhere in the codebase
  (confirmed by a repo-wide search) — `StockTransaction` rows *are* the ledger: append-only,
  `RESERVATION_HOLD`/`RESERVATION_RELEASE`/`ISSUE` types, written in the same commit as the
  Balance/Reservation rows, each carrying a `resulting_on_hand_qty`/`resulting_available_qty`
  snapshot. `SqlAlchemyStockTransactionRepository` has no `update()` — genuinely immutable once
  posted.
- **Reservation → Requisition/PO/Receipt: NONE (classification D for all three)**, confirmed by a
  full-module search — zero "reservation" reference anywhere under
  `application/procurement/*` (`procurement_lifecycle.py`, `purchasing_lifecycle.py`,
  `purchasing_receiving.py`). `INVENTORY_SOURCE_REFERENCE_TYPES` (shared by Reservation,
  Requisition, and PO's own `source_reference_type` field) does list `"reservation"` as an
  allowed value — the schema permits a future Requisition/PO to declare a Reservation as its
  source — but no current code path ever sets it; the enum entry is unused, not wired.
  Goods Receipt posting (`purchasing_receiving.py`) has no Reservation interaction at all — does
  not auto-fulfill, allocate to, or change the status of any reservation.
- **Reservation → Project/Task**: `source_reference_type`/`source_reference_id` is the same
  shared free-text pair pattern as Requisition's own (enum-validated against
  `project`/`task`/`work_order`/`reservation`/`requisition`/`purchase_order`, but the ID itself is
  never checked for existence or cross-org membership) — the same source-reference-typing debt
  P29 already documented for Requisition, not resolved here, not worsened here.
- **Transaction ownership**: raw process-lifetime `Session` (`platform_services.session`, shared
  with `StockControlService`), service-owned commit — classification **A**, not a canonical UoW,
  not ApprovalService-owned. Same-transaction multi-repo atomicity (reservation + balance +
  transaction/ledger) is real today, achieved only by every internal call passing `commit=False`
  and one caller-owned `self._session.commit()` — fragile in the sense that it depends on every
  future call site remembering the flag, not enforced by a type.
- **Audit atomicity gap — same class P27A/P28A already found for Requisition/PO's raw-Session
  operations**: `record_activity(...)` for the main action (create/issue/close) is called *after*
  `self._session.commit()` has already succeeded, and defaults to `commit=True` (its own,
  separate transaction). A failure there leaves "mutation committed, audit trail lost," and —
  since the call isn't wrapped in `try`/`except` — would also prevent the legacy
  `inventory_reservations_changed.emit(...)` a few lines later from ever running, compounding
  silent UI staleness on top of the lost audit entry.
- **No-op/idempotency**: no no-op gap to find for "update," because no update/profile-change
  operation exists. Duplicate close (`INVENTORY_RESERVATION_STATUS_INVALID`/
  `INVENTORY_RESERVATION_ALREADY_CONSUMED`) and over-issue
  (`INVENTORY_RESERVATION_QTY_EXCEEDED`) are hard-rejected by explicit guards, not silently
  no-op'd — a deliberate reject pattern, not a gap.
- **Quantity invariants**: `reserved_qty > 0` enforced at creation
  (`normalize_positive_quantity`); `issued_qty <= reserved_qty` enforced both in
  `issue_reserved_stock` (`issue_qty > remaining_qty` guard) and independently in
  `StockReservation`'s own `model_validator`; reserved-vs-available is enforced at the Balance
  layer (`_post_reservation_transaction`'s `new_available < 0` guard). All server-computed, no
  client-supplied `remaining_qty`.
- **Concurrent reservation race — SAFE, verified mechanism, not just sequential tests**: both
  `StockReservation.update()` and `StockBalance.update()` go through
  `update_with_version_check` (`src/infra/persistence/db/optimistic.py`) — an atomic
  `UPDATE ... WHERE id=? AND version=?`. Two concurrent reservations against the same balance can
  both pass the in-app availability check against a stale read, but only the first to commit
  succeeds; the second's version-guarded `UPDATE` affects zero rows and the repository raises
  `ConcurrencyError` (`STALE_WRITE`) before any inconsistent state persists.
  `ReservationService`'s blanket `except Exception: rollback; raise` propagates this untouched to
  the caller — no silent oversubscription.
- **Cross-org/reference integrity**: `_ensure_same_scope` explicitly checks both the Item's and
  Storeroom's `organization_id` against the active organization at creation; no Location field
  exists to independently verify. Requester is a session-principal snapshot, not a separately
  org-checked Employee reference.
- **Read models**: `reservation_list`/`reservation_detail`/`reservation_overview` — all live
  queries through `ReservationService`, no separate cache, owned exclusively by the Reservations
  workspace. Dashboard's "Open Reservations" KPI (`api/desktop/dashboard.py`) is a second genuine
  consumer — a live count of `ACTIVE`/`PARTIALLY_ISSUED` reservations via
  `list_reservations(limit=500)`, no caching. Inventory(Foundation)'s "Stock Balances" table
  displays `reserved_qty`, but that is the **Balance** projection (classification **C**, derived
  from Balance) — already kept fresh by `inventory_balances_changed`, which fires on every
  quantity-affecting Reservation operation; its `inventory_reservations_changed` subscription is
  redundant for that table, not a genuine Reservation dependency.
- **Consumers**: all 6 workspace binders subscribe identically to all 4 remaining raw Inventory
  signals (same fan-out pattern P24/P25/P27A/P28A already found and narrowed for their own
  signals). Re-audit found only Reservations (owner) and Dashboard (KPI) have a real dependency;
  Catalog, Pricing, and Procurement have **zero** "reserv" reference anywhere in their own
  presenter/state-builder trees — the same incidental-subscription pattern already found and
  removed elsewhere; Inventory(Foundation)'s dependency is real but on Balance, not Reservation
  (see above).
- **Proposed DomainEvents**: `InventoryReservationCreated`, `InventoryReservationReleased` /
  `InventoryReservationCancelled` (or one `InventoryReservationClosed{resulting_status}` — an
  open design choice for P30B, not resolved here, mirroring how P28A left PO's own two-vs-one
  event shape choices to its implementation phase), `InventoryReservationConsumptionAdvanced`
  (covers both partial and full issue — `resulting_status` distinguishes them, not a fact split).
  Document link/unlink: no proposed event, per the PO precedent above.
- **Proposed EventScope**: `reservation_list` (`OrganizationScope`) and `reservation_detail`
  (`ResourceScope`, `module_code="inventory_procurement"`, `entity_type="stock_reservation"`) —
  identical shape to Requisition's own P29 target. No project-specific or storeroom-specific scope
  is justified — every real Reservation read model is either org-wide or single-entity.
- **Cross-capability event matrix**: Reservation fact → Balance fact: yes, for create/close/issue
  (existing `inventory_balances_changed` path, unchanged, out of scope); → Ledger fact: yes, a
  `StockTransaction` row for the same three operations (already persisted, no new event needed);
  → Requisition/PO/Receipt fact: none.
- **Recommended sequencing — OPTION A**: P30B can fully retire `inventory_reservations_changed`
  in one phase. Reservation is its sole owner (5 producer sites, zero cross-capability
  producers); no cross-capability mutation blocks clean event ownership (Balance/Ledger stay
  exactly as they are today, by this phase's own explicit scope boundary); the only
  cross-workspace consumer with a genuine dependency (Dashboard's KPI) is trivially
  re-subscribable to a typed event, the same move P29 already made for Dashboard's Requisition
  KPIs. P30B's shape: (1) a new `InventoryReservationUnitOfWork` spanning
  `reservations`/`balances`/`transactions` together (no existing Inventory UoW covers all three;
  this is new, not an Option-A extension of an existing one — unlike P29's reuse of
  `RequisitionSubmissionUnitOfWork`), replacing the current `commit=False`-threaded raw-Session
  pattern with the same atomicity under a canonical UoW; (2) the 3 typed events above; (3) fix the
  audit-atomicity gap as part of convergence (same fix class P27A/P28A each called for their own
  capability); (4) a `ReservationViewInvalidationAdapter` mirroring
  `requisition_view_invalidation_adapter.py`; (5) rewire Reservations + Dashboard onto it; (6)
  drop the redundant subscription entirely from Catalog/Pricing/Procurement/Inventory(Foundation)
  — the last keeps only its already-correct `inventory_balances_changed` subscription; (7) delete
  the 5 legacy emit sites and the `DomainEvents` field.
- `inventory_reservations_changed` **can be deleted in one implementation phase**: prerequisites
  are exactly the 7 items above — no other capability's own modernization needs to happen first
  (unlike PO/Requisition's mutual PO-approval-triggers-Requisition-sourcing blocker).

No source was changed by this audit. Legacy Signal count unchanged at 17.

**Inventory Reservation is fully modernized as of P30B**, implementing P30A's audit exactly as
recommended (Option A: single phase, new `InventoryReservationUnitOfWork` since no existing
Inventory UoW naturally owned this transaction).

| Aspect | Status |
|---|---|
| Reservation transaction ownership | MODERNIZED — new `InventoryReservationUnitOfWork`/`SqlAlchemyInventoryReservationUnitOfWorkFactory` (fresh Session per call, mirrors `InventoryFoundationUnitOfWork`'s shape). Accessors: `reservations`/`balances`/`stock_transactions` (repos), `stock_service` (the existing, unmodified `StockControlService` posting logic rebound to this UoW's own session/repos — Balance/Ledger behavior preserved exactly, not re-implemented), `_enterprise_audit_service`/`_activity_service` |
| Typed DomainEvents | CANONICALIZED — 4 new events in `reservation_events.py`: `InventoryReservationCreated`, `InventoryReservationConsumptionAdvanced` (covers both partial and full issue — `resulting_status` distinguishes them), `InventoryReservationReleased`, `InventoryReservationCancelled` (kept distinct from Released despite sharing the `_close_reservation` implementation helper) |
| Enterprise audit | ADDED — `record_audit_entry(uow, ..., commit=False, fail_closed=True)` now runs atomically with create/issue/release/cancel; previously these paths had zero enterprise audit (best-effort activity-feed only, P30A finding — same gap class P27A/P28A found for Requisition/PO). Proven atomic by a real audit-failure-rollback regression test: Reservation row, Balance row, and StockTransaction row all roll back together, zero postcommit hint escapes |
| Document link/unlink | RESOLVED, P16D-only — confirmed link/unlink mutate only `DocumentLink`, never the Reservation row/Balance/StockTransaction. The legacy `inventory_reservations_changed.emit(...)` in both is deleted with no replacement Reservation event, mirroring PO's own link/unlink (P28A) and P24's identical Item finding. `document_integration_service`'s own P16D-typed `document_links` target is unmodified. Proven by a regression test: zero Reservation DomainEvent, zero `reservation_list`/`reservation_detail`/`reservation_open_count` hints, unchanged `version`/`status` |
| ViewInvalidation targets | `reservation_list` (`OrganizationScope`), `reservation_detail` (`ResourceScope`, `entity_type="stock_reservation"`) — identical shape to Requisition's own (P29). Plus a third, narrower `reservation_open_count` (`OrganizationScope`) reserved for Dashboard's KPI, mirroring `requisition_pending_approval`'s precedent (P29-FIX) |
| Event → invalidation mapping | `Created` → list + open_count only (never detail — no pre-existing detail view can be stale for an id that didn't exist a moment ago, same reasoning P29-FIX applied). `ConsumptionAdvanced`/`Released`/`Cancelled` → list + detail. `open_count` is additionally computed from the KPI's own `{ACTIVE, PARTIALLY_ISSUED}` membership predicate: Created/Released/Cancelled always fire it; `ConsumptionAdvanced` only when `resulting_status == FULLY_ISSUED` — a partial issue keeps the reservation counted and must not stale the KPI. Proven by two dedicated regression tests (one per issue outcome) |
| Consumer cutover | CUT OVER — new `ReservationViewInvalidationAdapter` (mirrors `RequisitionViewInvalidationAdapter`). Reservations workspace (owner): `_request_domain_refresh()` on list or detail staleness. Dashboard: `reservationOpenCountStale`, routed through `_request_domain_refresh` (not a direct `.refresh` connect — P30B-FIX, see below). Catalog/Pricing/Procurement/Inventory(Foundation) legacy subscriptions removed, no replacement (P30A proved zero real Reservation dependency for all four; Inventory(Foundation)'s own Balance-table dependency is unaffected, still served by its unchanged `inventory_balances_changed` subscription). Reservations workspace's own `inventory_balances_changed` subscription — zero real dependency (its "available stock" references are UI copy text) — is also removed, no replacement (**P30B-FIX**, see below) |
| Concurrency | PRESERVED, re-verified — `update_with_version_check` (atomic `UPDATE ... WHERE id=? AND version=?`) unchanged, now exercised through the canonical UoW's own `balances` repo. A genuine two-Session regression test (mirroring P28B's `PurchaseRequisitionLine` race template) proves it: available stock 10, two transactions each reserve 8 against the same stale read; the first commits, the second's version-guarded write raises `ConcurrencyError`, final persisted `reserved_qty` is 8, never 16 |
| Reservation → Balance/Ledger | UNCHANGED BY DESIGN — Reservation genuinely mutates persisted `StockBalance`/`StockTransaction` state via the same, unmodified posting logic; `inventory_balances_changed` continues to be emitted exactly as before. Balance/Ledger remain a separate, still-legacy capability, explicitly out of this phase's scope |
| `inventory_reservations_changed` | DELETED — field, all 5 former producer sites (3 converged to typed events, 2 — document link/unlink — converged to no event at all), all 6 legacy consumer subscriptions. Legacy Signal count: 16 (17 → 16, confirmed via `dataclasses.fields(DomainEvents)`) |

Test coverage added: `src/tests/inventory_procurement/test_p30b_reservation_full_modernization.py`
(legacy-field-deleted proof, Created's list+open_count-only mapping, partial-issue's
open-count-preserving mapping, full-issue's open-count-staling mapping, Released vs Cancelled as
distinct event types, document link/unlink's zero-event proof, an audit-failure-rollback proof for
the new UoW boundary, and the two-Session Balance concurrency race). Full
`src/tests/inventory_procurement/` suite plus `src/tests/architecture/test_service_architecture.py`:
246 passed, 3 pre-existing failures confirmed unrelated (unchanged from P28B/P29's own baseline —
one `source_reference_type` test-data bug and two unrelated import/reporting tests, verified via
`git stash` to fail identically on the pre-P30B baseline).

See ADR-005 §26.27 for the full design.

**P30B-FIX — Remove proven incidental Reservations↔Balance subscription + verify
`reservation_open_count` mapping: one real gap found and closed, no typed-event/UoW/concurrency
change.** P30B's own transaction convergence, typed events, ViewInvalidation targets, and
`inventory_reservations_changed` deletion were approved and out of scope for re-verification. This
follow-up re-examined only two closure items:

- **Gap — Reservations workspace's `inventory_balances_changed` subscription was proven
  incidental, but P30B left it in place.** P30B's own re-audit (P30B §24, not covered by P30A)
  already found zero real Balance dependency for the Reservations workspace — its "available
  stock" references are UI copy text, not a data read — but reasoned that removing it was
  Balance-capability wiring, out of scope. On review that reasoning was wrong: removing a
  *proven-incidental* consumer of a legacy signal changes nothing about Balance itself (its
  producers, business semantics, and every genuine consumer — Inventory(Foundation)'s own "Stock
  Balances" table — are untouched); it is the same class of incidental-subscription cleanup
  already applied to Catalog/Pricing/Procurement earlier in the same phase. Removed, no
  replacement. A regression test proves Reservations workspace reacts to its own
  `ReservationCreated` but not at all to an unrelated Balance-only mutation, and a second proves
  Inventory(Foundation)'s own genuine Balance reaction is unaffected.
- **`reservation_open_count` mapping — verified accurate, no code change needed.** Re-reading
  `build_reservation_view_invalidation_handler` directly confirms the mapping already matches the
  expected source-derived table exactly (see ADR-005 §26.27's mapping table, added by this
  follow-up for full unambiguity): Created/Released/Cancelled always notify `reservation_open_
  count`; `ConsumptionAdvanced` only when `resulting_status == FULLY_ISSUED`. The prior report's
  own prose summary had compressed Released/Cancelled's `reservation_open_count` participation
  into the same clause as their `reservation_list`/`reservation_detail` participation, reading as
  more ambiguous than the actual (correct) implementation — a reporting-clarity issue, not a code
  gap.
- **A third, previously-unverified gap found while building an end-to-end proof of the mapping
  above**: Dashboard's `reservationOpenCountStale` was wired with a direct `.connect(self.
  _dashboard_workspace.refresh)`, identical to PO's/Requisition's own Dashboard connections.
  Unlike PO/Requisition, Reservation is the only capability whose typed events co-occur, in the
  same transaction, with a legacy signal Dashboard already independently reacts to
  (`inventory_balances_changed` — Reservation genuinely mutates Balance): Created, a full issue,
  Released, and Cancelled each risked a double `refresh()` call — once via the direct typed
  connection, once via the legacy binder's `_request_domain_refresh()`. Fixed by routing
  `reservationOpenCountStale` through `_request_domain_refresh` instead — the same coalescing
  entrypoint the legacy binder already uses, collapsing both triggers into one rebuild per
  transaction under a live Qt event loop (P29-FIX's own established remedy for this exact class of
  problem). PO's/Requisition's own direct-`.refresh` Dashboard connections are untouched — neither
  co-emits a legacy signal alongside its typed events (P28A/P30A), so this risk class does not
  apply to them.
- **What did NOT change**: `InventoryReservationUnitOfWork`, the typed event vocabulary, the
  concurrency mechanism, enterprise audit, Balance/StockTransaction mutation behavior, and P16D
  document-link ownership are all untouched. `inventory_reservations_changed` remains deleted
  (producers 0, consumers 0, field absent); `inventory_balances_changed` remains present, its own
  producers and every genuine consumer unmodified — only one proven-incidental *consumer* was
  removed, not the signal itself.
- Legacy Signal count unchanged: 16. `inventory_reservations_changed`/`inventory_purchase_orders_
  changed`/`inventory_requisitions_changed` all remain deleted; producers/consumers remain 0 for
  all three. `inventory_balances_changed`'s own consumer count dropped by exactly one (Reservations
  workspace) — recorded here as a consumer-wiring correction, not misreported as a second Signal
  deletion.

See ADR-005 §26.27 for the full design (updated in place with this correction and the explicit
mapping table).

**P31A — Stock Balance + StockTransaction/Ledger: system-wide semantic + transaction audit
complete (design only, no migration yet).** Full source re-audit, deliberately going beyond
`StockControlService` per this phase's own explicit instruction — traced every capability capable
of writing `StockBalance`: Reservation, Purchase Order (approve/cancel), Goods Receipt, Cycle
Count, and Inventory(Foundation)'s own manual stock-movement operations. Confirms 9 exact
`inventory_balances_changed`-producing mechanisms across 5 files, no reflective/generic router
beyond the one `ApprovalPostCommitEvent` bridge already known from P28A, and finds a genuine
silent-mutation gap P30A/P30B's own narrower scope never had reason to surface.

- **9 producer mechanisms, not one**: `stock_control_adjustments.py:314`
  (`_post_transaction`, backing `post_opening_balance`/`post_adjustment`), `:424`
  (`_post_reservation_transaction`, backing `hold_reservation`/`release_reservation` — live for any
  future direct caller, but its sole current caller is Reservation's own UoW, always
  `commit=False`, so this exact line never fires in practice today);
  `stock_control_movements.py:183`/`:185` (`transfer_stock`'s two legs, source + destination
  balance) and `:344` (`_post_movement_transaction`, backing `issue_stock`/`return_stock`);
  `reservation_service.py:588` (P30B's own post-UoW-commit re-emission);
  `purchasing_receiving.py:287` (`post_receipt`, post-UoW-commit, per touched balance) and `:418`
  (`apply_submitted_purchase_order_approval`, via the legacy `ApprovalPostCommitEvent` reflective
  bridge — a different production mechanism than every other site's direct `.emit()`);
  `foundation_service.py:744` (`complete_cycle_count`, post-`self._session`-commit, only when
  variance is nonzero). All 9 confirmed by a repo-wide grep, not assumed from
  `StockControlService`'s own surface.
- **A genuine, previously-undocumented silent-mutation gap**: `purchasing_lifecycle.py::
  cancel_purchase_order` mutates `on_order_qty` (via the same `_adjust_on_order_balance` helper
  approval uses to increment it) but contains **zero** `inventory_balances_changed` references
  anywhere in that file — confirmed by a dedicated grep. A cancelled PO's on-order reversal is a
  real Balance mutation with no legacy notification at all; any consumer relying solely on the
  legacy signal shows a stale on-order figure until an unrelated refresh happens. Not fixed here
  (P31A is audit-only) — flagged as a concrete prerequisite for P31B, and as a defect this phase
  should close rather than carry forward as "legacy behavior."
- **`StockBalance` writers, independent of signal correctness** (this phase's own §2 mandate — do
  not assume every mutation is correctly signalled): confirmed exactly 3 code paths can create the
  *first* balance row for a position — `_post_transaction` (opening balance/adjustment),
  `_post_movement_transaction` (`RETURN`/`TRANSFER_IN` only), and `_adjust_on_order_balance` (PO
  approval). All persisted mutations funnel through exactly two repository methods
  (`SqlAlchemyStockBalanceRepository.add`/`.update`) regardless of which of the 9 producer call
  sites or 5 capabilities originates the write — confirmed no other write path exists (no direct
  ORM instantiation outside the mapper, no bulk-import path, no migration seed data).
- **`StockBalance` role: HYBRID, not the simple "maintained aggregate" P30A's narrower audit
  described**. `on_hand_qty`/`reserved_qty`/`on_order_qty` are genuinely independently maintained,
  authoritative running totals (classification A) — each mutated by a different capability with no
  single owner. `available_qty` is **strictly derived**, not independently writable: a
  `model_validator` enforces `available_qty == on_hand_qty - reserved_qty` on every construction —
  confirmed no writer ever sets it inconsistently, so it needs no independent event/write path of
  its own (classification B for this one field only). `committed_qty` exists in the schema (ORM,
  mapper, domain, serializers, UI) but is **never mutated by any current business operation** —
  confirmed by a repo-wide grep across every posting method — a vestigial, always-zero field, not
  a maintained dimension. Identity: `UniqueConstraint(organization_id, stock_item_id,
  storeroom_id)` — **no `location_id`** in the key; Balance has no location-level granularity
  despite `StorageLocation` existing as a separate hierarchy. `version` is the optimistic
  concurrency column, incremented on every `update()`.
- **`StockTransaction` role: immutable, append-only business ledger** — confirmed no `update()`
  method exists on its repository. Exactly 9 `StockTransactionType` values, exhaustively
  enumerated from source (not inferred): `OPENING_BALANCE`, `ADJUSTMENT_INCREASE`,
  `ADJUSTMENT_DECREASE`, `ISSUE`, `RETURN`, `TRANSFER_OUT`, `TRANSFER_IN`, `RESERVATION_HOLD`,
  `RESERVATION_RELEASE`. **No dedicated `RECEIPT` type** — Goods Receipt posts as
  `ADJUSTMENT_INCREASE` with `reference_type="inventory_receipt"`. **No dedicated `CYCLE_COUNT`
  type** — Cycle Count posts as `ADJUSTMENT_INCREASE`/`DECREASE` with
  `reference_type="cycle_count"`. **`on_order_qty` changes never produce a `StockTransaction` row
  at all** — `_adjust_on_order_balance` (PO approve/cancel, Receipt's on-order decrement) mutates
  Balance directly with no ledger entry; this is consistent, not a bug, but means the ledger has no
  provenance for the entire on-order dimension. `reference_type`/`reference_id` are free-form text
  (`normalize_optional_text`, no enum), unlike `StockReservation`'s own enum-constrained
  `source_reference_type` — less strict provenance than Reservation's own source references. No
  reconciliation capability (Balance vs. `sum(StockTransaction)`) exists anywhere in source —
  confirmed by a targeted grep — Balance is independently maintained, never derived-on-read from
  the ledger.
- **Balance↔Ledger atomic consistency, confirmed by capability**: every on-hand/reserved-affecting
  operation writes Balance + `StockTransaction` in the same transaction/session across all 5
  producer files — no path found where one commits without the other for those two fields.
  `on_order_qty` changes simply never touch the ledger (see above) — the "consistency model"
  doesn't apply there, there is nothing to be inconsistent with.
- **Reservation → Balance** (recap only, P30B unchanged): create → `reserved_qty` +=; issue
  (partial/full) → `on_hand_qty` -=, `reserved_qty` -= (via `issue_stock`'s
  `release_reserved_qty`); release/cancel → `reserved_qty` -=. All atomic with `StockTransaction`
  (`RESERVATION_HOLD`/`RESERVATION_RELEASE`/`ISSUE`) and, since P30B, atomic with enterprise audit
  too via `InventoryReservationUnitOfWork`.
- **Purchase Order → Balance, reconfirmed with exact operations**: approve → `on_order_qty` +=
  `quantity_ordered` per line, via `ApprovalService`'s own fresh Session/UoW, producer via the
  legacy `ApprovalPostCommitEvent` bridge (not a direct `.emit()`), no `StockTransaction`, no
  enterprise-audit call for the Balance mutation specifically (only an activity-feed entry for the
  PO approval itself). Cancel → `on_order_qty` -= outstanding per line (only if the PO was ever
  approved — `prior_status != DRAFT`), via the canonical `PurchaseOrderSubmissionUnitOfWork`, no
  `StockTransaction`, **no legacy signal at all** (the gap above). Reject → no Balance touch
  (on-order was never incremented). Send/Close → no Balance touch, confirmed from source.
- **Goods Receipt → Balance, critical finding — Receipt is already on a canonical UoW**:
  `post_receipt` reuses the **same** `PurchaseOrderSubmissionUnitOfWork` PO's own
  create/submit/cancel commands use (`self._require_purchase_order_uow_factory()`), not a raw
  Session. Per accepted receipt line: `on_hand_qty` += accepted, via a fresh `StockControlService`
  bound to the *same* UoW session (built by `_build_purchase_order_receiving_collaborators`,
  mirroring exactly the "capability-UoW-session → fresh `StockControlService`" pattern P30B later
  used for Reservation) — writes a real `ADJUSTMENT_INCREASE` `StockTransaction`. Separately,
  `on_order_qty` -= processed (accepted+rejected) via `_adjust_on_order_balance` on the same UoW's
  `balances` repo — no `StockTransaction`, confirming even a *rejected* line still consumes PO
  open-quantity even though nothing enters stock. Enterprise audit: atomic (`record_audit_entry`
  for the receipt itself, `fail_closed=True`, inside the same UoW). Legacy signals
  (`inventory_receipts_changed` always, `inventory_balances_changed` per touched balance) both
  emitted post-commit. **This directly resolves this phase's central sequencing question**:
  Receipt's transaction boundary needs no work to host a canonical Balance event.
- **Cycle Count → Balance, confirms "counting ≠ changing stock" cleanly**: `schedule_cycle_count`
  only *reads* Balance for an `expected_qty` snapshot, no mutation. `complete_cycle_count` mutates
  Balance **only when `variance != 0`** (`abs(variance) > 1e-9`), via
  `self._stock_service.post_adjustment` (direction from variance sign, `reference_type=
  "cycle_count"`) — writes a real `StockTransaction`. Transaction boundary: **raw
  `self._session`**, not `InventoryFoundationService`'s own `InventoryFoundationUnitOfWork` — that
  UoW is imported and already used by three *other* methods in the same class (Storeroom/Location
  create/update, confirmed at lines 175/298/487), but Cycle Count's own two methods bypass it
  entirely, `self._session.commit()` directly. Zero enterprise audit (`record_audit_entry` is never
  called from either method — activity-feed only, and even that runs after the commit, the same
  non-atomic-audit gap class P27A/P28A/P30A each found for their own raw-Session capability). Both
  legacy signals emitted post-commit, `inventory_balances_changed` conditionally.
- **Other Balance mutations — Inventory(Foundation)'s own manual stock operations, a distinct
  producer group P30A's narrower scope never covered**: `post_opening_balance`, `post_adjustment`,
  `issue_stock`, `return_stock`, `transfer_stock` are all directly callable from the Inventory
  workspace's own "Recent Movements" panel (`api/desktop/inventory/movements.py`), every call site
  using `StockControlService`'s **default `commit=True`** — meaning `StockControlService` is its
  own transaction owner here (raw Session, self-contained mini-transaction), not participating in
  any capability UoW. Zero enterprise audit for any of the five. No duplicate-submission guard for
  four of the five (`post_adjustment`/`issue_stock`/`return_stock`/`transfer_stock`);
  `post_opening_balance` alone has a one-time-only guard (rejects if any transaction already exists
  for that position). `transfer_stock` mutates two Balance rows (source `TRANSFER_OUT`,
  destination `TRANSFER_IN`) and writes two `StockTransaction` rows, both legs posted with
  `commit=False` internally then one outer `self._session.commit()` — genuinely atomic across both
  rows, then two direct `.emit()` calls (one per balance) after commit.
- **First-balance-creation race — SAFE, but with real error-quality gaps**: the DB-level
  `UniqueConstraint(organization_id, stock_item_id, storeroom_id)` prevents a genuine duplicate
  row — the losing concurrent `INSERT` raises `IntegrityError`, caught by the surrounding
  `except IntegrityError` in `_post_transaction`/`_post_movement_transaction`. But that handler
  unconditionally reports `"Stock transaction number already exists"` even when the real cause is
  the *Balance* unique-constraint collision, not the (separately-constrained)
  `StockTransactionORM.transaction_number` one — a misattributed error message, not a correctness
  gap. `_adjust_on_order_balance` (PO approve/cancel/Receipt) has **no** `try`/`except
  IntegrityError` of its own around its `repo.add(...)` call — a first-row race hit via PO approval
  would propagate a raw, unwrapped SQLAlchemy `IntegrityError` all the way to the caller — safe (no
  duplicate row, no silent corruption) but a worse error-UX gap than the misattributed-message
  case. Neither is fixed here.
- **Quantity invariants, exhaustive, service-layer only (no DB `CheckConstraint` exists
  anywhere for any of these)**: `on_hand_qty >= 0`, `reserved_qty >= 0`, `on_order_qty >= 0`
  (each an explicit `ValidationError` guard in its own posting method); `available_qty ==
  on_hand_qty - reserved_qty` (hard `model_validator`, every construction); issue quantity ≤
  available (via the combined on-hand/reserved guard); release quantity ≤ reserved (guarded at
  both the Reservation row and the Balance row); receipt quantity ≤ remaining PO quantity (explicit
  `INVENTORY_RECEIPT_EXCEEDS_OPEN_QTY` check); a cycle-count correction that would drive on-hand
  negative is **rejected**, not applied (same generic on-hand ≥ 0 guard — a live business question
  worth flagging, not resolved here: a physical count correction is arguably supposed to win over
  this guard, since it exists precisely to correct system state to physical reality); transfer-out
  is bound by the same on-hand ≥ 0 guard.
- **`available_qty` semantics: persisted but strictly derived**, confirmed via the
  `model_validator` above — no writer ever needs to independently compute or carry it; a future
  Balance event needs only `on_hand_qty`/`reserved_qty` (or their delta) to let a consumer derive
  `available_qty` itself, or can carry the resulting value as a convenience field.
- **Concurrency mechanism: uniform across every producer**, confirmed — all Balance writes funnel
  through the same `SqlAlchemyStockBalanceRepository.update()`, which uses
  `update_with_version_check` (atomic `UPDATE ... WHERE id=? AND version=?`), regardless of which
  of the 5 capabilities or which Session/UoW originates the write. No `SELECT FOR UPDATE` anywhere
  — purely optimistic, never pessimistic. No automatic retry anywhere — `ConcurrencyError`
  propagates to the caller in every case. **Whole-row optimistic versioning, confirmed and
  reported as instructed, not treated as a defect**: because `update()` writes every column from
  the caller's own (possibly stale-in-other-fields) read, two capabilities changing *different*
  fields on the *same* balance row concurrently (e.g. Reservation's `reserved_qty` vs. Receipt's
  `on_hand_qty`) will still conflict at the version level even though their fields don't logically
  overlap — a real, safety-preserving but contention-increasing characteristic of the current
  design, not something P31A resolves.
- **`StockControlService`'s architectural role: mixed, dual-mode by design, not accidental**. It
  simultaneously holds Balance/Ledger invariants (average-cost calculation, quantity-delta
  resolution, the `reorder_required` formula, every negative-quantity guard) *and* acts as its own
  transaction owner when called with the default `commit=True` (every manual-movement call site)
  — but cleanly accepts an externally-owned Session/UoW when called with `commit=False`
  (Reservation's own UoW since P30B, Receipt's PO UoW, Cycle Count's raw `self._session`). Public
  mutation surface: `post_opening_balance`, `post_adjustment`, `hold_reservation`,
  `release_reservation`, `issue_stock`, `return_stock`, `transfer_stock` (7); reads:
  `list_balances`, `get_balance`, `get_balance_for_stock_position`, `list_transactions`.
  `_adjust_on_order_balance` (the on-order mutator) lives **outside** `StockControlService`
  entirely, as PO's own private helper in `purchasing_support.py` — on-order mutation bypasses
  `StockControlService` completely, a distinct architectural seam from every on-hand/reserved
  mutation. Legacy-signal emission only happens inside `StockControlService`'s own methods when
  `commit=True`; every `commit=False` caller (Reservation, Receipt, Cycle Count) correctly
  re-emits it themselves, externally, post their own outer commit.
- **No service locator, confirmed clean**: every capability UoW that needs
  `StockControlService` constructs a **fresh instance bound to its own session** at UoW-
  construction time — Reservation's `InventoryReservationUnitOfWork` (P30B) and Receipt's
  `_build_purchase_order_receiving_collaborators` factory both follow the identical
  "capability-UoW-session → fresh `StockControlService`" pattern, proven twice already. The one
  process-wide shared instance (`inventory_stock_service` in `inventory_registry.py`) is plain,
  explicit constructor injection — passed by name into Cycle Count, Manual Movements, and
  Dashboard's read-only balance queries — never a `container.get()`/`repository_for()`/global
  singleton resolution. Dependency direction is consistently one-way: capability → session →
  service, never the reverse.
- **Event ownership recommendation (§21's core question) — Option A**: since Balance mutation
  already happens *inside* the originating capability's own transaction (confirmed for all 5
  groups above), the originating capability's own UoW should record **both** its own typed event
  and a separate Balance-fact typed event in the same `uow.record_event(...)` sequence — exactly
  the multi-event-per-operation pattern PO approval already uses today
  (`PurchaseOrderApproved` + `InventoryRequisitionSourcingAdvanced` from one operation). Option C
  (a transactional handler reacting to the originating event to *perform* the mutation) is invalid
  here, as the brief itself anticipated: the mutation already happened before any event dispatch —
  a reactive handler would either duplicate the write or run too late.
- **Proposed Balance event vocabulary — narrow, field-oriented, not movement-type-oriented**:
  `StockOnHandQuantityChanged`, `StockReservedQuantityChanged`, `StockOnOrderQuantityChanged`.
  Chosen over a 9-event movement-type-mirroring vocabulary (would recreate the legacy signal's own
  overload risk) and over a single generic `StockBalanceChanged`/`InventoryStockBalanceUpdated`
  (would recreate the exact problem this phase exists to solve — Dashboard's dedicated "On Order
  Qty" KPI and Pricing's `on_order_qty`-only metric must not refresh on a Reservation-only change,
  mirroring the exact class of over-notification P30B already fixed once for
  `reservation_open_count`). `issue_stock` touches both on-hand and reserved in one call — record
  **both** events from that one operation, the same multi-event pattern as PO approval. Not
  recorded here as a decision, only as the recommended shape.
- **Separate Ledger DomainEvents: NOT recommended.** No consumer or business process was found
  anywhere in this audit reacting specifically to "a `StockTransaction` was posted" independent of
  the Balance-quantity fact itself — Inventory(Foundation)'s own "Recent Movements" panel is
  rebuilt by the same monolithic `refresh()` as its Balance table, already covered by the Balance
  events' own ViewInvalidation target. `StockTransaction` remains a pure persistence/ledger
  mechanism, not a DomainEvent-worthy capability of its own.
- **Proposed event payload identity: `balance_id`** (the persisted `StockBalance.id` surrogate
  key) as the `ResourceScope` `entity_id` — already the exact payload every current legacy
  `.emit(balance.id)` call site uses, already stable for the row's lifetime. Not a compound
  organization+item+storeroom string.
- **Proposed `EventScope`**: `stock_balance_list` (`OrganizationScope`) and `stock_balance_detail`
  (`ResourceScope`, `module_code="inventory_procurement"`, `entity_type="stock_balance"`,
  `entity_id=balance_id`) — no separate storeroom-filtered scope is justified; every current
  consumer filters the same org-wide collection live/client-side at query time, confirmed from
  source, matching P20's own established storeroom-scope precedent. A third, narrower target for
  Dashboard's/Pricing's on-order-only KPIs (mirroring P30B's `reservation_open_count`) is a P31B
  design candidate, not decided here.
- **Balance consumers — recomputed from current source, field-by-field, not inherited from prior
  phases' labels (this phase's own explicit instruction)**: P30B's own "5 genuine consumers"
  characterization for `inventory_balances_changed` (Catalog, Dashboard, Inventory(Foundation),
  Pricing, Procurement) is **only 3/5 accurate on independent re-verification** — Catalog and
  Procurement have **zero** real Balance-field reference anywhere in either their desktop-API
  *or* QML-presenter layers (confirmed by an exhaustive keyword sweep of every file in both
  layers for every Balance field name plus `StockBalance`/`stock_service`/`stock_report`) — the
  same class of incidental-subscription mislabeling this document's own P30B-FIX entry just
  corrected for a different signal. **Dashboard (genuine)**: of 8 metrics, exactly 3 are
  Balance-derived and each depends on a *different* field subset — "Stock Positions"
  (`len(balances)`, row-count only), "Low Stock" (`reorder_required` for row membership;
  `available_qty`/`reserved_qty`/`on_order_qty` for row content — `reorder_required` itself is
  computed only from `on_hand_qty`/`reserved_qty` vs. `item.reorder_point`, confirmed **never**
  recomputed by `_adjust_on_order_balance`, so a PO-only on-order change never staless this row
  set), "On Order Qty" (`sum(on_order_qty)` **only** — the cleanest single-field dependency found
  in the whole audit). **Pricing (genuine, and considerably deeper than previously assumed)**:
  its own `stock_report` (feeding both its workspace snapshot metrics/rows *and* its CSV/Excel
  stock-status export) reads `reorder_required`, `on_order_qty`, `reserved_qty`, `available_qty`,
  `average_cost`, `uom`, `last_receipt_at`, `last_issue_at` — confirmed at
  `api/desktop/pricing/api.py` (not merely the UI-copy-text "reserved" this document's own earlier
  P30A entry found when it checked only the QML-presenter layer for Reservation specifically, not
  Balance). **Inventory(Foundation) (genuine, primary owner)**: its own serializer exhaustively
  round-trips every `StockBalance` field — `on_hand_qty`, `reserved_qty`, `available_qty`,
  `on_order_qty`, `committed_qty` (even the vestigial always-zero one), `average_cost`,
  `reorder_required` — plus `StockTransaction`'s `resulting_on_hand_qty`/`resulting_available_qty`
  in the same monolithic "Stock Balances" + "Recent Movements" workspace, confirmed from source,
  not inferred from its own subtitle text.
- **Proposed ViewInvalidation consumer cutover shape (design only)**: Dashboard subscribes only to
  `StockOnHandQuantityChanged`/`StockReservedQuantityChanged` for "Low Stock"/"Stock Positions"
  and only to `StockOnOrderQuantityChanged` for "On Order Qty" — three narrow reactions instead of
  one blanket refresh. Pricing and Inventory(Foundation), given their much broader field
  dependency, subscribe to all three onto their own existing monolithic `refresh()` — the same
  "broad refresh for the owning workspace is acceptable" precedent already established for every
  other Inventory capability. Catalog and Procurement's subscriptions are removed outright, no
  replacement.
- **Recommended sequencing — OPTION A**: Balance can modernize before Receipt or Cycle Count
  modernize as their own capabilities. Receipt needs zero transaction-boundary work (already
  canonical, confirmed above). Cycle Count and Manual Movements need their raw-Session Balance-
  mutating code paths moved onto a canonical UoW — either a new one or an extension of the
  already-existing `InventoryFoundationUnitOfWork` (which already covers three sibling methods in
  the same class) — but this is transaction-boundary work for the *Balance mutation code path
  itself*, not "modernizing Cycle Count/Manual-Movements as their own capabilities": their own
  legacy signals (`inventory_cycle_counts_changed`) and UI stay untouched, exactly mirroring how
  P28B gave PO's approval-triggered Requisition-sourcing mutation its own typed event years ahead
  of Requisition's own full P29 modernization.
- **`inventory_balances_changed` can be deleted in one P31B**, with these prerequisites: (1) all 9
  current producer mechanisms converge onto the 3-event vocabulary in their own existing (Reservation,
  PO approve/cancel, Receipt) or minimally-extended (Cycle Count, Manual Movements) transactions;
  (2) the PO-cancel missing-signal gap is closed as part of adding its typed event (the same code
  path, not separate work); (3) Cycle Count's and Manual Movements' raw-Session paths gain a
  canonical UoW; (4) the 3 genuine consumers (Dashboard, Inventory(Foundation), Pricing) cut over;
  (5) the 2 incidental consumers (Catalog, Procurement) drop their subscription, no replacement;
  (6) field deleted. Larger in scope than P30B (5 capability groups, not 1) but not architecturally
  blocked by anything external — every pattern required is already proven at least once elsewhere
  in this codebase.

No source was changed by this audit. Legacy Signal count unchanged at 16.

**Inventory Stock Balance is fully modernized as of P31B**, implementing P31A's audit exactly as
recommended (Option A: single phase, distributed transaction ownership preserved — no centralized
Balance mega-UoW).

| Aspect | Status |
|---|---|
| Typed DomainEvents | CANONICALIZED — 3 new events in `balance_events.py`: `StockOnHandQuantityChanged`, `StockReservedQuantityChanged`, `StockOnOrderQuantityChanged` — field-oriented, not movement-type-oriented (would have recreated the legacy signal's own overload) and not a single generic `StockBalanceChanged` (would have recreated its imprecision). Each carries `balance_id`/`stock_item_id`/`storeroom_id`/`quantity_delta`/`resulting_quantity`, computed as `resulting − previous` rather than re-derived from a caller's line-UOM quantity (avoids duplicating UOM-conversion math) |
| Transaction ownership | DISTRIBUTED, preserved per capability — Reservation records its own Balance fact in its own `InventoryReservationUnitOfWork` (P30B, unchanged); PO approval records its own in `ApprovalService`'s own `PlatformUnitOfWork`; PO cancel and Receipt record theirs in the shared `PurchaseOrderSubmissionUnitOfWork` (already canonical, no transaction-boundary work needed — P31A's own finding confirmed); Cycle Count and Inventory(Foundation)'s manual stock movements (opening balance/adjustment/issue/return/transfer) converged onto the *existing* `InventoryFoundationUnitOfWork` (P20), extended with `cycle_counts`/`balances`/`stock_transactions` repos and a `stock_service` accessor — the same "capability-UoW-session → fresh `StockControlService`" pattern P30B/Receipt already proved, not a new architecture |
| `StockControlService` | PRESERVED exactly as P31A characterized it — dual-mode (self-owned transaction by default, clean `commit=False` participant otherwise), reused unmodified by every writer. One narrow, consistent addition: `transfer_stock` gained the same `commit: bool = True` parameter every sibling method already had (it previously always self-committed, which would have prematurely committed a caller's UoW) — not a broader refactor |
| Reservation → Balance | UNCHANGED mutation behavior, now records `StockReservedQuantityChanged` (create/release/cancel) and both `StockReservedQuantityChanged` + `StockOnHandQuantityChanged` (issue, from the one call that mutates both fields) in place of the retired `_emit_legacy_balance_signal` |
| PO approval → Balance | Records `StockOnOrderQuantityChanged` via `ApprovalHandlerResult.domain_events` — the reflective `ApprovalPostCommitEvent("inventory_balances_changed", ...)` bridge is deleted, not left coexisting |
| PO cancel → Balance | **P31A's confirmed silent-mutation gap is fixed** — `cancel_purchase_order`'s on-order reversal (for a PO cancelled past `DRAFT`) now records `StockOnOrderQuantityChanged`; previously emitted nothing at all. Proven by a dedicated regression test |
| Receipt → Balance | Records both `StockOnHandQuantityChanged` and `StockOnOrderQuantityChanged` per accepted/processed line, in the same already-canonical UoW; `inventory_receipts_changed` is unchanged/retained — Receipt itself is not modernized as a capability |
| Cycle Count → Balance | Converged onto `InventoryFoundationUnitOfWork`; records `StockOnHandQuantityChanged` only when `abs(variance) > 1e-9` — a zero-variance completion mutates nothing and records nothing, preserving "counting ≠ changing stock". Gains real atomic enterprise audit for the first time (previously zero, P31A finding); `inventory_cycle_counts_changed` is unchanged/retained |
| Manual stock movements | `post_opening_balance`/`post_adjustment`/`issue_stock`/`return_stock`/`transfer_stock` moved from the desktop API calling the raw shared `StockControlService` instance directly (self-committing, `movements.py`) to calling 5 new `InventoryFoundationService` methods that open the UoW, delegate to `uow.stock_service.*(commit=False)`, record the Balance fact(s), and commit. Each also gains atomic enterprise audit for the first time (previously zero). `transfer_stock` records two distinct `StockOnHandQuantityChanged` facts (source + destination), not one org-wide event |
| Concurrency | PRESERVED — every writer still funnels through the same `update_with_version_check`. A genuine two-Session cross-capability test (manual on-hand adjustment vs. a reservation hold on the *same* balance row) proves whole-row optimistic versioning still rejects the loser with `ConcurrencyError`, no lost update |
| Consumer cutover | New `StockBalanceViewInvalidationAdapter` (`stockBalanceListStale`/`stockBalanceDetailStale`, mirroring every prior typed adapter). Inventory(Foundation), Pricing, and Dashboard — all 3 re-confirmed genuine by this phase's own field-level re-audit (correcting P30B's stale "5 genuine" label to 3, per P31A) — subscribe to both signals via `_request_domain_refresh`, matching the coalescing-safe pattern P30B-FIX established. Catalog and Procurement's legacy subscriptions are removed outright, no replacement — proven zero-reaction by a dedicated regression test. All 3 typed events route to the *same* two targets (`stock_balance_list`/`stock_balance_detail`) because every genuine consumer's own field-level audit showed a dependency spanning all three quantity dimensions, not because field-sensitivity was skipped (see the handler's own docstring for the full reasoning) |
| `inventory_balances_changed` | DELETED — field, all 9 former producer mechanisms (8 direct `.emit()` sites across `stock_control_adjustments.py`/`stock_control_movements.py`/`reservation_service.py`/`purchasing_receiving.py`/`foundation_service.py`, plus the 1 reflective `ApprovalPostCommitEvent` bridge), all 5 legacy consumer subscriptions. The one confirmed-dead `.emit()` site (`_post_reservation_transaction`'s own unreachable `if commit:` branch) was deleted along with the rest, not converted. Legacy Signal count: 15 (16 → 15, confirmed via `dataclasses.fields(DomainEvents)`) |

Test coverage added: `src/tests/inventory_procurement/test_p31b_stock_balance_full_modernization.py`
(legacy-field-deleted proof, per-capability event-recording proofs for Reservation/PO-approve/
PO-cancel/PO-reject/Receipt/Cycle-Count-zero-variance/Cycle-Count-nonzero-variance/manual-
adjustment/manual-transfer, two atomicity-rollback proofs for Cycle Count's and Manual Movements'
newly-atomic audit, the cross-capability two-Session concurrency race, and consumer-cutover proofs
for both the 3 genuine and 2 incidental workspaces). One existing P30B-FIX test
(`test_real_inventory_workspace_still_reacts_to_balance_mutation`) was updated in place — its
Balance-mutation call site moved from the raw `inventory_stock_service` instance to
`inventory_foundation_service.post_adjustment`, the new canonical entry point; its exact-one-
refresh assertion was relaxed to "reacted at all" since asserting an exact call count depends on a
live Qt event loop's `QTimer(0)` coalescing (P29-FIX), which this synchronous test harness does not
run — the same class of test-environment limitation already accepted elsewhere in this suite, not
a production behavior change. Full `src/tests/inventory_procurement/` suite plus
`src/tests/architecture/test_service_architecture.py`: 268 passed, 3 pre-existing failures
confirmed unrelated (unchanged from P30B/P30B-FIX's own baseline — one `source_reference_type`
test-data bug and two unrelated import/reporting tests).

See ADR-005 §26.28 for the full design.

## 4. Current State

**Legacy Signal count: 15 as of P31B** (source-derived from
`src/core/shared/events/domain_events.py`, re-verified against current source when this document
was last updated — `dataclasses.fields(domain_events)`, not a manual field count).

| Area | Count |
|---|---|
| Platform | 0 |
| Auth/Security | 1 |
| Project Management | 6 |
| Finance | 6 |
| Inventory/Procurement | 2 |

> **This is a snapshot, not a fact.** Recompute the count directly from
> `src/core/shared/events/domain_events.py` before relying on it - do not trust this table if it
> is more than a few phases old. Concurrent development in any module can add or remove fields
> between updates to this document.

## 5. Current Priority

**Purchase Order, Inventory Requisition, Inventory Reservation, and Stock Balance are all fully
modernized** (P28B/P28B-FIX/P29/P29-FIX/P30B/P30B-FIX/P31B, see §3). `inventory_purchase_orders_changed`,
`inventory_requisitions_changed`, `inventory_reservations_changed`, and `inventory_balances_changed`
are all deleted — zero producers, zero consumers, fields absent. Inventory/Procurement's remaining
legacy signals (2: `inventory_receipts_changed`, `inventory_cycle_counts_changed`) cover Goods
Receipt and Cycle Count as their own capabilities — both continue to genuinely mutate Balance in
their existing transactions and now correctly record the typed Balance facts alongside their own
still-legacy signal (P31B), exactly mirroring the precedent P30B set for Reservation. **No next
capability has been chosen/committed yet.** Per this
document's own repeated caution, re-run prioritization from current source before committing to a
target — concurrent development elsewhere may have changed readiness since P17/P26A. **Auth
Credential & Session remains AUDITED / DEFERRED** (P26A, see §3) — still not recommended given no
canonical UoW exists yet on that surface.

**P28B/P28B-FIX/P29/P29-FIX/P30B/P30B-FIX/P31A/P31B's own explicit non-gaps, resolved rather than carried forward**: the
Procurement-workspace-refresh-breadth note from P28B (full `_request_domain_refresh()` on either
PO/Requisition ViewInvalidation target, matching its pre-existing monolithic `build_workspace_state`)
remains accepted, unaddressed future work, not a phase gap — no narrower seam existed before P28B
either. The supplier same-organization "gap" P27A/P28A/P28B all carried forward as
"unverified"/"real" was investigated in P29 and found not to exist (see §3's P29 entry) — closed as
a documentation correction, not a code fix.

## 6. Provisional Roadmap

This is a **provisional sequence from the P17 system-wide ranking, not a permanent commitment.**
Re-run prioritization after each major capability - current source is authoritative, and
concurrent development elsewhere in the codebase may change any capability's readiness before
its turn comes up.

P18 Project Resource, P19 Finance Forecast, P20 Inventory Storeroom/Location, P21 Finance
Financial Setup, P22 Finance Rate Card, P23 PM Baseline Approval, P24 Inventory Item Catalog +
Item Category, and P25 Inventory Reorder Policy are all DONE (see §3). No further phase has a
number assigned yet — see the remaining capability groups below.

Remaining capability groups, not yet assigned rigid phase numbers:

- **Project Management**: Task Lifecycle (highly overloaded - split into ~9 real facts before
  any typed-event design), Project Lifecycle, Timesheet Period, Collaboration
  Comment (+ Collaboration Presence, which needs a non-`DomainEvent` mechanism, not a migration
  target), Portfolio (Template/Scenario/Intake/Dependency), Risk Register.
- **Finance**: Financial Change, Project Commitment (fix the missing-rollback bug in
  `commitment_service.py` first), Project Cost Entry, Project Budget, Planned Cost, Billing
  Preparation.
- **Inventory/Procurement**: **Purchase Order — DONE (P28B/P28B-FIX, see §3)**, **Requisition —
  DONE (P29/P29-FIX, see §3)**, **Reservation — DONE (P30B/P30B-FIX, see §3)**, and **Stock
  Balance — DONE (P31A/P31B, see §3)**, all four fully modernized:
  `inventory_purchase_orders_changed`, `inventory_requisitions_changed`,
  `inventory_reservations_changed`, and `inventory_balances_changed` all deleted (fields absent,
  zero producers, zero consumers). Cycle Count and Goods Receipt remain unaudited as their own
  capabilities (each still owns `inventory_cycle_counts_changed`/`inventory_receipts_changed`) —
  no next Inventory/Procurement target has been chosen yet.
- **Auth/Security — AUDITED / DEFERRED**: Auth Credential & Session Lifecycle (`auth_changed` -
  largest remaining raw-Session surface in the codebase). Fully audited in P26A (see §3): proposed
  **P26B** (Credentials + Account Security + Session Persistence) and **P26C**
  (Login/Registration/Provisioning), with no canonical UnitOfWork yet on this surface -
  transaction convergence is a prerequisite for whichever slice goes first. **Implementation is
  deliberately deferred** (post-P26A roadmap decision): 19 producers span multiple ownership
  boundaries (Auth durable facts, Authorization-owned custom-role/policy-reconciliation facts,
  Login/failed-login's own fail-open/fail-closed question, Registration/Bootstrap's
  Membership/RoleBinding under-instrumentation), so a single partial slice would not retire
  `auth_changed`, would not reduce the legacy consumer count, and would not change the legacy
  Signal field count - not the best next modernization step versus other capabilities below.
  Revisit after cleaner remaining capabilities are modernized. Custom-role/policy-reconciliation's
  `auth_changed` usage remains a separate, Authorization-owned cleanup, not part of either Auth
  slice.

## 7. Known Architectural Hotspots

Findings from the P17 system-wide audit, recorded here for visibility. **Not solved by this
document** - each is addressed when its owning capability's phase is implemented.

- `tasks_changed` - highly overloaded (~9 distinct real business facts under one signal name,
  the worst offender in the system by call-site count).
- `auth_changed` - covers multiple unrelated security facts (password, MFA, federated identity,
  session, bootstrap/registration, custom-role). Fully decomposed and slice-planned in P26A (§3) -
  cannot be deleted in one phase (no UoW convergence yet; custom-role bulk-revocation and
  registration's Membership/RoleBinding conflation each need their own fix first).
- `project_changed` - broadest PM fan-out signal; touches 11 consumer files.
- ~~`inventory_balances_changed`~~ **RESOLVED by P31B** - all 9 former producer mechanisms
  (Reservation, PO approve/cancel, Receipt, Cycle Count, Manual Movements) converged onto 3 typed,
  field-oriented facts (`StockOnHandQuantityChanged`/`StockReservedQuantityChanged`/
  `StockOnOrderQuantityChanged`), field deleted (ADR-005 §26.28). The P31A-confirmed
  `cancel_purchase_order` silent-mutation gap is fixed, not carried forward. Receipt's and Cycle
  Count's own legacy signals (`inventory_receipts_changed`/`inventory_cycle_counts_changed`) are
  unchanged — neither capability was modernized in its own right, mirroring how P30B left
  Balance's own signal untouched while still recording Reservation's genuine Balance mutation.
- ~~`inventory_purchase_orders_changed`~~ **RESOLVED by P28B** - all 12 producer sites converged,
  field deleted; the PO-approval → Requisition-sourcing-mutation boundary is now the typed
  `InventoryRequisitionSourcingAdvanced` fact (ADR-005 §26.23).
- ~~`inventory_requisitions_changed`~~ **RESOLVED by P29** - all 7 remaining producer sites
  converged onto the existing `RequisitionSubmissionUnitOfWork` (Option A extension) and
  `ApprovalHandlerResult.domain_events`, field deleted (ADR-005 §26.25). The supplier
  same-organization concern carried forward since P27A was investigated and found not to be a
  real gap - `PartyService.get_party` already scopes to the active organization.
- ~~`inventory_reservations_changed`~~ **RESOLVED by P30B** - all 5 former producer sites
  converged (3 onto a new `InventoryReservationUnitOfWork` and typed events, 2 — document
  link/unlink — onto no event at all, matching PO's/Item's own precedent), field deleted (ADR-005
  §26.27). Reservation's genuine Balance/Ledger mutation was unchanged at the time, still routed
  through the legacy `inventory_balances_changed` - Balance itself was not yet modernized (now
  resolved by P31B, see below).
- `collaboration_changed` - durable comment mutations and ephemeral presence pings share one
  signal name; a category error, not just an overload - presence needs a different mechanism
  entirely, not a `DomainEvent`.
- Reflective Approval/Finance legacy dispatch - `ApprovalService._emit_signal_safely` and
  `FinanceGovernedServicePort.__getattr__` both use `getattr(domain_events, signal_name)`
  string-keyed dispatch (bounded to their own call sites, not a generic repo-wide router, but
  still indirection worth being aware of when tracing a producer). `FinanceGovernedServicePort`'s
  reflective command *routing* (dispatching a read-service method name to the right
  `FinanceGovernanceCommandBoundary` family) is unrelated to and untouched by P19 — Forecast's
  typed-event construction happens inside `ForecastVersionService`/`ForecastGenerationService`
  themselves, not in the reflective layer, so removing the routing reflection would have zero
  effect on event correctness and was left in place. `ApprovalService._emit_signal_safely` also
  remains — P19 added a second, coexisting reporting channel (`ApprovalHandlerResult.domain_events`,
  ADR-005 §26.16) rather than replacing it, since every other Approval participant still reports
  through the legacy Signal-name bridge.
- Remaining raw process-lifetime Sessions - Auth (all 10 producer files, on one shared Session),
  most of PM and Inventory/Procurement, and part of Finance (`cost_entries_changed`,
  `commitments_changed` - notably, both already have an unused canonical UoW repo declared for
  them).
- ~~Orphan Resource typed events before P18~~ **RESOLVED by P18A** -
  `ResourceMasterChanged`/`ResourceCapabilityChanged` now dispatch through the canonical
  post-commit bus (bespoke `Signal[T]` transport deleted); still zero real UI subscribers until
  P18B builds the ViewInvalidation handler.
- Coarse Inventory workspace refresh fan-out - narrowing since P20; by P30B each of the 6
  Inventory/Procurement workspace controllers subscribes only to the 3 remaining legacy signals
  it has a real (or still-unaudited) dependency on, not a blanket 11 - PO, Requisition, and
  Reservation facts now route through their own typed ViewInvalidation adapters instead.

## 8. Migration Checklist

For every capability, before it is considered modernized:

- [ ] semantic audit (enumerate every real business fact currently hidden behind the legacy
      signal - do not assume one signal = one fact)
- [ ] transaction/UoW convergence (one canonical UnitOfWork, one commit, one `DomainEvent`
      lifecycle)
- [ ] cross-org boundary verification
- [ ] no-op behavior (a request identical to already-persisted state records nothing)
- [ ] typed DomainEvents
- [ ] transactional dispatch (FAIL_FAST, pre-commit)
- [ ] postcommit dispatch (ISOLATE_AND_CONTINUE)
- [ ] ViewInvalidation target/scope
- [ ] narrow UI consumer cutover
- [ ] duplicate refresh audit (no capability left double-refreshing from both old and new paths)
- [ ] legacy producers = 0
- [ ] legacy consumers = 0
- [ ] legacy Signal deleted (field removed from `DomainEvents`, not merely unused)
- [ ] architecture guards pass (`src/tests/architecture/`, `src/tests/platform/test_p*`)
- [ ] ADR/plan updated (this document's ledger, and ADR-005 §26 if the design itself needed a
      correction, as P16D-FIX did)

## 9. Pre-Release Convergence Rule

This application is **pre-release**. Therefore, for every phase above:

- Remove obsolete architecture directly - do not leave a superseded path running "just in case."
- No compatibility aliases, unless a concrete, currently-live dependency actually requires one
  (not a hypothetical future one).
- No generic bridges for retired legacy Signals - each capability gets its own typed
  replacement, never a shared string-keyed router standing in for several at once.
- Do not preserve incorrect semantics merely for backward compatibility - if a phase finds a
  legacy behavior was already wrong (e.g. P16B's missing no-op guards), fix it as part of the
  phase and say so explicitly, rather than migrating the bug forward.
