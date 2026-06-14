---
name: project-activity-audit-split
description: Architecture plan for splitting current AuditService into Activity (user-facing UI feed) and Audit (compliance ledger). Plan at docs/ACTIVITY_AUDIT_SECURITY_ROADMAP.md. Awaiting approval before implementation.
metadata:
  type: project
---

Plan created at `docs/ACTIVITY_AUDIT_SECURITY_ROADMAP.md` (2026-06-14). Implementation NOT started — awaiting approval.

**Core decision:** Current `audit_logs` table serves both UI activity feeds and security/compliance events. These must be split.

**Database:** Option B — keep `audit_logs` intact, create new `activity_entries` (business ops) and `audit_entries` (compliance/security) tables. Backfill, then drop `audit_logs` last.

**Key classifications:**
- Activity: task.create/update, project ops, inventory ops, resource ops, cost ops — all business module operations
- Audit: auth.login/logout/failed_login, role/permission changes, approval decisions, user admin ops
- Borderline → Audit: site.create/update, department.create/update (admin settings)

**Do NOT rename** `AdminAuditSection.qml` — platform admin keeps "Audit" label.
**Do NOT show** Audit records in PM/Inventory/Maintenance normal workspaces.

**Phase order:** Discovery → Docs Review → Activity Foundation → Remove Audit Labels → Enterprise Audit → RBAC Decorators → DB Migrations → Tests

**Why:** [[user-profile]]
