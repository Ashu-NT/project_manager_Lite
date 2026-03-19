# Inventory & Procurement Module Blueprint

## Purpose

This document defines the first real implementation plan for the `inventory_procurement` module.

It is intentionally written before deeper implementation so the module starts with:

- real-world inventory and procurement behavior
- a clean ownership boundary
- strict reuse of the shared platform seams

This module is also the first architecture proof that the shared-platform model works in practice.

## Architecture Proof Goal

Inventory must prove the following:

- no local supplier master
- no local site master
- no local document system
- all shared references come from platform seams
- all writes stay in the owning domain

If Inventory passes these rules, the shared platform is working as intended.

## Ownership Model

### Platform Owns

Inventory must consume these shared capabilities; it must not duplicate them:

- `site`
- `party`
- `documents`
- `approvals`
- `audit`
- auth, RBAC, notifications, and shared module runtime

### Inventory & Procurement Owns

The module owns inventory and procurement workflow truth:

- `stock_item`
- `storeroom`
- `stock_balance`
- `stock_transaction`
- `stock_reservation`
- `purchase_requisition`
- `purchase_requisition_line`
- `purchase_order`
- `purchase_order_line`
- `receipt_header`
- `receipt_line`

### Other Modules Consume By Reference

- `maintenance_management` must reference item, storeroom, reservation, requisition, purchase-order, and receipt records
- no other module may create a shadow item master or stock ledger

## First Implementation Scope

The user-defined first core entities are correct and should remain the center of phase 1:

- `stock_item`
- `storeroom`
- `stock_balance`
- `purchase_requisition`
- `purchase_order`

However, a real-world system cannot operate those safely without a few supporting records.

The smallest professional inventory slice also needs:

- `stock_transaction`
- `purchase_requisition_line`
- `purchase_order_line`
- `receipt_header`
- `receipt_line`

Without those supporting records:

- stock cannot be traced safely
- on-hand values become unreliable
- PO receiving cannot be partial or auditable
- requisitions and POs become header-only shells with no operational meaning

## Real-World Design Principles

This blueprint follows common enterprise patterns:

- items exist as reusable master data before they are stocked in specific storerooms
- storerooms are operational stock locations tied to sites
- balances are per item plus storeroom, and may later extend to bin, lot, serial, or status dimensions
- requisitions request supply; purchase orders commit external procurement
- receipts can be partial and can happen multiple times against one PO
- on-order and reserved quantities matter alongside physical on-hand
- platform approvals and audit stay shared, while inventory owns the business records

## Core Entities

### 1. `stock_item`

Represents the canonical material or product master used by inventory and purchasing.

Recommended fields for phase 1:

- `id`
- `item_code`
- `name`
- `description`
- `item_type`
- `status`
- `stock_uom`
- `order_uom`
- `issue_uom`
- `category_code`
- `commodity_code`
- `is_stocked`
- `is_purchase_allowed`
- `is_active`
- `default_reorder_policy`
- `min_qty`
- `max_qty`
- `reorder_point`
- `reorder_qty`
- `lead_time_days`
- `is_lot_tracked`
- `is_serial_tracked`
- `shelf_life_days`
- `preferred_party_id`
- `created_at`
- `updated_at`
- `notes`

Important rules:

- `preferred_party_id` references platform `party`
- item identity is module-owned, but supplier identity is platform-owned
- documents are linked through platform document links, not local attachment columns

### 2. `storeroom`

Represents an operational stock-holding location inside a site.

Recommended fields for phase 1:

- `id`
- `storeroom_code`
- `name`
- `description`
- `site_id`
- `status`
- `storeroom_type`
- `is_active`
- `is_internal_supplier`
- `allows_issue`
- `allows_transfer`
- `allows_receiving`
- `default_currency_code`
- `manager_party_id`
- `created_at`
- `updated_at`
- `notes`

Important rules:

- `site_id` references platform `site`
- `manager_party_id` is optional and references platform `party`
- a future link to a maintenance `location` must be by reference only, after Maintenance exists

### 3. `stock_balance`

Represents the current stock position for an item in a storeroom.

Recommended phase-1 fields:

- `id`
- `stock_item_id`
- `storeroom_id`
- `uom`
- `on_hand_qty`
- `reserved_qty`
- `available_qty`
- `on_order_qty`
- `committed_qty`
- `average_cost`
- `last_receipt_at`
- `last_issue_at`
- `reorder_required`
- `updated_at`

Important rules:

- `stock_balance` is the operational balance projection
- `stock_transaction` remains the traceable movement source
- `available_qty` should be derived from balance rules, not edited directly by users

### 4. `purchase_requisition`

Represents an internal request to procure items or replenish inventory.

Recommended phase-1 fields:

- `id`
- `requisition_number`
- `requesting_site_id`
- `requesting_storeroom_id`
- `requester_user_id`
- `status`
- `purpose`
- `needed_by_date`
- `priority`
- `approval_request_id`
- `source_reference_type`
- `source_reference_id`
- `submitted_at`
- `approved_at`
- `cancelled_at`
- `notes`

Recommended statuses:

- `draft`
- `submitted`
- `under_review`
- `approved`
- `rejected`
- `partially_sourced`
- `fully_sourced`
- `cancelled`
- `closed`

Important rules:

- requisitions are demand records
- they do not directly increase stock
- they may later be sourced from internal stock or external PO flow

### 5. `purchase_order`

Represents the external procurement commitment to a supplier or vendor.

Recommended phase-1 fields:

- `id`
- `po_number`
- `site_id`
- `supplier_party_id`
- `status`
- `order_date`
- `expected_delivery_date`
- `currency_code`
- `approval_request_id`
- `submitted_at`
- `approved_at`
- `sent_at`
- `closed_at`
- `cancelled_at`
- `supplier_reference`
- `notes`

Recommended statuses:

- `draft`
- `submitted`
- `approved`
- `sent`
- `partially_received`
- `fully_received`
- `closed`
- `cancelled`

Important rules:

- `supplier_party_id` references platform `party`
- POs are line-based documents; the header is never enough by itself
- receiving must allow multiple partial receipts

## Supporting Operational Records

### `stock_transaction`

This is required in the first real implementation even if it was not in the initial five entities.

Recommended transaction types:

- `opening_balance`
- `receipt`
- `issue`
- `return`
- `transfer_out`
- `transfer_in`
- `adjustment_increase`
- `adjustment_decrease`
- `reservation_hold`
- `reservation_release`

Core fields:

- `id`
- `transaction_number`
- `stock_item_id`
- `storeroom_id`
- `transaction_type`
- `quantity`
- `uom`
- `unit_cost`
- `transaction_at`
- `reference_type`
- `reference_id`
- `performed_by_user_id`
- `notes`

### `stock_reservation`

This should exist in the first real inventory implementation even if reservation creation UI stays simple at first.

Core fields:

- `id`
- `reservation_number`
- `stock_item_id`
- `storeroom_id`
- `reserved_qty`
- `issued_qty`
- `remaining_qty`
- `uom`
- `status`
- `need_by_date`
- `source_reference_type`
- `source_reference_id`
- `requested_by_user_id`
- `created_at`
- `released_at`
- `cancelled_at`
- `notes`

Recommended statuses:

- `active`
- `partially_issued`
- `fully_issued`
- `released`
- `cancelled`

Important rules:

- reservations are inventory-owned supply commitments
- reservations must reference the upstream business demand by `source_reference_type` and `source_reference_id`
- a reservation may reduce `available_qty` without reducing `on_hand_qty`
- a reservation becomes `fully_issued` only when `remaining_qty` reaches zero
- a released or cancelled reservation must return its remaining quantity to availability

### `purchase_requisition_line`

Core fields:

- `id`
- `purchase_requisition_id`
- `line_number`
- `stock_item_id`
- `description`
- `quantity_requested`
- `uom`
- `needed_by_date`
- `estimated_unit_cost`
- `suggested_supplier_party_id`
- `status`
- `notes`

### `purchase_order_line`

Core fields:

- `id`
- `purchase_order_id`
- `line_number`
- `stock_item_id`
- `description`
- `ordered_qty`
- `received_qty`
- `uom`
- `unit_price`
- `currency_code`
- `delivery_site_id`
- `delivery_storeroom_id`
- `line_status`
- `notes`

### `receipt_header`

Core fields:

- `id`
- `receipt_number`
- `purchase_order_id`
- `received_at`
- `received_by_user_id`
- `packing_slip_number`
- `supplier_reference`
- `status`
- `notes`

### `receipt_line`

Core fields:

- `id`
- `receipt_header_id`
- `purchase_order_line_id`
- `stock_item_id`
- `storeroom_id`
- `received_qty`
- `accepted_qty`
- `rejected_qty`
- `uom`
- `unit_cost`
- `notes`

## Quantity, Uniqueness, and Integrity Constraints

These constraints should be treated as first-class business rules, not optional UI checks.

### Quantity Rules

- all business quantities must be positive when entered on lines or transactions unless the transaction type itself encodes the direction
- `on_hand_qty`, `reserved_qty`, `available_qty`, and `on_order_qty` must never be persisted as negative values
- `accepted_qty + rejected_qty` must equal `received_qty` on each `receipt_line`
- `received_qty` on a PO line must never exceed `ordered_qty` unless a later explicit over-receipt rule is introduced
- `reserved_qty` on a reservation must never exceed the available quantity at the time the reservation is committed unless backorder behavior is explicitly added later

### Suggested Uniqueness Rules

- `stock_item.organization_scope + item_code` must be unique in the inventory domain
- `storeroom.organization_scope + storeroom_code` must be unique in the inventory domain
- `purchase_requisition.requisition_number` must be unique
- `purchase_order.po_number` must be unique
- `receipt_header.receipt_number` must be unique
- `(stock_item_id, storeroom_id)` must be unique in `stock_balance`
- `(purchase_requisition_id, line_number)` must be unique in `purchase_requisition_line`
- `(purchase_order_id, line_number)` must be unique in `purchase_order_line`

### Integrity Rules

- every `stock_balance` row must reference an existing `stock_item` and `storeroom`
- every `storeroom.site_id` must resolve through platform `site`
- every supplier or preferred supplier field must resolve through platform `party`
- every document link must resolve through the shared platform document service
- inventory must reject writes that point to inactive or out-of-scope shared references unless an explicit exception rule is defined

## First Shared Integrations

These are mandatory in phase 1.

### `site_id`

- all storerooms belong to a platform `site`
- requisitions and POs reference sites through platform-owned IDs
- inventory must never create a local site table

### `party_id`

- suppliers, vendors, contractors, and service providers come from platform `party`
- inventory can define preferred suppliers and procurement relationships
- inventory must never create a local supplier or vendor master

### `documents`

- item manuals, datasheets, contracts, quotations, and PO attachments use platform document links
- inventory may define why a document matters
- inventory must not create a second document library

### `approvals`

- requisitions and purchase orders use the platform approval engine
- approval thresholds and routing can be inventory-owned policy, but the workflow engine remains platform-owned

### `audit`

- item, storeroom, requisition, PO, and receipt mutations must write to the platform audit trail
- stock transactions are operational records and must remain traceable

## Calculation and Balance Rules

To behave like a real inventory system:

- `on_hand_qty` increases on accepted receipt and adjustment increase
- `on_hand_qty` decreases on issue, transfer out, adjustment decrease, and accepted return to supplier
- `reserved_qty` increases when inventory is committed to demand
- `available_qty` is derived from `on_hand_qty - reserved_qty`
- `on_order_qty` increases when an approved PO is open and not fully received
- `on_order_qty` decreases as receipt lines are posted

Phase 1 should avoid fake balance editing screens.

Users should create business actions:

- receipt
- issue
- transfer
- reservation
- adjustment

The system should update `stock_balance` from those actions.

## UOM Conversion Rule

Phase 1 should support a simple but explicit conversion policy:

- `stock_uom` is the balance authority for `stock_item`
- `order_uom` is the default commercial purchasing unit
- `issue_uom` is the operational consumption unit
- balances should always be persisted in `stock_uom`
- requisition, PO, receipt, issue, and reservation actions may start in another allowed UOM, but must convert to `stock_uom` before balance impact is posted

Recommended implementation rule:

- introduce an item-level UOM conversion table before allowing mixed-UOM transactions in production workflows
- if no conversion exists between the entered UOM and `stock_uom`, the transaction must be rejected
- do not allow ad hoc free-text conversion factors at transaction time

For the first runtime slice:

- either restrict all phase-1 stock-affecting transactions to `stock_uom`
- or support only explicit item-level fixed conversion factors

## Status Transition Rules

The module should lock a small set of valid transitions early so behavior stays predictable.

### `stock_item`

- `draft -> active`
- `active -> inactive`
- `inactive -> active`
- `active -> obsolete`

### `storeroom`

- `draft -> active`
- `active -> inactive`
- `inactive -> active`
- `active -> closed`

### `purchase_requisition`

- `draft -> submitted`
- `submitted -> under_review`
- `under_review -> approved`
- `under_review -> rejected`
- `approved -> partially_sourced`
- `partially_sourced -> fully_sourced`
- `approved -> cancelled`
- `fully_sourced -> closed`

### `purchase_order`

- `draft -> submitted`
- `submitted -> approved`
- `approved -> sent`
- `sent -> partially_received`
- `partially_received -> fully_received`
- `approved -> cancelled`
- `sent -> cancelled`
- `fully_received -> closed`

### `stock_reservation`

- `active -> partially_issued`
- `partially_issued -> fully_issued`
- `active -> released`
- `partially_issued -> released`
- `active -> cancelled`

### `receipt_header`

- `draft -> posted`
- `draft -> cancelled`

Invalid transitions should be rejected explicitly and audited.

## Receipt Acceptance and Rejection Logic

The blueprint should be explicit here because this is where stock integrity usually drifts.

- `received_qty` is what physically arrived
- `accepted_qty` is what is allowed into usable stock
- `rejected_qty` is what failed inspection, quality, or receiving acceptance
- only `accepted_qty` increases `on_hand_qty`
- `rejected_qty` must not increase usable stock
- `purchase_order_line.received_qty` should increase by the full `received_qty` for operational receiving traceability
- if quality-hold inventory is introduced later, rejected or quarantined quantities can move into a separate non-available state rather than disappearing

Phase-1 recommended simplification:

- treat rejected quantity as non-stocked and auditable only
- do not add quarantine subinventory unless QHSE or quality inventory is implemented

## Organization Scoping and Shared Reference Validation

Inventory must apply explicit scope checks from the beginning.

- every inventory record must resolve inside the active organization scope
- `site_id` must belong to the active organization through the platform site service
- `party_id` must belong to the active organization through the platform party service
- cross-site operations must only be allowed when both source and destination are in the same active organization unless intercompany behavior is introduced later
- shared document links must use platform link records that belong to the same active organization context
- inventory services must validate scope on read and write paths, not only in UI selectors

This is especially important because `inventory_procurement` is the first true test of shared-master reuse.

## Business Workflows

### 1. Item Master Flow

- create draft item
- classify and configure stocking behavior
- link preferred supplier and supporting documents
- activate item
- add item to one or more storerooms

### 2. Storeroom Setup Flow

- create storeroom under a platform site
- define internal supplier behavior
- define issue, transfer, and receiving permissions
- optionally seed opening balances

### 3. Purchase Requisition Flow

- create draft requisition
- add one or more requisition lines
- submit for approval
- approve or reject through platform approvals
- convert approved lines into sourcing actions

### 4. Purchase Order Flow

- create PO from approved requisition or direct procurement
- add line pricing and supplier commitment
- submit and approve
- send to supplier
- track partial and full receipts
- close when completed

### 5. Receiving Flow

- create receipt header against PO
- receive one or more lines
- allow partial receipt
- update transaction history
- update stock balances
- reduce on-order quantity

## Basic Domain Event Outputs

Inventory should emit a small but explicit event surface from the start.

Recommended first events:

- `inventory_items_changed`
- `inventory_storerooms_changed`
- `inventory_balances_changed`
- `inventory_reservations_changed`
- `inventory_requisitions_changed`
- `inventory_purchase_orders_changed`
- `inventory_receipts_changed`

Recommended event payload direction:

- emit the primary entity ID
- bridge later into the generic `domain_changed` model just like PM and shared masters do today
- use events for UI refresh and cross-module awareness only
- do not let another module mutate inventory-owned tables directly in place of an event-driven refresh or command call

## UI Plan

Recommended first workspaces:

- `Inventory Dashboard`
- `Items`
- `Storerooms`
- `Stock`
- `Requisitions`
- `Purchase Orders`
- `Receiving`

Recommended first implementation order:

1. `Items`
2. `Storerooms`
3. `Stock` inquiry and transaction history
4. `Requisitions`
5. `Purchase Orders`
6. `Receiving`

Phase-1 UI principle:

- keep list/detail workflows clean and operational
- do not build a generic admin-style CRUD shell only
- show important columns first, hide secondary metadata behind detail views

## Service Boundary Plan

Recommended core service packages:

- `core/modules/inventory_procurement/services/reference_service`
- `core/modules/inventory_procurement/services/item_master`
- `core/modules/inventory_procurement/services/inventory`
- `core/modules/inventory_procurement/services/procurement`
- `core/modules/inventory_procurement/services/receiving`

Recommended responsibilities:

- `reference_service`
  - shared `site` and `party` lookups only
- `item_master`
  - create, activate, classify, and maintain items
- `inventory`
  - storerooms, balances, transactions, reservations, adjustments
- `procurement`
  - requisitions, approvals, sourcing, POs
- `receiving`
  - receipts, accepted or rejected quantities, balance updates

## Implementation Slices

### Slice 1. Shared Reference Consumption

Already started:

- consume platform `site`
- consume platform `party`
- keep no local shared-master copies

### Slice 2. Item and Storeroom Foundations

Build:

- `stock_item`
- `storeroom`
- document linking for items
- item-to-party relationship rules

Exit criteria:

- inventory can create items
- inventory can create storerooms under platform sites
- inventory can link items to shared parties and documents

### Slice 3. Stock Transaction and Balance Core

Build:

- `stock_transaction`
- `stock_balance`
- opening balance
- adjustment
- receipt-to-balance update logic

Exit criteria:

- balances are updated by transactions, not direct edits
- transaction history explains current stock position

### Slice 4. Requisition and Approval Flow

Build:

- `purchase_requisition`
- `purchase_requisition_line`
- approval integration

Exit criteria:

- requisitions move through draft, submit, approve, reject
- audit and approvals are platform-owned but inventory-owned in meaning

### Slice 5. Purchase Order and Receiving Flow

Build:

- `purchase_order`
- `purchase_order_line`
- `receipt_header`
- `receipt_line`

Exit criteria:

- approved demand can become a PO
- PO receiving can be partial
- receipts update on-order and on-hand correctly

### Slice 6. Maintenance Integration

Build later:

- maintenance demand references inventory items and storerooms
- maintenance reservations and PO demand use inventory-owned records by reference

Exit criteria:

- no stock ledger exists inside Maintenance
- maintenance consumes inventory through IDs, business keys, and events only

## First Acceptance Criteria

Inventory phase 1 should be considered valid only if all of the following are true:

- there is no local supplier table
- there is no local site table
- documents use platform document links
- requisitions and POs use platform approvals
- inventory mutations are written to platform audit
- item and storeroom writes stay inside the inventory module
- balances come from inventory-owned transaction logic
- future maintenance integration can reference inventory without owning stock logic

## Sources Used To Ground This Plan

This plan was aligned with patterns shown in official product documentation, including:

- IBM Maximo item master and storeroom usage:
  - https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=items-item-master
  - https://www.ibm.com/support/knowledgecenter/SS8CCV/com.ibm.mbs.doc/storeroom/t_use_storerooms_pos_prs.html
- Microsoft Dynamics 365 requisition, purchase-order, receiving, and on-hand behaviors:
  - https://learn.microsoft.com/en-us/dynamics365/unified-operations/supply-chain/procurement/purchase-requisitions-overview
  - https://learn.microsoft.com/en-us/dynamics365/supply-chain/procurement/purchase-order-creation
  - https://learn.microsoft.com/en-us/dynamics365/supply-chain/procurement/product-receipt-against-purchase-orders
  - https://learn.microsoft.com/en-us/dynamics365/supply-chain/inventory/inventory-on-hand-list

These sources reinforce the design choices above:

- item master separated from storeroom stock
- storerooms participating in requisition and PO flow
- partial receipts against a PO
- on-hand, reserved, available, and on-order views
- supplier and site references treated as existing enterprise masters rather than duplicated local records
