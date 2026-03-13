# Enterprise PM Roadmap

## Scope

This roadmap covers the three enterprise workspaces added in this phase:

- `Access`: enterprise permissions, project-scoped memberships, account lockout visibility
- `Collaboration`: inbox, mentions, recent task activity
- `Portfolio`: intake, scenario planning, budget/capacity evaluation

## Architecture

The implementation is split by feature and layer to keep boundaries clear:

- `core/services/access`
- `core/services/collaboration`
- `core/services/portfolio`
- `infra/db/access`
- `infra/db/collaboration`
- `infra/db/portfolio`
- `ui/access`
- `ui/collaboration`
- `ui/portfolio`

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

## Phase 2: Next Follow-Ups

Priority: high

- Move task collaboration UI fully behind the new collaboration service contract
- Add email/in-app notification delivery for mentions, approvals, and locked periods
- Add edit conflict handling and presence indicators for concurrent task updates
- Add richer portfolio scenario comparison with side-by-side saved scenarios
- Add project demand scoring templates configurable by PMO admins
- Add a dedicated payroll workspace and service layer using the shipped `payroll.*` permission set

## Phase 3: Hardening

Priority: medium

- SSO and MFA hooks for enterprise identity providers
- Session revocation, forced password reset, and suspicious login reporting
- Portfolio capacity heatmaps and cross-project dependency visualizations
- Audit reports for membership changes and privileged account actions
- Public API and webhook layer for Jira, Excel, Teams, and directory sync

## Recommended Build Order

1. Finish notification delivery and collaboration service adoption in task dialogs.
2. Add payroll domain objects, workflows, and admin tooling on top of the new RBAC matrix.
3. Expand portfolio scoring and scenario comparison.
4. Add integrations and external identity hooks.
