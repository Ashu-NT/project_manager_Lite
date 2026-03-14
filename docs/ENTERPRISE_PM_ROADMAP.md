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

Delivered in this phase already:

- Added PM in-app notifications in the Collaboration workspace for mentions, approval activity, and timesheet workflow updates
- Extended PM notification delivery into the task workspace header so workflow alerts are visible outside the Collaboration inbox
- Added project-scoped notification filtering so mixed-project timesheet activity does not leak inaccessible project names
- Finished PM task runtime adoption of the collaboration service, with the task workspace and collaboration dialog now using the service-backed path by default
- Added side-by-side saved portfolio scenario comparison in the portfolio service and UI
- Added configurable PMO scoring templates with active-template selection and template-driven intake scoring
- Wired desktop project/task/resource/cost edit actions to pass `expected_version` so stale writes are rejected in normal PM edit flows
- Added desktop stale-write recovery for project, task, resource, and cost edits so the latest rows are reloaded instead of trapping users in stale dialogs
- Added task presence indicators in PM collaboration and task workspace flows so active editing/reviewing sessions are visible

## Phase 3: PM Hardening

Status: in progress

Priority: medium

Pending:

- Cross-project dependency visualization once PM either supports cross-project task links or introduces a dedicated portfolio-level dependency concept

Delivered in this phase already:

- Added a portfolio executive heatmap for late-task, critical-task, utilization, and cost-variance pressure across accessible projects
- Added a recent PM action summary so portfolio users can review time-period and delivery changes without leaving the portfolio workspace

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

1. Decide whether cross-project dependency visualization should come from true cross-project task links or from a new portfolio-level dependency model.

## Current PM-Specific Remainder

If we ignore platform/security and future-module work, the remaining enterprise
PM backlog is:

- cross-project dependency visualization once PM has a model that supports it
