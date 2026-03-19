# ADR-002: Maintenance Owns Location and System

- Status: accepted
- Date: 2026-03-19

## Context

After ADR-001, one ownership ambiguity was still worth freezing before `inventory_procurement` and `maintenance_management` grow further:

- should `platform` own a shared `location` master
- or should `maintenance_management` own both `location` and `system`

The current codebase already has a clear platform-owned organization spine:

- `organization`
- `site`
- `department`
- `employee`

That shared spine is broad enough for enterprise identity, access scope, workplace context, and shared master reuse.

What remained undecided was whether the product also needed a second generic cross-platform place hierarchy called `location`.

## Decision

`maintenance_management` owns both `location` and `system`.

`platform` does **not** introduce a second shared `location` master.

The frozen split is:

- `platform` owns enterprise-wide shared references such as `organization`, `site`, `department`, `employee`, `party`, and shared document infrastructure
- `maintenance_management` owns the operational physical hierarchy used for maintenance execution: `location`, `system`, `asset`, and related work history

## Why

This is the cleaner enterprise boundary for this codebase:

- `site` already provides the shared enterprise placement anchor
- maintenance `location` is operational and domain-specific, not a generic enterprise master
- maintenance `system` is also operational and only makes sense inside the maintenance domain
- introducing a platform-wide `location` now would create a second quasi-platform hierarchy that future modules would be pressured to reuse even when the semantics do not fit
- the safer pattern is: share broad enterprise references once, keep operational hierarchies in the business module that owns them

## Rules

- `maintenance_management` owns the canonical `location` records
- `maintenance_management` owns the canonical `system` records
- `location` and `system` are referenced by other modules only through stable IDs or business keys once the maintenance module exists
- `platform` may keep generic address and site metadata, but it must not become the owner of the maintenance operational hierarchy
- `inventory_procurement` owns `storeroom` and stock operating structures, not maintenance `location`
- if `inventory_procurement` needs physical placement context, it references:
  - platform `site`
  - maintenance `location` only when the maintenance hierarchy is the right operational anchor
- `project_management`, `qhse`, and `hr_management` must not create their own shadow `location` or `system` masters

## Consequences

- future maintenance implementation should create `location` and `system` under:
  - `core/modules/maintenance_management`
  - `infra/modules/maintenance_management`
  - `ui/modules/maintenance_management`
- future inventory implementation should continue using shared `site` and `party` from the platform spine
- if inventory later needs storeroom-to-maintenance-location linkage, that linkage must be by reference, not by duplicated ownership
- no further platform-level `location` design should proceed unless a new ADR explicitly changes this rule
