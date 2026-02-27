# UI Governance Module

`ui/governance/` provides an approval queue for governed operations.

## File

- `tab.py`

## `GovernanceTab` Responsibilities

- list approval requests by status
- display request metadata and human-readable change summaries
- approve and apply request payloads
- reject requests with optional note
- switch governance mode (`off` vs `required`) when authorized

## Dependencies

- `ApprovalService`
- `ProjectService`
- optional:
  - `TaskService`
  - `CostService`
- `MainWindowSettingsStore` for persistence of governance mode

## Governance Mode UX

- mode selector persists state and updates `PM_GOVERNANCE_MODE`.
- switching mode provides explicit user feedback.
- mode change requires `settings.manage`.

## Decision Permissions

- approval and rejection actions require `approval.decide`.
- users without decide permission can still view queue content.

## Queue Rendering

Request rows include:

- request timestamp
- status
- request type
- computed change summary
- project label
- requester
- decision note

Change summary generation interprets request payload by type:

- baseline.create
- dependency.add/remove
- cost.add/update/delete

## Event Synchronization

- subscribes to `domain_events.approvals_changed` and reloads queue automatically.
