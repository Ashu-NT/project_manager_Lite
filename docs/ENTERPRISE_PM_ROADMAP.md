# Enterprise PM Roadmap

## Scope

This roadmap tracks the remaining enterprise work that still belongs to the
`Project Management` module itself.

Primary PM-focused enterprise areas:

- `Access` as it affects PM delivery work and project-scoped memberships
- `Collaboration` for inbox, mentions, recent task activity, and PM team
  coordination
- `Portfolio` for intake, scenario planning, and budget/capacity evaluation

This document does not own:

- platform security and identity controls such as SSO, MFA, and session
  revocation
- module-level payroll implementation
- future module work for Maintenance Management or QHSE
- hosted API/router delivery planning

Those are now tracked in:

- `docs/ENTERPRISE_RBAC_MATRIX.md`
- `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`
- `docs/module_licensing/README.md`

## Architecture

The implementation is split by feature and layer to keep boundaries clear:

- `core/platform/access`
- `core/modules/project_management/services/collaboration`
- `core/modules/project_management/services/portfolio`
- `infra/platform/db/access`
- `infra/modules/project_management/db/collaboration`
- `infra/modules/project_management/db/portfolio`
- `ui/platform/admin/access`
- `ui/modules/project_management/collaboration`
- `ui/modules/project_management/portfolio`

## Phase 1: Delivered

Status: implemented in this repo

- Added user lockout/session metadata to the auth domain and persistence model
- Added project-scoped membership domain objects, repositories, and service orchestration
- Enforced scoped permissions across project, task, register, cost, reporting, baseline, dashboard, and finance paths
- Added dedicated main-window workspaces for Access, Collaboration, and Portfolio
- Split register, timesheet, audit, support, collaboration, and portfolio UI permissions onto dedicated permission codes
- Added a migration for new auth/access/portfolio tables and columns
- Expanded global RBAC into enterprise-ready role templates including `access_admin`, `security_admin`, `payroll_manager`, `portfolio_manager`, and `approver`
- Canonicalized project-scoped roles to `viewer`, `contributor`, `lead`, and `owner` with legacy `editor` compatibility
- Opened read-only identity visibility via `auth.read` and isolated unlock/session operations behind `security.manage`
- Added payroll-ready permission boundaries so the future payroll module can ship without reusing broad finance/admin permissions

## Phase 2: PM Follow-Ups

Status: in progress

Priority: high

- Extend notification delivery beyond the in-app feed for mentions, approvals, and locked periods
- Add presence indicators and broader concurrent-edit UX on top of the desktop optimistic-lock checks now wired into PM edit flows
- Add project demand scoring templates configurable by PMO admins

Delivered in this phase already:

- Added PM in-app notifications in the Collaboration workspace for mentions, approval activity, and timesheet workflow updates
- Added project-scoped notification filtering so mixed-project timesheet activity does not leak inaccessible project names
- Finished PM task runtime adoption of the collaboration service, with the task workspace and collaboration dialog now using the service-backed path by default
- Added side-by-side saved portfolio scenario comparison in the portfolio service and UI
- Wired desktop project/task/resource/cost edit actions to pass `expected_version` so stale writes are rejected in normal PM edit flows

## Phase 3: PM Hardening

Status: pending

Priority: medium

- Portfolio capacity heatmaps and cross-project dependency visualizations
- Audit reports for membership changes and privileged account actions

## Cross-Cutting Dependencies

These affect PM, but they are not PM-owned roadmap items anymore:

- `Platform security`
  - SSO and MFA hooks
  - session revocation
  - forced password reset
  - suspicious login reporting
  - tracked under `docs/ENTERPRISE_RBAC_MATRIX.md`
- `Payroll module`
  - dedicated payroll workspace and service layer
  - payroll periods, run states, exceptions, exports, and approvals
  - tracked under `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md` and
    `docs/ENTERPRISE_RBAC_MATRIX.md`
- `External integrations`
  - public API and webhook layer
  - Jira, Excel, Teams, and directory sync
  - tracked as broader platform work in
    `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`

## Recommended Build Order

1. Add presence indicators and richer concurrent-edit UX around stale-write recovery.
2. Add PMO scoring templates.
3. Add PM-facing heatmaps, cross-project views, and audit reporting.
4. Extend notification delivery beyond the in-app feed.

## Current PM-Specific Remainder

If we ignore platform/security and future-module work, the remaining enterprise
PM backlog is:

- richer notification delivery beyond the in-app feed
- presence indicators and richer concurrent-edit recovery
- PMO scoring template configuration
- PM-facing audit and executive visualization polish
