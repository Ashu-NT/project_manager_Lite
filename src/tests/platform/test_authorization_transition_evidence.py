from __future__ import annotations

# RBAC-TRANSITION-ONLY: Delete with the transition-evidence verifier.

import hashlib
import json
from pathlib import Path

import pytest

from src.infra.security import (
    AuthorizationTransitionEvidenceError,
    verify_authorization_transition_evidence,
)
from tools.verify_authorization_transition_evidence import main as verify_main


_INVENTORY_HASH = "a" * 64
_BACKUP_HASH = "b" * 64
_POLICY_HASH = "c" * 64


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _policy_payload(mode: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": "2026-07-31T09:00:00+00:00",
        "mode": mode,
        "application_version": "2.1.1",
        "runtime_security": {
            "deployment_environment": "production",
            "tenancy_mode": "saas",
            "authorization_migration_mode": "LEGACY_AUTHORITATIVE",
        },
        "plan": {
            "change_set_hash": _POLICY_HASH,
            "current_version": 1,
            "target_version": 2,
        },
    }


def _build_manifest(
    tmp_path: Path,
    *,
    stage: str = "pre_apply",
) -> Path:
    before_path = tmp_path / "before-inventory.json"
    preview_path = tmp_path / "policy-preview.json"
    before_sha256 = _write_json(
        before_path,
        {
            "snapshot_sha256": _INVENTORY_HASH,
            "snapshot": {
                "database": {
                    "alembic_revisions": ["8b3c4d5e6f7a"],
                }
            },
        },
    )
    preview_sha256 = _write_json(preview_path, _policy_payload("dry-run"))

    manifest: dict[str, object] = {
        "schema_version": 1,
        "stage": stage,
        "environment_id": "production-eu-1",
        "deployment_environment": "production",
        "tenancy_mode": "saas",
        "generated_at": "2026-07-31T12:00:00+00:00",
        "change_ticket": "SEC-2026-0042",
        "application_version": "2.1.1",
        "database_revision": "8b3c4d5e6f7a",
        "current_mode": "LEGACY_AUTHORITATIVE",
        "target_mode": "CANONICAL_SHADOW",
        "backup": {
            "reference": "vault://backups/production-eu-1/before-shadow",
            "sha256": _BACKUP_HASH,
            "created_at": "2026-07-31T08:00:00+00:00",
            "database_revision": "8b3c4d5e6f7a",
            "application_version": "2.1.1",
            "encrypted": True,
            "immutable": True,
        },
        "before_inventory": {
            "artifact": {
                "path": before_path.name,
                "sha256": before_sha256,
            },
            "snapshot_sha256": _INVENTORY_HASH,
        },
        "policy_preview": {
            "artifact": {
                "path": preview_path.name,
                "sha256": preview_sha256,
            },
            "change_set_hash": _POLICY_HASH,
            "current_version": 1,
            "target_version": 2,
        },
        "restore_rehearsal": {
            "passed": True,
            "completed_at": "2026-07-31T09:30:00+00:00",
            "environment_id": "rehearsal-eu-1",
            "deployment_environment": "test",
            "evidence_reference": "evidence://SEC-2026-0042/restore",
            "backup_sha256": _BACKUP_HASH,
            "restored_database_revision": "8b3c4d5e6f7a",
        },
        "rollback_rehearsal": {
            "passed": True,
            "completed_at": "2026-07-31T10:00:00+00:00",
            "evidence_reference": "evidence://SEC-2026-0042/rollback",
            "from_mode": "CANONICAL_SHADOW",
            "to_mode": "LEGACY_AUTHORITATIVE",
            "replay_tested": True,
            "session_rebuild_tested": True,
        },
        "audit_retention": {
            "policy_reference": "policy://security/audit-retention-v3",
            "approved_at": "2026-07-31T10:30:00+00:00",
            "approved_by": "security-reviewer-1",
            "privileged_retention_days": 2555,
            "authorization_retention_days": 400,
        },
        "approvals": [
            {
                "role": "platform_operations",
                "approver_id": "operations-reviewer-1",
                "approved_at": "2026-07-31T11:00:00+00:00",
                "evidence_reference": "ticket://SEC-2026-0042/operations",
            },
            {
                "role": "security",
                "approver_id": "security-reviewer-1",
                "approved_at": "2026-07-31T11:15:00+00:00",
                "evidence_reference": "ticket://SEC-2026-0042/security",
            },
        ],
    }

    if stage == "post_apply":
        rollback_path = tmp_path / "policy-rollback.json"
        rollback_sha256 = _write_json(
            rollback_path,
            {"reviewed_plan": {"change_set_hash": _POLICY_HASH}},
        )
        receipt_path = tmp_path / "policy-apply-receipt.json"
        receipt_payload = _policy_payload("apply")
        receipt_payload["generated_at"] = "2026-07-31T11:30:00+00:00"
        receipt_payload["result"] = {
            "applied": True,
            "change_set_hash": _POLICY_HASH,
            "from_version": 1,
            "to_version": 2,
            "rollback_artifact_sha256": rollback_sha256,
        }
        receipt_sha256 = _write_json(receipt_path, receipt_payload)
        post_path = tmp_path / "post-inventory.json"
        post_snapshot_hash = "d" * 64
        post_sha256 = _write_json(
            post_path,
            {
                "snapshot_sha256": post_snapshot_hash,
                "snapshot": {
                    "database": {
                        "alembic_revisions": ["8b3c4d5e6f7a"],
                    }
                },
            },
        )
        manifest["policy_apply"] = {
            "receipt": {
                "path": receipt_path.name,
                "sha256": receipt_sha256,
            },
            "rollback_artifact": {
                "path": rollback_path.name,
                "sha256": rollback_sha256,
            },
            "applied_at": "2026-07-31T11:30:00+00:00",
            "change_set_hash": _POLICY_HASH,
            "from_version": 1,
            "to_version": 2,
        }
        manifest["post_inventory"] = {
            "artifact": {
                "path": post_path.name,
                "sha256": post_sha256,
            },
            "snapshot_sha256": post_snapshot_hash,
        }

    manifest_path = tmp_path / "transition-evidence.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _read_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rewrite_manifest(path: Path, payload: dict[str, object]) -> None:
    _write_json(path, payload)


def test_pre_apply_manifest_verifies_all_operational_gates(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)

    result = verify_authorization_transition_evidence(
        manifest_path,
        expected_environment_id="production-eu-1",
    )

    assert result["status"] == "ready_for_review"
    assert result["stage"] == "pre_apply"
    assert result["transition"] == {
        "from": "LEGACY_AUTHORITATIVE",
        "to": "CANONICAL_SHADOW",
    }
    assert result["gates"]["two_person_approval"] is True
    assert set(result["verified_artifacts"]) == {
        "before_inventory",
        "policy_preview",
    }


def test_post_apply_manifest_binds_receipt_rollback_and_inventory(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path, stage="post_apply")

    result = verify_authorization_transition_evidence(manifest_path)

    assert result["stage"] == "post_apply"
    assert set(result["verified_artifacts"]) == {
        "before_inventory",
        "policy_apply_receipt",
        "policy_preview",
        "policy_rollback",
        "post_inventory",
    }


def test_evidence_verifier_rejects_artifact_tampering(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    (tmp_path / "policy-preview.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        AuthorizationTransitionEvidenceError,
        match="Policy preview artifact SHA-256 does not match",
    ):
        verify_authorization_transition_evidence(manifest_path)


def test_manifest_rejects_retention_below_adr_minimum(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["audit_retention"]["authorization_retention_days"] = 399
    _rewrite_manifest(manifest_path, manifest)

    with pytest.raises(
        AuthorizationTransitionEvidenceError,
        match="greater than or equal to 400",
    ):
        verify_authorization_transition_evidence(manifest_path)


def test_manifest_requires_independent_operations_and_security_approvers(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["approvals"][1]["approver_id"] = "operations-reviewer-1"
    manifest["audit_retention"]["approved_by"] = "operations-reviewer-1"
    _rewrite_manifest(manifest_path, manifest)

    with pytest.raises(
        AuthorizationTransitionEvidenceError,
        match="must be different people",
    ):
        verify_authorization_transition_evidence(manifest_path)


def test_manifest_rejects_skipped_authorization_mode(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["target_mode"] = "CANONICAL_AUTHORITATIVE"
    manifest["rollback_rehearsal"]["from_mode"] = "CANONICAL_AUTHORITATIVE"
    _rewrite_manifest(manifest_path, manifest)

    with pytest.raises(
        AuthorizationTransitionEvidenceError,
        match="advance exactly one approved mode",
    ):
        verify_authorization_transition_evidence(manifest_path)


def test_manifest_rejects_sensitive_fields_before_schema_validation(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["operator_password"] = "must-never-be-recorded"
    _rewrite_manifest(manifest_path, manifest)

    with pytest.raises(
        AuthorizationTransitionEvidenceError,
        match="Sensitive field is prohibited.*operator_password",
    ):
        verify_authorization_transition_evidence(manifest_path)


def test_verification_cli_writes_an_immutable_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _build_manifest(tmp_path)
    receipt_path = tmp_path / "verification-receipt.json"

    assert (
        verify_main(
            [
                str(manifest_path),
                "--expected-environment",
                "production-eu-1",
                "--output",
                str(receipt_path),
            ]
        )
        == 0
    )
    assert receipt_path.is_file()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["status"] == (
        "ready_for_review"
    )
    assert verify_main([str(manifest_path), "--output", str(receipt_path)]) == 2
    assert "File exists" in capsys.readouterr().err
