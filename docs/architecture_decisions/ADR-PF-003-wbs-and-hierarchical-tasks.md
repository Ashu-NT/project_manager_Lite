# ADR-PF-003: WBS and Hierarchical Tasks

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase B planned-cost and budget dimensions

## Context

Current Tasks belong to Projects but have no parent/child hierarchy, WBS code, work-package behavior, or cost rollup. Cost code describes what a cost is; WBS describes where project work/cost occurs. Duplicating Task and WorkPackage hierarchies would create synchronization risk unless the product needs non-schedulable financial work packages.

## Decision

- Recommended first implementation: PM Tasks own the WBS hierarchy through optional parent Task, project-unique WBS code, cycle prevention, ordering, and summary/leaf semantics.
- A summary Task acts as a work package; schedulable leaf Tasks remain execution units.
- Project Finance references Task/WBS IDs and rolls up descendants but does not own hierarchy mutations.
- Cost codes remain a separate classification dimension.
- A separate WorkPackage aggregate is deferred until a confirmed requirement needs financial WBS nodes that cannot be represented as Tasks.

## Alternatives Rejected

- Treat existing flat Tasks as complete WBS: no hierarchy or code currently exists.
- Use cost-code hierarchy as WBS: conflates where with what.
- Create a second hierarchy immediately: adds synchronization and UX complexity without proven need.

## Consequences

Task cycle, cross-project parent, move/recode, descendant rollup, and summary scheduling rules must be explicit. QML Tasks/Scheduling become hierarchy-aware before finance relies on WBS rollups.

## Migration Impact

Existing Tasks become root/leaf nodes. WBS codes are assigned deterministically under a reviewed policy; current financial rows may remain project/task scoped until mapping completes.

## Test Impact

Add hierarchy cycle, cross-tenant/project parent, ordering, move/recode, descendant rollup, deletion/archive, and finance-dimension tests.
