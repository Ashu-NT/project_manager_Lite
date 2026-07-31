# ADR-003 Operational Evidence Runbook

Status: Tooling implemented; execution and archival remain required per deployed environment.

Lifecycle: `RBAC-TRANSITION-ONLY`. Archive the verifier version and digest with the final
promotion evidence, then remove product-runtime verifier code under the README decommission
gate. Preserve generated receipts for their approved retention period.

This runbook operationalizes the backup, restore, rollback, retention, approval, inventory, and
policy evidence required by
[ADR-003](../architecture_decisions/ADR-003-tenancy-and-authorization-authority.md).
It does not promote authorization mode, create or restore a database backup, approve a change,
or replace a deployment change-management system.

## Ownership

| Evidence | Accountable owner |
| --- | --- |
| Encrypted immutable backup and restore rehearsal | Platform Operations |
| Binding classification, mismatch acceptance, and retention approval | Security |
| Inventory, policy artifacts, verifier, rollback replay, and test results | Application Engineering |
| Authority-mode promotion | Independent Operations and Security approvers |

The Operations and Security approvers must be different people. Evidence artifacts can contain
opaque user, tenant, role, binding, and session identifiers, so they belong in the controlled
deployment evidence store and must not be committed to source control.

## Safety Rules

- Run inventory and verification with read-only access.
- Never place passwords, MFA codes, tokens, database URLs, connection strings, recovery codes,
  private keys, or signed storage URLs in artifacts or manifests.
- Use interactive credential entry for reconciliation where possible. Environment-provided
  credentials are process inputs only and must not be captured in shell history or evidence.
- Never overwrite an evidence artifact. The supplied CLIs use exclusive file creation.
- Never infer backup immutability or human approval from application state. The verifier checks
  declared evidence consistency; accountable reviewers attest the external facts.
- Never promote by changing `PM_AUTHORIZATION_MIGRATION_MODE` alone. Reserved modes continue to
  fail startup until their runtime behavior and transition gates are implemented.

## Before-Change Evidence

Create a change ticket and an evidence directory in the access-controlled external store. Record
the environment ID, application version, current database revision, tenancy mode, current
authorization mode, and intended next mode.

Platform Operations creates an encrypted immutable backup using the database platform's native
tooling. Record its external reference and SHA-256 digest. Do not copy database credentials into
the manifest.

Create the read-only tenancy/RBAC inventory:

```powershell
python -m tools.inventory_tenancy_rbac `
  --output <evidence-store>\before-inventory.json `
  --fail-on high
```

Create the reviewed policy-v2 dry-run artifact. This command does not apply the policy:

```powershell
python -m tools.reconcile_role_policy `
  --output <evidence-store>\policy-preview.json
```

If the inventory exits non-zero, classify every high or critical finding. Do not suppress the
threshold merely to continue. If the preview reports missing definitions, unexpected drift, or
a version newer than the application, stop the change.

## Rehearsals

Restore the declared backup into a separate non-production environment and verify:

- the restored database revision equals the manifest revision
- the restored backup digest equals the declared backup digest
- migrations and the authorization test matrix pass against the deployed database engine
- the restored environment cannot send production notifications or reach production services

Rehearse rollback from the intended next mode to the current mode. The evidence must show:

- transactional legacy/canonical replay remained current for the rollback point
- affected sessions were revoked or rebuilt
- the before/after inventories and authorization decisions matched the accepted rollback state
- changing only an environment variable was not treated as data rollback

Record external restore and rollback evidence references. Set `passed`, `replay_tested`, and
`session_rebuild_tested` to `true` only after the accountable owner reviews the result.

## Retention And Approval

Security records the approved retention policy:

- at least 2,555 days for platform-owner, support-access, policy-reconciliation, migration,
  promotion, and quarantine evidence
- at least 400 days for other authorization and membership security evidence

The manifest's retention approver must be the same person as its Security approver. Platform
Operations and Security then approve the exact ticket, inventory hash, policy hash, backup
digest, and intended one-step transition.

## Manifest Verification

Create a `pre_apply` JSON manifest in the external evidence store with these top-level fields:

```json
{
  "schema_version": 1,
  "stage": "pre_apply",
  "environment_id": "production-eu-1",
  "deployment_environment": "production",
  "tenancy_mode": "saas",
  "generated_at": "2026-07-31T12:00:00+00:00",
  "change_ticket": "SEC-2026-0042",
  "application_version": "2.1.1",
  "database_revision": "8b3c4d5e6f7a",
  "current_mode": "LEGACY_AUTHORITATIVE",
  "target_mode": "CANONICAL_SHADOW",
  "backup": {},
  "before_inventory": {},
  "policy_preview": {},
  "restore_rehearsal": {},
  "rollback_rehearsal": {},
  "audit_retention": {},
  "approvals": []
}
```

The strict Pydantic schema rejects unknown fields, invalid hashes, naive timestamps, transition
skips, insufficient retention, same-person approval, production restore into the source
environment, inconsistent backup/revision/version claims, and sensitive-looking keys.

Verify it offline and write an immutable verification receipt:

```powershell
python -m tools.verify_authorization_transition_evidence `
  <evidence-store>\transition-pre-apply.json `
  --expected-environment production-eu-1 `
  --output <evidence-store>\transition-pre-apply-verification.json
```

`ready_for_review` means the manifest and local artifacts are internally consistent. It is not
automatic approval and does not make a reserved authorization mode operational.

## Deliberate Policy Apply

Policy reconciliation is separate from authority-mode promotion. Apply only the exact version and
hash reviewed in `policy-preview.json`:

```powershell
python -m tools.reconcile_role_policy `
  --apply `
  --expected-version <reviewed-current-version> `
  --expected-hash <reviewed-change-set-sha256> `
  --rollback-output <evidence-store>\policy-rollback.json `
  --output <evidence-store>\policy-apply-receipt.json
```

The apply transaction persists the policy ledger and invalidates affected sessions. The CLI
creates the rollback artifact before applying and, after a successful commit, creates a separate
receipt binding the applied hash and versions to the rollback artifact SHA-256.

After apply, create a new read-only inventory. Change the manifest stage to `post_apply` and add:

- `policy_apply.receipt`
- `policy_apply.rollback_artifact`
- the applied change-set hash and versions
- `post_inventory`

Run the verifier again and archive the post-apply verification receipt. If receipt creation
fails after database commit, stop promotion and recover evidence from the durable reconciliation
ledger before retrying any deployment step. Never reapply blindly.

## Completion Boundary

This tooling completes the repository-side evidence contract. Phase 0 remains in progress until
every deployed environment has externally archived:

- before and after inventories
- immutable backup metadata and successful restore rehearsal
- rollback rehearsal evidence
- retention approval
- independent Operations and Security approvals
- policy preview, rollback, apply receipt, and verification receipts
- hosted PostgreSQL migration and isolation test evidence where applicable
