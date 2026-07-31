from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.infra.platform.security_config import AuthorizationMigrationMode


# RBAC-TRANSITION-ONLY: Remove this verifier after CANONICAL_ONLY promotion,
# the rollback window, and ADR-003 evidence retention. Preserve its receipts.
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ENVIRONMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
_SENSITIVE_KEY_FRAGMENTS = frozenset(
    {
        "credential",
        "database_url",
        "mfa",
        "password",
        "private_key",
        "recovery_code",
        "secret",
        "token",
    }
)
_NEXT_MODE = {
    AuthorizationMigrationMode.LEGACY_AUTHORITATIVE: (
        AuthorizationMigrationMode.CANONICAL_SHADOW
    ),
    AuthorizationMigrationMode.CANONICAL_SHADOW: (
        AuthorizationMigrationMode.CANONICAL_AUTHORITATIVE
    ),
    AuthorizationMigrationMode.CANONICAL_AUTHORITATIVE: (
        AuthorizationMigrationMode.CANONICAL_ONLY
    ),
}


class AuthorizationTransitionEvidenceError(RuntimeError):
    pass


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class FileArtifactEvidence(_EvidenceModel):
    path: str
    sha256: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value or "\x00" in value:
            raise ValueError("Artifact path is required.")
        return value

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Artifact SHA-256 must be a 64-character hex digest.")
        return normalized


class InventoryArtifactEvidence(_EvidenceModel):
    artifact: FileArtifactEvidence
    snapshot_sha256: str

    @field_validator("snapshot_sha256")
    @classmethod
    def _validate_snapshot_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Inventory snapshot SHA-256 is invalid.")
        return normalized


class PolicyPreviewEvidence(_EvidenceModel):
    artifact: FileArtifactEvidence
    change_set_hash: str
    current_version: int = Field(ge=0)
    target_version: int = Field(ge=1)

    @field_validator("change_set_hash")
    @classmethod
    def _validate_change_set_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Policy change-set hash is invalid.")
        return normalized


class BackupEvidence(_EvidenceModel):
    reference: str
    sha256: str
    created_at: datetime
    database_revision: str
    application_version: str
    encrypted: Literal[True]
    immutable: Literal[True]

    @field_validator("reference")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _validated_external_reference(value)

    @field_validator("sha256")
    @classmethod
    def _validate_backup_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Backup SHA-256 is invalid.")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class RestoreRehearsalEvidence(_EvidenceModel):
    passed: Literal[True]
    completed_at: datetime
    environment_id: str
    deployment_environment: Literal["development", "test"]
    evidence_reference: str
    backup_sha256: str
    restored_database_revision: str

    @field_validator("completed_at")
    @classmethod
    def _validate_completed_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @field_validator("environment_id")
    @classmethod
    def _validate_environment_id(cls, value: str) -> str:
        return _validated_environment_id(value)

    @field_validator("evidence_reference")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _validated_external_reference(value)

    @field_validator("backup_sha256")
    @classmethod
    def _validate_backup_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Restore backup SHA-256 is invalid.")
        return normalized


class RollbackRehearsalEvidence(_EvidenceModel):
    passed: Literal[True]
    completed_at: datetime
    evidence_reference: str
    from_mode: AuthorizationMigrationMode
    to_mode: AuthorizationMigrationMode
    replay_tested: Literal[True]
    session_rebuild_tested: Literal[True]

    @field_validator("completed_at")
    @classmethod
    def _validate_completed_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @field_validator("evidence_reference")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _validated_external_reference(value)


class AuditRetentionEvidence(_EvidenceModel):
    policy_reference: str
    approved_at: datetime
    approved_by: str
    privileged_retention_days: int = Field(ge=2555)
    authorization_retention_days: int = Field(ge=400)

    @field_validator("policy_reference")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _validated_external_reference(value)

    @field_validator("approved_at")
    @classmethod
    def _validate_approved_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @field_validator("approved_by")
    @classmethod
    def _validate_approved_by(cls, value: str) -> str:
        if not value:
            raise ValueError("Retention approver is required.")
        return value


class ApprovalEvidence(_EvidenceModel):
    role: Literal["platform_operations", "security"]
    approver_id: str
    approved_at: datetime
    evidence_reference: str

    @field_validator("approver_id")
    @classmethod
    def _validate_approver_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Approver identifier is required.")
        return value

    @field_validator("approved_at")
    @classmethod
    def _validate_approved_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @field_validator("evidence_reference")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _validated_external_reference(value)


class PolicyApplyEvidence(_EvidenceModel):
    receipt: FileArtifactEvidence
    rollback_artifact: FileArtifactEvidence
    applied_at: datetime
    change_set_hash: str
    from_version: int = Field(ge=0)
    to_version: int = Field(ge=1)

    @field_validator("change_set_hash")
    @classmethod
    def _validate_change_set_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Applied policy change-set hash is invalid.")
        return normalized

    @field_validator("applied_at")
    @classmethod
    def _validate_applied_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class AuthorizationTransitionEvidenceManifest(_EvidenceModel):
    schema_version: Literal[1]
    stage: Literal["pre_apply", "post_apply"]
    environment_id: str
    deployment_environment: Literal["development", "test", "production"]
    tenancy_mode: Literal["local_single_tenant", "saas"]
    generated_at: datetime
    change_ticket: str
    application_version: str
    database_revision: str
    current_mode: AuthorizationMigrationMode
    target_mode: AuthorizationMigrationMode
    backup: BackupEvidence
    before_inventory: InventoryArtifactEvidence
    policy_preview: PolicyPreviewEvidence
    restore_rehearsal: RestoreRehearsalEvidence
    rollback_rehearsal: RollbackRehearsalEvidence
    audit_retention: AuditRetentionEvidence
    approvals: tuple[ApprovalEvidence, ...]
    policy_apply: PolicyApplyEvidence | None = None
    post_inventory: InventoryArtifactEvidence | None = None

    @field_validator("environment_id")
    @classmethod
    def _validate_environment_id(cls, value: str) -> str:
        return _validated_environment_id(value)

    @field_validator("generated_at")
    @classmethod
    def _validate_generated_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @field_validator(
        "change_ticket",
        "application_version",
        "database_revision",
    )
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("Evidence identity fields cannot be empty.")
        return value

    @model_validator(mode="after")
    def _validate_transition_gates(self) -> "AuthorizationTransitionEvidenceManifest":
        expected_target = _NEXT_MODE.get(self.current_mode)
        if expected_target is not self.target_mode:
            raise ValueError(
                "Authorization transitions must advance exactly one approved mode."
            )
        if self.backup.application_version != self.application_version:
            raise ValueError("Backup application version does not match the manifest.")
        if self.backup.database_revision != self.database_revision:
            raise ValueError("Backup database revision does not match the manifest.")
        if self.restore_rehearsal.backup_sha256 != self.backup.sha256:
            raise ValueError("Restore rehearsal did not use the declared backup.")
        if (
            self.restore_rehearsal.restored_database_revision
            != self.database_revision
        ):
            raise ValueError("Restore rehearsal database revision does not match.")
        if self.restore_rehearsal.environment_id == self.environment_id:
            raise ValueError(
                "Restore rehearsal must run in a separate non-production environment."
            )
        if (
            self.rollback_rehearsal.from_mode is not self.target_mode
            or self.rollback_rehearsal.to_mode is not self.current_mode
        ):
            raise ValueError("Rollback rehearsal does not reverse this transition.")

        approvals_by_role = {approval.role: approval for approval in self.approvals}
        if set(approvals_by_role) != {"platform_operations", "security"}:
            raise ValueError(
                "Independent Platform Operations and Security approvals are required."
            )
        if len(self.approvals) != 2:
            raise ValueError("Exactly two transition approvals are required.")
        if len({approval.approver_id for approval in self.approvals}) != 2:
            raise ValueError("Operations and Security approvers must be different people.")
        if self.audit_retention.approved_by != approvals_by_role["security"].approver_id:
            raise ValueError("Security must own the audit-retention approval.")

        evidence_times = (
            self.backup.created_at,
            self.restore_rehearsal.completed_at,
            self.rollback_rehearsal.completed_at,
            self.audit_retention.approved_at,
            *(approval.approved_at for approval in self.approvals),
        )
        if any(value > self.generated_at for value in evidence_times):
            raise ValueError("Manifest generation cannot predate its evidence.")
        if (
            self.policy_apply is not None
            and self.policy_apply.applied_at > self.generated_at
        ):
            raise ValueError("Manifest generation cannot predate policy apply.")

        if self.stage == "pre_apply":
            if self.policy_apply is not None or self.post_inventory is not None:
                raise ValueError("Pre-apply evidence cannot claim post-apply artifacts.")
        elif self.policy_apply is None or self.post_inventory is None:
            raise ValueError(
                "Post-apply evidence requires an apply receipt and post inventory."
            )

        if self.policy_apply is not None:
            if (
                self.policy_apply.change_set_hash
                != self.policy_preview.change_set_hash
            ):
                raise ValueError("Applied policy hash differs from the reviewed preview.")
            if (
                self.policy_apply.from_version
                != self.policy_preview.current_version
                or self.policy_apply.to_version
                != self.policy_preview.target_version
            ):
                raise ValueError("Applied policy versions differ from the reviewed preview.")
        return self


def load_authorization_transition_manifest(
    manifest_path: Path,
) -> AuthorizationTransitionEvidenceManifest:
    path = manifest_path.expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationTransitionEvidenceError(
            f"Cannot read authorization transition manifest: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationTransitionEvidenceError(
            "Authorization transition manifest must be a JSON object."
        )
    sensitive_path = _find_sensitive_key(payload)
    if sensitive_path is not None:
        raise AuthorizationTransitionEvidenceError(
            f"Sensitive field is prohibited in evidence manifests: {sensitive_path}"
        )
    try:
        return AuthorizationTransitionEvidenceManifest.model_validate(payload)
    except Exception as exc:
        raise AuthorizationTransitionEvidenceError(
            f"Authorization transition manifest is invalid: {exc}"
        ) from exc


def verify_authorization_transition_evidence(
    manifest_path: Path,
    *,
    expected_environment_id: str | None = None,
) -> dict[str, object]:
    path = manifest_path.expanduser().resolve()
    manifest = load_authorization_transition_manifest(path)
    if (
        expected_environment_id is not None
        and manifest.environment_id != expected_environment_id.strip()
    ):
        raise AuthorizationTransitionEvidenceError(
            "Manifest environment does not match the requested environment."
        )

    verified_artifacts: dict[str, str] = {}
    before_payload = _verify_json_artifact(
        path,
        manifest.before_inventory.artifact,
        label="before inventory",
        verified_artifacts=verified_artifacts,
    )
    _verify_inventory_payload(
        before_payload,
        expected_snapshot_sha256=manifest.before_inventory.snapshot_sha256,
        expected_database_revision=manifest.database_revision,
        label="before inventory",
    )

    preview_payload = _verify_json_artifact(
        path,
        manifest.policy_preview.artifact,
        label="policy preview",
        verified_artifacts=verified_artifacts,
    )
    _verify_policy_payload(
        preview_payload,
        expected_mode="dry-run",
        expected_hash=manifest.policy_preview.change_set_hash,
        expected_from_version=manifest.policy_preview.current_version,
        expected_to_version=manifest.policy_preview.target_version,
        application_version=manifest.application_version,
        current_mode=manifest.current_mode,
        deployment_environment=manifest.deployment_environment,
        tenancy_mode=manifest.tenancy_mode,
    )

    if manifest.policy_apply is not None:
        rollback_payload = _verify_json_artifact(
            path,
            manifest.policy_apply.rollback_artifact,
            label="policy rollback",
            verified_artifacts=verified_artifacts,
        )
        _verify_reviewed_plan(
            rollback_payload,
            expected_hash=manifest.policy_apply.change_set_hash,
        )
        receipt_payload = _verify_json_artifact(
            path,
            manifest.policy_apply.receipt,
            label="policy apply receipt",
            verified_artifacts=verified_artifacts,
        )
        _verify_policy_payload(
            receipt_payload,
            expected_mode="apply",
            expected_hash=manifest.policy_apply.change_set_hash,
            expected_from_version=manifest.policy_apply.from_version,
            expected_to_version=manifest.policy_apply.to_version,
            application_version=manifest.application_version,
            current_mode=manifest.current_mode,
            deployment_environment=manifest.deployment_environment,
            tenancy_mode=manifest.tenancy_mode,
        )
        _require_payload_value(
            receipt_payload,
            ("generated_at",),
            manifest.policy_apply.applied_at.isoformat(),
            label="apply receipt timestamp",
        )
        _require_payload_value(
            receipt_payload,
            ("result", "change_set_hash"),
            manifest.policy_apply.change_set_hash,
            label="apply result change-set hash",
        )
        _require_payload_value(
            receipt_payload,
            ("result", "from_version"),
            manifest.policy_apply.from_version,
            label="apply result current version",
        )
        _require_payload_value(
            receipt_payload,
            ("result", "to_version"),
            manifest.policy_apply.to_version,
            label="apply result target version",
        )
        _require_payload_value(
            receipt_payload,
            ("result", "rollback_artifact_sha256"),
            manifest.policy_apply.rollback_artifact.sha256,
            label="apply receipt rollback hash",
        )

    if manifest.post_inventory is not None:
        post_payload = _verify_json_artifact(
            path,
            manifest.post_inventory.artifact,
            label="post inventory",
            verified_artifacts=verified_artifacts,
        )
        _verify_inventory_payload(
            post_payload,
            expected_snapshot_sha256=manifest.post_inventory.snapshot_sha256,
            expected_database_revision=manifest.database_revision,
            label="post inventory",
        )

    return {
        "schema_version": 1,
        "status": "ready_for_review",
        "stage": manifest.stage,
        "environment_id": manifest.environment_id,
        "change_ticket": manifest.change_ticket,
        "transition": {
            "from": manifest.current_mode.value,
            "to": manifest.target_mode.value,
        },
        "manifest_sha256": _sha256_file(path),
        "verified_artifacts": dict(sorted(verified_artifacts.items())),
        "gates": {
            "backup_encrypted_immutable": True,
            "restore_rehearsal_passed": True,
            "rollback_rehearsal_passed": True,
            "retention_approved": True,
            "two_person_approval": True,
            "artifact_integrity_verified": True,
        },
    }


def _verify_json_artifact(
    manifest_path: Path,
    artifact: FileArtifactEvidence,
    *,
    label: str,
    verified_artifacts: dict[str, str],
) -> dict[str, Any]:
    artifact_path = Path(artifact.path).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = manifest_path.parent / artifact_path
    artifact_path = artifact_path.resolve()
    if artifact_path == manifest_path:
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} cannot reference the manifest itself."
        )
    if not artifact_path.is_file():
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} artifact does not exist: {artifact_path}"
        )
    actual_sha256 = _sha256_file(artifact_path)
    if actual_sha256 != artifact.sha256:
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} artifact SHA-256 does not match."
        )
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} artifact is not valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} artifact must be a JSON object."
        )
    sensitive_path = _find_sensitive_key(payload)
    if sensitive_path is not None:
        raise AuthorizationTransitionEvidenceError(
            f"Sensitive field is prohibited in {label}: {sensitive_path}"
        )
    verified_artifacts[label.replace(" ", "_")] = actual_sha256
    return payload


def _verify_policy_payload(
    payload: dict[str, Any],
    *,
    expected_mode: str,
    expected_hash: str,
    expected_from_version: int,
    expected_to_version: int,
    application_version: str,
    current_mode: AuthorizationMigrationMode,
    deployment_environment: str,
    tenancy_mode: str,
) -> None:
    _require_payload_value(payload, ("mode",), expected_mode, label="policy mode")
    _require_payload_value(
        payload,
        ("application_version",),
        application_version,
        label="policy application version",
    )
    _require_payload_value(
        payload,
        ("runtime_security", "deployment_environment"),
        deployment_environment,
        label="policy deployment environment",
    )
    _require_payload_value(
        payload,
        ("runtime_security", "tenancy_mode"),
        tenancy_mode,
        label="policy tenancy mode",
    )
    _require_payload_value(
        payload,
        ("runtime_security", "authorization_migration_mode"),
        current_mode.value,
        label="policy authorization mode",
    )
    _require_payload_value(
        payload,
        ("plan", "change_set_hash"),
        expected_hash,
        label="policy change-set hash",
    )
    _require_payload_value(
        payload,
        ("plan", "current_version"),
        expected_from_version,
        label="policy current version",
    )
    _require_payload_value(
        payload,
        ("plan", "target_version"),
        expected_to_version,
        label="policy target version",
    )


def _verify_inventory_payload(
    payload: dict[str, Any],
    *,
    expected_snapshot_sha256: str,
    expected_database_revision: str,
    label: str,
) -> None:
    _require_payload_value(
        payload,
        ("snapshot_sha256",),
        expected_snapshot_sha256,
        label=f"{label} snapshot",
    )
    _require_payload_value(
        payload,
        ("snapshot", "database", "alembic_revisions"),
        [expected_database_revision],
        label=f"{label} database revision",
    )


def _verify_reviewed_plan(
    payload: dict[str, Any],
    *,
    expected_hash: str,
) -> None:
    _require_payload_value(
        payload,
        ("reviewed_plan", "change_set_hash"),
        expected_hash,
        label="rollback reviewed policy hash",
    )


def _require_payload_value(
    payload: dict[str, Any],
    path: tuple[str, ...],
    expected: object,
    *,
    label: str,
) -> None:
    current: object = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise AuthorizationTransitionEvidenceError(
                f"{_display_label(label)} is missing from its artifact."
            )
        current = current[key]
    if current != expected:
        raise AuthorizationTransitionEvidenceError(
            f"{_display_label(label)} does not match the evidence manifest."
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_label(label: str) -> str:
    return label[:1].upper() + label[1:]


def _validated_environment_id(value: str) -> str:
    if _ENVIRONMENT_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("Environment identifier contains unsupported characters.")
    return value


def _validated_external_reference(value: str) -> str:
    if not value:
        raise ValueError("External evidence reference is required.")
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "Evidence references cannot contain credentials, queries, or fragments."
        )
    return value


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Evidence timestamps must include a UTC offset.")
    return value


def _find_sensitive_key(
    value: object,
    *,
    path: tuple[str, ...] = (),
) -> str | None:
    if isinstance(value, dict):
        for raw_key, nested in value.items():
            key = str(raw_key).strip().lower()
            current_path = (*path, str(raw_key))
            if any(fragment in key for fragment in _SENSITIVE_KEY_FRAGMENTS):
                return ".".join(current_path)
            found = _find_sensitive_key(nested, path=current_path)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _find_sensitive_key(nested, path=(*path, str(index)))
            if found is not None:
                return found
    return None


__all__ = [
    "AuthorizationTransitionEvidenceError",
    "AuthorizationTransitionEvidenceManifest",
    "load_authorization_transition_manifest",
    "verify_authorization_transition_evidence",
]
