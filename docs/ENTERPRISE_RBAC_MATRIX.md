# Enterprise RBAC Matrix

## Goal

This matrix moves the app from a small-role RBAC model to an enterprise-ready foundation with:

- separated platform, PMO, finance, and HR/payroll responsibilities
- canonical project-scoped roles
- read-only identity access separate from identity mutation
- payroll-ready permissions for the future HR Management module

## Status Snapshot

Delivered:

- enterprise role templates and canonical project-scoped roles
- payroll-ready permission codes
- read-only identity visibility split from mutation/security operations
- access/security separation in the admin surfaces
- explicit bootstrap-admin password requirements and forced-password-change flags for first-run admin creation
- repo-backed session validation plus `security.manage` session revocation controls
- federated identity linking and MFA enrollment/verification hooks in shared auth
- per-user session-timeout policy plus session-revision invalidation controls
- true non-project scoped access persistence with first live `storeroom` scope grants
- first separation-of-duties guardrails for conflicting approval and access/security permission combinations
- a platform-owned authorization engine seam so future web-policy and ABAC-style adapters have one integration point

Pending:

- HR Management feature slice implementation
- broader configurable separation-of-duties policy beyond the delivered core conflicts
- stronger `security.manage` capabilities such as hosted SSO adapters, external IdP provisioning, and richer device/session posture governance
- deeper non-project scope adoption beyond `storeroom`, especially asset and maintenance-area controls

## Global Roles

| Role | Purpose | Key permissions |
| --- | --- | --- |
| `viewer` | Read-only delivery visibility | `project.read`, `task.read`, `report.view`, `collaboration.read` |
| `team_member` | Collaboration + time submission | viewer + `collaboration.manage`, `timesheet.submit` |
| `planner` | Delivery planning and governed change requests | team_member + `project.manage`, `task.manage`, `baseline.manage`, `approval.request` |
| `project_manager` | Delivery ownership with schedule/cost control | planner + `cost.manage`, `finance.read`, `finance.export`, `timesheet.approve` |
| `resource_manager` | Staffing and capacity administration | `resource.manage`, `timesheet.approve`, `timesheet.lock`, `report.export` |
| `finance_controller` | Cost and finance administration | `finance.read`, `finance.manage`, `finance.export`, `cost.manage`, `payroll.read` |
| `payroll_manager` | Payroll preparation and release | `payroll.read`, `payroll.manage`, `payroll.approve`, `payroll.export`, `timesheet.approve`, `timesheet.lock` |
| `portfolio_manager` | Intake and scenario planning | `portfolio.read`, `portfolio.manage`, `approval.request`, `report.export` |
| `approver` | Governance approvals without broad edit power | `approval.decide`, `finance.read`, `payroll.read`, `portfolio.read` |
| `auditor` | Audit and operational review | `audit.read` plus read-only delivery, finance, payroll, and portfolio visibility |
| `access_admin` | Project membership administration | `access.manage`, `auth.read`, `project.read`, `audit.read` |
| `security_admin` | Login security and lockout/session administration | `security.manage`, `auth.read`, `audit.read`, `settings.manage` |
| `support_admin` | Product support triage and diagnostics | `support.manage`, `auth.read`, `audit.read`, core read visibility |
| `admin` | Full platform control | all permissions |

Compatibility roles kept in place:

- `finance` remains as an alias-style legacy role mapped to the `finance_controller` permission set.
- `viewer`, `planner`, and `admin` keep their original names so older UI/tests and seeded data stay valid.

## Project-Scoped Roles

Canonical project membership roles:

- `viewer`: project/task/report/register visibility
- `contributor`: viewer + task updates, collaboration posts, timesheet submission
- `lead`: contributor + baseline, register, cost, and export control inside the project
- `owner`: lead + project management, timesheet approval, and lock control

Legacy scope compatibility:

- stored or requested `editor` memberships resolve to `contributor`

## Payroll-Ready Permission Set

The HR Management module should build on these dedicated payroll permissions:

- `payroll.read`
- `payroll.manage`
- `payroll.approve`
- `payroll.export`

This keeps payroll separate from generic finance admin and supports segregation of duties:

- finance can review payroll inputs without releasing payroll
- payroll can prepare/release runs without broad identity or project admin rights
- approvers can review payroll outcomes without mutating payroll setup

## Concrete Next Plan

1. Move session governance from the current user-row session markers to a true per-session model for future desktop + web deployments.
2. Add hosted SSO adapter seams and IdP-provisioning workflows on top of the delivered federated identity model.
3. Expand the scoped-access policy registry and persistence layer to asset, maintenance-area, and other non-project scopes.
4. Move separation-of-duties from fixed guardrails to a configurable enterprise policy matrix.
5. Add richer Security workspace actions for password reset, MFA state inspection/reset, and federated-account lifecycle.
6. Add a dedicated `hr_management` feature slice that consumes the delivered payroll-ready permissions.

## Follow-Ups

- add role descriptions and search/filtering in the Users admin workspace
- add broader deny rules / configurable separation-of-duties checks beyond the delivered baseline conflicts
- add hosted SSO rollout, IdP provisioning, and stronger device/session governance so `security.manage` grows beyond lockout + revocation + timeout policy
- add payroll-specific reports, payslip exports, and ERP/journal integration once the HR Management module lands
