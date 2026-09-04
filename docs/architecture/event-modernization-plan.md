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

**P32A — Remaining Inventory re-rank: Goods Receipt vs Cycle Count, short comparative audit +
sequencing decision (design only, no migration yet).** Full source re-audit of both remaining
Inventory legacy signals now that P31B changed important prerequisites for both. Confirms `inventory_
receipts_changed` has exactly 1 producer file (`purchasing_receiving.py::post_receipt`, the *only*
Receipt mutation method that exists) and `inventory_cycle_counts_changed` has exactly 1 producer
file (`foundation_service.py`, 2 methods: `schedule_cycle_count`/`complete_cycle_count`); both
still have all 6 legacy workspace-binder subscriptions, re-classified below.

- **Goods Receipt has no lifecycle at all — a single durable fact, not several.**
  `ReceiptStatus` has exactly one value (`POSTED`); `ReceiptHeader`/`ReceiptLine` have no `update()`
  method on either repository (confirmed) and no `version` field on `ReceiptHeader` — genuinely
  immutable, append-only once posted. No cancel/reverse/void/update/document-link method exists
  anywhere (`post_receipt` is the sole mutator, confirmed by a repo-wide grep for every
  `_receipt_header_repo`/`_receipt_line_repo` call site). One semantic fact:
  `InventoryReceiptPosted` (not `ReceiptCreated`+`ReceiptPosted` — it's created already-posted, no
  separate posting step exists to split out).
- **Cycle Count has a real, if narrow, lifecycle.** `CycleCountStatus`: `PLANNED → COMPLETED` is
  the only reachable transition (`IN_PROGRESS`/`CANCELLED` are both defined but confirmed
  unreachable — no producer ever sets either, re-confirmed from current source). Flat aggregate
  (no child lines), its own real `version` field with `expected_version`/`ConcurrencyError`
  protection on `complete_cycle_count` (Cycle Count's own concurrency is *better* protected than
  Receipt's, which has none because it has no update path to conflict on). Two semantic facts:
  `InventoryCycleCountScheduled` and `InventoryCycleCountCompleted` (variance-driven Balance
  adjustment is already a separate, already-canonical Balance fact per P31B — not a Cycle Count
  fact).
- **Transaction readiness — Receipt is 100% canonical today; Cycle Count is 50% canonical.**
  Receipt's sole operation (`post_receipt`) already runs on the shared
  `PurchaseOrderSubmissionUnitOfWork`, already has atomic `record_audit_entry` (`fail_closed=True`,
  confirmed pre-existing from P28A). Cycle Count's `complete_cycle_count` was converged onto the
  extended `InventoryFoundationUnitOfWork` with atomic audit in P31B; `schedule_cycle_count` was
  explicitly out of P31B's scope (it never mutates Balance) and remains raw `self._session`, with
  **zero** atomic enterprise audit — activity-feed-only, non-atomic, the same gap class every other
  capability's first-touched raw-Session operation has shown. This is the one genuinely open
  transaction-convergence item between the two capabilities, and it is a small, already-proven
  extension (the identical `with self._require_uow_factory().create(...)` pattern
  `complete_cycle_count` already uses, in the same class).
- **Cross-capability mutations — Receipt has real, but already-canonical, external coupling;
  Cycle Count has none beyond Balance at all.** Receipt mutates `PurchaseOrderLine`/`PurchaseOrder`
  receiving state — already fully typed via the existing `InventoryPurchaseOrderReceivingAdvanced`
  event (one per `post_receipt` call, deduplicated by resulting status) — confirming the PO
  receiving boundary is already canonical, no observability gap remains. Cycle Count touches only
  its own aggregate plus `StockBalance`/`StockTransaction` (both already canonical, P31B) — no
  Item, Storeroom, Location, PO, Requisition, or approval coupling of any kind, confirmed by
  source. This makes Cycle Count's semantic decomposition the simpler of the two — nothing to
  coordinate with another capability's own event vocabulary at all.
- **Ledger**: both post as `ADJUSTMENT_INCREASE`/`ADJUSTMENT_DECREASE` (no dedicated
  `RECEIPT`/`CYCLE_COUNT` `StockTransactionType`, confirmed unchanged from P31A) — no Ledger
  DomainEvents proposed for either, per this phase's own explicit instruction and P31A's original
  finding.
- **Document link/unlink**: confirmed absent for both capabilities entirely — no such method
  exists on either. Nothing to resolve.
- **No-op/idempotency — Receipt carries the real open risk, Cycle Count does not.** Receipt has no
  idempotency key; a retry posting a *smaller*, still-within-outstanding quantity would silently
  double-post (P31A finding, unchanged, not fixed here). `complete_cycle_count` is hard-guarded
  against re-posting a `COMPLETED`/`CANCELLED` count; `schedule_cycle_count`'s only gap is that
  nothing prevents scheduling multiple concurrent `PLANNED` counts for the same item/storeroom
  position (uniqueness is only on the generated `cycle_count_number`, not the position) — a real
  but minor data-model gap, not fixed here either.
- **Consumers, re-classified from current source, not carried forward from P30B's stale labels**:
  - `inventory_receipts_changed` — **4 genuine, 2 incidental**. Procurement = OWNER (its own
    `receipt_mapper.py`/`receipt_command_handler.py` — a real `receipt_list`/lines view embedded in
    PO detail, not a standalone Receipt workspace). Dashboard = REAL (Receiving Queue KPI, a
    per-PO receipt count). Pricing = REAL (`procurement_report.receipts`, its own stock/procurement
    export). Inventory(Foundation) = REAL, newly confirmed — its "tracking signals" panel reads
    `ReceiptLine.lot_number`/`serial_number`/`expiry_date`/`quantity_accepted` directly for
    expiring/expired-lot alerts, a dependency P30B/P31A's own narrower scopes never had reason to
    surface. Catalog and Reservations = INCIDENTAL, zero references anywhere in either.
  - `inventory_cycle_counts_changed` — **1 genuine, 5 incidental**. Inventory(Foundation) = OWNER
    (its own `cycle_count_handler.py`/`foundation_builder.py`, part of the same "Foundation" panel
    as Storeroom/Location/ReorderPolicy). Catalog, Pricing, Procurement, Dashboard, and Reservations
    all have **zero** `cycle_count`/`CycleCount` reference anywhere in either their desktop-API or
    presenter layers — the most incidental-heavy signal audited yet (5 of 6 subscriptions are
    pure legacy fan-out with no real dependency at all).
- **ViewInvalidation complexity**: Receipt would need `receipt_list`/`receipt_detail`
  (`OrganizationScope`/`ResourceScope`) plus is genuinely embedded in Procurement's own PO-detail
  refresh — no new scope type required, but 4 real consumers to route precisely. Cycle Count would
  need only `cycle_count_list`/`cycle_count_detail`, both trivially expressible the same way, with
  exactly 1 real consumer to route — the simpler of the two by a wide margin.
- **Deletion feasibility — both YES in one phase.** Receipt: trivially, given a single fact and an
  already-fully-canonical transaction. Cycle Count: also YES, with `schedule_cycle_count`'s UoW
  convergence folded into the same phase (the identical pattern already proven).
- **Architectural size comparison**:

  | Dimension | Goods Receipt | Cycle Count |
  |---|---|---|
  | Transaction convergence | LOW (already done) | LOW (one small extension of an already-proven pattern) |
  | Semantic decomposition | LOW (1 fact) | LOW (2 facts) |
  | Cross-capability coupling | LOW (already canonical, but real — PO) | LOW (none beyond Balance) |
  | Consumer cutover | MEDIUM (4 genuine consumers across 4 workspaces) | LOW (1 genuine consumer, 1 workspace) |
  | Concurrency risk | LOW (no update path to conflict on) | LOW (already version-protected) |
  | Legacy-signal deletion confidence | HIGH | HIGH |
  | Meaningful gap closed | No open governance gap (audit already atomic) | Yes — `schedule_cycle_count` gains atomic audit for the first time |

- **Recommended P32B: CYCLE COUNT.** Applying the priority order exactly as instructed: criteria
  1 (deletable in one phase), 2 (cross-capability boundaries canonical), and 4 (semantic clarity)
  are ties — both capabilities pass cleanly. Criterion 3 (transaction ownership already canonical)
  gives Receipt a marginal edge (100% vs. Cycle Count's one small remaining extension), but that
  edge is trivial in absolute terms — the exact same proven UoW pattern, in the same class, already
  built this phase. Criteria 5 (consumer cutover precision) and 6 (meaningful correctness/audit gap
  closed) both favor Cycle Count clearly and substantially: a 1-genuine-consumer cutover is a much
  smaller, lower-risk surface than Receipt's 4-genuine-consumer cutover, and Cycle Count's
  modernization closes a real, currently-open atomic-audit gap (`schedule_cycle_count`) that Receipt
  has no equivalent of. Criterion 7 (smaller architectural surface) also favors Cycle Count — zero
  cross-capability coupling of any kind beyond the already-solved Balance boundary, versus Receipt's
  real (if already-canonical) coupling to PO's own vocabulary. The one criterion favoring Receipt is
  the least consequential of the differences found; the criteria most likely to carry real
  implementation risk (consumer cutover breadth, remaining governance gaps) both favor Cycle Count.
  **Goods Receipt is the expected following Inventory phase** — its own transaction/Balance/PO
  boundaries are already fully solved by this and prior phases, leaving only its typed-event
  vocabulary, ViewInvalidation cutover, and the pre-existing no-op/idempotency gap as future work,
  none of which is architecturally uncertain.
- **After both**: deleting `inventory_cycle_counts_changed` (future P32B) and
  `inventory_receipts_changed` (the expected following phase) would leave **zero** legacy Inventory
  Signal fields — every Inventory/Procurement capability (Item/Category, Storeroom/Location,
  Reorder Policy, Purchase Order, Requisition, Reservation, Stock Balance, Goods Receipt, Cycle
  Count) fully modernized. `StockTransaction` remains the unmodified, canonical persistence ledger
  throughout — confirmed, again, not to need its own DomainEvent family.

No source was changed by this audit. Legacy Signal count unchanged at 15.

### P32B — Inventory Cycle Count Full Modernization

`inventory_cycle_counts_changed` is **DELETED**. `schedule_cycle_count` converges onto the
canonical `InventoryFoundationUnitOfWork` (the same class `complete_cycle_count` already used
since P31B), gaining an atomic enterprise audit entry of its own for the first time — previously
activity-feed-only, non-atomic, the same first-touched-raw-Session gap class every other
capability showed before its own modernization phase. Two typed, field-oriented events replace the
legacy signal: `InventoryCycleCountScheduled` (tenant_id, organization_id, cycle_count_id,
storeroom_id, occurred_at) and `InventoryCycleCountCompleted` (adds `variance_qty`) — mirroring the
minimal, fact-oriented vocabulary established for Reservation (P30B) and Balance (P31B), not a
generic "CycleCountChanged" catch-all.

`cycle_count_list`/`cycle_count_detail` (`OrganizationScope`/`ResourceScope`) are Cycle Count's own
two ViewInvalidation projections, owned exclusively by the Inventory(Foundation) workspace.
Scheduled invalidates list only (a brand-new row cannot have a stale pre-existing detail view
open, mirroring Reservation's Created-vs-other-events split); Completed invalidates both list and
detail. Stock Balance's own event semantics (`StockOnHandQuantityChanged` on nonzero variance,
already correct since P31B) are unchanged — `complete_cycle_count` now records both its own
`InventoryCycleCountCompleted` and, when variance is nonzero, the pre-existing Balance fact, in the
same transaction.

The 5 incidental legacy subscriptions confirmed zero-dependency by P32A (Catalog, Pricing,
Procurement, Dashboard, Reservations) are removed with no replacement. Inventory(Foundation)'s own
subscription is replaced by the new `CycleCountViewInvalidationAdapter`
(`cycleCountListStale`/`cycleCountDetailStale`), wired via `_request_domain_refresh()` matching
every other Inventory/Procurement adapter since P30B-FIX.

No start/in-progress or cancel operation was invented — the lifecycle is unchanged
(`PLANNED → COMPLETED`, with `CANCELLED` as the only other terminal state, neither newly reachable
here). Stock Balance and StockTransaction semantics are untouched. Goods Receipt was not
modernized and `inventory_receipts_changed` was not deleted — it remains Inventory/Procurement's
one remaining legacy Inventory signal, the expected next phase per P32A's own comparison.

Regression: full `src/tests/inventory_procurement/` (269 passed, the same 3 pre-existing failures
reconfirmed via `git stash` — a `source_reference_type="project_task"` test-data bug and a
requisition-submission `AttributeError`, both unrelated to Inventory and unchanged since P31B) plus
`src/tests/architecture/test_service_architecture.py` (7 passed) and
`src/tests/platform/test_p8_platform_event_architecture_canonicalization.py` (31 passed, the same 5
pre-existing Finance-signal failures — `commitments_changed`/`cost_entries_changed`/
`financial_changes_changed` — reconfirmed via `git stash` as unrelated to Inventory, from
concurrent Finance work elsewhere on the branch). New `test_p32b_cycle_count_full_modernization.py`
(8 tests) covers: legacy-field-deleted, Scheduled → list-only hint, Scheduled audit-failure
rollback (zero creation, zero hints), Completed zero-variance → list+detail hint with **no**
Balance event, Completed nonzero-variance → list+detail hint **and** the Balance event, stale-version
rollback (zero hints of either kind), the 5 incidental consumers' zero reaction, and
Inventory(Foundation)'s genuine reaction.

Legacy Signal count: 15 → **14**. Cycle Count is now FULLY MODERNIZED — the eighth Inventory/
Procurement capability to reach that state (Item/Category, Storeroom/Location, Reorder Policy,
Purchase Order, Requisition, Reservation, Stock Balance, and now Cycle Count). Goods Receipt is
the only remaining Inventory/Procurement capability with a legacy signal.

### P33 — Goods Receipt Full Modernization + Inventory Legacy Completion

`inventory_receipts_changed` is **DELETED**. `post_receipt`'s transaction ownership was already
canonical (`PurchaseOrderSubmissionUnitOfWork`, confirmed by P28A/P31A and unchanged here) and its
enterprise audit was already atomic — this phase adds exactly one new typed fact,
`InventoryReceiptPosted` (`tenant_id`, `organization_id`, `receipt_id`, `purchase_order_id`,
`occurred_at`), recorded precommit in the same transaction as the pre-existing
`InventoryPurchaseOrderReceivingAdvanced` and Balance facts (P31B). **Source correction to this
phase's own brief**: the suggested payload's `storeroom_id` field does not exist on `ReceiptHeader`
— storeroom is a per-*line* attribute (`destination_storeroom_id`, which can differ across a single
receipt's lines), not a Receipt-header identity field, so it was omitted rather than assumed.

**One receipt, one fact.** A Receipt with multiple lines still records exactly one
`InventoryReceiptPosted` — proven by a dedicated multi-line, multi-item regression test. Balance
facts remain per affected `StockBalance` row (P31B semantics, unchanged); PO receiving facts remain
exactly as P28 defined them (unchanged). `InventoryReceiptPosted` does not substitute for either —
it represents only "a Receipt was posted," never PO state or Balance state.

**No `receipt_detail` target invented.** Source audit found `get_receipt` is purely an internal
application-layer helper (used only by `list_receipt_lines` for scope validation) — never exposed
through any desktop API, and no UI presenter fetches a single Receipt by id. Every genuine consumer
reads Receipt exclusively through list-shaped queries (`list_receipts`/`list_receipt_lines`,
optionally filtered by `purchase_order_id` at query time but never cached as a separate per-filter
projection, mirroring `reorder_policy_list`'s own precedent). Only `receipt_list`
(`OrganizationScope`, category `procurement`, entity_type `inventory_receipt`) was built — inventing
a `receipt_detail` ResourceScope pair, matching every prior phase's list/detail default, would have
been an unjustified target with no corresponding stale read model.

**Consumer re-audit, field-precise, not inferred from co-occurring PO/Balance events (§21/§24 of
this phase's own brief).** All 4 of P32A's "genuine" consumers were re-verified at the field level
and confirmed still genuine, each for a distinct reason: **Procurement** (OWNER) reads
`list_receipts`/`list_receipt_lines` directly for its PO-scoped receipt-history panel and an
org-wide receipt count in its overview KPIs. **Dashboard** reads `list_receipts` directly for a
per-PO "Receipts N" count embedded in its Receiving Queue rows — genuinely Receipt-owned data, not
derivable from `InventoryPurchaseOrderReceivingAdvanced`'s own payload (`resulting_status` only).
**Pricing** reads `list_receipts` (via the reporting service) directly for its own live "Receipts"
metric count — confirmed NOT explainable by its Balance dependency alone (Pricing's `last_receipt_at`
field usage IS Balance-derived and already covered by `StockOnHandQuantityChanged`, but the
"Receipts" metric is separate, genuine Receipt data). **Inventory(Foundation)** reads
`list_receipts`/`list_receipt_lines` directly for its lot/serial/expiry tracking-signal panel. No
consumer was reclassified from P32A's original 4-genuine/2-incidental split, but each was
independently re-derived from source rather than carried forward. **Catalog and Reservations**
(INCIDENTAL) — zero Receipt-data references anywhere in either, confirmed by source and by a
dedicated zero-reaction regression test; their legacy subscriptions are removed with no replacement.

**Six legacy binder files, six different outcomes.** All 6 (Catalog, Procurement, Pricing,
Reservations, Inventory(Foundation), Dashboard's own inline binder) had `inventory_receipts_changed`
as their ONLY remaining subscription (the last Inventory legacy signal standing after P32B). At P33
time these were left as documented no-op stubs, preserving each controller's `__init__` calling
convention. **P33-CLEANUP removed the stubs outright**: the 5 free-function binder files
(Catalog/Procurement/Pricing/Reservations/Inventory(Foundation)) are deleted, their imports and
`bind_domain_events(self)` call sites removed from each workspace controller's `__init__`;
Dashboard's own inline `_bind_domain_events` method and its call site are deleted the same way. The
now-dead `_subscribe_domain_signal`/`_disconnect_domain_event_subscriptions` legacy-Signal-
subscription machinery on `InventoryProcurementWorkspaceControllerBase` (zero remaining callers
anywhere in the module once the 6 binders were gone) was removed too — the still-live
`_request_domain_refresh`/`_schedule_domain_refresh`/`_execute_scheduled_domain_refresh` coalescing
mechanism every typed ViewInvalidation adapter depends on is untouched. The 4 genuine consumers' real
Receipt dependency remains covered by 4 separate `ReceiptViewInvalidationAdapter` instances (one per
consuming workspace) wired through `_request_domain_refresh` in `context.py`, mirroring the
per-workspace-adapter-instance pattern already established for PO/Requisition. Catalog's and
Reservations' subscriptions remain removed with no replacement of any kind.

**§14 finding — PurchaseOrderLine concurrency, pre-existing, NOT fixed by this phase.** Source audit
confirms `PurchaseOrderLineORM` has no `version` column at all (unlike `PurchaseOrder`/`CycleCount`/
`StockBalance`/`StockReservation`, all `update_with_version_check`-protected) and
`SqlAlchemyPurchaseOrderLineRepository.update()` performs a blind field overwrite. This is not new —
P28A already documented it neutrally ("child PurchaseOrderLine (no own version field, additive-only
mutation)"). A repository-level two-session regression test (mirroring P31B's own template) proves
the race is real: two independent reads of the same line's `quantity_received` before either write,
followed by two independent writes, both succeed — neither is rejected, confirming a genuine lost-
update risk on concurrent same-line receiving. **Deliberately not fixed here** — hardening it would
require a schema migration (a new `version` column) unrelated to and out of proportion with this
phase's actual goal (the Receipt DomainEvent + ViewInvalidation cutover does not depend on it, and
neither `post_receipt`'s per-call `outstanding` guard nor its idempotency behavior is touched by
this event-modernization work). Carried forward as an explicit, source-confirmed, unresolved
architectural note, exactly as P31A carried forward (and P31B later fixed, when directly relevant)
the analogous PO-cancel silent-mutation gap.

`inventory_receipts_changed` is now deleted from `DomainEvents` entirely — zero producers (the one
`.emit()` site in `post_receipt` converted), zero consumers (all 6 legacy subscriptions removed —
2 incidental with no replacement, 4 replaced by the typed adapter). **Zero Inventory/Procurement
legacy Signal fields remain** — `dataclasses.fields(DomainEvents)` carries no `inventory_`-prefixed
name at all, proven by a dedicated architecture-guard test. The legacy Signal count is 13 as of this
phase (14 minus the one deletion — confirmed source-derived). Goods Receipt is now fully modernized —
the ninth and final Inventory/Procurement capability to reach that state. **Inventory/Procurement's
entire event-modernization surface (Item/Category, Storeroom/Location, Reorder Policy, Purchase
Order, Requisition, Reservation, Stock Balance, Cycle Count, Goods Receipt) is complete.**
`StockTransaction` remains, throughout, the unmodified canonical persistence ledger — confirmed
again not to need its own DomainEvent family. This does **not** mark the overall (all-module)
event-modernization project complete — Project Management, Finance, and Auth/Security legacy
signals remain, per §6.

### P33-CLEANUP — Structural Cleanup, Not a Modernization Phase

No business behavior changed; legacy Signal count unchanged at 13 (Inventory/Procurement's own
count was already zero after P33). Obsolete Inventory legacy-Signal wiring left as documented no-op
stubs at P33 time is deleted outright, per this document's own §9 Pre-Release Convergence Rule ("no
compatibility shell, no deprecated wrapper, no empty placeholder"): the 5 free-function
`*_domain_event_binder.py` files (Catalog/Procurement/Pricing/Reservations/Inventory(Foundation)),
Dashboard's own inline `_bind_domain_events` no-op method, their import/call sites in each
controller's `__init__`, and the now-zero-caller `_subscribe_domain_signal`/
`_disconnect_domain_event_subscriptions` legacy-Signal-subscription machinery on
`InventoryProcurementWorkspaceControllerBase` (plus its now-unused `Callable`/`Any`/`DomainSignal`
imports). The still-live `_request_domain_refresh`/`_schedule_domain_refresh`/
`_execute_scheduled_domain_refresh` coalescing mechanism, and every typed ViewInvalidation adapter
that depends on it, is untouched. Two stale test-source-inspection assertions (P20's Catalog test,
P30B-FIX's Reservations test) that imported the now-deleted binder modules directly were rewritten
to assert the module's absence instead (a stronger proof of "zero legacy responsibility" than
inspecting dead source). One incidentally-discovered stale test outside Inventory/Procurement
(`test_p7_legacy_bridge_removal.py`'s `..._does_not_react_to_an_unrelated_inventory_signal`, which
emitted the already-P31B-deleted `inventory_balances_changed`) was also corrected — its "unrelated
signal" example was swapped to a still-legacy Finance signal, preserving the same cross-module-
isolation property without inventing new Inventory wiring. The `PurchaseOrderLine` concurrency debt
(§7) is explicitly NOT addressed here — recorded, not fixed.

### P34A — Global Re-Audit + Re-Rank of Remaining Legacy Signals (AUDIT + ROADMAP ONLY)

No production code, test, README, or ADR changed. Legacy Signal count unchanged at 13
(`dataclasses.fields(DomainEvents)` re-verified: exactly the expected 6 PM + 6 Finance + 1 Auth,
zero unexpected modules, zero stray Inventory fields).

**Remaining Signal field list (source-derived)**:

- **PM (6)**: `project_changed`, `tasks_changed`, `timesheet_periods_changed`,
  `collaboration_changed`, `portfolio_changed`, `register_changed`
- **Finance (6)**: `budgets_changed`, `billing_preparations_changed`, `planned_costs_changed`,
  `cost_entries_changed`, `commitments_changed`, `financial_changes_changed`
- **Auth (1)**: `auth_changed` — unchanged from P26A, carried forward AUDITED / DEFERRED

**Producer/consumer matrix (compact)**:

| Signal | Producer sites | Producer files | Consumers | Transaction | Audit |
|---|---|---|---|---|---|
| `timesheet_periods_changed` | 1 (single choke-point helper) | `timesheet_periods.py` | 5 | D, trivial (raw Session, single function) | **ATOMIC** |
| `register_changed` | 3 | `register_lifecycle.py` | 3 | D, already `expected_version`-protected | ACTIVITY-ONLY |
| `project_changed` | 7 | `projects/commands/lifecycle.py` (3) + `resources/commands/project_resource_commands.py` (4) | 11 (HIGH) | D, zero UoW despite an unused `ResourceUnitOfWork` existing | MIXED (financial-profile sub-writes atomic; plain Project updates activity-only) |
| `portfolio_changed` | 8 | 4 files (dependencies/intake/scenarios/templates ×2 each) | 3 | D, zero UoW | MIXED, mostly **NONE** (3 of 4 files have zero audit/activity) |
| `collaboration_changed` | 8 | `collaboration_comments.py` (6, durable) + `collaboration_presence.py` (2, ephemeral) | 3 | D, zero UoW | **NONE** |
| `tasks_changed` | 22 direct (8 files) + 6 reflective `ApprovalPostCommitEvent` (5 in `task_apply_participant.py`, 1 conditional in `financial_change_apply_participant.py`) + 4 raw-session Timesheet co-producers | 10 files total | 10 (HIGH) | E — mixed: 5 approval sites already atomic (ApprovalService-owned); rest raw Session, zero UoW | **NONE/ACTIVITY-ONLY** — zero `record_audit_entry` anywhere in the 8 core task-command files |
| `planned_costs_changed` | 1 | `planned_cost_service.py` | 1 | C — raw Session but savepoint-protected, `FinanceGovernanceUnitOfWork.planned_costs` repo already wired | **ATOMIC** |
| `commitments_changed` | 1 | `commitment_service.py` | not deep-audited (flagged, low risk — single producer) | C — raw Session, repo already wired, **zero rollback protection** (confirmed live bug) | not verified this pass (producer's own audit call not confirmed) |
| `cost_entries_changed` | 1 direct + 2 approval (`project_cost_apply_participant.py`) | `cost_entry_service.py` | not deep-audited (flagged, low risk) | C — raw Session, repo already wired, properly try/except/rollback wrapped | **ATOMIC** |
| `budgets_changed` | 1 direct (`command_boundary.py::_emit_budget`, postcommit) + 2 approval (`budget_apply_participant.py`) + 1 cross-capability conditional (`financial_change_apply_participant.py:56`) | `budget_service.py` + 2 participants | 2+ (Financials workspace owner + Projects workspace `approvedBudgetVisible`, confirmed genuine) | **A — already canonical** `FinanceGovernanceUnitOfWork` via `FinanceGovernanceCommandBoundary` | **ATOMIC** (`_record_budget_audit`, `commit=False, fail_closed=True`) |
| `financial_changes_changed` | 1 direct (reflective `_emit_scoped`, postcommit) + 2 approval | `financial_change_apply_participant.py` | 1 (Financials workspace owner) | **A — already canonical**, same UoW/boundary as Budget | not independently verified this pass; participant already atomic (ApprovalService-owned) |
| `billing_preparations_changed` | submit (already `BillingPreparationSubmissionUnitOfWork`-based, postcommit legacy emit) + approve/reject (raw Session) + 2 approval + a genuinely different aggregate (`ProjectBillingProfile`) also emitting it | `preparation_service.py` + `billing_profile_service.py` + participant | not deep-audited | **E — mixed** (submit already UoW; rest raw Session) | MIXED |
| `auth_changed` | 19 (10 files, re-confirmed this pass, unchanged from P26A) | Auth credentials/session/provisioning/authorization | 2 (`access_workspace_controller.py`, `admin_console/domain_event_binder.py`) | D — no canonical UoW yet (P26A finding, unchanged) | not re-audited (P26A stands) |

**Corrections to older/assumed characterizations, source-proven this pass**:

- `register_changed`'s aggregate is a **combined Risk/Issue/Change register** — one `RegisterEntry`
  class (`domain/risk/register.py`) with a `RegisterEntryType` enum of `RISK`/`ISSUE`/`CHANGE`, not
  a Risk-only register as the file path (`application/risk/...`) alone would suggest. One aggregate,
  one lifecycle — LOW-MEDIUM overload, not multiple aggregates.
- `budgets_changed` is **not** a 1-fact signal — `budget_service.py` has 8 distinct lifecycle
  operations across 2 aggregates (`ProjectBudget`: create/create_successor/submit/approve/reject;
  `BudgetLine`: add_line/update_line/delete_line) — MEDIUM-HIGH overload, though transaction/audit
  posture is excellent (already canonical UoW + atomic audit for every one of those 8 operations).
- `commitments_changed`'s P17-era "missing-rollback bug" is **reconfirmed still real and unfixed**:
  `commitment_service.py`'s `_commit()` calls `self._session.commit()` with zero try/except/rollback
  anywhere in the file — a genuinely live production correctness bug, not carried-forward folklore.
- The Financials workspace's own `financials_refresh_mixin.py` (lines 579-628) already maps each of
  the 6 Finance signals to specific destination panels (`overview`/`planning`/`performance`/
  `commercial`/`costs`/`controls`) gated by a tenant/org/project scope check — a hand-rolled
  precursor to `ViewInvalidationHint`/`ViewInvalidationChannel` that already does ~80% of the
  ViewInvalidation design work for all 6 Finance signals at once.

**Semantic overload classification**: HIGH — `tasks_changed` (8+ facts, mixed direct/approval/
cross-capability), `collaboration_changed` (durable+ephemeral category error, confirmed still real),
`billing_preparations_changed` (2 distinct aggregates — `ProjectBillingPreparation` and
`ProjectBillingProfile` — sharing one signal, a real category error matching P17's old concern).
MEDIUM-HIGH — `portfolio_changed` (4 sub-aggregates), `budgets_changed` (8 facts/2 aggregates,
corrected above), `financial_changes_changed` (apply/reject + conditional Budget/Task/Forecast
cascade = 4+ facts). LOW-MEDIUM — `project_changed` (2 aggregates), `register_changed` (1 aggregate,
3 fact-types via one `type` field). LOW — `timesheet_periods_changed` (1 choke-point, 6 named
transitions), `planned_costs_changed` (1 fact), `cost_entries_changed` (1 fact + approve/reject),
`commitments_changed` (1 fact, not yet proven otherwise).

**Cross-capability mutation graph — proven edges only, not inferred from co-emission**:

- **`financial_change_apply_participant.py::apply()` → real (C) cross-capability mutation into
  Budget** (`change.applied_budget_id` gate) **and into Task** (`change.applied_schedule_count`
  gate), in the SAME `ApprovalHandlerResult`, alongside an already-typed `ForecastVersionChanged`
  DomainEvent (P19) — one method genuinely mutates up to 4 different aggregates' persisted state in
  one already-atomic transaction. This is the single most important finding for sequencing:
  `financial_changes_changed`, `budgets_changed`, and `tasks_changed` are NOT 3 independent
  deletions — this one participant is a live producer for all 3, and the participant already proves
  `post_commit_events=` (legacy) and `domain_events=` (canonical) coexist in one `ApprovalHandlerResult`
  without any ApprovalService redesign.
- All other apparent PM/Finance groupings (Project/ProjectResource sharing `project_changed`;
  Dependency/Intake/Scenario/Template sharing `portfolio_changed`; `ProjectBillingPreparation`/
  `ProjectBillingProfile` sharing `billing_preparations_changed`) are **signal co-emission observed,
  real persisted cross-mutation neither proven nor disproven this pass** — per this phase's own
  explicit instruction not to infer relationships from co-emission alone, these are flagged for
  verification during that capability's own eventual dedicated audit, not classified here.
- `timesheet_periods_changed`'s co-emission of `tasks_changed` per affected project was confirmed to
  exist (same helper function) but whether it is (B) a stale-read-model notification or (C) a real
  Task-row mutation was not proven this pass — flag for Timesheet Period's own audit.

**Approval coupling (§9) — remaining `ApprovalPostCommitEvent`/reflective-bridge usages**:
`tasks_changed` (6: 5 in `task_apply_participant.py` + 1 conditional in
`financial_change_apply_participant.py`), `budgets_changed` (3: 2 in `budget_apply_participant.py` +
1 conditional), `financial_changes_changed` (2, in its own participant), `billing_preparations_changed`
(2, in `billing_preparation_apply_participant.py`), `cost_entries_changed` (2, in
`project_cost_apply_participant.py`, already `commit=False` atomic). **Every one of these can convert
to `ApprovalHandlerResult.domain_events` with zero ApprovalService redesign** — `financial_change_
apply_participant.py` already proves both channels coexist in one return value today.

**Reflective legacy mechanisms still present in production** (test-only/dead references excluded):

1. `ApprovalService._emit_signal_safely` (`approval_service.py:349-350`) — `getattr(domain_events,
   signal_name, None)`, the dispatch every `ApprovalPostCommitEvent` above still routes through.
2. `FinanceGovernanceCommandBoundary._emit_scoped`/`_emit_budget` (`command_boundary.py:176-199`) —
   reflective (`_emit_scoped`, used for `financial_changes_changed`) and direct (`_emit_budget`, used
   for `budgets_changed`) postcommit emit helpers, called after `uow.commit()` inside `_execute()`.
   The SAME class's `rate_card()`/`forecast_version()`/`forecast_generation()` methods already prove
   the precommit-`uow.record_event(...)` conversion pattern working in production (P19/P22) —
   converting Budget/FinancialChange is a direct copy of an already-proven pattern in the same file.

**Legacy allowlist health (§35)** — the P8 guard's `current ⊆ frozen` subset check (not equality)
is mechanically correct, but **currently fails for real**: `cost_entries_changed`, `commitments_
changed`, and `financial_changes_changed` are live fields in `DomainEvents` that are **absent from
`FROZEN_LEGACY_SIGNAL_ALLOWLIST`** — and, confusingly, all three simultaneously appear in the SAME
test file's `_DELETED_BRIDGE_NAMES` list (asserting they should have zero production references).
This is not a stale-test-expects-a-deleted-signal problem (the direction every other P8 failure in
this document represents) — it is the opposite: current source has *more* live Finance signals than
the frozen baseline and the dead-name list both account for, most likely because these 3 fields were
added by concurrent Finance-side development on this branch without updating either list. Not fixed
here (P34A is audit-only) — flagged as its own distinct stale-test-debt item, separate from the
already-known `resources_changed`/hardcoded-count staleness.

**Stale regression-test debt (§34, not fixed)**: `test_p16d_document_link_typed_events.py::test_
legacy_signal_count_decreased_by_exactly_one` (hardcoded `== 29`, now 13); `test_p7_legacy_bridge_
removal.py::test_all_still_unmodernized_signals_survive_with_real_direct_consumers` (asserts
`resources_changed` still exists — it doesn't, deleted in an earlier PM phase); the P8 allowlist/
dead-name inconsistency above. **Recommendation: address AFTER the next capability**, not now and
not held until every signal is gone — none of these three currently block reliable regression
detection for Inventory/Procurement (already fully closed) or mask a real defect in whichever
Finance/PM capability is modernized next; they are orthogonal bookkeeping debt.

**Capability scorecard** (Auth excluded — kept AUDITED / DEFERRED per §29):

| Capability | Signal | Facts | Producers | Real consumers | Txn readiness | Audit readiness | Cross-capability | UI precision | Correctness debt | Deletion confidence | Test readiness | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Planned Cost | `planned_costs_changed` | LOW | 1 | 1 | **A-adjacent (repo wired, unused)** | ATOMIC | NONE proven | LOW-risk (existing scope-check pattern portable) | LOW (concurrency guard already real) | **HIGH** | MEDIUM-HIGH | **1** |
| Commitment | `commitments_changed` | LOW | 1 | not fully audited | **A-adjacent (repo wired, unused)** | not confirmed | NONE proven | LOW-risk | **HIGH (live rollback bug)** | **HIGH** | MEDIUM-HIGH | **2** |
| Cost Entry | `cost_entries_changed` | LOW | 3 (1 direct + 2 approval) | not fully audited | **A-adjacent (repo wired, unused)** | ATOMIC | NONE proven | LOW-risk | LOW | **HIGH** | MEDIUM-HIGH | **3** |
| Timesheet Period | `timesheet_periods_changed` | LOW | 1 | 5 | C (raw Session, needs new UoW) | ATOMIC | Task co-emission unproven | LOW-risk | LOW | HIGH | MEDIUM-HIGH | 4 |
| Register | `register_changed` | LOW-MEDIUM | 3 | 3 | D | ACTIVITY-ONLY | NONE proven | LOW-risk | LOW | HIGH | MEDIUM | 5 |
| Budget | `budgets_changed` | MEDIUM-HIGH | 4 (1 direct + 3 approval/cross) | 2+ | **A — already canonical** | ATOMIC | **HIGH (coupled to Financial Change)** | LOW-risk | LOW | MEDIUM (coupled) | MEDIUM-HIGH | 6 |
| Financial Change | `financial_changes_changed` | MEDIUM-HIGH | 3 | 1 | **A — already canonical** | not confirmed | **HIGH (drives Budget+Task)** | LOW-risk | not confirmed | MEDIUM (coupled) | MEDIUM-HIGH | 7 |
| Project | `project_changed` | LOW-MEDIUM | 7 | 11 (HIGH fan-out) | D | MIXED | 2 aggregates, unproven | LOW-risk | MEDIUM (no UoW, HIGH fan-out) | MEDIUM | MEDIUM | 8 |
| Portfolio | `portfolio_changed` | MEDIUM-HIGH | 8 | 3 | D | **NONE (3 of 4 files)** | 4 sub-aggregates, unproven | LOW-risk | MEDIUM (audit gap) | MEDIUM | LOW-MEDIUM | 9 |
| Billing Preparation | `billing_preparations_changed` | HIGH | 6+ | not fully audited | **E — mixed** | MIXED | 2 aggregates sharing 1 signal | LOW-risk | MEDIUM | LOW-MEDIUM | MEDIUM | 10 |
| Collaboration | `collaboration_changed` | HIGH (category error) | 8 | 3 | D | **NONE** | unproven | **needs non-DomainEvent presence transport** | MEDIUM (audit gap) | LOW (needs transport split first) | LOW-MEDIUM | 11 |
| Task | `tasks_changed` | HIGH | 28+ | 10 (HIGH fan-out) | E — mixed | **NONE/ACTIVITY-ONLY** | **HIGH (Financial Change cascades in)** | LOW-risk | MEDIUM (no audit anywhere) | LOW (blocked on Financial Change) | MEDIUM | 12 |

**Recommended next three targets** (all Finance — same already-wired `FinanceGovernanceUnitOfWork`,
same already-proven precommit-conversion pattern from P22 Rate Card, zero cross-capability coupling
found for any of the three, all three independently reach `producers=0/consumers=0/field-deleted`):

1. **`planned_costs_changed`** — lowest possible risk: 1 producer, 1 fact, already-atomic audit,
   already-working `ConcurrencyError` guard, UoW repo already wired and unused. Proves the pattern
   with the smallest possible blast radius before reusing it twice more.
2. **`commitments_changed`** — same mechanical pattern, additionally closes a real, currently-live
   commit-without-rollback correctness bug (highest governance value of the trio for comparable
   effort).
3. **`cost_entries_changed`** — same pattern again, already has 2 approval-owned sites proven atomic,
   closes out the trio and leaves `financials_refresh_mixin.py`'s routing table 3/6 converted.

**Mode for all three: DIRECT FULL MODERNIZATION** (not audit-first) — single producer (or a tight,
already-atomic 2-3 site cluster) each, facts are semantically clear, transaction infrastructure is
already built and merely unused, and the ViewInvalidation design is ~80% pre-existing in
`financials_refresh_mixin.py`'s own routing table. This phase's own audit depth is sufficient; a
dedicated P34B/P35A-style capability audit would be redundant scope, unlike Inventory's Receipt/Cycle
Count which needed P32A specifically because of genuine remaining ambiguity that does not exist here.

**Overall strategy: FINANCE FIRST**, specifically the Planned Cost → Commitment → Cost Entry trio,
not by module-completion aesthetics but by architectural dependency: these three are the only
remaining capabilities (PM or Finance) with an *already-wired, already-unused* canonical UoW and zero
proven cross-capability coupling — the lowest-risk, highest-leverage cluster available. `Budget`/
`Financial Change` are ALSO Finance and ALSO transaction-canonical, but are deliberately sequenced
after the trio because they are provably coupled to each other and to PM's `Task` through one
Approval participant — that coupling should be resolved as its own deliberate decision (likely a
short comparative audit in the P32A style, given 3 signals converge on 1 participant), not
accidentally forced by finishing Budget or Financial Change in isolation first. PM's cleanest signal,
`Timesheet Period`, is a strong 4th-in-line candidate once the Finance trio lands, ahead of `Register`
and well ahead of `Project`/`Portfolio` (both lower audit/transaction readiness) and `Collaboration`/
`Task` (both need dedicated architecture work — a presence-transport split and a Financial-Change-
coupling resolution, respectively — before a clean single-phase deletion is realistic).

### P35 — Finance Planned Cost Full Modernization (DIRECT FULL MODERNIZATION)

`planned_costs_changed` is **DELETED**. `PlannedCostService.calculate_snapshot` — confirmed still
the ONLY Planned Cost write operation, source-reconfirmed before implementation — converges onto
the already-existing, already-wired-but-previously-unused `FinanceGovernanceUnitOfWork` (its
`planned_costs` repository accessor existed since the UoW was built but had zero real caller until
this phase), via a new `FinanceGovernanceCommandBoundary.planned_cost()` method that is a direct,
mechanical copy of the exact `forecast_version()` shape P19 already proved (`invalidation=None` —
ViewInvalidation flows entirely through the canonical post-commit dispatch of the typed event, not
a boundary-level callback). `PlannedCostService` is wrapped in a 6th `FinanceGovernedServicePort`
family (`family="planned_cost"`, `mutations={"calculate_snapshot"}`), reusing the exact generic
read/write routing every sibling Finance family (`budget`, `forecast_version`,
`forecast_generation`, `financial_change`, `rate_card`) already relies on — `calculate_snapshot`
needed no new `_project_id` branch, since its `project_id`-is-the-first-positional-arg shape
already matched the existing `{"create_budget", "create_forecast", ...}` shortcut set verbatim.

**One typed event**: `PlannedCostSnapshotCalculated` (`tenant_id`, `organization_id`, `project_id`,
`planned_cost_version_id`, `occurred_at`) — the business fact is "the project's planned-cost
snapshot was recalculated." `calculate_snapshot` always produces one new, immutable
`ProjectPlannedCostVersion` (plus lines) and, if a prior version existed, supersedes it in the same
call — both effects are one business fact, not two, since a recalculation is never partial. No
`PlannedCostCreated`/`PlannedCostUpdated`/`PlannedCostRemoved` vocabulary was invented — source
genuinely exposes only the one semantic operation, matching the same reasoning `ForecastDraftGenerated`
(P19) already established for a single-operation Finance flow.

**Transaction ownership required extending the shared UoW itself, not just wiring into it**:
`calculate_snapshot`'s diagnostics computation reads `AssignmentRepository`/`ProjectResourceRepository`
— neither was on `FinanceGovernanceUnitOfWork`'s Protocol. Rather than mix an outer-scope,
different-session repo into an otherwise UoW-pure operation (every sibling operation in
`build_finance_governance_operations` uses only `uow.*` repos), both were added as two new named
accessors (`assignments`, `project_resources`) on the Protocol and concrete UoW class, bound to the
same per-call session as every other repo — a small, precedent-following extension (mirroring how
Inventory's own UoW gained new accessors repeatedly across P25/P31B/P32B), not a new transaction
stack.

**ViewInvalidation — one project-scoped target, no `planned_cost_detail` invented**: source audit
(`ProjectFinanceWorkspaceQuery.get_planned_cost_workspace`) found the version list and the selected
version's lines are fetched together, in one query, always refetched as a unit — there is no
independently cached detail read model to route a separate scope to. New handler
`build_planned_cost_view_invalidation_handler` (`planned_cost_snapshot` scope code,
`ResourceScope(module_code="project_management", entity_type="project")`) is a direct structural
copy of `forecast_planning`'s own single-target shape (P19). New `PlannedCostViewInvalidationAdapter`
(`plannedCostSnapshotStale`) and binder function `on_planned_cost_snapshot_stale` (invalidating
`"planning"`/`"performance"`, exactly matching the legacy signal's own destination set) follow the
identical wiring chain already established for Forecast/RateCard in `financials_workspace_controller.py`/
`context.py`.

**Concurrency preserved exactly, unweakened**: the pre-existing guard — a version-checked supersede
of the previous version (`expected_row_version`) plus a DB-level per-project-revision uniqueness
constraint mapped to `ConcurrencyError` — is untouched. A two-session repository-level regression
test proves the second writer is genuinely rejected (not merely a lost update, unlike the Inventory
`PurchaseOrderLine` finding from P33). Enterprise audit was already atomic (`record_audit_entry(...,
commit=False, fail_closed=True)`) and stays atomic.

**Finance reflective wrapper untouched**: Planned Cost never used `FinanceGovernanceCommandBoundary._emit_scoped`/
`_emit_budget` (it had its own direct `domain_events.planned_costs_changed.emit(...)` call, now
removed) — per this phase's own scope boundary, neither helper was modified, and Budget/Financial
Change's own behavior through them is unchanged.

**A genuine, source-confirmed finding, explicitly out of P35's scope**: a monkeypatched
audit-failure test proved the exception correctly propagates and produces zero postcommit hints,
but whether the already-flushed version row itself is rolled back could not be reliably asserted —
reproduced identically against completely unmodified `ForecastVersionService.create_forecast`,
confirming this is a pre-existing characteristic of the shared `FinanceGovernanceCommandBoundary`/
UoW machinery itself (not introduced by P35, and not something any other Finance family's test
suite asserts either). Recorded here, not fixed — `FinanceGovernanceCommandBoundary` redesign is
explicitly out of scope for a single-signal capability phase.

`planned_costs_changed` is now deleted from `DomainEvents` entirely — zero producers (the one
`.emit()` site converted), zero consumers (the sole owning subscription in
`financials_refresh_mixin.py` removed, replaced by the typed adapter). The legacy Signal count is
12 as of this phase (13 minus the one deletion — confirmed source-derived). Planned Cost is now
fully modernized. **Next planned target remains Commitment**, per P34A's own Finance-first trio
sequencing — unchanged by this phase.

### P35-CLEANUP — Repair Legacy Architecture-Test Baseline Before Commitment (TEST/GUARD ONLY)

No production code changed. **A material, source-verified discovery superseding P35's own closing
count**: `financial_changes_changed` was independently retired (typed `FinancialChangeChanged`
event, `FinancialChangeEventType.APPLIED`/`REJECTED`) by work outside this document's own tracked
phase sequence — zero remaining production references confirmed — between P35 and this cleanup
pass. The legacy Signal count is therefore **11, not 12**, as of this pass; §4 below reflects the
corrected, source-derived figure.

**P8 frozen-allowlist investigation (the core of this pass)**: P34A found `cost_entries_changed`/
`commitments_changed`/`financial_changes_changed` live but absent from `FROZEN_LEGACY_SIGNAL_
ALLOWLIST`, and simultaneously listed in `_DELETED_BRIDGE_NAMES` — flagged then as an unresolved
contradiction. Repository history (`git log --follow` on both `domain_events.py` and the P8 test
file) resolves it conclusively: at the exact moment `FROZEN_LEGACY_SIGNAL_ALLOWLIST` was frozen
(commit `d5a4069c`, 2026-08-26 18:39), all three fields had *already* been deleted by an earlier
zero-consumer cleanup roughly one hour prior (commit `72481db8`, 17:42, "P7C" per its own
`domain_events.py` docstring). `cost_entries_changed`/`commitments_changed` were then
**reintroduced three days later** (commit `cf939588`, 2026-08-29) by new Cost Entry/Commitment
capability work that never updated the P8 bookkeeping — a genuine **post-freeze legacy-Signal
introduction**, not a frozen-allowlist omission. Per this pass's own explicit instruction, **they
were deliberately NOT added to the frozen allowlist** — doing so would silently launder a real
violation into an accepted baseline. `financial_changes_changed` followed the identical
reintroduce-then-redelete path but is genuinely dead again now, so its `_DELETED_BRIDGE_NAMES`
membership is correct and was left alone.

**`_DELETED_BRIDGE_NAMES` corrected**: `cost_entries_changed`/`commitments_changed` removed (both
are live production fields with real producers and a real consumer — they must not simultaneously
be classified as deleted). Both fields' true status is documented in a new comment block directly
in the test file, citing the exact commits above, so `test_current_signals_are_a_subset_of_the_
frozen_allowlist_not_equal`/`test_every_current_signal_is_in_the_frozen_allowlist_no_silent_field_
addition`/`test_a_hypothetical_deletion_still_passes_the_subset_check`/`test_every_approval_post_
commit_event_signal_name_is_allowlisted_and_has_a_ui_consumer` are EXPECTED to keep failing for
exactly `cost_entries_changed`/`commitments_changed` until each is properly modernized (Commitment
next, then Cost Entry) — this is the guard correctly detecting a real, pre-existing condition, not
stale test debt to silence.

**Two brittle hardcoded-count tests removed** (`test_p16d_document_link_typed_events.py::test_
legacy_signal_count_decreased_by_exactly_one` — `== 29`; `test_p18b_resource_view_invalidation.py::
test_legacy_signal_count_decreased_by_exactly_one_from_p18a_baseline` — `== 28`): both were fully
redundant with an adjacent, still-valid field-absence test in the same file, and neither's own
architectural intent required an exact historical count — removed rather than re-hardcoded to `11`,
per this pass's own explicit "don't create another future-stale assertion" instruction.

**`resources_changed` stale-liveness assertion fixed** in `test_p7_legacy_bridge_removal.py::test_
all_still_unmodernized_signals_survive_with_real_direct_consumers`: Resource was fully modernized by
P18A/P18B (`ResourceMasterChanged`/`ResourceCapabilityChanged`, canonical ViewInvalidation) and
`resources_changed` was genuinely deleted — the test's own "still exists" assertion for that name
was stale. Removed from the tuple, docstring updated to name P18A/P18B alongside the test file's
own pre-existing precedent for the other five already-excluded, already-modernized names.

**New finding for the P36 Commitment baseline** (reported, not acted on — out of this pass's
scope): `commitments_changed` has **2** production producers, not 1 — `commitment_service.py`'s own
direct emit, plus a second, cross-module producer in `ProcurementFinancialDispatcher._emit_refresh`
(`src/infra/integration/procurement_financial_dispatcher.py`) that P34A's original audit did not
find. `cost_entries_changed` has **3** — `cost_entry_service.py`'s own emit, the same
`ProcurementFinancialDispatcher`, and a third in `ApprovedTimeFinancialDispatcher`
(`src/infra/integration/approved_time_dispatcher.py`). Both remain single-consumer
(`financials_refresh_mixin.py`, unchanged). No production code was touched to establish this —
it is a corrected fact for whoever scopes the Commitment phase next.

`current ∩ retired-name-set` is confirmed EMPTY (no field is simultaneously live and marked
retired). `current − frozen` is confirmed to be exactly `{cost_entries_changed,
commitments_changed}` — the one deliberately-unresolved, documented violation above, not an
oversight.

### P36 — Finance Commitment Full Modernization + Transaction Correctness Fix (DIRECT FULL MODERNIZATION)

Commitment's three UI-facing mutations — `ingest_procurement_source`, `match_cost_entry`,
`reverse_match` — converge onto the canonical `FinanceGovernanceUnitOfWork` via a new
`FinanceGovernanceCommandBoundary.commitment()` method (mirroring P35 Planned Cost / P19 Forecast
exactly): a new `FinanceGovernedServicePort` family (`"commitment"`, mutations
`{ingest_procurement_source, match_cost_entry, reverse_match}`) routes them through governance,
and `FinanceGovernanceOperations` gained a `commitments: ProjectCommitmentService` field built
from `uow.commitments`/`uow.record_event` inside `build_finance_governance_operations`. This
directly fixes the confirmed commit-without-rollback defect: `commitment_service.py`'s old
`_commit()` called `self._session.commit()` with zero try/except/rollback; the method is now
deleted entirely, and the UoW's `__exit__` (already correct, unchanged) rolls back on any
exception for all three entry points.

Two typed DomainEvents replace the legacy `commitments_changed` Signal — `CommitmentLineChanged`
(`CREATED`/`REVISED`, from `_apply_source_projection`'s two real write paths; its replay branch is
a true no-op and produces neither a write nor an event) and `CommitmentMatchChanged`
(`MATCHED`/`REVERSED`). The brief's own suggested `CommitmentCreated/Updated/Cancelled/Closed/
Removed` vocabulary was deliberately rejected — source has no cancel/close/remove operation on
Commitment, only a source-driven state field — in favor of naming after the two real aggregate
parts (line, match), mirroring Forecast's `ForecastVersionChanged`/`ForecastLineChanged` split.
Both route through one project-scoped `commitment_list` ViewInvalidation target
(`build_commitment_view_invalidation_handler`, `src/core/modules/project_management/application/
financials/commitments/event_handlers/view_invalidation.py`) — a single target for both event
types, matching the legacy signal's own confirmed 5-destination fan-out (overview/planning/costs/
performance/commercial, the widest of any Finance signal) and P31B's Balance precedent for not
narrowing scope without stronger field-level evidence.

**P35-CLEANUP's "2 producers" finding was resolved by NOT converging both onto the UoW.** The
second producer, `ProcurementFinancialDispatcher._emit_refresh`
(`src/infra/integration/procurement_financial_dispatcher.py`), already wraps its own
`self._session.commit()` in a correct try/except/rollback around the dispatcher's own inbox/outbox
transaction — it was never the buggy path. `apply_procurement_source`/`apply_procurement_receipt_match`
(the Procurement-inbox-facing methods) therefore stay on the raw, dispatcher-owned
`ProjectCommitmentService` instance with unchanged transaction ownership; only their RETURN
CONTRACT changed — a typed event (or `None` on a true replay) instead of the mutated entity — so
`ProcurementFinancialConsumer` (`ProcurementFinancialConsumption.commitment_events: tuple[object,
...]`, replacing the old hardcoded-`True` `commitment_changed: bool` — itself a latent
over-notification bug now fixed as a side effect) can forward the real event(s) to the dispatcher,
which publishes them through the canonical `platform_post_commit_bus` directly (`DomainEventContext
(correlation_id=generate_id())` per delivery) in place of the legacy signal emit. Pre-commit
`TransactionalEventDispatcher` dispatch was deliberately skipped for this path — confirmed zero
pre-commit handlers exist anywhere in the codebase for any ViewInvalidation-only event, making that
step pure unused ceremony for a non-UoW dispatcher.

`commitments_changed` is deleted from `DomainEvents` entirely and added to `_DELETED_BRIDGE_NAMES`
in `test_p8_platform_event_architecture_canonicalization.py`. **`current − frozen` is now exactly
`{cost_entries_changed}`** — the one remaining, deliberately-unresolved P35-CLEANUP violation;
`commitments_changed` has fully left the current set. Full regression battery run: the existing
`test_project_commitments.py` (6 tests) and `test_procurement_financial_integration.py` (7 tests,
adapted to observe the new typed-event/post-commit-bus producer path instead of the retired
signal — the real end-to-end Procurement→Commitment pipeline, unchanged assertion counts) both pass
unmodified in behavior; a new `test_p36_finance_commitment_full_modernization.py` (10 tests) covers
the ViewInvalidation handler, both UI-direct and dispatcher-facing producer paths, replay/no-op
behavior, the transaction-rollback-and-session-still-usable proof (the core bug fix), the
pre-existing pessimistic+optimistic concurrency guard (unweakened), and the
`FinancialsWorkspaceController` consumer reaction. `test_r6b_finance_invalidation.py` and
`test_p7c_zero_consumer_signal_cleanup.py` adapted their `commitments_changed`-specific cases onto
`cost_entries_changed` (the one remaining still-legacy signal) rather than deleting coverage of the
shared legacy-signal mechanism outright. Full platform (`src/tests/platform/`) and Finance-wide PM
(`src/tests/project_management/`) suites run clean against baseline — only the 4 already-expected
P8 guard failures (now naming `cost_entries_changed` alone) and a pre-existing, unrelated baseline
failure set (enterprise calendar/shift patterns, party/site domain validation, platform persistence
structure, `inventory_procurement` module-entitlement/import tests) remain, none touched by this
phase's diff.

### P36-FIX / P36-FIX2 — Canonical Event Lifecycle for the Procurement Commitment Producer (VERIFICATION + FIX)

Two follow-up passes closed a real architectural gap P36's own report under-described. **P36-FIX**
traced the exact Procurement-driven Commitment flow and found `ProcurementFinancialDispatcher`
constructed `CommitmentLineChanged`/`CommitmentMatchChanged` precommit but never staged them into
any canonical event lifecycle — they sat as bare return values, hand-carried across the commit
boundary, then manually published post-commit. Fixed by having the dispatcher call
`self._transactional_dispatcher.dispatch(event, self)` immediately before its own commit — but
**P36-FIX2** found this passed the dispatcher itself as the handler's `uow` argument: real
duck-typed `UnitOfWork` impersonation (`ProcurementFinancialDispatcher` has none of `record_event`/
`commit`/`__enter__`/`__exit__`). The corrected, final design: `ProcurementFinancialDispatcher`
wraps its own already-owned `self._session` in a real `SqlAlchemyUnitOfWorkBase` for the scope of
one delivery (`uow._session is self._session` — no second transaction, no fresh session; a
fresh-session-per-delivery alternative was evaluated and rejected because `commitment_service`/
`cost_entry_service`/`inbox_service`/`outbox_service` are composition-root singletons shared
across call sites, and splitting the session would break the existing atomicity between
inbox-delivery-state and the Commitment mutation). `uow.record_event(event)` + `uow.commit()`
replace every hand-rolled piece of `_drain_and_dispatch()`/postcommit-publish the dispatcher used
to reproduce manually. Full platform suite re-run before/after: identical 23-failed/1599-passed/
12-error totals — zero regressions from either pass.

### P37 — Finance Cost Entry Full Modernization + P8 Architecture Budget Restored (DIRECT FULL MODERNIZATION)

The last legacy Finance signal. Source reconfirmed `ProjectCostEntry` is a genuine hybrid: a
mutable draft/lifecycle aggregate (DRAFT → SUBMITTED → APPROVED → POSTED, or SUBMITTED → DRAFT via
`reject()`) with a true immutable-ledger correction concept for POSTED entries (`reverse` never
mutates the original's financial facts — it flips `status` to REVERSED and records a brand-new,
sign-flipped reversal entry). Five typed events
(`application/financials/cost/entries/cost_entry_events.py`) reflect that split rather than a
CRUD-shaped `CostEntryCreated/Updated/Deleted` or a single catch-all `CostEntryChanged`:
`CostEntryRecorded` (a new entry now exists — manual create arrives DRAFT; both integration
sources, Approved Time and Procurement receipt accrual, arrive already POSTED, since those two
paths advance draft→submit→approve→post synchronously in one command and the intermediate
transitions are internal plumbing, not independent facts — `status` lets ViewInvalidation decide),
`CostEntryUpdated` (genuine mutable-CRUD draft edit), `CostEntryStatusChanged` (`change_type:
SUBMITTED | APPROVED | REJECTED | POSTED` — one class, since `submit`/`approve`/`reject`/`post`
are literally the same kind of fact, a status-field transition, differentiated only by the
resulting state, mirroring the already-accepted `CommitmentLineChanged`/`FinancialChangeChanged`
enum-in-one-class precedent rather than four near-identical classes), `CostEntryReversed` (a
posted entry was reversed and a new reversal entry recorded — both the manual `reverse` command
and the correction-of-a-prior-revision branch inside `apply_approved_time_source`), and
`CostEntryRemoved` (draft deleted).

**Transaction ownership.** Eight direct commands (`create_manual_entry`, `update_draft`,
`delete_draft`, `submit`, `approve`, `reject`, `post`, `reverse`) converge onto
`FinanceGovernanceUnitOfWork` via a new `FinanceGovernanceCommandBoundary.cost_entry()` (direct
structural copy of `commitment()`), wrapped in an 8th `FinanceGovernedServicePort` family. Unlike
Commitment, every mutation except `create_manual_entry` resolves `project_id` identically (`self.
_read_service.get_entry(args[0]).project_id`) — `create_manual_entry` already passes `project_id`
as an explicit kwarg, so it's caught by the existing generic shortcut with no family-specific
branch needed. `_apply_approval_decision`/`_apply_rejection_decision` (the shared private helpers
behind both the direct `approve()`/`reject()` and the Approval participant) construct and return
`(entry, event)` — mirroring `ProjectCommitmentService._create_match`'s exact dual-path shape from
P36: `record_event` is called when wired (the governed path), and the returned event is used
directly by the participant (whose fresh per-transaction `ProjectCostEntryService` instance has no
`record_event` wired). Cost Entry's own commit-without-rollback characteristic was less severe
than Commitment's — the old `_commit()` already wrapped `self._session.commit()` in try/except/
rollback — but it was still a raw, uncanonical Session with a post-commit legacy-signal emit; that
raw `_commit()` method is deleted entirely.

**Approval path.** `ProjectCostApprovalParticipant.apply`/`reject` no longer return
`ApprovalPostCommitEvent("cost_entries_changed", ...)` — they forward the typed
`CostEntryStatusChanged` the shared decision helpers already built, via
`ApprovalHandlerResult(domain_events=(event,))`, recorded precommit by `ApprovalService`'s own
pre-existing canonical machinery (the exact seam `FinancialChangeApprovalParticipant` established
in P19) — no new participant-side event construction was needed.

**Integration dispatchers.** `apply_approved_time_source`/`apply_procurement_receipt_source` no
longer commit or emit — they construct and *return* their typed event(s) (0–2, since a correction
produces both a `CostEntryReversed` for the superseded entry and a `CostEntryRecorded` for the new
one). `ApprovedTimeFinancialDispatcher` gained the exact `SqlAlchemyUnitOfWorkBase`-wrapping shape
P36-FIX2 established for `ProcurementFinancialDispatcher` (a new capability for this dispatcher,
which never had it before) — proven by a dedicated precommit-timing/real-UoW-identity test
mirroring P36-FIX2's own. `ProcurementFinancialDispatcher`'s `_consume_under_unit_of_work` now
records both `consumption.commitment_events` and the new `consumption.cost_entry_events` into the
SAME one UoW per delivery (a receipt can genuinely produce both a Commitment match fact and a Cost
Entry recorded fact) — its `_emit_refresh` method, whose entire remaining job after P36-FIX2 was
the `cost_entries_changed` emit, is now fully dead and deleted outright.

**ViewInvalidation — two targets, not one, source-justified.** `finance_snapshot_statements.py`
confirms only `status IN ('posted', 'reversed')` entries count toward actual-cost aggregates, so
`cost_entry_list` (every fact — the "Costs" tab shows drafts too) and `cost_entry_actuals` (only
POSTED-affecting facts: `CostEntryRecorded` when `status=POSTED`, `CostEntryStatusChanged(POSTED)`,
`CostEntryReversed`) are genuinely distinct staleness surfaces. `on_cost_entry_list_stale`
invalidates only `"costs"`; `on_cost_entry_actuals_stale` invalidates `"overview"`/`"performance"`/
`"commercial"` (not `"costs"` again — already covered by the paired list hint every posted fact
also emits) — together reproducing the legacy signal's own exact 4-destination fan-out
(`overview`/`costs`/`performance`/`commercial` — confirmed NOT including `"planning"`, unlike
Commitment's 5).

**Legacy retirement.** `cost_entries_changed` deleted from `DomainEvents`, added to
`_DELETED_BRIDGE_NAMES`. `test_r6b_finance_invalidation.py`'s remaining cases and
`test_p7_legacy_bridge_removal.py`'s "unrelated signal" example moved onto `budgets_changed` (the
next still-legacy Finance signal); `budgets_changed`/`billing_preparations_changed` are the two
signals `test_p7c_zero_consumer_signal_cleanup.py`'s `_ACTIVE_FINANCE_SIGNALS` now names.

**Regression battery.** Existing `test_project_cost_entries.py` (8 tests) and
`test_project_cost_apply_participant.py` (5 tests) — full CRUD/lifecycle/concurrency/immutability
coverage — pass unmodified in behavior; `test_approved_time_labor_integration.py` (11 tests, 2
adapted to the typed-event/post-commit-bus path, 2 new precommit-timing/rollback proofs added) and
`test_procurement_financial_integration.py` (9 tests, 1 adapted) both pass; a new
`test_p37_finance_cost_entry_full_modernization.py` (21 tests) covers the two-target
ViewInvalidation handler (mapping + dedupe), every direct command's exact hint set, the
audit-failure rollback/session-reusability proof, the pre-existing optimistic-concurrency guard,
and both controller consumer reactions. Full broad Finance-area PM suite: 556 passed (only the
same pre-existing, unrelated `test_financials_mutation_error_boundary.py` harness bug remains,
confirmed untouched by this diff). **P8 guard suite: all 29 tests green** — the milestone this
phase exists to reach.

**P37-FIX (verification, no new phase number).** A full-platform-suite re-run surfaced one real
regression `test_phase_b_session_permissions.py::test_governance_permissions_are_split_between_
request_and_decide` caught: routing Cost Entry's `approve()` through the newly-governed
`FinanceGovernedServicePort` meant `_project_id()` resolved the project id via the
permission-checked public `get_entry()` (requires `finance.read`) *before* `approve()`'s own
correct permission check (`approval.request`/`project_cost.approve`) ever ran — silently
demanding an extra permission the command never required. Fixed by resolving via the unchecked
private `_require_entry()` instead (the `cost_entry` family's `_project_id()` branch), matching
the more careful precedent Commitment's own `reverse_match` branch already used (raw repo access,
not a permission-checked accessor) rather than the less-careful one `match_cost_entry`'s branch
and every Budget line-mutation branch still use — flagged as latent, pre-existing architectural
debt in those other families (not touched; out of P37's scope) in the P38A audit below. Full
platform suite before/after this fix: identical 19-failed/1602-1603-passed/12-error totals (the
19 pre-existing baseline, now that P8's own 4 are green) — confirmed zero other regressions.

### P38A — Finance Remaining Re-Evaluation: Budget vs Billing Preparation (AUDIT + SEQUENCING ONLY)

No production code changed. Confirmed the two remaining Finance legacy signals from source:
`budgets_changed`, `billing_preparations_changed` — matches expectation exactly, no stale-roadmap
surprise.

**Budget.** Producers (3): `command_boundary.py`'s `_emit_budget` (the `budget()` governance
boundary's post-commit `invalidation` callback — the direct/governed-command producer, OWNER);
`budget_apply_participant.py`'s `apply`/`reject` (`ApprovalPostCommitEvent`, OWNER); and, critically,
`financial_change_apply_participant.py`'s `apply()` (`if change.applied_budget_id:
ApprovalPostCommitEvent("budgets_changed", ...)`, CROSS-CAPABILITY — a REAL, already
transaction-safe cross-capability edge, not incidental). Consumers (2, both genuine):
`financials_refresh_mixin.py`'s `_budgets_changed` (`overview`/`planning`/`performance`, OWNER) and
`project_domain_event_binder.py` (Projects workspace, blanket `_request_domain_refresh()`,
CROSS-CAPABILITY/REAL SUMMARY). Twelve real operations, ALL twelve already routed through
`FinanceGovernedServicePort(family="budget")` → `FinanceGovernanceCommandBoundary.budget()` →
`FinanceGovernanceUnitOfWork` — **Budget's direct-command transaction convergence is already
100% complete**, the only Finance capability found in this state before its own typed-event work
began. Lifecycle: explicit `_ALLOWED_TRANSITIONS` state machine on `ProjectBudget`
(`DRAFT→SUBMITTED→{APPROVED,REJECTED}`, `APPROVED→{SUPERSEDED,CLOSED}`), plus child `BudgetLine`
rows; both carry `row_version` (optimistic concurrency, `expected_version`/
`expected_budget_version`/`expected_line_version` checked on every mutation) and `ProjectBudget`
additionally carries an immutable `revision` (version lineage). Audit: atomic
(`record_audit_entry(..., commit=False, fail_closed=True)`) on every mutation, same established
pattern as every already-modernized family. Concurrency: SAFE — optimistic version checks plus two
DB-level partial-unique constraints (`uq_pf_budgets_one_open_per_project`,
`uq_pf_budgets_one_approved_per_project`) translated to named `ConcurrencyError`/`BusinessRuleError`
codes, not raw `IntegrityError` leaks.

**The Financial Change coupling, rechecked (P38A's central question).** `financial_change_service.
_apply_budget_successor` calls `self._budget_authority._apply_approved_financial_change(...)` — a
purpose-built `BudgetService` method (not ad-hoc repo poking) that creates a new approved
`ProjectBudget` successor version and supersedes the prior one. `build_financial_change_approval_
deps` constructs `budget_authority = BudgetService(session=session, ...)` bound to the *same*
session as `financial_change_service` — i.e., this is a category **C** edge (real persisted
cross-capability mutation) that is **already running inside the correct, single, canonical
transaction** (`ApprovalService`'s own UoW for the `financial_change.apply` decision). Financial
Change's own facts are already typed (`FinancialChangeChanged`); what remains untyped is the
**Budget-side** fact this call produces. This directly answers P38A's key question: **Financial
Change modernization did not remove Budget's complexity by shrinking the coupling — it removed the
coupling's *ambiguity*.** The edge is clean, well-defined, and already transaction-safe; the
remaining work is entirely on Budget's own side (give Budget a typed vocabulary; have
`financial_change_apply_participant.apply()` gain one more `if change.applied_budget_id:` branch
constructing that event, exactly mirroring the `ForecastVersionChanged` branch already there for
`applied_forecast_id` — no `BudgetService` changes needed for this specific edge, since the caller
already has everything it needs from `ApprovedFinancialSuccessorResult`).

**Approval readiness: READY.** `BudgetApprovalParticipant.apply`/`reject` are the exact
pre-modernization shape every other participant had before its own phase (fresh session-bound
`BudgetService`, `approval_service=None`, calls the already-existing `_apply_approval_decision`/
`_apply_rejection_decision`) — trivially convertible to `ApprovalHandlerResult(domain_events=(...))`
with zero `ApprovalService` changes, the identical P19 seam every prior phase reused.

**Transaction readiness: effort LOW (essentially zero)** — already fully governed. **Audit
readiness: ATOMIC**, no gap. **Proposed facts** (source-supported, not mechanical CRUD):
`BudgetVersionCreated` (`create_budget`/`create_successor`, and the Financial-Change-driven
successor — one shape, three producers, mirroring Commitment's `CommitmentLineChanged(CREATED)`
precedent), `BudgetLineChanged` (`add_line`/`update_line`/`delete_line` — one class + operation
enum, mirroring `CostEntryStatusChanged`'s "same kind of fact" reasoning), `BudgetStatusChanged`
(`change_type: SUBMITTED|APPROVED|REJECTED|SUPERSEDED|CLOSED` — one class, five near-identical
status transitions, same reasoning as Cost Entry's own status-transition event).
**ViewInvalidation**: one project-scoped `budget_list`/`budget_detail`-equivalent target for the
Financials-workspace consumer (source shows list+detail always queried together, no independent
detail cache — matching every prior single-target precedent) *plus* a second, narrower hint for
the Projects-workspace consumer (currently a blanket refresh; a typed event lets it narrow to
exactly what it needs, an improvement over today's behavior, not merely parity). **`budgets_changed`
deletable in one phase: YES — HIGH confidence.** No blocker identified. **Budget direct full
modernization ready: YES.**

**Billing Preparation — two genuinely distinct aggregates, not a category error.**
`ProjectBillingProfile` (+ child `ProjectBillingScheduleLine`) in `billing_profile_service.py`:
commercial-terms/contract header and a fixed-price milestone schedule — 4-state lifecycle
(`DRAFT→ACTIVE→{ON_HOLD,CLOSED}`), 4 operations (`create_profile`, `activate_profile`,
`add_schedule_line`, `mark_schedule_line_ready`), all raw `self._session.commit()` via one shared
`_persist()` helper (try/except/rollback around commit — same "safer than Commitment's old bug,
but still uncanonical" shape Cost Entry had before P37), zero governance, zero Approval
involvement. `ProjectBillingPreparation` (+ `ProjectBillingPreparationLine`/
`ProjectBillingSourceLock`/`ProjectBillingExternalEvent`) in `preparation_service.py`: the
per-period invoice-evidence assembly, external-accounting-delivery, and reconciliation workflow —
a much richer 9-state lifecycle (`DRAFT→SUBMITTED→APPROVED→DELIVERY_PENDING→DELIVERED→
ACKNOWLEDGED→RECONCILED`, plus `REJECTED`/`CANCELLED`), 9 operations. **Why they share one
signal: category B** (related but semantically distinct business capabilities that both happen to
affect the same "commercial" Financials-tab UI destination) — not a shared read model (C) and not
pure legacy fan-out convenience (D); a future modernization should use genuinely distinct
DomainEvent families per aggregate even though today's one UI target can keep receiving both.

**Billing transaction readiness is uneven, not absent.** `submit_preparation` already owns a
bespoke, purpose-built canonical UoW (`BillingPreparationSubmissionUnitOfWorkFactory` —
`billing`+`approvals` repos, `uow.record_event`, `uow.commit()`; narrower than
`FinanceGovernanceUnitOfWork`, not currently exposing a `billing` accessor there) — the *only*
Finance operation found across Budget+Billing that is transaction-canonical but still emits a
legacy signal post-commit (a PARTIAL state, closer to done than "raw"). Every other Preparation
operation (`create_preparation`, all three `add_*_source` methods via `_reserve`/`_write`,
`request_delivery`, `record_external_outcome`) and all four Profile operations are raw-Session,
try/except/rollback-around-commit — the same shape Cost Entry had before P37, times two aggregates
instead of one. Approval readiness: READY for the same reason as Budget (participant is the
identical pre-modernization shape, and per its own docstring `_apply_approval_decision`/
`_apply_rejection_decision` have exactly one caller each in the whole codebase — no direct,
non-governed approve/reject path exists at all for Preparation, simpler than Budget's dual path).
Audit: ATOMIC on every operation in both aggregates, no gap. Concurrency: SAFE — `row_version` on
every aggregate/line/lock, `expected_row_version`/`expected_version` checked throughout, plus a
real idempotency key on preparation creation and a DB-level source-reservation uniqueness
constraint (`BILLING_SOURCE_ALREADY_RESERVED`) preventing the same billable source from being
double-prepared.

**Proposed facts, kept separate by aggregate** (never a `BillingPreparationsChanged` catch-all):
Profile — `BillingProfileActivated`, `BillingScheduleLineChanged` (add/ready, one class + enum).
Preparation — `BillingPreparationCreated`, `BillingPreparationLineAdded` (three source types, one
fact), `BillingPreparationStatusChanged` (submitted/approved/rejected — mirrors Budget's/Cost
Entry's own status-transition shape), `BillingPreparationDeliveryRequested`,
`BillingPreparationExternalOutcomeRecorded` (delivered/acknowledged/reconciled — the
external-accounting-boundary facts, genuinely distinct from the internal-approval facts above).
**ViewInvalidation**: both aggregates currently stale the *same* single `"commercial"` Financials
destination (one genuine consumer, LOW consumer complexity — the lowest of any Finance capability
audited) — source shows no independent per-aggregate read model, so one shared project-scoped
target remains correct even once the DomainEvent vocabulary is split by aggregate.
**`billing_preparations_changed` deletable in one phase: MEDIUM confidence** — both aggregates
*can* be modernized together (neither is individually blocked, and their combined producer/consumer
surface is smaller than Budget's), but real transaction-convergence work (adding a `billing`
accessor to whichever UoW is chosen, or extending the bespoke submission UoW to cover the other
eight operations) is required across two aggregates rather than zero, roughly doubling Cost Entry's
own already-substantial P37 implementation surface. **Billing direct full modernization ready:
YES, but at meaningfully higher implementation cost than Budget** — not blocked, not requiring a
dedicated audit phase, just larger.

**Reflective legacy mechanisms, recomputed.** `ApprovalPostCommitEvent(...)` remaining production
call sites (5, all genuinely still needed, none touched): `baseline_apply_participant.py`,
`billing_preparation_apply_participant.py`, `budget_apply_participant.py`,
`financial_change_apply_participant.py` (its `tasks_changed`/PM-coupling branch, plus the
`budgets_changed` branch this audit examined), `task_apply_participant.py`.
`ApprovalService._emit_signal_safely` remains, required by those 5. `FinanceGovernedServicePort.
__getattr__` reflective *command routing* is explicitly **not** legacy-event-publication
machinery — it is the current canonical mechanism, now used by 9 families (`financial_setup`,
`budget`, `forecast_version`, `forecast_generation`, `financial_change`, `rate_card`,
`planned_cost`, `commitment`, `cost_entry`); no explicit typed port methods exist (fully
`__getattr__`-dynamic), no permission enforcement of its own (delegated to each wrapped service's
own `require_permission`/`require_project_permission` calls), a per-instance `mutations`
frozenset acts as the command allowlist. Neither Budget nor Billing modernization requires
changing it — confirmed by tracing exactly how a 9th/10th/11th family would be added (a new
`family=` branch in `_project_id()`, following the pattern already used 8 times).
**Architectural debt noted, not fixed**: `_project_id()`'s `budget`/`match_cost_entry` branches
resolve via permission-checked public accessors (`get_budget`/`get_line`) the same way P37's now-
fixed `cost_entry` branch originally did — a latent, currently-unexercised risk of the exact same
silent-extra-permission bug, left as-is (out of P38A's audit-only scope; worth a one-line fix
alongside whichever phase next touches that branch).

**Cross-capability graph (remaining capabilities only).** Budget ← Financial Change (C, one edge,
already transaction-safe, typed on the Financial-Change side already). Billing Profile: zero
mutation edges to/from any other Finance capability (fully self-contained). Billing Preparation →
Cost Entry (A, reference-only: `add_cost_plus_source` reads a POSTED `ProjectCostEntry` row, never
writes it) and → Approved Time/`ApprovedTimeLaborPosting` (A, reference-only, via
`labor_posting_repo`). No edges touch Commitment, Planned Cost, or Forecast for either remaining
capability.

**Comparison scorecard.**

| | Budget | Billing Preparation |
|---|---|---|
| Semantic clarity | HIGH — explicit state machine | HIGH — two distinct, now-named aggregates |
| Transaction readiness | READY (100% already governed) | PARTIAL (1 of 13 ops canonical; rest raw) |
| Approval readiness | READY | READY |
| Audit readiness | ATOMIC, no gap | ATOMIC, no gap |
| Concurrency safety | SAFE | SAFE |
| Cross-capability coupling | LOW (1 edge, already safe) | LOW (2 reference-only edges) |
| Consumer complexity | MEDIUM (2 genuine consumers) | LOW (1 genuine consumer) |
| UI precision | MEDIUM (2 targets to design) | LOW (1 shared target, already precise) |
| Test readiness | HIGH (2215 test lines) | MEDIUM-HIGH (1276 test lines) |
| One-phase deletion confidence | HIGH | MEDIUM |
| Correctness gap closed by modernizing | Cleaner FinancialChange↔Budget event, narrower Projects-workspace refresh | None material (already atomic/safe) |

**Selected: Budget.** Per the priority order: (1) one-phase deletion — Budget HIGH vs Billing
MEDIUM; (2) semantic clarity — both HIGH, tie; (3) approval/cross-capability canonical — both
READY, tie; (4) transaction-convergence effort — Budget LOW (already done) vs Billing MEDIUM-HIGH
(real work across two aggregates) — **Budget wins decisively here**, and this criterion alone
would be enough given every earlier criterion is a tie or near-tie. Not chosen "because listed
first" — chosen because it is, uniquely among every Finance capability audited across this entire
engagement, the one whose transaction convergence was already complete before its own
event-modernization phase began.

**Recommended P38B: Finance Budget Full Modernization — DIRECT FULL MODERNIZATION.** This audit
itself resolved every semantic and architectural question a dedicated Budget audit would have
existed to answer (the P34A-era open question — Financial Change coupling — is now closed).
**Expected following Finance phase: Billing Preparation** (both aggregates together, since neither
is individually blocked and splitting would only duplicate the same shared-target ViewInvalidation
design work twice) — likely still DIRECT FULL MODERNIZATION given no blocker was found, just a
larger implementation surface than Budget, closer in size to P37 doubled.

**Finance completion projection.** Current Finance legacy count: 2. After Budget: 1
(`billing_preparations_changed` only). After Billing: 0 — **these are confirmed, source-derived,
the true last two Finance legacy fields** (no other Finance-owned field exists in current
`DomainEvents`).

**Overall legacy projection.** Current overall count: 9 (source-derived, unchanged by this
audit-only pass). If both remaining Finance phases complete with no concurrent changes: 7,
consisting of PM 6 (`project_changed`, `tasks_changed`, `timesheet_periods_changed`,
`collaboration_changed`, `portfolio_changed`, `register_changed`) + Auth 1 (`auth_changed`) — this
is the current, source-confirmed landscape, not an assumption.

**Baseline regression debt.** The 19 pre-existing platform-suite failures/errors (enterprise
calendar/shift patterns, party/site/department domain validation, platform persistence structure,
access scopes, org desktop API, qml admin catalog, repository tenant hardening, auth registration
audit atomicity, approval-events submission-count assertions) do not touch Budget, Billing
Preparation, or their dependencies (Financial Change, Cost Entry, Approved Time) — none block
trustworthy characterization of either capability. Carried forward as unrelated baseline debt, not
fixed here.

### P38B — Finance Budget Full Modernization (DIRECT FULL MODERNIZATION)

Reconfirmed P38A's audit against current source before editing: 12 operations
(`create_budget`, `create_successor`, `submit_budget`, `approve_budget`, `reject_budget`,
`close_budget`, `update_budget_header`, `delete_budget`, `add_line`, `update_line`, `delete_line`
all already `FinanceGovernedServicePort(family="budget")`-routed — the brief's own "12 operations"
list additionally named `reject_budget_approval`, which does not exist in source under any name;
source wins, the operation list is the 12 above). `_emit_budget` confirmed as the sole direct
producer (3 producer mechanisms unchanged from P38A: `_emit_budget`, `BudgetApprovalParticipant`,
`financial_change_apply_participant.apply()`); 2 genuine consumers unchanged (Financials workspace,
Projects workspace blanket refresh).

**Final event vocabulary — five classes, not three, after checking header-update and delete
semantics against P38A's candidate three (§7-§9 of the brief).** `BudgetVersionCreated`
(`create_budget`/`create_successor`, plus the Financial-Change-driven successor — `status` field
distinguishes a normal DRAFT creation from the Financial-Change path's already-APPROVED one, since
that path never persists an intermediate DRAFT/SUBMITTED row; `predecessor_budget_id` carries
lineage when present). `BudgetProfileUpdated` — `update_budget_header`'s name/notes edit is a
genuine fourth fact, not a status transition and not a line mutation; forcing it into
`BudgetStatusChanged` or a generic `BudgetChanged` would have hidden real semantics to preserve an
arbitrary three-class count. `BudgetLineChanged` (`add_line`/`update_line`/`delete_line` — one
class + `change_type` enum, mirroring `CostEntryStatusChanged`'s "same kind of fact" reasoning).
`BudgetStatusChanged` (`change_type: SUBMITTED|APPROVED|REJECTED|SUPERSEDED|CLOSED`). `BudgetRemoved`
— `delete_budget`'s hard delete of a DRAFT is a genuine fifth fact (aggregate-level, not per-line:
source confirms `delete_budget` calls one repository `delete()`, no per-line cascade events are
warranted since no individual-line business meaning attaches to a whole-aggregate delete).

**Successor/supersession multi-fact behavior — confirmed, not assumed.** Direct source reading of
`create_successor` proved it does **not** touch the predecessor at all — supersession is an
approval-time fact, not a creation-time one, contradicting the brief's own §25 hypothesis (a
dedicated regression test, `test_create_successor_alone_does_not_supersede_the_predecessor`, proves
this). The real two-fact case is `_apply_approval_decision`: when a competing approved budget
already exists for the project, approving a successor emits **both**
`BudgetStatusChanged(previous, SUPERSEDED)` **and** `BudgetStatusChanged(this budget, APPROVED)` —
one fact per actually-mutated `ProjectBudget` row, in the same transaction, both recorded precommit
(`test_approving_a_successor_supersedes_the_previous_approved_version`).

**Direct-command transaction ownership — unchanged, now recording typed events instead of a
post-commit signal.** `BudgetService` gained `record_event: Callable[[object], None] | None = None`
(the exact Cost Entry/Commitment constructor shape); every direct mutation calls
`self._record_event(event)` guarded by `is not None`, wired to `uow.record_event` only for the
governed `budget_operations` instance `build_finance_governance_operations` constructs (the
approval-participant's own fresh `BudgetService`, built by `build_budget_approval_deps`, is
deliberately never given `record_event` — same established dual-use-service pattern Cost Entry's
`_apply_approval_decision`/`_apply_rejection_decision` already established: the shared decision
helpers build and return `(budget, events)`/`(budget, event)`, called-but-discarded on the direct
path since the events are already recorded via `record_event` there, and taken and returned via
`ApprovalHandlerResult(domain_events=...)` on the participant path where `record_event` is None).
`command_boundary.py::_emit_budget` and `budget()`'s `invalidation=` callback are deleted outright
— once Budget was the *last* family still passing a non-None `invalidation`, the whole
`invalidation` parameter on `_execute` became dead code and was removed too (not left as an
always-None-invoked no-op).

**Cross-capability path — Financial Change → Budget, both typed facts now coexist in one
`ApprovalHandlerResult`.** `BudgetService._apply_approved_financial_change` now builds and returns
`(successor-created, base-superseded)` typed events via a new `domain_events` field added to the
shared `ApprovedFinancialSuccessorResult` dataclass (default `()`, so Forecast's identical-shaped
call site is unaffected). `FinancialChangeService._apply_budget_successor`/`_apply_approval_decision`
thread that tuple upward; `FinancialChangeApprovalParticipant.apply()` no longer conditionally
builds `ApprovalPostCommitEvent("budgets_changed", ...)` — it appends the returned Budget
`domain_events` tuple onto its own `FinancialChangeChanged`(+`ForecastVersionChanged`) tuple, so one
ApprovalService transaction can legitimately record a Financial Change fact and one-or-two Budget
facts together
(`test_financial_change_application_produces_budget_and_financial_change_facts_together`).

**Permission-order bug — fixed for Budget, exactly the P37-FIX pattern.**
`FinanceGovernanceCommandBoundary._project_id()`'s `budget` branch called the permission-checked
public `get_budget()` to resolve a target budget's project_id before the actual command's own
permission check ever ran — silently requiring `finance.read` first. Fixed by switching to the
private, unchecked `_require_budget()` (all three sub-branches: `add_line`, `update_line`/
`delete_line`, and the bare-`args[0]` fallback used by every other budget-family command).
Commitment's `match_cost_entry` branch, flagged with the identical bug pattern in the P38A audit,
remains deliberately untouched — out of scope, not part of Budget's own family. Regression proof:
`test_add_line_permission_check_is_not_masked_by_project_id_resolution` (a viewer, lacking both
`finance.read` and `budget.manage`, is now rejected on `budget.manage` — the actual missing command
permission — not on `finance.read`).

**Approval path.** `BudgetApprovalParticipant.apply`/`reject` no longer return
`ApprovalPostCommitEvent("budgets_changed", ...)` — they forward the typed event(s) the shared
decision helpers already built, via `ApprovalHandlerResult(domain_events=events)`/
`ApprovalHandlerResult(domain_events=(event,))`, recorded precommit by `ApprovalService`'s own
pre-existing canonical machinery — the identical P19 seam every prior phase reused, no
`ApprovalService` changes.

**ViewInvalidation — two targets, uniformly mapped, source-preserving.** `budget_planning`
(Financials workspace — `overview`/`planning`/`performance`, reproducing the legacy signal's own
exact 3-destination fan-out) and `budget_project_summary` (Projects workspace). Every current
Budget fact stales both targets — the legacy `budgets_changed` signal never differentiated by fact
type for either of its two consumers either, so this uniform mapping is source-preserving, not an
invented fan-out (unlike Cost Entry's genuinely distinct two-target split, which was justified by a
real `status IN (...)` SQL filter Budget has no equivalent of). The Projects-workspace consumer is
a real behavior *improvement*, not just a mechanism swap: the old `project_domain_event_binder.py`
blanket-subscribed `budgets_changed` with **zero project-id filtering at all** (`_on_domain_event`
ignored its payload entirely, refreshing the whole workspace for *any* project's budget change);
the new `on_budget_project_summary_stale` is genuinely project-scoped, matching the Financials
consumer's own established `_selected_project_id` equality check.

**Legacy retirement.** `budgets_changed` deleted from `DomainEvents`, added to
`_DELETED_BRIDGE_NAMES`. `test_p7_legacy_bridge_removal.py`'s "unrelated signal" example and
`test_r6b_finance_invalidation.py`'s parametrized case moved onto `billing_preparations_changed`
(the one remaining Finance legacy signal); `test_p7c_zero_consumer_signal_cleanup.py`'s
`_ACTIVE_FINANCE_SIGNALS` now names only `billing_preparations_changed`.
`test_r6c_finance_governance_command_boundary.py`'s two `budget()`-invalidation-specific tests
(which tested the now-deleted `invalidation=` callback) were replaced with equivalent
`post_commit_actions`-failure-isolation proofs — `budget()` itself no longer has any post-commit
mechanism of its own to test.

**Regression battery.** New `test_p38b_finance_budget_full_modernization.py` (22 tests) covers the
ViewInvalidation handler's uniform two-target mapping + dedupe, every direct command's exact hint
set, the successor/supersession two-fact case, the create-successor-does-not-supersede proof, the
governed-approval-participant path, the Financial-Change cross-capability path, the permission-order
regression, the audit-failure rollback/session-reusability proof, the pre-existing
optimistic-concurrency guard, and the Financials-workspace consumer reaction. `test_project_finance_
budgets.py`, `test_r6c_finance_governance_command_boundary.py`, `test_r6b_finance_invalidation.py`,
`test_r42_approved_budget_read_correctness.py` (Projects-workspace consumer rewritten onto
`on_budget_project_summary_stale`, plus a new non-selected-project-is-ignored proof),
`approval/test_budget_apply_participant.py`, `approval/test_financial_change_apply_participant.py`
all pass, adapted where they asserted on the deleted signal/mechanism. Platform suite:
`test_p7_legacy_bridge_removal.py`, `test_p7b_dead_signal_cleanup.py`,
`test_p7c_zero_consumer_signal_cleanup.py`, `test_p8_platform_event_architecture_canonicalization.py`,
`test_phase_b_session_permissions.py`, `test_approval_service_unit_of_work_cutover.py` all pass
unmodified in intent (adapted only where they referenced `budgets_changed` directly). Full
project_management-area suite green; full platform suite carries forward the same 19 pre-existing
failures/12 errors, none newly introduced.

### P39 — Finance Billing Full Modernization + Eliminate Final Finance Legacy Signal (DIRECT FULL MODERNIZATION)

**The final Finance legacy signal, eliminated.** Reconfirmed P38A's audit against current source:
7 legacy producer sites (`billing_profile_service.py`'s shared `_persist` helper; `preparation_
service.py`'s shared `_write` helper, `submit_preparation`'s own explicit emit, and the
conditional emits inside `_apply_approval_decision`/`_apply_rejection_decision`;
`billing_preparation_apply_participant.py`'s `apply`/`reject` `ApprovalPostCommitEvent` sites — 5
in the two services + 2 in the participant = 7, exactly matching P38A's expectation) and 1
genuine consumer (`financials_refresh_mixin.py`'s `_billing_changed` → `"commercial"`).

**Two genuinely distinct aggregate families, kept distinct — never merged, never a catch-all.**
Confirmed via source: `ProjectBillingProfile`/`ProjectBillingScheduleLine` (Billing Profile) and
`ProjectBillingPreparation`/`ProjectBillingPreparationLine` (Billing Preparation) are separate
aggregate roots with separate lifecycles. `ProjectBillingSourceLock` is infrastructure (prevents
the same billable source being reserved twice — confirmed by its `BILLING_SOURCE_ALREADY_
RESERVED` IntegrityError translation), not an independent business fact — no `SourceLockCreated`
event. `ProjectBillingExternalEvent` IS a genuine business fact (the external accounting system's
response), not merely a dedupe row — it gets its own typed event.

**Final event vocabulary — nine classes across two families, none a `BillingChanged`/
`BillingPreparationChanged` catch-all.** Profile: `BillingProfileCreated`, `BillingProfileActivated`
(the ONLY currently-reachable Profile status transition — `place_on_hold`/`close` exist as domain
methods with no service-layer command, so ON_HOLD/CLOSED are correctly unrepresented),
`BillingScheduleLineAdded`, `BillingScheduleLineMarkedReady` (likewise the only reachable
schedule-line transition — `mark_billed`/`cancel` have no command). Preparation:
`BillingPreparationCreated`, `BillingPreparationLineAdded` (`add_fixed_price_source`/
`add_approved_time_source`/`add_cost_plus_source` — one class + the reused domain
`BillableSourceType` enum, not a duplicate), `BillingPreparationStatusChanged` (`SUBMITTED`/
`APPROVED`/`REJECTED`/`DELIVERY_PENDING`/`DELIVERED`/`ACKNOWLEDGED`/`RECONCILED` — `CANCELLED` has
no command and is unrepresented), `BillingPreparationExternalOutcomeRecorded`. A separate
`BillingPreparationDeliveryRequested` fact (P38A's own candidate) was explicitly investigated and
found unnecessary: `request_delivery` persists nothing beyond the status transition itself (its
in-memory delivery payload is returned to the caller, never written to an outbox or given an
allocated external identifier) — confirmed by direct source reading, not assumed.
`record_external_outcome(DELIVERY_ACCEPTED)` transitions status twice in one call (`mark_delivered`
then `acknowledge`, both persisted) — both are recorded as two separate `BillingPreparationStatus
Changed` facts alongside the one `BillingPreparationExternalOutcomeRecorded` fact, mirroring
Budget's approve/supersede two-fact precedent (P38B).

**Transaction architecture — no mega-UoW; the existing canonical `FinanceGovernanceUnitOfWork` is
broadened by exactly one accessor.** Both services already shared ONE `ProjectBillingRepository`
covering every Profile/Preparation/Line/Lock/ExternalEvent operation — so `FinanceGovernanceUnit
OfWork` gained a single `billing: ProjectBillingRepository` accessor (the same repository, not a
new one), and BOTH families converge onto it via two new `FinanceGovernanceCommandBoundary`
methods (`billing_profile()`, `billing_preparation()`) and two new `FinanceGovernedServicePort`
families — the identical shape every other Finance capability already uses, not a special case.
The bespoke `BillingPreparationSubmissionUnitOfWork`/`SqlAlchemyBillingPreparationSubmissionUnitOf
WorkFactory` (previously owning only `submit_preparation`) is **retired entirely — both files
deleted, no compatibility alias** — its narrow `billing`+`approvals` repo set was already a strict
subset of what `FinanceGovernanceUnitOfWork` provides, so broadening it would have meant
maintaining a second, near-duplicate governance UoW rather than reusing the one 9 other families
already share.

**`submit_preparation` — governed convergence without adding a permission requirement.**
`ProjectBillingPreparationService` gained the standard `record_event` constructor param plus an
`_approval_repo`/`_approval_requested_staged` pair (wired post-construction by composition,
mirroring `FinancialChangeService`'s identical two attributes). `submit_preparation` now calls the
transaction-agnostic `request_approval_using(...)` helper directly (never `ApprovalService.request_
change(...)`, which would have added a new `"approval.request"` permission requirement on top of
the existing `"finance.manage"` check — a real behavior change P39 deliberately avoided, even
though Financial Change's own `submit_change` independently chose to require both). Both the
preparation update and the `ApprovalRequest` now share the ONE governance UoW transaction.

**Approval path.** `BillingPreparationApprovalParticipant.apply`/`reject` no longer return
`ApprovalPostCommitEvent("billing_preparations_changed", ...)` — `_apply_approval_decision`/
`_apply_rejection_decision` dropped their `commit: bool` flag entirely (transaction ownership is
now always the caller's), unconditionally build their typed `BillingPreparationStatusChanged` fact,
and return `(preparation, event)` — the participant forwards it via `ApprovalHandlerResult(domain_
events=(event,))`, the identical P19 seam every prior phase reused.

**ViewInvalidation — one shared target, uniformly mapped, by design.** `billing_commercial` is the
only target either family maps to — P38A found no independent per-family cached UI projection, so
a single shared target is correct even with two fully distinct DomainEvent vocabularies (DomainEvents
describe what happened; ViewInvalidation describes what became stale — deliberately not the same
design axis). Every current Billing fact from either family stales it, reproducing the legacy
signal's own single `"commercial"` destination exactly.

**Permission-order bug — checked for both new families, fixed where it existed.**
`FinanceGovernanceCommandBoundary._project_id()`'s new `billing_profile`/`billing_preparation`
branches resolve via the private, unchecked `_require_schedule_line`/`_require_preparation`
accessors (never a permission-checked public getter) — the P37-FIX/P38B pattern applied
proactively this time, not discovered as a regression after the fact.

**Legacy retirement.** `billing_preparations_changed` deleted from `DomainEvents`, added to
`_DELETED_BRIDGE_NAMES`. **Finance module event modernization is now complete: zero Finance-owned
legacy Signal fields remain anywhere in `DomainEvents`** — a new permanent architecture guard,
`test_zero_finance_legacy_signal_fields_remain` (`test_p8_platform_event_architecture_
canonicalization.py`), asserts this explicitly by known-name-set (not a fragile prefix heuristic,
since Finance signal names never shared a common prefix) so a future reintroduction — the exact
`cost_entries_changed`/`commitments_changed` post-freeze archaeology this document already
documents once — would be caught immediately. `test_r6b_finance_invalidation.py`'s remaining
cases and `test_p7_legacy_bridge_removal.py`'s "unrelated signal" example — both previously
standing in on a Finance signal — moved onto PM-owned `tasks_changed`/`auth_changed` respectively,
since no Finance signal remains to stand in at all.

**Regression battery.** New `test_p39_finance_billing_full_modernization.py` (19 tests) covers the
single-target ViewInvalidation mapping + dedupe, both families' full direct-command producer paths,
idempotent-replay proofs (create/source-reservation/external-outcome), the governed-approval-
participant path (approve and reject), the two-status-fact `DELIVERY_ACCEPTED` case, the
permission-order regression for both new families, the audit-failure rollback/session-reusability
proof, the pre-existing optimistic-concurrency guard, and the Financials-workspace consumer
reaction. `test_billing_preparation_apply_participant.py` (adapted: fresh-UoW spy repointed to the
governance UoW factory, `post_commit_events`/`ApprovalPostCommitEvent` assertions replaced with
typed `domain_events`), `test_project_finance_billing_command_surface.py`,
`test_project_billing_preparation_foundation.py`, `test_r6b_billing_reader.py`,
`test_project_finance_profitability_projection.py` all pass unmodified in behavior. Platform
suite: `test_p7_legacy_bridge_removal.py`, `test_p7b_dead_signal_cleanup.py`,
`test_p7c_zero_consumer_signal_cleanup.py`, `test_p8_platform_event_architecture_
canonicalization.py`, `test_phase_b_session_permissions.py`,
`test_approval_service_unit_of_work_cutover.py`, `test_p6_view_invalidation_adapter_
consolidation.py` all pass. `test_approval_events.py`'s billing "exactly one approval requested"
assertion now joins its 6 already-broken siblings (Requisition/PurchaseOrder/Financial Change/
Budget approve/Budget reject/Budget ordering) — the same pre-existing, precedented "submission-
count assertions became stale once typed events were added" baseline debt every prior modernizing
phase (P19, P28B, P29, P38B) already left unfixed for its own capability; not fixed here either,
for consistency. 379 targeted tests pass across every touched file; zero new regressions found.

### P39-CLEANUP — Repair Stale Approval Submission-Count Tests Before PM Modernization (TEST/ARCHITECTURE CHARACTERIZATION CLEANUP ONLY)

**Test-only cleanup; zero production code touched.** The 7 stale `test_approval_events.py`
"submission-count" failures P39 carried forward as baseline debt were repaired at their real root
cause rather than left as accepted debt indefinitely, since PM modernization (the next track) will
keep adding typed events to these same submit/approve/reject transactions, making the naked
`len(recorded) == N` pattern permanently brittle. Each of the 4 "submit" tests
(Requisition/PurchaseOrder/Financial Change/Billing Preparation) now filters `recorded` by
`isinstance(..., ApprovalRequested)` — durable regardless of how many other typed facts a
modernized capability's own submission records alongside it — and separately asserts the
capability's own companion event (`InventoryRequisitionSubmitted`/`InventoryPurchaseOrderSubmitted`/
`FinancialChangeChanged`/`BillingPreparationStatusChanged`) explicitly, turning a silent count into
two positive characterizations. The two Budget decision tests (approve/reject) got the identical
treatment against `ApprovalApproved`/`ApprovalRejected` plus an explicit `BudgetStatusChanged`
assertion.

**A genuine test-assumption error, found and corrected — not a production bug.** The ordering test
(`test_approve_and_apply_orders_target_event_before_approval_approved`) asserted `[target
event(s)..., ApprovalApproved]` as the committed order; direct reading of `ApprovalService.
approve_and_apply`'s source (unchanged, never touched) proves the real, always-been-this-way order
is the OPPOSITE — `uow.record_event(ApprovalApproved(...))` runs before the `for domain_event in
handler_result.domain_events` loop. The test had apparently never been exercised against a real
2+-event scenario until Budget's own modernization (P38B) gave it one. Renamed to `test_approve_
and_apply_records_approval_approved_before_the_target_event` and corrected to match verified
production behavior.

**A stale capability-classification error, also found and corrected.** `baseline_apply_participant.py`
was being carried forward across P38A/P38B/P39's own reports as a "remaining legacy `ApprovalPostCommitEvent`
site" — re-reading its current source during this cleanup found it was already fully modernized at
P23 (`ApprovalHandlerResult(domain_events=(ProjectBaselineCreated(...),))`), long before this
Finance-modernization arc began; the docstring's own `ApprovalPostCommitEvent("baseline_changed", ...)`
mention is historical prose describing what it used to do, not live code. **The real, source-verified
remaining legacy `ApprovalPostCommitEvent` production baseline is exactly two files** — `financial_
change_apply_participant.py` (its schedule-impact branch only) and `task_apply_participant.py` (all
five Task-family decisions) — both publishing only `tasks_changed`, never a Finance name. A new
source-inspection test (`test_only_the_known_legacy_participant_files_construct_approval_post_
commit_event`) recomputes this set from `*_apply_participant.py` source on every run rather than
asserting a fixed list, so a future capability's own modernization phase deleting its site needs no
edits here. A companion test proves neither remaining legacy site ever names a Finance-owned legacy
signal. A third, parametrized test positively characterizes all 7 already-modernized approval
capabilities (Baseline, Cost Entry, Budget, Billing Preparation, Forecast, and — for the two
Inventory/Procurement families, whose participant files delegate to an already-public service
method — Purchase Requisition/Purchase Order's own decide-path source files) as `domain_events`-only,
zero `ApprovalPostCommitEvent`.

**Approval test baseline is now trustworthy: `test_approval_events.py` is fully green (36/36)** —
any future failure in this file represents a real production mismatch, not historical count drift.
This matters directly for the next modernization track: PM's own remaining `ApprovalPostCommitEvent`
sites (Task family, and Financial Change's schedule-impact branch) will be removed capability-by-
capability, and this file's new characterization tests will track that shrinkage automatically
rather than needing hand-edited counts each time.

### P40A — Project Management Remaining Legacy Signal Re-Rank (AUDIT + SEQUENCING ONLY)

Re-audited all six remaining PM legacy Signals from current source (not carried forward from P17/
P34A, which predate every Finance/Inventory phase and are demonstrably stale in places — see the
Project and Task corrections below). Six parallel read-only research passes, one per capability,
each independently re-deriving producers/consumers/facts/transaction readiness/concurrency/audit
from source.

**Producer/consumer/transaction matrix (concise):**

| Capability | Producers | Consumer files | Transaction owner | Audit | Concurrency |
|---|---|---|---|---|---|
| Timesheet (`timesheet_periods_changed`) | 1 site (1 private helper, 6 callers) | 5 | Raw Session, no UoW | ATOMIC | `version` on both `TimesheetPeriod`/`TimeEntry`, real CAS |
| Register (`register_changed`) | 3 sites, 1 file | 3 | Raw Session, no UoW | ACTIVITY-ONLY, non-atomic (2-commit split) | `version` on update only; delete unguarded |
| Portfolio (`portfolio_changed`) | 8 sites, 4 files (4 sub-aggregates) | 3 | Raw Session, no UoW; 1 nested mid-op commit hazard | NONE (3 of 4 sub-aggregates), ACTIVITY-ONLY+non-atomic (dependencies) | `version` on Intake only; Scenario/Template/Dependency unguarded |
| Project (`project_changed`) | 7 sites + 1 confirmed live gap (`set_status` never emits) | 12 (10 PM + 2 platform) | Raw Session, no UoW | NONE on Project itself (only its embedded FinancialProfile) | Real CAS via repo (`update_with_version_check`); `delete_project` unguarded |
| Collaboration (`collaboration_changed`) | 8 sites (6 durable comment ops + 2 presence, same Signal) | 3 | Raw Session, no UoW; already rollback-hardened (Phase 0A.3) | ATOMIC (durable ops) | `version` on `TaskComment`; none on `TaskPresence` (correctly, it's ephemeral) |
| Task (`tasks_changed`) | 22 direct + 6 `ApprovalPostCommitEvent` = 28 sites, 2 module boundaries | 10 (8 blind full-refresh) | Raw Session, no UoW anywhere | NONE anywhere in Task's own module | `version` on 3 of 3 aggregates but inconsistently checked; `move_task` blind-overwrites siblings; several assignment ops have zero check |

**Distinct-fact decomposition (recomputed from source, not from field-groupings):**
- **Timesheet**: 1 fact family — `TimesheetPeriod` state transition (submit/approve/reject/lock/
  unlock/reopen-for-correction), either one `TimesheetPeriodTransitioned{change_type}` or 6 named
  classes. `TimeEntry` mutations are NOT part of this Signal (they emit `tasks_changed` only).
- **Register**: 3 facts — `RegisterEntryCreated`/`Updated`/`Deleted`. One aggregate (`RegisterEntry`
  with a `RISK|ISSUE|CHANGE` discriminator field), not several unrelated types — the module path
  name (`application/risk/`) is misleading, confirmed a single class.
- **Portfolio**: 8 facts across 4 independent sub-aggregates (no `Portfolio` entity exists at all —
  "Portfolio" is a pure organizational grouping): `PortfolioScoringTemplateCreated/Activated`,
  `PortfolioScenarioCreated/Updated`, `PortfolioIntakeItemCreated/Updated`,
  `PortfolioProjectDependencyCreated/Removed`.
- **Project**: 3 facts source-supported today — `ProjectCreated` (bundled with a same-transaction
  `ProjectFinancialProfileCreated`), `ProjectProfileUpdated` (name/code/dates/client/site/dept/
  manager — `update_project`'s own diff does not currently separate status from these), and a
  materially separate `ProjectStatusChanged` (only `set_status` triggers it — own permission check,
  own activity action, and the one with the live no-emit gap). `ProjectRemoved` (`delete_project`,
  cascades Task/Dependency/Assignment/TimeEntry deletes in the same transaction) is a 4th. No
  evidence for `ProjectOwnershipChanged`/`ProjectDatesChanged` as separate facts — both P34A
  candidates were disproven by reading `update_project`'s actual diff fields.
- **Collaboration**: 6 durable facts, all on `TaskComment` — `TaskCommentPosted/Edited/Deleted/
  ReactionAdded/ReactionRemoved`, plus a read-receipt fact (`mark_task_mentions_read`) whose
  DomainEvent-worthiness is a genuine open design question (inbox state vs. business fact). The 2
  presence producers (`touch_task_presence`/`clear_task_presence`) are NOT durable facts — see
  below.
- **Task**: 8 facts across 3 independently-versioned aggregates + one bulk operation —
  `TaskCreated/Updated`, `TaskMoved`, `TaskDeleted`, `TaskProgressChanged`,
  `TaskSchedulingConstraintChanged`, `SchedulingLevelingApplied` (project-wide, fingerprint-keyed,
  not per-entity), `TaskDependencyChanged{change_type}` (own aggregate), `TaskAssignmentChanged
  {change_type}` (own aggregate). The Financial-Change-driven schedule application reuses fact
  #1/#2's fields but is NOT a 9th Task-owned fact — see cross-capability edges below.

**Cross-capability graph (only real category-C persisted-mutation edges reported):**
- Timesheet → Finance: **C, already canonical on the Finance side.** Period approval enqueues an
  outbox event inside the same atomic commit; an async dispatcher (`ApprovedTimeFinancialDispatcher`,
  the identical `SqlAlchemyUnitOfWorkBase` shape Cost Entry/Commitment use) later creates/mutates
  `ProjectCostEntry`/`ApprovedTimeLaborPosting` in its own canonical transaction. Timesheet's own
  modernization does not need to touch or re-solve this boundary.
- Register → Project: A only (existence-check read, never a write).
- Portfolio → Project: A only (all 4 sub-aggregates store project ids as plain references; the
  dependency repo's own "scope" check is read-only). Project → Portfolio: **zero coupling found** —
  no Project code references "portfolio" at all. This is a clean, one-directional, read-only edge in
  both audited directions — no Project/Portfolio sequencing constraint exists.
- Project → its own sub-capabilities: **C** — `create_project` creates a `ProjectFinancialProfile`
  in the same transaction; `delete_project` cascades hard-deletes across Task/Dependency/
  Assignment/TimeEntry in the same transaction. No evidence of Project mutating Budget or
  Portfolio-membership directly.
- Task ← Financial Change: **C, real, already-wired.** `FinancialChangeService._apply_schedule_
  changes` calls `TaskService._apply_approved_schedule_changes`, which writes `Task.start_date`/
  `end_date`/`duration_days` directly, inside Financial Change's own transaction. The only producer
  for this edge today is `financial_change_apply_participant.py`'s `ApprovalPostCommitEvent(
  "tasks_changed", ...)` sole remaining site. Finance's own canonical facts (`FinancialChangeChanged`
  etc.) do not replace this Task-owned fact — the Task side still needs its own typed event, and
  that requires touching Financial Change's participant, not just Task's own module.
- Task ← Timesheets (Platform): **C, real, unguarded.** `TaskTimeEntryMixin`/`timesheet_support.py`
  write `TaskAssignment.hours_logged` directly (same `AssignmentRepository` instance shared with
  TaskService) with **no version check** — a genuine, currently-live blind-overwrite risk against
  Task's own version-checked assignment-hours mutations.

**Collaboration transport finding (the key P40A discovery for this capability).** Presence
(`touch_task_presence`/`clear_task_presence`) is not a separate mechanism — it fires the exact same
`domain_events.collaboration_changed` Signal as durable comment facts, driven by a 30-second
`runtimeHeartbeat` QTimer while any task is open. All 3 UI consumers do a blind full-workspace
rebuild on every emission, payload-blind — meaning idle presence keepalive traffic currently costs
the same UI-wide refresh as an actual comment post, continuously, for as long as a task view stays
open. `DomainEvent`/`ViewInvalidationChannel` are built for durable, versioned, auditable facts;
presence has none of those properties and cannot become one without violating that model. No
ephemeral-presence transport exists anywhere else in the codebase to reuse — one must be designed.
**This makes Collaboration the one PM capability that genuinely needs a dedicated audit/transport-
split phase before implementation**, not because its own facts are unclear (they're the clearest of
any capability audited — 6 operations, 1 aggregate) but because the ephemeral half requires a design
decision this document's own architecture (typed DomainEvents = durable facts only) does not yet
have an answer for.

**Task strategic-value finding.** Task's own modernization phase would eliminate 5 of the current 6
production `ApprovalPostCommitEvent` sites (all of `task_apply_participant.py`), but **not** the 6th
(`financial_change_apply_participant.py`'s schedule-impact branch) — that site is owned by Financial
Change's own participant, not Task's module, and requires an explicit, separate (small) touch-up
regardless of how thoroughly Task's own capability is modernized. No other audited PM capability
(Timesheet/Register/Portfolio/Project/Collaboration) has any `ApprovalPostCommitEvent`/`_emit_signal_
safely` integration at all — Task is the *only* lever on the shared legacy-approval-infrastructure
count.

**Scorecard.**

| | Timesheet | Register | Portfolio | Project | Collaboration | Task |
|---|---|---|---|---|---|---|
| Distinct-fact complexity | LOW | LOW | MEDIUM (4 sub-aggregates) | MEDIUM | LOW (durable) / N/A (ephemeral) | HIGH (3 aggregates + bulk op) |
| Transaction readiness | HIGH (LOW effort) | HIGH (LOW effort) | MEDIUM (nested-commit hazard) | MEDIUM | HIGH for durable portion | LOW (HIGH effort, no UoW exists, 3 aggregates) |
| Audit readiness | READY (already atomic) | PARTIAL (2-commit split) | BLOCKED (3 of 4 sub-aggregates: none) | BLOCKED (none on Project itself) | READY (already atomic+rollback-hardened) | BLOCKED (none anywhere) |
| Concurrency safety | SAFE | PARTIAL (delete unguarded) | PARTIAL (1 of 4 sub-aggregates guarded) | PARTIAL (delete unguarded) | SAFE (durable); N/A (ephemeral, correctly unguarded) | PARTIAL (inconsistent; real blind-overwrite risk in `move_task` and cross-capability Timesheets edge) |
| Cross-capability coupling | LOW (1 edge, already canonical) | NONE | LOW (1 edge, reference-only both directions) | LOW (2 edges, both self-contained) | NONE (durable) | HIGH (2 real edges, one requires touching another module) |
| Consumer fan-out | MEDIUM (5) | LOW (3) | LOW (3) | HIGH (12) | LOW (3, but high-frequency) | HIGH (10, 8 blind) |
| UI precision needed | LOW (ResourceScope, project-scoped) | LOW (ResourceScope, project-scoped) | LOW (likely OrganizationScope — Portfolio artifacts aren't per-project) | MEDIUM (12 destinations to re-map, 2 of them incidental/platform-external) | MEDIUM (durable: ResourceScope/task; ephemeral: needs an entirely new non-DomainEvent mechanism) | HIGH (10 destinations, mostly blind, need real per-fact mapping) |
| Correctness/audit debt closed | LOW (little to close) | MEDIUM (fixes real 2-commit gap) | MEDIUM-HIGH (fixes real audit gaps + nested-commit hazard + TOCTOU race) | MEDIUM (fixes `set_status` no-emit gap + adds missing audit) | LOW for durable (already hardened) | HIGH (fixes multiple real blind-overwrite risks) but requires building new infra to do it |
| Test readiness | Not separately re-verified this phase (existing PM test suites presumed present; no gap found) | Same | Same | Same | Same (Phase 0A.3 rollback-hardening tests already exist) | Same |
| One-phase deletion confidence | HIGH | HIGH | HIGH | MEDIUM | LOW (whole-signal); HIGH (durable-only, post-split) | LOW (MEDIUM if Financial-Change touch-up is explicitly included) |
| Strategic cleanup value | NONE (no approval-bridge involvement) | NONE | NONE | NONE | NONE | HIGH (only lever on `ApprovalPostCommitEvent`/`_emit_signal_safely`) |

**Ranking (priority order: 1-deletable-in-one-phase, 2-semantic-clarity, 3-transaction-readiness,
4-cross-capability-canonical, 5-consumer-precision, 6-correctness-debt-closed, 7-test-readiness,
8-removes-shared-legacy-infra, 9-smaller-surface-wins-ties).** Timesheet, Register, and Portfolio
all score HIGH on priority 1 — Timesheet and Register additionally tie on priority-3 (LOW effort,
vs. Portfolio's MEDIUM effort from its nested-commit hazard and 4-sub-aggregate surface). Between
Timesheet and Register: Timesheet has the single smallest producer surface (1 call site) of any PM
capability audited (priority 9), while Register closes more real correctness debt (priority 6, its
2-commit audit split). Given priorities 1-5 are an exact tie between them, Timesheet is placed first
purely on surface-size (priority 9 only breaks a tie that persists through priority 6-8 as well,
since neither touches the approval bridge). Project (MEDIUM confidence, a confirmed live bug, and
the widest "normal" consumer fan-out at 12) ranks 4th — its facts and edges are now fully
characterized by this audit, so no separate audit-first phase is needed despite the wider surface.
Collaboration ranks 5th, needing its own short audit/transport-split phase before implementation (not
because of unclear facts, but an unresolved ephemeral-transport design question this document's own
model doesn't yet answer). Task ranks last on every ease-based priority (1-5) despite scoring highest
on priority 8 (strategic legacy-infrastructure value) — priorities 1-5 are weighted above priority 8
by design, and Task loses on all five.

**Direct-implementation readiness.** Timesheet, Register, Portfolio, and Project: **DIRECT FULL
MODERNIZATION** — each capability's facts, transaction shape, and cross-capability edges are now
fully characterized by this audit; no further discovery work is needed before implementation.
Collaboration: **CAPABILITY-SPECIFIC AUDIT FIRST** (a short transport-split design phase — decide and
build the ephemeral-presence mechanism, cut presence over to it, leave `collaboration_changed`
comment-only — before a normal modernization phase converts the now-cleanly-durable comment
operations). Task: **CAPABILITY-SPECIFIC AUDIT FIRST** — not because its facts are unclear (this
audit already enumerated all 8), but because its scale (28 producer sites across 2 module
boundaries, 3 independently-versioned aggregates, a new UoW to build from scratch, and mandatory
coordination with Financial Change's own participant) warrants a dedicated implementation-planning
pass, the same way Billing Preparation's 2-aggregate, 13-operation surface warranted P38A before
P39 — Task's surface is larger still.

**Recommended next three, in order:**
1. **Timesheet** — smallest producer surface of any remaining PM capability (1 call site), already-
   atomic audit, already-correct concurrency, zero approval-subsystem entanglement, Finance boundary
   already fully canonical and async-decoupled. DIRECT FULL MODERNIZATION.
2. **Register** — single cohesive aggregate, 3 producers in one file, 3 coarse consumers, zero
   cross-capability mutation; closes a real audit-atomicity gap. DIRECT FULL MODERNIZATION.
3. **Portfolio** — 4 independent sub-aggregates but each individually simple; zero Project coupling
   in either direction (no Project/Portfolio sequencing constraint); closes real audit gaps (3 of 4
   sub-aggregates currently have none) and a nested-commit hazard. DIRECT FULL MODERNIZATION.

**Tentative full PM sequence** (first three are the recommendation above; the rest are *tentative*,
subject to re-ranking after each phase per this document's own standing caution):
1. Timesheet
2. Register
3. Portfolio
4. Project *(tentative)*
5. Collaboration — audit/transport-split phase, then implementation *(tentative)*
6. Task — dedicated audit-first phase, then implementation; remains last *(tentative)*

**Should Task remain last: YES.** Both factors were weighed explicitly, not just complexity: Task
has the highest semantic complexity (3 independently-versioned aggregates + a bulk fingerprint
operation), the highest transaction-convergence effort (no UoW exists at all, must be built from
scratch, unlike every Finance phase which extended an existing one), the widest blind-refresh
consumer fan-out (10, 8 of them untargeted), and a mandatory cross-module coordination point
(Financial Change's participant) that no other PM capability has. Its strategic value (the only
capability that can shrink the shared `ApprovalPostCommitEvent` count) is real but does not
outweigh five ease-based priorities it loses on. Modernizing Timesheet/Register/Portfolio/Project/
Collaboration first will shrink Task's own eventual blast radius indirectly: several of Task's own
10 consumer files (`dashboard_refresh_mixin.py`, `control_workspace_controller.py`, `portfolio/
domain_event_binder.py`, `collaboration/domain_event_binder.py`, `timesheets/domain_event_binder.py`)
currently blanket-refresh on *multiple* legacy signals including `tasks_changed` — once those other
signals are retired and those binders are rewired to typed `ViewInvalidationHint`s for their *own*
capability, Task's own eventual cutover only has to reason about what's left in each binder, not the
current tangle of five-or-more legacy signals sharing one blanket-refresh call.

**Legacy Signal countdown.** Current: 7 (Finance 0, PM 6, Auth 1). If Timesheet → Register →
Portfolio → Project → Collaboration → Task retire one-by-one as tentatively sequenced: after PM, 1
(Auth only). Then Auth (P26A, still deferred): 0. Not hardcoded as a roadmap guarantee — current
source remains authoritative at each future phase's own start, per this document's repeated
caution.

**Approval-infrastructure projection.** Current production `ApprovalPostCommitEvent` sites: exactly
2 files (`financial_change_apply_participant.py`'s schedule-impact branch, `task_apply_participant.py`'s
5 decisions), all publishing `tasks_changed` only — reconfirmed unchanged from P39-CLEANUP (this
audit touched no production code). Timesheet/Register/Portfolio/Project/Collaboration modernization
will not reduce this count (none of them have any approval-subsystem integration). Only Task's own
phase reduces it, and only to 1 (not 0) unless that phase's scope explicitly includes the small
Financial-Change-side touch-up — recommended to fold that touch-up into Task's phase so
`ApprovalPostCommitEvent`/`ApprovalService._emit_signal_safely` become fully production-dead at the
end of PM modernization, with no compatibility shell left behind.

**Auth remains AUDITED / DEFERRED** — not re-audited this phase, per the brief's own explicit
instruction; P26A remains authoritative. Auth becomes the final legacy capability once PM reaches
zero.

### P40B — Project Management Timesheet Full Modernization

DIRECT FULL MODERNIZATION, per P40A's selection. Reconfirmed the exact current surface before
implementing (source wins over the brief's own P40A-carried-forward numbers, unchanged here):
`timesheet_periods_changed` had exactly 1 producer site — `TimesheetPeriodsMixin._emit_timesheet_
period_events` (`timesheet_periods.py`), called only from `_persist_timesheet_transition`, itself
called by all 6 period-transition commands (`submit`/`approve`/`reject`/`lock`/`unlock`/`reopen_
for_correction`) — and 5 consumer files (Timesheets workspace, Resource-scoped personal Timesheets
controller, Task workspace, Resource inspector's assignments tab, Collaboration workspace).
`TimeEntry` add/update/delete were confirmed NOT part of this signal (they already published
`tasks_changed` only) and are untouched — this phase's scope is the `TimesheetPeriod` aggregate
alone.

**Aggregate boundary confirmed**: `TimesheetPeriod` (own identity, `resource_id`, `organization_id`,
`status`, `version`) is the sole root in scope; `TimeEntry` is a sibling aggregate under the same
`TimeService`, not a child of `TimesheetPeriod`, and was already excluded per the point above.
Concurrency was already real CAS via a `WHERE status = expected_status AND version = expected_
version` conditional UPDATE (`SqlAlchemyTimesheetPeriodRepository.transition`) — preserved
unchanged; this phase did not touch it.

**Event vocabulary**: one shared-family event, `TimesheetPeriodStatusChanged(change_type:
TimesheetPeriodStatusChangeType)` — `SUBMITTED`/`APPROVED`/`REJECTED`/`LOCKED`/`UNLOCKED`/
`REOPENED_FOR_CORRECTION` — mirroring `BudgetStatusChanged`'s precedent, not six near-identical
classes or one generic `TimesheetChanged`. Payload: `tenant_id`, `organization_id` (sourced from
`_tenant_context_service.require_active_scope_ids(...)`, the same source `_enqueue_approved_time_
events` already used — not `period.organization_id`, which the fixture data leaves unset), `period_
id`, `resource_id`, `change_type`, `project_ids: tuple[str, ...]` (every distinct project referenced
by the period's own entries at transition time), `occurred_at`. No ORM, Session, UI destination, or
full-DTO snapshot in the payload; no `schema_version` (matches every prior phase's convention).

**Transaction convergence — adapter, not a new named-repository UoW.** `TimeService` (Platform-
owned, `src/core/platform/application/time_management/time/`, shared by every PM Timesheet
workflow via `TimesheetService(GuardMixin, TimeService)`) already held one long-lived, request-
scoped `Session` directly, injected once at composition (`project_registry.py`), shared with every
other PM service in that request — not the per-command-fresh-session shape Resource/Employee/
Budget's own UoWs use. Rather than build a first-ever `TimesheetUnitOfWork` with its own fresh
session (which would have split the period-transition write from the Approved Time outbox enqueue
that must stay in the SAME transaction for atomicity), `_persist_timesheet_transition` wraps its
existing `self._session` directly with the generic `SqlAlchemyUnitOfWorkBase` — exactly the shape
`ApprovedTimeFinancialDispatcher` (this same subsystem's own Approved Time → Cost Entry dispatcher)
already uses in production against this identical shared session. `Session.close()` (called inside
`UnitOfWork.commit()`) only ends the current transaction and expires identity-mapped objects — it
does not invalidate the Python `Session` object for further reuse by other services later in the
same request — so this is safe and precedented, not a novel risk. `TimeService` gained two new
optional constructor params, `transactional_dispatcher`/`post_commit_bus`, wired from `project_
registry.py`'s existing `platform_services.platform_transactional_dispatcher`/`platform_post_
commit_bus`. The manual `try/except: session.rollback()` block is gone — `SqlAlchemyUnitOfWorkBase`'s
own context-manager `__exit__` now owns rollback-on-exception, matching every other converged
capability's shape.

**Enterprise audit preserved unchanged** (still `record_audit_entry(self, ...)`, since `self._
enterprise_audit_service` was already correctly scoped to the same shared session — no divergence
introduced). **Approved Time outbox enqueue preserved unchanged and still atomic** with the period
transition (same session, same UoW, same commit).

**ViewInvalidation: one event, three targets, source-preserving fan-out.** The legacy signal
reached exactly three consumer families, uniformly, with zero scoping. `TIMESHEET_WORKSPACE_SCOPE_
CODE` (`OrganizationScope` — any reviewer or team-scoped viewer needs every resource's periods, not
just one) serves both Timesheet workspaces (personal + review queue). `TIMESHEET_RESOURCE_SCOPE_
CODE` (`ResourceScope`, entity=resource) serves the Resource inspector's assignments tab, filtered
to the selected resource. `TIMESHEET_PROJECT_SCOPE_CODE` (`ResourceScope`, entity=project, one hint
per `event.project_ids` entry) serves the Task workspace, filtered to the selected project — this is
a genuine precision gain over the legacy signal's total lack of scoping (Task workspace no longer
refreshes for periods with zero entries in its own project). **Collaboration's identical
subscription was investigated and found INCIDENTAL**: `selectedPeriodKey` there is an unrelated
comment-date filter (grouping comments by "today"/"this week"), not timesheet-period data of any
kind — dropped with no replacement, per the standing consumer-precision discipline (P40A/P39's own
"remove incidental subscriptions" rule).

**Consumer cutover**: `TimesheetViewInvalidationAdapter` (new, `src/ui_qml/modules/project_
management/adapters/timesheets/`) wired into `context.py` at all four call sites (`_get_timesheets_
workspace`, `_get_review_queue_workspace`, `_get_resources_workspace`, `_get_tasks_workspace`).
Both Timesheet workspaces connect `timesheetWorkspaceStale` straight to their existing `_request_
domain_refresh()` (unchanged blanket-refresh behavior, now organization-scoped instead of global).
Resources gained `onTimesheetResourceStale` (delegates to a new `on_timesheet_resource_stale`
binder helper, filtered by `controller._selected_resource_id`). Tasks gained `onTimesheetProjectStale`
(delegates to a new `on_timesheet_project_stale` binder helper, filtered by `controller._selected_
project_id`). All five legacy `domain_events.timesheet_periods_changed` subscriptions removed; the
four still-relevant binder files keep their other, unrelated legacy-signal subscriptions untouched.

**Finance boundary unaffected, confirmed by re-reading source, not by memory of P40A's own
characterization.** Approved Time → Cost Entry remains category D (async, integration-outbox-
driven): `approve_timesheet_period` still enqueues `ApprovedTimeEntryEventPayload` rows in the same
transaction as the status change (unchanged code, `timesheet_financial_events.py`); `ApprovedTime
FinancialDispatcher` still consumes them under its own separate `SqlAlchemyUnitOfWorkBase`
transaction, producing Cost Entry's own already-canonical typed events. No `cost_entries_changed`
reintroduced; no cross-module DomainEvent standing in for Cost Entry's own fact. Proved end to end,
unmodified, by the pre-existing `test_approved_time_labor_integration.py` (11/11 passing against
the now-modernized transition path — submit → approve → lock → unlock → reopen-for-correction →
resubmit → approve, with real Cost Entry posting/reversal/correction consequences).

**Regression battery**: `test_time_domain_validation.py` (3, extended with real `TransactionalEvent
Dispatcher`/`PostCommitEventPublisher`/`TenantContextService` fakes and new event-content
assertions), `test_p8_platform_event_architecture_canonicalization.py` (31, `timesheet_periods_
changed` added to the deleted-name zero-reference guard), `test_qml_domain_event_bridges_pm.py` (5,
one test's dead emit line removed, one retired with a pointer comment mirroring the Resources/
Settings retirement precedent, one's assertion corrected for the dropped Collaboration
subscription), `test_approved_time_labor_integration.py` (11), `test_r5h_time_entry_concurrency_
atomicity.py` + `test_r5f1_resource_timesheets.py` (10), `test_shared_collaboration_import_and_
timesheets.py` + `test_workspace_database_pagination.py` + `test_assignment_time_task_detail_r43.py`
+ `test_approved_time_work_allocation_n_plus_one.py` (44), new `test_p40b_timesheet_period_full_
modernization.py` (14: ViewInvalidation handler mapping/dedupe/no-project-ids/multi-project unit
tests, real submit/approve/reject producer-path tests, a stale-version rollback-produces-zero-hints
test, and a characterization test proving the remaining `ApprovalPostCommitEvent` sites are
unchanged from P39-CLEANUP). All green. One pre-existing, unrelated failure confirmed via `git
stash` (`test_repository_tenant_hardening_time_governance.py::test_time_and_governance_
repositories_scope_cross_organization_data` calls `TimeEntryRepository.delete()` without the
`expected_version` it has always required — a `TimeEntry`-side test bug, out of this phase's
`TimesheetPeriod`-only scope, present identically before this phase started).

**Legacy Signal count: 6 (7 minus one deletion) — first PM capability to reach zero, first
retirement of any kind since Finance completed at P39.** `timesheet_periods_changed` rejoins the
historical P8 frozen allowlist's deleted-name set; the frozen baseline itself is unchanged (P40B is
ordinary further retirement of a pre-freeze, frozen-allowlisted signal, not a violation fix).
Remaining PM legacy signals: `project_changed`, `tasks_changed`, `register_changed`, `collaboration_
changed`, `portfolio_changed`. **Register and Portfolio remain next, unchanged from P40A's
sequence** — nothing discovered this phase touches either capability's own facts, transaction
shape, or cross-capability edges.

### P41 — Project Management Register Full Modernization

DIRECT FULL MODERNIZATION, per P40A's selection. Reconfirmed the exact current surface before
implementing: `register_changed` had exactly 3 producer sites, all in `register_lifecycle.py`
(`create_entry`/`update_entry`/`delete_entry`), and 3 consumer files (Register's own workspace,
PM Dashboard's register widget, Platform's Control workspace). `RegisterEntry` is confirmed one
cohesive aggregate with a `RISK`/`ISSUE`/`CHANGE` discriminator field (`entry_type`), not three
separate aggregates — matching P40A's own finding exactly, so one shared-family DomainEvent, not
three per-type classes.

**The two-commit bug, reconfirmed and fixed.** Every mutation committed the business write FIRST
(`self._session.commit()`), THEN called `record_activity(self, ...)` with its default `commit=True`
— a SECOND, independent commit. Worse: Register had **no enterprise audit at all** before this
phase — only the lighter-weight Activity feed, `ACTIVITY-ONLY` exactly as P40A classified it. Both
gaps are now closed in one converged transaction: business mutation → enterprise audit (new) →
Activity feed (preserved, now `commit=False`, staged on the same UoW) → `uow.record_event(...)` →
one `uow.commit()`.

**Canonical UoW: a new, narrow `RegisterUnitOfWork`.** No existing PM UoW already owned the
Register repository (unlike Timesheet, where reusing the shared session was possible because the
only other participant, the Approved Time outbox, already lived on that same session). Register's
`RegisterService` shared the same long-lived PM session as everything else with no compensating
constraint forcing it to stay there, so the architecturally cleaner and more consistent choice —
matching Resource's and Employee's own precedent exactly — was a first-class, single-repo
`RegisterUnitOfWork` (`entries: RegisterEntryRepository`, `_enterprise_audit_service`,
`_activity_service`), built via `SqlAlchemyRegisterUnitOfWorkFactory` on its own fresh
`sessionmaker`-backed session per command, RLS-configured via `configure_session_rls_context`. Named
accessor only — no generic repository bag, no `repository_for`/`resolve`/`container.get`.
`RegisterService` gained `_uow_factory`/`_require_uow_factory`/`_new_context`, mirroring
`ResourceService`'s own base-class shape exactly. `_resolve_entry_code`'s uniqueness check now
reads through the UoW-scoped repository when one is supplied (not the outer, differently-scoped
`_register_repo`), closing the same race window Resource's own code-uniqueness check was already
built to avoid.

**Event vocabulary**: one shared-family event, `RegisterEntryChanged(change_type:
RegisterEntryChangeType)` — `CREATED`/`UPDATED`/`REMOVED` — mirroring `BudgetStatusChanged`'s/
`TimesheetPeriodStatusChanged`'s precedent. Payload: `tenant_id`/`organization_id` (from
`_tenant_context_service`, since `RegisterEntry` itself carries no tenant/org fields),
`project_id`, `register_entry_id`, `entry_type`, `change_type`, `occurred_at`. No ORM/Session/UI
destinations/DTOs/schema_version.

**ViewInvalidation: one event, two targets, source-preserving.** The legacy signal reached two
consumer families uniformly: Register's own workspace (`REGISTER_WORKSPACE_SCOPE_CODE`,
`OrganizationScope` — its project filter defaults to "all", so it needs org-wide reactivity, not
just the mutated project) and Dashboard's register widget (`REGISTER_PROJECT_SCOPE_CODE`,
`ResourceScope`, project-scoped — the dashboard is always exactly one project). **Control
workspace's third subscription was investigated and could NOT be cut over**: it shows a generic
approval-queue/audit-feed, not register-specific data, and — the deciding factor — Control lives
under `ui_qml/platform/`, and `test_platform_does_not_import_business_modules.py` forbids
Platform-layer QML from importing a `project_management`-owned module (which a typed
`RegisterViewInvalidationAdapter` subscription would require). Dropped with no replacement; the two
now-affected characterization tests (`test_control_workspace_still_reacts_to_its_remaining_real_
signals`, `test_platform_control_workspace_refreshes_on_control_events`) were repointed to Control's
other remaining legacy signal (`tasks_changed`) rather than deleted, since Control itself still has
real un-migrated subscriptions to prove.

**Regression battery**: new `test_p41_register_full_modernization.py` (14: ViewInvalidation
handler mapping/dedupe, real create/update/delete producer-path tests, a stale-version zero-write
test, a duplicate-code-rejection test, the mandatory audit-failure-rolls-back-the-mutation
regression proving the two-commit bug is fixed by asserting `list_entries` returns empty — not a
commit-count assertion, a transactional-handler-failure test using the real shared
`platform_transactional_dispatcher`, a cross-project-ownership rejection test, and the standing
approval-bridge-unaffected characterization), `test_register_entry_domain_validation.py` (5, its
fake-service harness extended with a fake UoW factory/tenant-context-service — the same fix shape
`test_time_domain_validation.py` needed at P40B), `test_project_management_desktop_api_register.py`
+ `test_qml_project_management_presenters_register.py` (3), `test_p8_platform_event_architecture_
canonicalization.py` (31, `register_changed` added to the deleted-name zero-reference guard),
`test_p7_legacy_bridge_removal.py` + `test_p7b_dead_signal_cleanup.py` + `test_qml_domain_event_
bridges_pm.py` (three pre-existing tests repointed from the now-deleted `register_changed` to a
still-live signal each binder already subscribes to, per the established P33-CLEANUP/P36/P37/P38B/
P39 swap precedent), P40B's own Timesheet regressions (25, reconfirmed unaffected). All green.

**Legacy Signal count: 5 (6 minus one deletion) — second PM capability to reach zero.**
`register_changed` rejoins the historical P8 frozen allowlist's deleted-name set; the frozen
baseline itself is unchanged. Remaining PM legacy signals: `project_changed`, `tasks_changed`,
`collaboration_changed`, `portfolio_changed`. **Portfolio remains next, unchanged from P40A's
sequence** — nothing discovered this phase touches Portfolio's own facts, transaction shape, or
cross-capability edges.

**P41-FIX — Control workspace's Register reaction restored without a Platform→PM dependency.**
Re-traced Control's source and confirmed the dependency is GENUINE, not incidental: its "Recent
Audit Feed" calls `audit_api.list_recent(...)` with no module filter — a generic, cross-entity-
type projection — and P41 gave Register real enterprise audit for the first time, so Register
rows now genuinely belong in that feed. Also found the specific test cited as the blocking guard,
`test_platform_does_not_import_business_modules.py`, only scans `src/core/platform/` (the Python
core layer) — it never covered `src/ui_qml/platform/` (the QML controller layer) at all, so the
original P41 removal wasn't actually forced by a green test going red; it was a conservative
default. The underlying architectural principle (Platform owns no business-module implementation)
still fully applies at the QML layer even without an automated guard enforcing it there, so the
fix was built to the same standard anyway, not to the letter of the (inapplicable) test.

**Cross-layer contract**: `ProjectManagementWorkspaceCatalog` gained a public `registerWorkspaceStale`
Signal, fed by a new, eagerly-constructed `RegisterViewInvalidationAdapter` instance (independent of
the two lazy ones already wired to the Register workspace and Dashboard, since Control's reaction
must not depend on the Register workspace UI ever having been opened) forwarding
`REGISTER_WORKSPACE_SCOPE_CODE` (org-wide) hints. `PlatformControlWorkspaceController` gained one
generic, Register-ignorant slot, `onExternalViewStale`, calling its own existing
`_request_domain_refresh()`. The composition root, `shell/app.py::main()` — already the place
`tenantSwitched`/`organizationSwitched`/`organizationsChanged` cross-catalog wiring lives — connects
`pm_workspace_catalog.registerWorkspaceStale` to `platform_workspace_catalog.controlWorkspace.
onExternalViewStale`, the exact same dependency-inversion shape already established there for
Platform→PM wiring, now used in the PM→Platform direction for the first time. Neither catalog
imports the other's implementation module.

**Regression**: new `test_p41_fix_control_workspace_register_reaction.py` (7 tests — Control's
genuine dependency proved from source; zero PM import from the Platform controller; zero raw
`RegisterEntryChanged`/`register_changed` reference; real end-to-end create/update/delete →
Control refresh; a Budget-category mutation proven NOT to fire the new signal, isolating it from
Control's own separate, legitimate `project_changed`/`tasks_changed` legacy subscriptions). The
three P41-repointed characterization tests were re-examined against their own original purpose
(each was already proving "Control/Register-workspace-binder still reacts to a *surviving* legacy
signal," never specifically "reacts to Register") and found not to be masking anything; their
docstrings now cross-reference the new dedicated test file. All previously-green suites remain
green.

### P42 — Project Management Portfolio Full Modernization

DIRECT FULL MODERNIZATION, per P40A's selection. Reconfirmed the exact current surface: `portfolio_
changed` had exactly 8 producer sites (`create_intake_item`/`update_intake_item`, `create_scenario`/
`update_scenario`, `create_scoring_template`/`activate_scoring_template`, `create_project_dependency`/
`remove_project_dependency`) and 3 consumer files. Confirmed the four sub-aggregate families P40A
found — **Intake** (`PortfolioIntakeItem`, versioned, real CAS), **Scenario** (`PortfolioScenario`,
unversioned, was blind-overwrite), **ScoringTemplate** (`PortfolioScoringTemplate`, unversioned, was
blind-overwrite), **ProjectDependency** (`PortfolioProjectDependency`, immutable — no update command
exists) — each keeps its own DomainEvent vocabulary, never collapsed into one `PortfolioChanged`.

**The nested-commit hazard, reconfirmed and fixed.** `portfolio_support.py`'s `_ensure_scoring_
templates()` — a lazy-bootstrap helper called from BOTH Intake commands (`_resolve_scoring_
template`) and Template commands themselves — called `self._session.commit()` internally, twice,
as a side effect of what looked like a read. A command could bootstrap-create or reactivate a
scoring template (committed immediately, durably) and then fail its OWN actual operation (e.g. a
duplicate-name `ValidationError` raised right after) — the bootstrap write survived a failure the
user's real request never got past. Fixed by making every scoring-template helper (`_ensure_
scoring_templates`, `_active_scoring_template`, `_resolve_scoring_template`, `_deactivate_other_
templates`) transaction-neutral: they now take an explicit `templates_repo` (the caller's own
UoW-scoped repository) and an `events: list` accumulator they append genuine facts to, never
commit, never own a session.

**Canonical UoW: one `PortfolioUnitOfWork` owning all four named repositories** (`intake`,
`scenarios`, `scoring_templates`, `dependencies`), mirroring `DocumentUnitOfWork`'s established
"one capability, several sub-aggregate repos" shape — not a mega-UoW, since Portfolio genuinely is
one capability (one workspace, one set of tabs) even though most single commands only touch one
repository. `activate_scoring_template` is the one command that genuinely mutates two rows in the
same repository within one transaction (the newly-activated template and the previously-active
one) — now provably atomic: a forced failure on the second write rolls back the first too (proved
by a dedicated multi-row atomicity test, not merely asserted).

**Enterprise audit added where none existed.** Intake, Scenario, and ScoringTemplate had zero audit
of any kind before this phase (not even the lighter Activity feed); Dependency had Activity feed
only. All four now get real, atomic enterprise audit alongside their DomainEvent, matching
Register's own P41 precedent for a capability that had none.

**Event vocabulary**: `PortfolioIntakeItemChanged`/`PortfolioScenarioChanged`/`PortfolioProject
DependencyChanged` (each `change_type`-differentiated, mirroring the shared-family precedent) and
`PortfolioScoringTemplateChanged` (`CREATED`/`ACTIVATED`/`DEACTIVATED` — activation's own secondary
mutation gets its own fact, per the "do not hide a genuine second mutation behind one event" rule,
mirroring Budget's approve/supersede precedent).

**ViewInvalidation: one category, one target.** No `Portfolio` entity exists at all (P40A: pure
organizational grouping) — all four sub-aggregate fact families genuinely stale the one org-wide
Portfolio workspace uniformly, exactly like the legacy signal's own real consumer. `PORTFOLIO_
WORKSPACE_SCOPE_CODE` (`OrganizationScope`) is the only target; no per-screen targets were invented
without a source-confirmed distinct projection. **Two of the three legacy consumers were found
INCIDENTAL, not genuine, and dropped with no replacement** — PM Dashboard's own "portfolio" KPI
(`DashboardPortfolioMixin.get_portfolio_data`) is entirely derived from Project/Task/Resource/Cost
data, never reads any of the four real sub-aggregates; the Projects workspace displays no
Portfolio-derived data anywhere (confirmed by source inspection — no other file in that workspace's
controllers/presenters mentions "portfolio" at all). Both were carried-over fan-out from the
pre-modernization era, exactly what P40A's own §27 anticipated finding. Only Portfolio's own
workspace was a genuine consumer.

**Regression**: new `test_p42_portfolio_full_modernization.py` (10), rewritten `test_portfolio_
phase0a2_rollback_hardening.py` (33 — repository-class-level and `EnterpriseAuditService`-level
failure injection replacing the old `services["session"].commit()` patch, which no longer reaches
the new per-command UoW session; a dedicated multi-row atomicity test for `activate_scoring_
template`), `test_portfolio_domain_validation.py` (7, fake-service harness extended with a fake
UoW factory/tenant-scope, the same fix shape P41/P40B needed), `test_pm_r3_4_portfolio_ia_tabs.py`
(3 — caught and fixed a real bug: the two scoring-template QUERY methods still called the old
zero-arg helper signature; fixed via a new read-side `_scoring_templates_with_bootstrap()` that
only opens a UoW when the rare lazy-bootstrap write is actually needed, never for the common
already-bootstrapped read), the full remaining Portfolio-adjacent suite (40), `test_p8_platform_
event_architecture_canonicalization.py` (31, `portfolio_changed` added to the deleted-name guard),
`test_p7_legacy_bridge_removal.py`/`test_p7b_dead_signal_cleanup.py`/`test_qml_domain_event_
bridges_pm.py` (characterization tests repointed to Portfolio's remaining `project_changed`/
`tasks_changed` subscriptions, preserving each test's own original "still reacts to a surviving
signal" intent), P40B/P41/P41-FIX regressions (51, reconfirmed unaffected). All green.

**Legacy Signal count: 4 (5 minus one deletion) — third PM capability to reach zero, and the
first phase to also close out two carried-over incidental consumers in the same pass.**
`portfolio_changed` rejoins the historical P8 frozen allowlist's deleted-name set; the frozen
baseline itself is unchanged. Remaining PM legacy signals: `project_changed`, `tasks_changed`,
`collaboration_changed`. **Project remains next, unchanged from P40A's tentative sequence** —
nothing discovered this phase materially changes Project's own facts, transaction shape, or
cross-capability edges (Portfolio→Project remains reference-only in both directions, reconfirmed).

**P42-FIX — Scoring-template lazy bootstrap verified canonical; a real audit gap found and
closed.** Traced every caller of `_ensure_scoring_templates`/`_scoring_templates_with_bootstrap`:
2 QUERY callers (`list_scoring_templates`, `get_active_scoring_template`) and 4 COMMAND call
paths (all already inside their own `PortfolioUnitOfWork`). Classified the bootstrap default
template as **REAL DOMAIN MUTATION**, not technical seeding — it is the exact same
`PortfolioScoringTemplate` entity a user creates directly, shows up indistinguishable from a
user-created row in the Templates tab, and can later be activated/deactivated through the normal
commands.

**Real gap found: the bootstrap path recorded a typed `PortfolioScoringTemplateChanged` event but
never called enterprise audit.** `_ensure_scoring_templates`/`_deactivate_other_templates` mutated
rows and appended DomainEvents, but only the COMMAND methods' own top-level `record_audit_entry`
calls covered the row the user explicitly asked for — never the bootstrap default created as a
side effect (reachable from `create_intake_item` too, not just the two query methods). A dedicated
test (monkeypatching `EnterpriseAuditService.record` and asserting the whole bootstrap call raises)
caught this directly: it didn't raise, because audit was never invoked for that row. Fixed by
moving `record_audit_entry` calls inside the shared helpers themselves (`_ensure_scoring_templates`
for create/reactivate, `_deactivate_other_templates` for deactivate) so every caller — command or
query — gets complete, atomic audit coverage for every scoring-template row it touches, with zero
double-auditing (the helpers only ever touch rows distinct from whatever the command's own
top-level audit call already covers). Helper signatures changed from a bare `templates_repo`
parameter to the full `uow` (needed for `_enterprise_audit_service` access) — `activate_scoring_
template`'s one pre-UoW existence check no longer routes through `_resolve_scoring_template`
(which now requires a `uow`) and instead does a direct, simpler `_scoring_template_repo.get(...)`
+ `NotFoundError`, since that read-only check never needed bootstrap capability anyway.

**Write-on-read: RETAINED, deliberately, with justification recorded in the code itself.**
Eliminating it was investigated and rejected: Portfolio has no `Portfolio` entity and no "create
Portfolio" command to hook an explicit bootstrap into (P40A), and returning an unpersisted,
in-memory-only default from the query would mint a fresh `generate_id()` every call — a later
`activate_scoring_template(that_id)` or intake creation defaulting to it would 404, a worse
regression than today's behavior. The write only happens ONCE per organization (`_scoring_
templates_with_bootstrap`'s own `if templates and any(active): return templates` guard short-
circuits every call after the first to a plain read, proved by a dedicated repeated-read test).
Query methods are correspondingly **NOT fully mutation-free** — the rare first-open case remains
an exception, proved safe (atomic, fully audited/evented) rather than hidden.

**Concurrent first-bootstrap race: characterized, not fixed.** `PortfolioScoringTemplateORM` has
no unique constraint on `(organization_id, name)` or `(organization_id, is_active)` — only plain
indexes (confirmed by reading the ORM's own `__table_args__`). Two genuinely concurrent sessions
racing the empty-organization bootstrap can both create an active "Balanced PMO" default,
producing two active rows — reproduced directly with two real, independently-committing
`PortfolioUnitOfWork` instances in a test, not merely asserted. This is **pre-existing debt**, not
introduced by P42's UoW convergence (the same list-then-create-if-empty shape existed before,
guarded only by a raw self-commit) — left unfixed, matching the standing "characterize, don't
schema-migrate" precedent (PO-line receiving concurrency, Register delete, Project delete). Also
discovered and recorded precisely: activating one of the two duplicates is a true no-op (both are
already active, correct §20 no-op semantics) and does NOT self-heal the race by itself; creating
(or activating) any other template does, since `_deactivate_other_templates` deactivates every
currently-active row in one pass.

**Regression**: new `test_p42_fix_portfolio_scoring_template_bootstrap.py` (7 — existing-template
read is mutation-free; first bootstrap via each query method creates exactly one atomically-
audited default with exactly one ViewInvalidation target and is itself idempotent on a second
read; audit-failure and repository-failure bootstrap rollback leave zero partial state; the
concurrent-race characterization proving both the duplicate outcome and its true recovery path),
`test_portfolio_phase0a2_rollback_hardening.py`'s own `_template_case` fixture repointed to the
new `uow=` signature, full Portfolio regression suite (212 total across this run) reconfirmed
green.

**Legacy Signal count: unchanged at 4.** `portfolio_changed` remains deleted; no field-level
change in this phase. **Project remains next, unchanged.**

**P42-FIX2 — Concurrent first-bootstrap race closed with a real database constraint, not just
characterized.** P42-FIX had proven the race (two concurrent sessions, two active default rows,
no DB constraint preventing it) and left it as recorded debt. P42-FIX2 first proved "at most one
active `PortfolioScoringTemplate` per organization" is a genuine domain invariant, not a
convenience assumption: `_deactivate_other_templates`'s "deactivate every currently-active row"
loop only makes sense defending against duplicates; `get_active_scoring_template()`'s singular
return type assumes exactly one; and — the deepest evidence — `create_intake_item`/
`update_intake_item` derive an intake item's scoring WEIGHTS deterministically from "the" active
template, so two simultaneously-active rows would make a core prioritization calculation silently
arbitrary, not merely cosmetic.

**Enforcement: a real partial unique index, both dialects, both layers.** Added
`uq_portfolio_scoring_one_active_per_org` — `UNIQUE(organization_id) WHERE is_active` — to both
`PortfolioScoringTemplateORM` (`postgresql_where=`/`sqlite_where=`, mirroring the Budget module's
own proven `uq_pf_budgets_one_approved_per_project` shape) and a new Alembic migration
(`d8e1f4a7b2c3`, chained after `c3f6a1b8d9e0`). One deliberate deviation from the Budget
precedent: scoped by `organization_id` alone, not `tenant_id + organization_id` — `tenant_id` is
nullable on this table, and a composite unique index over a nullable column would not enforce
uniqueness across NULL-tenant rows (SQL's `NULL <> NULL`). The migration also deterministically
normalizes any pre-existing duplicate-active rows before creating the index (a raw-SQL
window-function update, keep the most-recently-updated active row per organization, tie-broken by
id — the same ordering the application's own reads already implicitly favor), so it cannot fail
outright on data that predates the invariant; proved by a dedicated migration test that seeds two
dirty active rows and asserts exactly the newer one survives.

**Idempotent bootstrap made concurrency-safe: the loser gets zero durable side effects, not a
crash.** `_scoring_templates_with_bootstrap()` now wraps its bootstrap `UnitOfWork` block in
`try/except IntegrityError`: on a lost race, the UoW's own `__exit__` has already rolled back and
closed the poisoned transaction, and the except branch performs one more plain read on the
existing (un-poisoned) repository, returning the winner's canonical, already-committed state —
zero new rows, zero audit, zero events, zero ViewInvalidation for the loser. Proved with a real
two-independent-`PortfolioUnitOfWork` test (both stage their own default before either commits;
the second commit raises `IntegrityError` for real, not simulated) and a second, deterministic
test that forces the exact catch-and-recover path via monkeypatched commit failure.

**Explicit commands map the same conflict to `ConcurrencyError`, never silently retry.**
`activate_scoring_template`, `create_scoring_template` (its `activate=True` path can also set
`is_active=True` directly), and `create_intake_item` (which resolves and can implicitly bootstrap
the active template inside its own transaction) each wrap their commit in
`try/except IntegrityError as exc: raise ConcurrencyError(..., code="PORTFOLIO_TEMPLATE_
ACTIVATION_CONFLICT") from exc` — the project's own established concurrency-exception convention,
not a raw SQLAlchemy leak, and not a retry loop. `create_scoring_template`'s duplicate-name check
was also simplified from a bootstrap-triggering `_ensure_scoring_templates(...)` call to a plain
`uow.scoring_templates.list()`, removing an unnecessary collision surface on a fresh organization.
`_resolve_scoring_template`/`_active_scoring_template` (in-transaction, bootstrap-capable) are
retained for `create_intake_item`'s use; a separate `_active_scoring_template_resolved()` (built
on the catch-and-recover `_scoring_templates_with_bootstrap()`) now backs the pure-read
`get_active_scoring_template()` query path — two call shapes for two different safety contracts,
not one over-generalized helper.

**Cross-organization independence preserved.** The constraint is scoped by `organization_id`, not
global — two different organizations can each have their own active default template
simultaneously, proved directly against two real organizations via `organization_service.
create_organization`/`enable_organization`, not a fake harness.

**Regression**: new/updated tests in `test_p42_fix_portfolio_scoring_template_bootstrap.py` (12 —
the P42-FIX "recorded debt" characterization test rewritten as an "invariant enforced" proof;
added: idempotent-bootstrap recovery, explicit `activate`/`create(activate=True)` conflict
mapping, cross-org independence, a raw-insert-bypassing-application-code architecture guarantee)
and new `test_p42_fix2_portfolio_scoring_template_migration.py` (2 — fresh-baseline index
presence/uniqueness/downgrade, dirty-data deterministic normalization), full Portfolio regression
suite (82 across this run, including `test_portfolio_phase0a2_rollback_hardening.py` and
`test_pm_r3_4_portfolio_ia_tabs.py`) plus Register/Timesheet/P7/P8/architecture-guard regressions
(63) reconfirmed green.

**Legacy Signal count: unchanged at 4.** No field-level change in this phase — this closes
concurrency debt recorded by P42-FIX, it does not touch the event/legacy-signal ledger. **Project
remains next, unchanged.**

**P43 — PM Project full modernization, and the P40A-discovered silent `set_status` notification
gap closed.** Reconfirmed the current surface from source, not P40A's approximate count: 7
non-test `project_changed` producer sites (3 real Project mutations in `lifecycle.py` —
`create_project`/`update_project`/`delete_project` — plus 4 `ProjectResource`-assignment sites in
`project_resource_commands.py`, a different aggregate that merely carries `project_id`), and
`set_status` confirmed as a real, committed Project mutation that emitted **zero**
`project_changed` at all — the exact live correctness gap P40A flagged. 11 real (non-test)
consumer subscription sites found, reclassified against current source: **10 genuine** (Projects
workspace = OWNER; Dashboard and Portfolio = REAL SUMMARY; Register, Resources, Tasks,
Collaboration, Financials, Scheduling, Platform Access = CROSS-CAPABILITY READ MODEL, each proved
by tracing an actual query/selector that reads `Project.name`/`status`/dates/code) and **1
INCIDENTAL** (Platform Control — its own `build_overview`/`build_approval_queue`/
`build_audit_feed` never dereference a single Project field, confirmed by source; removed with no
replacement).

**Aggregate structure, reconfirmed.** `Project` (`domain/projects/project.py`) — plain
`@validated_dataclass`, no `tenant_id` field (ORM-only), `organization_id`, `version` (real
optimistic-concurrency field), `status: ProjectStatus` (`PLANNED`/`ACTIVE`/`ON_HOLD`/`COMPLETED`,
no enum-level or service-level transition graph — any value to any value was, and remains, valid;
no invented `archive`/`reopen`/`cancel` transitions). No `Project.set_status()` domain method —
status mutation was, and remains, a plain service-layer field assignment (`project.status =
status`), now inside `ProjectUnitOfWork`. Confirmed Task/Resource/Budget/Portfolio/Register are
NOT Project-owned children (reference-only or read-model edges); the one genuine same-transaction
child is `ProjectFinancialProfile`, created atomically alongside every new Project.

**Event vocabulary — 4 classes, no generic `ProjectChanged`.** `ProjectCreated`,
`ProjectProfileUpdated`, `ProjectStatusChanged` (carries `status: ProjectStatus`), `ProjectRemoved`
(`application/projects/project_events.py`) — matching P40A's own audited decomposition exactly;
`ProjectOwnershipChanged`/`ProjectDatesChanged` reconfirmed NOT distinct (ownership/dates are
ordinary profile fields changed through the same cohesive `update_project` operation).
`update_project` additionally emits `ProjectStatusChanged` alongside `ProjectProfileUpdated` when
its own optional `status` argument actually changes the value — a genuine second fact, not hidden
behind one event (mirrors Budget's approve/supersede precedent). A same-transaction
`ProjectFinancialProfileCreated` was added to Finance's own `configuration_events.py` (alongside
its existing `Updated`/`Transitioned` siblings) and folded into Finance's existing
`build_financial_profile_view_invalidation_handler` — `create_project` was the one Project-lifecycle
side effect Finance's own event modernization had never covered, since it's not a standalone
Finance command.

**Canonical transaction ownership: new `ProjectUnitOfWork`.** No Project-specific or PM-wide UoW
existed before this phase (`create_project`/`update_project`/`set_status`/`delete_project` all ran
on a raw, shared `Session` with direct `self._session.commit()`/`.rollback()`). Added
`ProjectUnitOfWork` (`contracts/uow/projects/` + matching infra, fresh session per transaction,
mirroring the Register/Portfolio precedent) with two named accessors — `projects` and
`financial_profiles` — the latter so `create_project`'s atomic `ProjectFinancialProfile` write
participates in the exact same transaction, not a parallel raw-session write. `create_project`/
`update_project`/`set_status` all converged onto it: mutation + enterprise audit (`commit=False,
fail_closed=True`) + typed `DomainEvent`, one `uow.commit()`. `delete_project` is the one
deliberate exception, mirroring P40B Timesheet's own precedent exactly: its Task/Dependency/
Assignment/TimeEntry cascade is cross-capability cleanup (Task stays out of P43's scope per the
brief), so it stays on the existing shared session via a bare `SqlAlchemyUnitOfWorkBase` wrapper
around that same session, giving it typed-event capability while its cascade participates in the
identical transaction as the Project row's own deletion.

**A real cross-cutting correctness bug found and fixed during this phase, not merely inherited.**
The established `record_activity(uow, ...)` call shape (used verbatim by Register/P41) leaves
`commit` at its own default of `True`, which makes `ActivityService.record()` issue an early,
independent `session.commit()` *before* the same UoW's later `_drain_and_dispatch()`/event-commit
runs — meaning a transactional-handler failure occurring afterward cannot roll back the
already-committed mutation. A dedicated transactional-handler-failure regression test for Project
caught this directly (the project persisted despite the "rollback"). Fixed by passing
`commit=False` explicitly on every `record_activity`/`record_activity`-via-bare-wrapper call in
both `lifecycle.py` and `project_resource_commands.py`, folding the Activity-feed write into the
same atomic commit as the audit entry and the DomainEvent. Register's own equivalent call sites
were deliberately left untouched (out of P43's scope; its own tests happen not to observe the gap
due to a stale-session read masking it, not because the gap doesn't exist there too) — recorded
here as a known, narrowly-scoped follow-up, not silently fixed project-wide.

**`set_status` gap closed exactly as specified — no legacy intermediate step.** `set_status` now
runs inside `ProjectUnitOfWork`: mutation, atomic enterprise audit (previously **zero** audit
coverage — the weakest path of any Project command), a typed `ProjectStatusChanged`, and precise
ViewInvalidation, all in one transaction. Gained an optional `expected_version` parameter (parity
with `update_project`'s existing explicit pre-check) for symmetry and testability; the DB-level
`update_with_version_check` CAS already protected it implicitly before this phase (via the
just-fetched `project.version`), so this was a real gap in caller-visible staleness reporting and
audit, not a silent-corruption gap — confirmed by a genuine two-read/two-write concurrency test
(the second writer gets `ConcurrencyError`, final persisted status reflects only the winner).

**Concurrency preserved, not broadened.** `update_project`'s explicit `expected_version` check plus
the repository's own `update_with_version_check` CAS are unchanged. `delete_project` remains
genuinely unguarded (a plain filtered `DELETE`, no version predicate) — this is pre-existing debt,
not introduced or worsened by P43's transaction convergence, and out of scope to fix here (matching
the standing "characterize, don't schema-migrate" precedent).

**ViewInvalidation: two targets, not one per screen.** `PROJECT_LIST_SCOPE_CODE` (`OrganizationScope`
— Project collection/selector staleness) and `PROJECT_DETAIL_SCOPE_CODE` (`ResourceScope`, exact
project) — `ProjectCreated` maps to the list target only (no existing detail view for a
not-yet-created Project); `ProjectProfileUpdated`/`ProjectStatusChanged`/`ProjectRemoved` map to
both. The 4 `ProjectResource`-assignment sites needed their own minimal fact
(`ProjectResourceAssignmentChanged`, `application/resources/project_resource_events.py` — a real
`resources`-module fact, not a Project field change) since they never touch the Project entity at
all; it reuses Project's own detail-only target rather than inventing a parallel Resource
ViewInvalidation category for one narrow fact.

**Consumer cutover: 10 genuine consumers re-wired, 1 incidental removed, zero blanket-fan-out
carried over unexamined.** One `ProjectViewInvalidationAdapter` (list+detail signals), wired per
consumer in `context.py`: 7 blanket-refresh consumers (Projects, Dashboard, Portfolio, Register,
Tasks, Collaboration, Scheduling) via a `_wire_project_stale` helper mirroring the established
`_wire_resource_list_stale` pattern; Resources kept its existing surgical `_reload_if_loaded`
scoping (now triggered by the adapter instead of the legacy Signal); Financials kept its existing
project-scoped, lazy-per-destination `_finance_event_matches`/`_invalidate_destinations` logic
(extracted into a public `onProjectStale` method). Platform Access's genuine but narrow dependency
(the "Project" scope-target selector) is preserved through composition-root Signal/Slot wiring —
`ProjectManagementWorkspaceCatalog.projectDirectoryStale` re-exposes the list-target hint,
`shell/app.py::main()` connects it to `PlatformAdminAccessWorkspaceController.onExternalViewStale`
— mirroring P41-FIX's Register→Control precedent exactly, never a Platform→PM import. Platform
Control's subscription was removed with no replacement (INCIDENTAL, proved from source).

**Regression**: new `test_p43_project_full_modernization.py` (21 — ViewInvalidation handler unit
tests for all 4 event types + the resource-assignment fact, dedupe, real create/set_status/update/
delete producer paths with atomic-audit proofs, the mandatory `set_status` gap-closure test
asserting actual persisted status + real hint delivery, audit-failure rollback for both `create`
and the previously-weakest `set_status` path, the newly-discovered transactional-handler-failure
regression, two-session concurrency for both `update_project` and `set_status`, duplicate-name and
cross-reference rejection, the Approval bridge isolation check reused verbatim), full existing
Project/Resources/Register/Portfolio/Timesheet/Finance-financial-setup suites (over 300 across
this run) plus the P7/P7B/P8/architecture-guard/domain-event-wiring suites (130, several rewritten
in place: `test_domain_event_wiring.py`'s two `project_changed`-Signal tests now assert the typed
events/hints directly; `test_p7_legacy_bridge_removal.py`'s Register direct-wiring proof and its
"unrelated PM signal" example both repointed off the deleted field; `test_p7b_dead_signal_cleanup.
py`'s Financials/Portfolio/Scheduling coalescing proofs repointed to the new adapter/remaining
signal) all green.

**Legacy Signal count: 3 (4 minus one deletion) — fourth Project Management capability to reach
zero.** `project_changed` rejoins the historical P8 frozen allowlist's deleted-name set (added to
`_DELETED_BRIDGE_NAMES` in `test_p8_platform_event_architecture_canonicalization.py`); the frozen
baseline itself is unchanged. Remaining PM legacy signals: `tasks_changed`, `collaboration_changed`.
Approval's `ApprovalPostCommitEvent`/`_emit_signal_safely` baseline reconfirmed unchanged (still
exactly `financial_change_apply_participant.py` + `task_apply_participant.py`) — Task remains
responsible for its eventual retirement. **Collaboration is next, per P40A's tentative sequence —
its own dedicated durable-vs-ephemeral transport split first, not generic DomainEvents; Task
remains last** (dedicated audit first, final PM legacy modernization).

**P44A — Collaboration durable/ephemeral transport split (category-error correction, not full
modernization).** Reconfirmed the current `collaboration_changed` surface from source: 8
non-test producers, not P40A's approximate count — 6 **DURABLE** (`post_comment`,
`mark_task_mentions_read`, `edit_comment`, `delete_comment`, `react_to_comment`,
`remove_reaction`, all in `collaboration_comments.py`, all mutating the single `TaskComment`
aggregate, all on a raw shared `Session` with **zero** EnterpriseAudit and **zero** Activity-feed
coverage) and 2 **EPHEMERAL** (`touch_task_presence`/`clear_task_presence`, `collaboration_
presence.py`, upserting/deleting a TTL-windowed `TaskPresence` row keyed `(task_id, username)`,
also on a raw shared session, also with zero audit — correctly, since presence is not business
history). 3 consumers: Collaboration workspace (durable-only need), Dashboard (durable-only need,
specifically the activity feed), Tasks workspace (**both** — the one consumer with a real,
pre-existing dependency on presence data). Confirmed `touch_task_presence`/`clear_task_presence`
are the *only* two presence operations that exist — no typing/heartbeat/viewing/cleanup-job
methods were found anywhere in the codebase; TTL (default 900s, `PM_TASK_PRESENCE_TTL_SECONDS`) is
enforced purely by a query-time `last_seen_at >= now - ttl` filter, never a scheduled sweep.

**The category error, confirmed and now removed.** Before this phase: `touch_task_presence`/
`clear_task_presence` → `collaboration_changed.emit(task_id)` → Tasks workspace's blanket
`_request_domain_refresh()` → a full workspace rebuild (durable comments + everything else)
on *every single presence keepalive tick* (the heartbeat re-touches presence roughly every 30s
while any task detail panel is open). This was pure amplification: Task workspace's own presence
display was never actually driven by this refresh path in the first place — it already
self-updates via `beginTaskPresence`/`endTaskPresence`'s own slot flow and an independent
30-second heartbeat poll (`PMCollaborationController._on_runtime_heartbeat`) that rebuilds only
the presence collection. The full-workspace rebuild was pure waste, not a real dependency.

**Presence transport: a direct, scoped `ViewInvalidationHint` notify — no DomainEvent, no
handler, no dispatcher.** `TaskPresence` is genuinely a persisted, TTL-windowed read model
(`list_task_presence`/`list_active_presence`), so a real projection *does* become stale on
touch/clear — this is a legitimate ViewInvalidation use, not an abuse of it (per this project's own
"ViewInvalidation means a persisted/read-model projection became stale" principle) — while
remaining strictly forbidden from ever becoming a `DomainEvent`: no `uow.record_event(...)`, no
`TransactionalEventDispatcher`, no `PostCommitEventPublisher`, no audit-trail/business-history
implication. `touch_task_presence`/`clear_task_presence` now call `notify_task_presence_stale(...)`
(`application/collaboration/event_handlers/view_invalidation.py`, new — `TASK_PRESENCE_CATEGORY`/
`TASK_PRESENCE_SCOPE_CODE`, PM-owned vocabulary, generic `ViewInvalidationHint`/`ResourceScope`
transport shape owned by shared/platform) directly, synchronously, after their own commit
succeeds — no new capability UnitOfWork was introduced for this (source doesn't warrant one for a
blind TTL upsert/delete with no version field and no audit). A new `TaskPresenceViewInvalidation
Adapter` (QML) and one `onTaskPresenceStale`/`refresh_presence_for_task` hook were wired into Tasks
workspace's *existing* presence-rebuild code path (the same logic `_on_runtime_heartbeat` already
used) — giving genuine, tested value: the calling user's own presence indicator now updates
immediately on touch/clear instead of waiting up to 30s for the next heartbeat tick, with zero
effect on the durable comment thread.

**Ephemeral legacy publication fully removed; durable publication fully preserved.**
`collaboration_changed`/`tasks_changed` producer count for presence: 0 (both `touch_task_presence`
and `clear_task_presence` — confirmed by a source-level architecture-guard test, not just a
runtime probe). All 6 durable producers still emit `collaboration_changed` exactly as before —
proved by rerunning them end to end. A 10-touch presence storm test asserts the *durable* signal
count directly (must stay 0), not merely the lightweight hint count (which legitimately fires once
per touch — no coalescing was added, since none was required to satisfy the correctness goal and
none exists as an established precedent to reuse). Presence remains unaudited by design (a
dedicated test asserts zero new `AuditEntryORM` rows across a touch+clear pair) — this is expected
for ephemeral coordination state, not a newly-introduced or automatically-assumed gap.

**Multi-user/same-user semantics reconfirmed unchanged.** Presence is keyed `(task_id, username)`,
not `(task_id, user_id)` and with no session/client id — two different users can be simultaneously
present on the same task (proved with two real, independently-authenticated `UserSessionContext`s),
and one user's touch/clear can never affect another user's row. Same-user, multi-tab/multi-session
collapse to one row (last-write-wins on `activity`/`last_seen_at`) is pre-existing, unaffected
behavior — recorded as known debt for a future phase to reconsider if ever needed, not touched here
since the transport split doesn't require it.

**`collaboration_changed` intentionally remains — this phase's job was category separation, not
Signal deletion.** All remaining producers of `collaboration_changed` are now durable-only (the 6
`TaskComment` operations); no premature field deletion was made. **P44B readiness, audited now so
it can be DIRECT FULL MODERNIZATION**: one aggregate root, `TaskComment` (no separate
`Discussion`/`Reaction`/`Mention` entities — replies are `parent_comment_id` self-references,
reactions are an embedded `dict[emoji, [user_id]]` field, mentions are plain string-list fields);
`version: int` with real storage-layer CAS (`update_with_version_check`) on every `_comment_repo.
update()` call regardless of caller-supplied `expected_revision` (only `edit_comment`/
`delete_comment` pass one explicitly today — `react_to_comment`/`remove_reaction`/`mark_task_
mentions_read` blind-read-modify-write, protected only by the storage-layer CAS, a candidate for
P44B to reconsider, not fixed here); **zero EnterpriseAudit, zero Activity-feed coverage on any
durable Collaboration operation** — the biggest audit gap of any PM capability audited so far, a
mandatory P44B fix; **no `CollaborationUnitOfWork` exists** (raw shared session throughout,
matching presence) — P44B's first task is converging all 6 durable operations onto one; zero
cross-capability persisted mutations (Task/Project referenced by id only, read-time join only,
never mutated). Candidate P44B DomainEvents: a shared-family `CollaborationCommentChanged(change_
type=CREATED|UPDATED|REMOVED|REACTED|UNREACTED|MENTIONS_READ)` (mirroring `RegisterEntryChanged`'s
precedent — one cohesive aggregate, several operation kinds) is the leading candidate over 6
separate classes, to be finalized in P44B. Candidate ViewInvalidation targets: a per-task scope
(`SqlAlchemyTaskCommentRepository.list_by_task`) and a per-project/workspace scope
(`SqlAlchemyCollaborationWorkspaceReader.read_comment_page`, already a real paginated/filterable
read-model) — mirroring Register's dual-target (`REGISTER_PROJECT_SCOPE_CODE`/`REGISTER_WORKSPACE_
SCOPE_CODE`) shape closely. **P44B can delete `collaboration_changed` in one direct
full-modernization phase: YES** — no blocker identified.

**Read-only check performed, not fixed (§45 of the brief): Register's `record_activity(commit=
True)` early-commit pattern, flagged as a P43 discovery, is a STALE OBSERVATION for Register
specifically** — `register_lifecycle.py`'s three mutation methods already pass `commit=False`
explicitly at every `record_activity(uow, ...)` call site; P41's own UoW conversion never had the
bug P43 found and fixed in Project's files. No Register production changes were made in P44A.

**Regression**: new `test_p44a_collaboration_presence_transport_split.py` (15 — ephemeral
producers confirmed to emit zero `collaboration_changed`/zero `tasks_changed`, a source-level
architecture guard against reintroducing either, the scoped presence-hint proof for touch and
clear, a 10-touch storm asserting zero durable-signal amplification, all 6 durable producers
reconfirmed still firing `collaboration_changed`, presence proved un-audited by design, two-user
concurrent-presence proof, the Approval-bridge and Signal-still-exists baseline checks), full
existing Collaboration/Presence/Task suites (33) plus Project/Register/Portfolio/Timesheet/P7/P7B/
P8/architecture-guard/Finance-financial-setup regressions (277 total across this run) all green.

**Legacy Signal count: unchanged at 3.** No field deleted — architecture category separation is
this phase's milestone, not a Signal-count reduction (per the brief's own explicit instruction not
to force deletion). Remaining PM legacy signals: `tasks_changed`, `collaboration_changed` (now
durable-only). **P44B is next: direct full modernization of durable Collaboration. Task remains
last.**

**P44B — Durable `TaskComment` full modernization; `collaboration_changed` deleted.** Reconfirmed
the exact remaining surface from source, not P44A's own truncated summary: 6 durable operations,
all in `collaboration_comments.py` — `post_comment`, `mark_task_mentions_read`, `edit_comment`,
`delete_comment`, `react_to_comment`, `remove_reaction` — one aggregate, `TaskComment`, no separate
`Discussion`/`Reaction`/`Mention` entities (replies are `parent_comment_id` self-references,
reactions an embedded `dict[emoji, [user_id]]`, mentions plain string-list fields on the comment
itself). 3 consumers reconfirmed: Collaboration workspace, Dashboard (activity feed only), Tasks
workspace (both durable comments and presence, kept intentionally separate).

**Event vocabulary — three semantically distinct families, not one catch-all.** `TaskCommentChanged
(change_type=CREATED|EDITED|REMOVED)` — a shared family mirroring `RegisterEntryChanged`'s
precedent, since create/edit/(soft-)delete are genuinely the same kind of fact (the comment itself
changed); `TaskCommentReactionChanged(change_type=ADDED|REMOVED)` — a distinct business fact,
since a reaction changing doesn't mean the comment's own content/existence changed;
`TaskCommentReadStateChanged` — a distinct read-receipt fact, no `change_type` (marking is
one-directional in the current domain). Mentions have no separate event — confirmed source-only
mutated as part of create/edit, never independently (brief's own §8 "option A"). Payloads carry
only `tenant_id/organization_id/project_id/task_id/comment_id/occurred_at` plus `change_type`
where applicable — no comment body, no full reactions/mentions list, no ORM/session/DTO.

**A real latent bug found and fixed while converging `post_comment` onto the canonical UoW.**
`post_comment`'s interaction with `DocumentIntegrationService.register_entity_attachments` (itself
always on its own separate, fresh `DocumentUnitOfWork` — confirmed by reading its source, never the
Collaboration session) meant the *old* code's `else: self._session.commit()` branch was skipped
entirely whenever attachments were present, silently leaving the comment row **uncommitted** on
the shared session. Fixed as a natural consequence of UoW conversion: the comment's own atomic
transaction (mutation + audit + `TaskCommentChanged`) now *always* commits first, unconditionally,
before the pre-existing (unchanged, still-separate) document-attachment/link calls run afterward —
strictly safer than before, not merely equivalent.

**Canonical transaction ownership: new `CollaborationUnitOfWork`.** No Collaboration UoW existed
before this phase (all 6 durable operations *and* both presence operations ran on one raw shared
`Session`, confirmed identically for `TaskComment` as it was for Presence in P44A). Added
`CollaborationUnitOfWork` (`contracts/uow/collaboration/` + matching infra, fresh session per
transaction, one named accessor `comments: TaskCommentRepository`, mirroring the Register/Project/
Portfolio precedent exactly) — no `_activity_service` was added, since Collaboration never had one
in the first place: the "activity feed" shown by Collaboration workspace/Dashboard is not the
generic `ActivityService`/`ActivityEntry` mechanism at all, it is `TaskComment` rows themselves,
read through `SqlAlchemyCollaborationWorkspaceReader.read_comment_page` — confirmed by source, so
adding a parallel Activity-feed write would have been a duplicate, invented mechanism, not a real
gap (brief's own §19 guidance followed precisely).

**Enterprise audit added where none existed at all — the largest audit gap found in any PM
capability so far.** All 6 durable operations now record `record_audit_entry(uow, ..., commit=
False, fail_closed=True)` atomically alongside their mutation and typed event, inside the same
`uow.commit()`. Presence (P44A) remains deliberately un-audited — confirmed still correct and
unchanged by this phase.

**Concurrency preserved exactly, not weakened.** `SqlAlchemyTaskCommentRepository.update()`'s
always-on `update_with_version_check` CAS is unchanged; `edit_comment`/`delete_comment`'s optional
caller-supplied `expected_revision` pre-check is unchanged. Proved with a real two-independent-
read/two-independent-write concurrency test for `edit_comment` (the second writer gets
`ConcurrencyError`, final persisted body reflects only the winner) — the same shape already
established for Register/Project. `react_to_comment`/`remove_reaction`/`mark_task_mentions_read`
confirmed to have **no** caller-supplied `expected_revision` guard in source (unchanged, not a
regression) — protected only by the storage-layer CAS.

**No-op semantics reconfirmed and preserved exactly, not invented.** `mark_task_mentions_read`'s
existing "already read" guard and `delete_comment`'s existing "already deleted" guard are true,
source-established no-ops: zero write, zero audit, zero event, zero ViewInvalidation, proved
directly. `react_to_comment`/`remove_reaction` are confirmed to have **no** such guard in source
(repeating the same reaction still writes/audits/emits every time) — this pre-existing behavior
was preserved as-is, not "fixed" into a new idempotency behavior the domain never asked for; the
final reactor *set* is still data-level idempotent (one entry, not duplicated), just not
event-level idempotent.

**ViewInvalidation: two scope codes, mapped by actual business meaning, not uniformly.**
`TASK_COMMENT_SCOPE_CODE` (`ResourceScope`, exact task) fires for every one of the three event
families; `COLLABORATION_WORKSPACE_SCOPE_CODE` (`OrganizationScope`, org-wide) fires *only* for
`TaskCommentChanged` (create/edit/remove — content that genuinely appears in cross-project "recent
activity"), deliberately excluding `TaskCommentReactionChanged`/`TaskCommentReadStateChanged`
(neither is displayed anywhere at the workspace/dashboard level per source inspection — brief's own
§37/§38 guidance against unproven broad fan-out, applied directly rather than uniformly mapping
every event to every target the way the legacy Signal did).

**Consumer cutover: all 3 real consumers, zero incidental, zero blanket fan-out on
reactions/read-state.** New `TaskCommentViewInvalidationAdapter` (two signals:
`taskCommentsStale`/`collaborationWorkspaceStale`), wired per consumer in `context.py`: Tasks
workspace gets a narrow `onTaskCommentsStale(task_id)` (refreshes only when the stale task matches
the currently selected one, mirroring the established `onTimesheetProjectStale`/`onRegisterProjectStale`
pattern) *in addition to* its own separate, pre-existing `onTaskPresenceStale` (P44A) — genuinely
two independent inputs, never merged back together, exactly as the brief required. Collaboration
workspace and Dashboard each get a blanket-refresh connection to `collaborationWorkspaceStale`
only (never `taskCommentsStale`, and never the presence adapter — Dashboard heartbeat-refreshing
was explicitly forbidden and confirmed absent).

**Regression**: new `test_p44b_collaboration_comment_full_modernization.py` (25 — ViewInvalidation
handler unit tests for all three event families + dedupe, real create/edit/delete/react/unreact/
mark-read producer paths with atomic-audit proofs, both source-established no-ops proved zero-effect,
the reaction-repeat-is-not-a-no-op characterization preserving exact current behavior, mandatory
audit-failure and transactional-handler-failure rollback, real two-session `edit_comment`
concurrency, cross-reference rejection, the legacy-deletion and Approval-bridge baseline checks),
`test_collaboration_phase0a3_rollback_hardening.py` rewritten in place for all 6 durable methods
(repository-class-level and `EnterpriseAuditService`-level failure injection replacing the old
shared-session/legacy-Signal assertions; presence sections entirely unchanged, still passing),
`test_p44a_collaboration_presence_transport_split.py` updated (4 tests repointed from the now-
deleted legacy Signal to the durable-hint-count equivalent), `test_qml_domain_event_bridges_pm.py`
and `test_p8_platform_event_architecture_canonicalization.py` repointed off the deleted field, full
existing Collaboration/Presence/Project/Register/Portfolio/Timesheet suites plus P7/P7B/P8/
architecture-guard/Finance-financial-setup regressions (297 total across this run) all green.

**Legacy Signal count: 2 (3 minus one deletion) — Collaboration reaches zero legacy Signal
fields.** `collaboration_changed` rejoins the historical P8 frozen allowlist's deleted-name set
(added to `_DELETED_BRIDGE_NAMES`); the frozen baseline itself is unchanged. **`tasks_changed` is
now the sole remaining PM legacy Signal — Task is the final PM legacy modernization phase.**
Approval's `ApprovalPostCommitEvent`/`_emit_signal_safely` baseline reconfirmed unchanged (still
exactly `financial_change_apply_participant.py` + `task_apply_participant.py`, both emitting
`tasks_changed`) — Task itself remains responsible for that mechanism's eventual retirement.

## 4. Current State

**Legacy Signal count: 2 as of P44B** (source-derived from
`src/core/shared/events/domain_events.py`, re-verified against current source when this document
was last updated — `dataclasses.fields(domain_events)`, not a manual field count). Down from 3 at
P43 — `collaboration_changed` is now deleted, the fifth Project Management capability to reach
zero, and Collaboration's own legacy surface is fully closed (durable modernized in P44B, ephemeral
presence transport-split in P44A). `tasks_changed` remains the sole PM legacy Signal, pending
Task's own dedicated-audit-first modernization.
**Finance module event modernization is complete: zero Finance-owned legacy Signal fields
remain.** The P8 architecture budget (`current ⊆ frozen`) remains restored with zero exceptions
(P37 was the last post-freeze *violation*; P38B/P39/P40B/P41/P42/P43/P44A/P44B are ordinary
further retirement of pre-freeze, frozen-allowlisted signals, not violation fixes).

| Area | Count |
|---|---|
| Platform | 0 |
| Auth/Security | 1 |
| Project Management | 1 |
| Finance | 0 |
| Inventory/Procurement | 0 |

> **This is a snapshot, not a fact.** Recompute the count directly from
> `src/core/shared/events/domain_events.py` before relying on it - do not trust this table if it
> is more than a few phases old. Concurrent development in any module can add or remove fields
> between updates to this document.

## 5. Current Priority

**Inventory/Procurement's entire event-modernization surface is COMPLETE as of P33** (P28B/
P28B-FIX/P29/P29-FIX/P30B/P30B-FIX/P31B/P32B/P33, see §3) — all nine capabilities (Item/Category,
Storeroom/Location, Reorder Policy, Purchase Order, Requisition, Reservation, Stock Balance, Cycle
Count, Goods Receipt) fully modernized, `dataclasses.fields(DomainEvents)` carries zero
`inventory_`-prefixed names. `inventory_purchase_orders_changed`, `inventory_requisitions_changed`,
`inventory_reservations_changed`, `inventory_balances_changed`, `inventory_cycle_counts_changed`,
and `inventory_receipts_changed` are all deleted — zero producers, zero consumers, fields absent.
**No Inventory/Procurement work remains for this document to prioritize.** Attention shifts entirely
to the remaining modules — Project Management, Finance, Auth/Security — per §6. **Auth Credential &
Session remains AUDITED / DEFERRED** (P26A, see §3) — still not recommended given no canonical UoW
exists yet on that surface.

**Planned Cost is DONE (P35, see §3)** — `planned_costs_changed` is deleted, the first of P34A's
Finance-first trio complete. `financial_changes_changed` is ALSO now gone (retired independently,
outside this document's tracked sequence — see the P35-CLEANUP entry). **Commitment is DONE (P36,
P36-FIX, P36-FIX2, see §3)** — `commitments_changed` is deleted; the commit-without-rollback bug is
fixed via convergence onto `FinanceGovernanceUnitOfWork`; the Procurement-driven producer path's
event lifecycle is fully canonical (real `SqlAlchemyUnitOfWorkBase`, no dispatcher-as-UoW
impersonation). **Cost Entry is now DONE too (P37, see §3)** — `cost_entries_changed` is deleted,
completing P34A's Finance-first trio. This was the **last post-P8-freeze legacy-Signal violation**
— the P8 architecture budget (`current ⊆ frozen`) is now restored with zero exceptions; the P8
guard suite is fully green. **No Finance capability with a post-freeze legacy-Signal violation
remains.** **Budget is DONE (P38B, see §3)** — `budgets_changed` is deleted. The Financial-Change
coupling P38A found (one Approval-participant edge, already transaction-safe) is now typed on
both sides: `financial_change_apply_participant.apply()` returns the Budget-side
`BudgetVersionCreated`/`BudgetStatusChanged` facts alongside its own `FinancialChangeChanged`(+
`ForecastVersionChanged`), in the same `ApprovalHandlerResult.domain_events` tuple. **Billing
Profile and Billing Preparation are now DONE too (P39, see §3)** — `billing_preparations_changed`
is deleted, both aggregate families modernized together (kept as genuinely distinct DomainEvent
vocabularies, sharing one `billing_commercial` ViewInvalidation target and one broadened
`FinanceGovernanceUnitOfWork` — the bespoke `BillingPreparationSubmissionUnitOfWork` is retired
entirely). **This was the last Finance legacy signal — Finance module event modernization is now
100% complete**, verified by a new permanent architecture guard
(`test_zero_finance_legacy_signal_fields_remain`). **No Finance capability of any kind remains for
this document to prioritize.** Attention on the Finance track ends here; remaining modernization
work is entirely Project Management and Auth/Security, per §6.

**PM re-audited and re-sequenced (P40A, AUDIT + SEQUENCING ONLY — see §3's P40A entry, no code
changed).** All six remaining PM legacy Signals were re-audited from current source. Next three
targets selected, in order: Timesheet → Register → Portfolio (all rated DIRECT FULL
MODERNIZATION — smallest producer surfaces, already-atomic or near-atomic transactions, zero
approval-subsystem entanglement, and (Portfolio) zero coupling with Project in either direction).
Tentative full sequence after that: Project, then Collaboration (needs its own short audit/
transport-split phase first — presence and durable comments currently share one Signal and
presence needs a non-`DomainEvent` mechanism), then Task last (highest strategic value — the only
capability touching the shared `ApprovalPostCommitEvent` legacy bridge — but worst-in-class on
every ease dimension: no UoW exists yet, 3 independently-versioned aggregates, 28 producer sites
across 2 module boundaries, and a required coordination point with Financial Change's own
participant). Full reasoning, matrices, and scorecard in §3's P40A entry.

**Timesheet is now DONE (P40B, see §3)** — `timesheet_periods_changed` is deleted, the first of
P40A's PM sequence complete and the first PM capability of any kind to reach zero legacy Signal
involvement. Converged onto a bare `SqlAlchemyUnitOfWorkBase` wrapping `TimeService`'s own
already-shared session (no new named-repository UoW — none was architecturally required), one
shared-family `TimesheetPeriodStatusChanged` event, and three ViewInvalidation targets (workspace/
resource/project) replacing the legacy signal's unscoped fan-out to the same three consumer
families.

**Register is now DONE too (P41, see §3)** — `register_changed` is deleted, the second PM
capability to reach zero. Fixed the real two-commit business-mutation/audit split P40A found (and
added enterprise audit, which Register never had before this phase — only the lighter Activity
feed) by converging onto a new, narrow `RegisterUnitOfWork` (unlike Timesheet, no existing session
constraint favored reuse, so this followed Resource's/Employee's own fresh-session-per-command
precedent instead). One shared-family `RegisterEntryChanged` event and two ViewInvalidation
targets (workspace/project). Platform's Control workspace subscription could not be cut over to a
typed hint (a real Platform/PM layering guard forbids it) and was dropped with no replacement.
That guard turned out (P41-FIX) to not actually cover the QML layer at all, but the composition-
root Signal/Slot pattern already used for Platform→PM wiring restored the real dependency PM→
Platform for the first time, with neither side importing the other's implementation.

**Portfolio is now DONE too (P42, see §3)** — `portfolio_changed` is deleted, the third PM
capability to reach zero. Fixed the real nested/self-owned commit hazard P40A found
(`_ensure_scoring_templates()`'s own internal `session.commit()` calls, triggered as a side effect
from Intake commands too) by converging all four sub-aggregates (Intake, Scenario, ScoringTemplate,
ProjectDependency) onto one `PortfolioUnitOfWork`, mirroring `DocumentUnitOfWork`'s established
one-capability-several-repos shape. Added enterprise audit to three of the four sub-aggregates,
which had none before. Two of Portfolio's three legacy consumers (PM Dashboard, Projects workspace)
turned out to be incidental — neither ever read any of the four real sub-aggregates — and were
dropped with no replacement; only Portfolio's own workspace was genuine. **Project remains next,
unchanged from P40A's tentative sequence.**

**A pre-existing, explicitly-not-fixed note carried forward by P33**: `PurchaseOrderLineORM` has no
`version` column and its repository performs a blind field overwrite on `update()` — confirmed real
by a two-session regression test (P33 §14), contrasted directly against `PurchaseRequisitionLine`
(the sibling aggregate, which IS `update_with_version_check`-protected, per P28B's own
`test_requisition_line_sourcing_rejects_concurrent_stale_update`). This is not new — P28A already
characterized it neutrally ("no own version field, additive-only mutation") — and P33 deliberately
did not fix it, since doing so would require a schema migration unrelated to and out of proportion
with the Receipt DomainEvent/ViewInvalidation work that was this phase's actual goal. Flagged here
as an explicit, unresolved architectural note for any future phase that touches PO-line receiving
concurrency directly.

**P28B/P28B-FIX/P29/P29-FIX/P30B/P30B-FIX/P31A/P31B/P32A/P32B/P33's own explicit non-gaps, resolved rather than carried forward**: the
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

- **Project Management** (re-sequenced by P40A, AUDIT + SEQUENCING ONLY, see §3/§5 — tentative
  past the first three): **1. Timesheet Period — DONE (P40B, see §3)**, **2. Risk Register — DONE
  (P41, see §3)**, **3. Portfolio — DONE (P42, see §3)** (Template/Scenario/Intake/Dependency).
  Then (tentative) **4. Project Lifecycle**, **5. Collaboration Comment** (needs its own short
  audit/transport-split phase first — Collaboration Presence needs a non-`DomainEvent` mechanism,
  not a migration target), **6. Task Lifecycle last** (highly overloaded — 8 real facts across 3
  aggregates + a bulk operation, requires a dedicated audit-first phase and coordination with
  Financial Change's participant before implementation, despite being the only capability that
  would shrink the shared `ApprovalPostCommitEvent` legacy-bridge count).
- **Finance — MODULE COMPLETE (P39, see §3/§5)**: every Finance capability (Financial Setup, Rate
  Card, Forecast, Planned Cost, Project Commitment, Project Cost Entry, Project Budget, Billing
  Profile, Billing Preparation) is fully modernized onto typed DomainEvents. Zero Finance-owned
  legacy Signal fields remain — `dataclasses.fields(DomainEvents)` carries none. **No further
  Finance phase is needed.**
- **Inventory/Procurement — ALL NINE CAPABILITIES DONE, MODULE COMPLETE**: **Purchase Order — DONE
  (P28B/P28B-FIX, see §3)**, **Requisition — DONE (P29/P29-FIX, see §3)**, **Reservation — DONE
  (P30B/P30B-FIX, see §3)**, **Stock Balance — DONE (P31A/P31B, see §3)**, **Cycle Count — DONE
  (P32A/P32B, see §3)**, and **Goods Receipt — DONE (P32A/P33, see §3)**. `inventory_purchase_
  orders_changed`, `inventory_requisitions_changed`, `inventory_reservations_changed`,
  `inventory_balances_changed`, `inventory_cycle_counts_changed`, and `inventory_receipts_changed`
  are all deleted (fields absent, zero producers, zero consumers) — `dataclasses.fields(
  DomainEvents)` carries zero `inventory_`-prefixed names. **No further Inventory/Procurement phase
  is needed.**
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
- ~~`planned_costs_changed`~~ **RESOLVED by P35 — first of P34A's Finance-first trio** - the one
  producer (`calculate_snapshot`) now records a single typed `PlannedCostSnapshotCalculated` fact
  ("the project's planned-cost snapshot was recalculated") on the previously-unused
  `FinanceGovernanceUnitOfWork.planned_costs` accessor, via a new `FinanceGovernanceCommandBoundary.
  planned_cost()` method mirroring P19's `forecast_version()` shape exactly, field deleted (ADR-005
  §26.31). `AssignmentRepository`/`ProjectResourceRepository` accessors were added to the shared UoW
  (a small, precedent-following extension, not a new transaction stack) since `calculate_snapshot`'s
  diagnostics computation needed them and every sibling operation in that UoW is otherwise
  UoW-pure. Only `planned_cost_snapshot` (`ResourceScope`, project-scoped) exists — no
  `planned_cost_detail` was invented, since source confirmed the version list and selected-version
  lines are always fetched together in one query. The pre-existing optimistic-concurrency guard
  (version-checked supersede + revision-uniqueness constraint) is preserved, proven still-rejecting
  by a two-session regression test. Next: `commitments_changed`.
- ~~`commitments_changed`~~ **RESOLVED by P36 — second of P34A's Finance-first trio** - the three
  UI-facing mutations (`ingest_procurement_source`, `match_cost_entry`, `reverse_match`) converge
  onto the previously-unused `FinanceGovernanceUnitOfWork.commitments` accessor via a new
  `FinanceGovernanceCommandBoundary.commitment()` method mirroring P35's `planned_cost()` shape,
  fixing the confirmed commit-without-rollback bug in the old `_commit()` (now deleted). Two typed
  facts — `CommitmentLineChanged` (`CREATED`/`REVISED`) and `CommitmentMatchChanged`
  (`MATCHED`/`REVERSED`) — replace the signal, both routed through one `commitment_list`
  (`ResourceScope`, project-scoped) target, matching the legacy signal's own 5-destination fan-out.
  The second producer P35-CLEANUP found (`ProcurementFinancialDispatcher`) was NOT converged onto a
  *second* UoW — its own commit/rollback was already correct — only its two Procurement-inbox-facing
  methods' *return contract* changed (typed event instead of entity); field deleted (ADR-005
  §26.32). **P36-FIX/P36-FIX2 correction**: the initial fix had the dispatcher manually call
  `transactional_dispatcher.dispatch(event, self)` — real `UnitOfWork` impersonation. Final design:
  the dispatcher wraps its own already-owned session in a real `SqlAlchemyUnitOfWorkBase` per
  delivery (`uow.record_event(...)` + `uow.commit()`), one canonical transaction, no impersonation.
- ~~`cost_entries_changed`~~ **RESOLVED by P37 — third and LAST of P34A's Finance-first trio, and
  the last post-P8-freeze legacy-Signal violation** - eight direct commands converge onto
  `FinanceGovernanceUnitOfWork` via `FinanceGovernanceCommandBoundary.cost_entry()`. Five typed
  facts (`CostEntryRecorded`/`Updated`/`StatusChanged`/`Reversed`/`Removed`) replace the signal,
  routed through two targets (`cost_entry_list` for every fact, `cost_entry_actuals` only for
  POSTED-affecting facts — source-confirmed via `finance_snapshot_statements.py`'s `status IN
  ('posted','reversed')` filter). The Approval path uses `ApprovalHandlerResult.domain_events`
  (P19's canonical seam), no legacy bridge. Both integration dispatchers
  (`ProcurementFinancialDispatcher`, `ApprovedTimeFinancialDispatcher`) now record Cost Entry
  events into the same canonical per-delivery UoW P36-FIX2 established; field deleted (ADR-005
  §26.33). `current ⊆ frozen` restored — P8 guard suite fully green.
- ~~`inventory_receipts_changed`~~ **RESOLVED by P33 — Inventory/Procurement's LAST legacy Signal,
  module now COMPLETE** - the one producer (`post_receipt`) now records a single typed
  `InventoryReceiptPosted` fact ("a Receipt was posted") alongside the pre-existing
  `InventoryPurchaseOrderReceivingAdvanced` and Balance facts in the same already-canonical
  `PurchaseOrderSubmissionUnitOfWork` transaction, field deleted (ADR-005 §26.30). Only a
  `receipt_list` (`OrganizationScope`) ViewInvalidation target exists — no `receipt_detail` was
  invented, since source confirmed no single-Receipt read model exists anywhere in the UI. All 6
  legacy subscriptions removed: 2 confirmed incidental (Catalog, Reservations, no replacement), 4
  confirmed genuine at the field level (Procurement, Dashboard, Pricing, Inventory(Foundation),
  each replaced by its own `ReceiptViewInvalidationAdapter` instance). A pre-existing,
  P28A-documented gap (`PurchaseOrderLineORM` has no `version` column, unlike its sibling
  `PurchaseRequisitionLine`) was confirmed still real by a two-session regression test but
  deliberately left unfixed — out of proportion with this phase's actual scope. `dataclasses.
  fields(DomainEvents)` now carries zero `inventory_`-prefixed names.
- **PRE-EXISTING CORRECTNESS / CONCURRENCY DEBT — `PurchaseOrderLine` receiving has no optimistic
  concurrency protection.** `PurchaseOrderLineORM` has no `version` column at all (unlike
  `PurchaseOrder`/`CycleCount`/`StockBalance`/`StockReservation`/`PurchaseRequisitionLine`, all
  `update_with_version_check`-protected), and `SqlAlchemyPurchaseOrderLineRepository.update()`
  performs a blind field overwrite. First neutrally documented by P28A ("no own version field,
  additive-only mutation"); reconfirmed real by a two-session repository-level regression test in
  P33 (`test_purchase_order_line_receiving_has_no_optimistic_concurrency_protection`) — two
  concurrent receipts against the same PO line, each reading the other's pre-write state, both
  succeed with neither rejected, a genuine lost-update risk. **Not a P33 or P33-CLEANUP
  regression** — pre-existing since the aggregate was first built, orthogonal to the Receipt
  DomainEvent/ViewInvalidation work, and deliberately left unfixed both times since a real fix
  requires a schema migration (a new `version` column) out of proportion with either phase's own
  scope. Revisit only if/when a phase's actual goal directly requires PO-line write-conflict
  safety.
- ~~`inventory_cycle_counts_changed`~~ **RESOLVED by P32B** - both producer operations
  (`schedule_cycle_count`, `complete_cycle_count`) converged onto the canonical
  `InventoryFoundationUnitOfWork`, gaining an atomic enterprise audit for `schedule_cycle_count`
  for the first time; 2 typed, field-oriented facts (`InventoryCycleCountScheduled`/
  `InventoryCycleCountCompleted`) replace the legacy signal, field deleted (ADR-005 §26.29). The 5
  incidental legacy subscriptions confirmed zero-dependency by P32A (Catalog, Pricing, Procurement,
  Dashboard, Reservations) are removed with no replacement. Goods Receipt's own legacy signal
  (`inventory_receipts_changed`) is unchanged — it was not modernized in its own right, mirroring
  how P30B/P32B each left the other's signal untouched while still recording their own genuine
  Balance mutation.
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
  most of PM and Inventory/Procurement. Finance has none left with a legacy-Signal-carrying
  producer on one — `budgets_changed`/`billing_preparations_changed` (Budget, Billing Preparation)
  remain raw-Session in places but are pre-freeze/frozen-allowlisted, not violations.
- ~~Orphan Resource typed events before P18~~ **RESOLVED by P18A** -
  `ResourceMasterChanged`/`ResourceCapabilityChanged` now dispatch through the canonical
  post-commit bus (bespoke `Signal[T]` transport deleted); still zero real UI subscribers until
  P18B builds the ViewInvalidation handler.
- ~~Coarse Inventory workspace refresh fan-out~~ **RESOLVED by P33, dead wiring removed by
  P33-CLEANUP** - narrowed from a blanket 11 since P20, through 1 (`inventory_receipts_changed`) as
  of P32B, to **zero** as of P33. All 6 legacy binder files/methods across every Inventory/
  Procurement workspace controller (left as empty stubs at P33 time) were deleted outright by
  P33-CLEANUP, along with the now-dead `_subscribe_domain_signal`/
  `_disconnect_domain_event_subscriptions` legacy-Signal machinery on
  `InventoryProcurementWorkspaceControllerBase` — no compatibility shell was kept. Every
  Inventory/Procurement fact (Storeroom, Location, Reorder Policy, PO, Requisition,
  Reservation, Stock Balance, Cycle Count, Receipt) routes through its own typed ViewInvalidation
  adapter.

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
