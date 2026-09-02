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
| ViewInvalidation handler | GENERALIZED — `build_requisition_sourcing_view_invalidation_handler` (which only ever handled the one PO-triggered event) was renamed `build_requisition_view_invalidation_handler` and its type union widened to all 8 Requisition event types, mirroring `build_purchase_order_view_invalidation_handler`'s own single-handler shape for its 10 PO events. Every event notifies both `requisition_list` and `requisition_detail` (P19-FIX/P22-FIX/P28B "notify both" precedent) — no per-event asymmetry attempted |
| Approval event return | CANONICAL (Option A pattern, same as PO) — `apply_submitted_requisition_approval`/`_rejection` now return `ApprovalHandlerResult(domain_events=(...))` instead of the legacy `ApprovalPostCommitEvent("inventory_requisitions_changed", ...)` bridge |
| No-op discipline | `update_requisition` gained a true no-op guard (zero write/audit/event/version bump on an identical payload) — P27A's own finding was that this guard never existed |
| Enterprise audit | ADDED — `record_audit_entry(uow, ..., commit=False, fail_closed=True)` now runs atomically with create/add-line/update/cancel; previously these paths had zero enterprise audit (best-effort activity-feed only, P27A finding). Proven atomic by a real audit-failure-rollback regression test (representative of all four, which share one transaction boundary) |
| Supplier same-organization integrity | **Re-investigated, found NOT a real gap** — P27A/P28A/P28B all characterized `_ensure_business_supplier_scope` as never checking organization membership, based on reading that method in isolation. Tracing its sole caller one line up shows `PartyService.get_party` already scopes its own lookup to the active organization and raises `NotFoundError` for a cross-org party — confirmed by a real regression test, not inferred. No code change was made (a second check would have been unreachable dead code); this corrects the prior phases' characterization rather than fixing a bug that doesn't exist |
| Consumer cutover | CUT OVER — the existing `RequisitionViewInvalidationAdapter` (P28B-FIX) is reused unchanged for all 8 event types (no second/parallel adapter). Procurement's wiring is unchanged (already existed). **Dashboard now has a genuine dependency** — Submitted/Approved/Rejected/Cancelled each move a Requisition into or out of its "Awaiting Approval" `{SUBMITTED, UNDER_REVIEW}` KPI filter (P28B-FIX only ever ruled out the *sourcing* event, not Requisition's own facts) — a new `RequisitionViewInvalidationAdapter` instance was wired for Dashboard, reacting to both `requisitionListStale`/`requisitionDetailStale` like every other Inventory capability's Dashboard wiring (no finer-than-scope_code granularity exists anywhere in this architecture, so Created/LineAdded/ProfileUpdated/SourcingAdvanced also reach Dashboard's `refresh()` — harmless, matching the established "full refresh, no narrower seam" acceptance class). Catalog/Reservations/Pricing/Inventory(Foundation) subscriptions removed, no replacement (confirmed zero real dependency, unchanged from P27A) |
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

## 4. Current State

**Legacy Signal count: 17 as of P29** (source-derived from
`src/core/shared/events/domain_events.py`, re-verified against current source when this document
was last updated — `dataclasses.fields(domain_events)`, not a manual field count).

| Area | Count |
|---|---|
| Platform | 0 |
| Auth/Security | 1 |
| Project Management | 6 |
| Finance | 6 |
| Inventory/Procurement | 4 |

> **This is a snapshot, not a fact.** Recompute the count directly from
> `src/core/shared/events/domain_events.py` before relying on it - do not trust this table if it
> is more than a few phases old. Concurrent development in any module can add or remove fields
> between updates to this document.

## 5. Current Priority

**Purchase Order and Inventory Requisition are both fully modernized** (P28B/P28B-FIX/P29, see
§3). `inventory_purchase_orders_changed` and `inventory_requisitions_changed` are both deleted —
zero producers, zero consumers, fields absent. Inventory/Procurement's remaining legacy signals
(4: `inventory_balances_changed`, `inventory_reservations_changed`, `inventory_receipts_changed`,
`inventory_cycle_counts_changed`) cover Stock Balance/Ledger, Reservation, Goods Receipt, and Cycle
Count — none of which have been audited yet. **No next capability has been chosen.** Per this
document's own repeated caution, re-run prioritization from current source before committing to a
target — concurrent development elsewhere may have changed readiness since P17/P26A. **Auth
Credential & Session remains AUDITED / DEFERRED** (P26A, see §3) — still not recommended given no
canonical UoW exists yet on that surface.

**P28B/P28B-FIX/P29's own explicit non-gaps, resolved rather than carried forward**: the
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
- **Inventory/Procurement**: **Purchase Order — DONE (P28B/P28B-FIX, see §3)** and **Requisition —
  DONE (P29, see §3)**, both fully modernized: `inventory_purchase_orders_changed` and
  `inventory_requisitions_changed` both deleted (fields absent, zero producers, zero consumers).
  Reservation, Stock Balance/Ledger, Cycle Count, Goods Receipt remain unaudited — no next
  Inventory/Procurement target has been chosen yet.
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
- `inventory_balances_changed` - ledger/balance overload; StockBalance is a maintained running
  total, not a derived read, so typed events here must carry enough identity to avoid
  reintroducing ambiguity.
- ~~`inventory_purchase_orders_changed`~~ **RESOLVED by P28B** - all 12 producer sites converged,
  field deleted; the PO-approval → Requisition-sourcing-mutation boundary is now the typed
  `InventoryRequisitionSourcingAdvanced` fact (ADR-005 §26.23).
- ~~`inventory_requisitions_changed`~~ **RESOLVED by P29** - all 7 remaining producer sites
  converged onto the existing `RequisitionSubmissionUnitOfWork` (Option A extension) and
  `ApprovalHandlerResult.domain_events`, field deleted (ADR-005 §26.25). The supplier
  same-organization concern carried forward since P27A was investigated and found not to be a
  real gap - `PartyService.get_party` already scopes to the active organization.
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
- Coarse Inventory workspace refresh fan-out - narrowing since P20; by P29 each of the 6
  Inventory/Procurement workspace controllers subscribes only to the 4 remaining legacy signals
  it has a real (or still-unaudited) dependency on, not a blanket 11 - PO and Requisition facts
  now route through their own typed ViewInvalidation adapters instead.

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
