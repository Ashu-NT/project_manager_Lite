"""Build reviewed, non-mutating plans for legacy role-binding migration."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.core.platform.auth.domain import (
    LEGACY_BINDING_MIGRATION_QUARANTINED,
    LEGACY_BINDING_MIGRATION_READY,
    legacy_role_binding_snapshot_sha256,
)
from src.core.platform.auth.domain.role_binding import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    normalize_role_scope_type,
)
from src.core.platform.common.exceptions import ValidationError as DomainValidationError


# RBAC-TRANSITION-ONLY: Remove after canonical backfill, rollback closure, and
# migration-evidence archival. This module never changes authorization data.
_SHA256_LENGTH = 64
_REASON_CODE_MAX_LENGTH = 128


class RoleBindingMigrationPlanError(RuntimeError):
    pass


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


def _canonical_sha256(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _stable_inventory_rows(rows: list[Any]) -> list[Any]:
    return sorted(
        rows,
        key=lambda row: json.dumps(row, sort_keys=True, default=str),
    )


def _require_sha256(value: str, *, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if len(normalized) != _SHA256_LENGTH:
        raise ValueError(f"{label} must be a SHA-256 digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256 digest.") from exc
    return normalized


def _require_aware_datetime(value: datetime, *, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a UTC offset.")
    return value.astimezone(timezone.utc)


def _normalize_reason_code(value: object) -> str | None:
    normalized = str(value or "").strip().upper()
    if len(normalized) > _REASON_CODE_MAX_LENGTH:
        raise ValueError("Migration reason code cannot exceed 128 characters.")
    return normalized or None


class ProposedRoleScope(_StrictModel):
    scope_type: str
    tenant_id: str | None = None
    scope_id: str | None = None

    @field_validator("scope_type", mode="before")
    @classmethod
    def _validate_scope_type(cls, value: object) -> str:
        try:
            return normalize_role_scope_type(value)
        except DomainValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("tenant_id", "scope_id", mode="before")
    @classmethod
    def _normalize_optional_id(cls, value: object) -> str | None:
        return str(value or "").strip() or None

    @model_validator(mode="after")
    def _validate_shape(self) -> "ProposedRoleScope":
        if self.scope_type == ROLE_SCOPE_PLATFORM:
            valid = self.tenant_id is None and self.scope_id is None
        elif self.scope_type == ROLE_SCOPE_TENANT:
            valid = self.tenant_id is not None and self.scope_id is None
        else:
            valid = self.tenant_id is not None and self.scope_id is not None
        if not valid:
            raise ValueError("Proposed role scope has an invalid tenant/resource shape.")
        return self


class LegacyRoleBindingSource(_StrictModel):
    binding_id: str
    user_id: str
    role_id: str
    role_name: str
    role_tenant_id: str | None = None
    role_allowed_scope_type: str
    role_status: str
    role_is_assignable: bool | None = None
    organization_id: str | None = None
    candidate_tenant_id: str | None = None
    active_tenant_ids: tuple[str, ...] = ()
    inventory_classification: str

    @field_validator("binding_id", "user_id", "role_id", mode="before")
    @classmethod
    def _validate_required_id(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Legacy binding references are required.")
        return normalized

    @field_validator(
        "role_name",
        "role_allowed_scope_type",
        "role_status",
        "inventory_classification",
        mode="before",
    )
    @classmethod
    def _normalize_label(cls, value: object) -> str:
        return str(value or "").strip().lower()

    @field_validator(
        "role_tenant_id",
        "organization_id",
        "candidate_tenant_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_id(cls, value: object) -> str | None:
        return str(value or "").strip() or None

    @field_validator("active_tenant_ids", mode="before")
    @classmethod
    def _normalize_active_tenants(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple, set, frozenset)):
            return ()
        normalized = {
            str(tenant_id or "").strip()
            for tenant_id in value
            if str(tenant_id or "").strip()
        }
        return tuple(sorted(normalized))

    @property
    def source_snapshot_sha256(self) -> str:
        return legacy_role_binding_snapshot_sha256(
            legacy_binding_id=self.binding_id,
            user_id=self.user_id,
            role_id=self.role_id,
            organization_id=self.organization_id,
        )


class LegacyRoleBindingMigrationProposal(_StrictModel):
    source: LegacyRoleBindingSource
    review_required: bool
    proposed_scope: ProposedRoleScope | None = None
    quarantine_reason_code: str | None = None

    @field_validator("quarantine_reason_code", mode="before")
    @classmethod
    def _normalize_reason(cls, value: object) -> str | None:
        return _normalize_reason_code(value)

    @model_validator(mode="after")
    def _validate_disposition(self) -> "LegacyRoleBindingMigrationProposal":
        if self.review_required:
            if self.proposed_scope is None or self.quarantine_reason_code is not None:
                raise ValueError("Review candidates require exactly one proposed scope.")
        elif self.proposed_scope is not None or self.quarantine_reason_code is None:
            raise ValueError("Non-reviewable bindings must be quarantined.")
        return self


class RoleBindingMigrationPreview(_StrictModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    inventory_report_sha256: str
    source_inventory_sha256: str
    records: tuple[LegacyRoleBindingMigrationProposal, ...]
    preview_sha256: str

    @field_validator("generated_at", mode="after")
    @classmethod
    def _validate_generated_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, label="Preview generation time")

    @field_validator(
        "inventory_report_sha256",
        "source_inventory_sha256",
        "preview_sha256",
        mode="before",
    )
    @classmethod
    def _validate_hashes(cls, value: str) -> str:
        return _require_sha256(value, label="Preview hash")

    @model_validator(mode="after")
    def _verify_hash(self) -> "RoleBindingMigrationPreview":
        if self.preview_sha256 != _preview_hash(
            self.source_inventory_sha256,
            self.records,
        ):
            raise ValueError("Role-binding migration preview hash does not match its records.")
        return self


class RoleBindingMigrationReviewDecision(_StrictModel):
    binding_id: str
    decision: Literal["approve", "quarantine"]
    reason_code: str | None = None

    @field_validator("binding_id", mode="before")
    @classmethod
    def _validate_binding_id(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Review decision binding id is required.")
        return normalized

    @field_validator("reason_code", mode="before")
    @classmethod
    def _normalize_reason(cls, value: object) -> str | None:
        return _normalize_reason_code(value)

    @model_validator(mode="after")
    def _validate_decision(self) -> "RoleBindingMigrationReviewDecision":
        if self.decision == "approve" and self.reason_code is not None:
            raise ValueError("An approved proposal cannot carry a quarantine reason.")
        if self.decision == "quarantine" and self.reason_code is None:
            raise ValueError("A quarantine decision requires a reason code.")
        return self


class RoleBindingMigrationReview(_StrictModel):
    schema_version: Literal[1] = 1
    inventory_report_sha256: str
    source_inventory_sha256: str
    preview_sha256: str
    reviewer_id: str
    reviewed_at: datetime
    decisions: tuple[RoleBindingMigrationReviewDecision, ...]

    @field_validator(
        "inventory_report_sha256",
        "source_inventory_sha256",
        "preview_sha256",
        mode="before",
    )
    @classmethod
    def _validate_hashes(cls, value: str) -> str:
        return _require_sha256(value, label="Review hash")

    @field_validator("reviewer_id", mode="before")
    @classmethod
    def _validate_reviewer(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Security reviewer id is required.")
        return normalized

    @field_validator("reviewed_at", mode="after")
    @classmethod
    def _validate_reviewed_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, label="Review time")

    @model_validator(mode="after")
    def _reject_duplicate_decisions(self) -> "RoleBindingMigrationReview":
        binding_ids = [decision.binding_id for decision in self.decisions]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("Review decisions must be unique by legacy binding id.")
        return self


class ReviewedLegacyRoleBindingRecord(_StrictModel):
    source: LegacyRoleBindingSource
    source_snapshot_sha256: str
    status: Literal["ready", "quarantined"]
    quarantine_reason_code: str | None = None
    resolved_scope: ProposedRoleScope | None = None
    reviewed_by: str
    reviewed_at: datetime

    @field_validator("source_snapshot_sha256", mode="before")
    @classmethod
    def _validate_source_hash(cls, value: str) -> str:
        return _require_sha256(value, label="Legacy source hash")

    @field_validator("reviewed_by", mode="before")
    @classmethod
    def _validate_reviewer(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Reviewed migration record requires a reviewer.")
        return normalized

    @field_validator("reviewed_at", mode="after")
    @classmethod
    def _validate_reviewed_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, label="Record review time")

    @field_validator("quarantine_reason_code", mode="before")
    @classmethod
    def _normalize_reason(cls, value: object) -> str | None:
        return _normalize_reason_code(value)

    @model_validator(mode="after")
    def _validate_record(self) -> "ReviewedLegacyRoleBindingRecord":
        if self.source_snapshot_sha256 != self.source.source_snapshot_sha256:
            raise ValueError("Reviewed source hash does not match the legacy binding.")
        if self.status == LEGACY_BINDING_MIGRATION_READY:
            if self.resolved_scope is None or self.quarantine_reason_code is not None:
                raise ValueError("Ready records require exactly one resolved scope.")
        elif self.resolved_scope is not None or self.quarantine_reason_code is None:
            raise ValueError("Quarantined records require exactly one reason.")
        return self


class ReviewedRoleBindingMigrationPlan(_StrictModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    inventory_report_sha256: str
    source_inventory_sha256: str
    preview_sha256: str
    reviewer_id: str
    reviewed_at: datetime
    record_count: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    quarantine_count: int = Field(ge=0)
    records: tuple[ReviewedLegacyRoleBindingRecord, ...]
    plan_sha256: str

    @field_validator("generated_at", "reviewed_at", mode="after")
    @classmethod
    def _validate_timestamps(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, label="Reviewed plan timestamp")

    @field_validator(
        "inventory_report_sha256",
        "source_inventory_sha256",
        "preview_sha256",
        "plan_sha256",
        mode="before",
    )
    @classmethod
    def _validate_hashes(cls, value: str) -> str:
        return _require_sha256(value, label="Reviewed plan hash")

    @field_validator("reviewer_id", mode="before")
    @classmethod
    def _validate_reviewer(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Reviewed plan requires a reviewer id.")
        return normalized

    @model_validator(mode="after")
    def _verify_counts_and_hash(self) -> "ReviewedRoleBindingMigrationPlan":
        binding_ids = [record.source.binding_id for record in self.records]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("Reviewed migration records must have unique source ids.")
        if self.reviewed_at > self.generated_at:
            raise ValueError("Reviewed plan cannot predate its review.")
        if any(
            record.reviewed_by != self.reviewer_id
            or record.reviewed_at != self.reviewed_at
            for record in self.records
        ):
            raise ValueError("Reviewed records must share the plan review identity.")
        ready_count = sum(record.status == "ready" for record in self.records)
        quarantine_count = len(self.records) - ready_count
        if (
            self.record_count != len(self.records)
            or self.ready_count != ready_count
            or self.quarantine_count != quarantine_count
        ):
            raise ValueError("Reviewed migration plan counts do not match its records.")
        if self.plan_sha256 != _reviewed_plan_hash(
            inventory_report_sha256=self.inventory_report_sha256,
            source_inventory_sha256=self.source_inventory_sha256,
            preview_sha256=self.preview_sha256,
            reviewer_id=self.reviewer_id,
            reviewed_at=self.reviewed_at,
            records=self.records,
        ):
            raise ValueError("Reviewed migration plan hash does not match its records.")
        return self


def _preview_hash(
    source_inventory_sha256: str,
    records: tuple[LegacyRoleBindingMigrationProposal, ...],
) -> str:
    return _canonical_sha256(
        {
            "schema_version": 1,
            "source_inventory_sha256": source_inventory_sha256,
            "records": [record.model_dump(mode="json") for record in records],
        }
    )


def _reviewed_plan_hash(
    *,
    inventory_report_sha256: str,
    source_inventory_sha256: str,
    preview_sha256: str,
    reviewer_id: str,
    reviewed_at: datetime,
    records: tuple[ReviewedLegacyRoleBindingRecord, ...],
) -> str:
    return _canonical_sha256(
        {
            "schema_version": 1,
            "inventory_report_sha256": inventory_report_sha256,
            "source_inventory_sha256": source_inventory_sha256,
            "preview_sha256": preview_sha256,
            "reviewer_id": reviewer_id,
            "reviewed_at": reviewed_at.isoformat(),
            "records": [record.model_dump(mode="json") for record in records],
        }
    )


def _verified_inventory(report: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if report.get("read_only") is not True:
        raise RoleBindingMigrationPlanError("A read-only inventory artifact is required.")
    snapshot = report.get("snapshot")
    if not isinstance(snapshot, dict):
        raise RoleBindingMigrationPlanError("Inventory snapshot is missing.")
    try:
        declared_hash = _require_sha256(
            str(report.get("snapshot_sha256") or ""),
            label="Inventory snapshot hash",
        )
    except ValueError as exc:
        raise RoleBindingMigrationPlanError(
            "Inventory snapshot hash is invalid."
        ) from exc
    if declared_hash != _canonical_sha256(snapshot):
        raise RoleBindingMigrationPlanError(
            "Inventory snapshot hash does not match its content."
        )
    return declared_hash, snapshot


def _source_from_inventory(row: dict[str, Any]) -> LegacyRoleBindingSource:
    return LegacyRoleBindingSource(
        binding_id=row.get("binding_id"),
        user_id=row.get("user_id"),
        role_id=row.get("role_id"),
        role_name=row.get("role_name"),
        role_tenant_id=row.get("role_tenant_id"),
        role_allowed_scope_type=row.get("role_allowed_scope_type"),
        role_status=row.get("role_status"),
        role_is_assignable=row.get("role_is_assignable"),
        organization_id=row.get("organization_id"),
        candidate_tenant_id=row.get("candidate_tenant_id"),
        active_tenant_ids=row.get("active_tenant_ids", ()),
        inventory_classification=row.get("classification"),
    )


def _quarantine(
    source: LegacyRoleBindingSource,
    reason_code: str,
) -> LegacyRoleBindingMigrationProposal:
    return LegacyRoleBindingMigrationProposal(
        source=source,
        review_required=False,
        quarantine_reason_code=reason_code,
    )


def _proposal_for_source(
    source: LegacyRoleBindingSource,
    *,
    duplicate: bool,
) -> LegacyRoleBindingMigrationProposal:
    if duplicate:
        return _quarantine(source, "DUPLICATE_LEGACY_BINDING")
    allowed_scope = source.role_allowed_scope_type
    if not source.role_name or not allowed_scope or not source.role_status:
        return _quarantine(source, "ROLE_METADATA_MISSING")
    if source.role_status != "active":
        return _quarantine(source, "ROLE_INACTIVE")

    if allowed_scope == ROLE_SCOPE_PLATFORM:
        if source.role_tenant_id is not None:
            return _quarantine(source, "PLATFORM_ROLE_TENANT_OWNERSHIP_INVALID")
        if source.organization_id is not None:
            return _quarantine(source, "INVALID_PLATFORM_RESOURCE_SCOPE")
        scope = ProposedRoleScope(scope_type=ROLE_SCOPE_PLATFORM)
    elif allowed_scope == ROLE_SCOPE_TENANT:
        if source.organization_id is not None:
            return _quarantine(source, "ROLE_SCOPE_MISMATCH")
        if not source.active_tenant_ids:
            return _quarantine(source, "NO_ACTIVE_MEMBERSHIP")
        if len(source.active_tenant_ids) != 1:
            return _quarantine(source, "AMBIGUOUS_MULTI_TENANT")
        tenant_id = source.active_tenant_ids[0]
        if source.candidate_tenant_id != tenant_id:
            return _quarantine(source, "TENANT_CANDIDATE_INVALID")
        if source.role_tenant_id not in {None, tenant_id}:
            return _quarantine(source, "ROLE_TENANT_MISMATCH")
        scope = ProposedRoleScope(
            scope_type=ROLE_SCOPE_TENANT,
            tenant_id=tenant_id,
        )
    elif allowed_scope == "organization":
        if source.organization_id is None:
            return _quarantine(source, "ORGANIZATION_SCOPE_REQUIRED")
        tenant_id = source.candidate_tenant_id
        if tenant_id is None:
            return _quarantine(source, "ORGANIZATION_TENANT_MISSING")
        if tenant_id not in source.active_tenant_ids:
            return _quarantine(source, "CROSS_TENANT_ORGANIZATION_BINDING")
        if source.role_tenant_id not in {None, tenant_id}:
            return _quarantine(source, "ROLE_TENANT_MISMATCH")
        scope = ProposedRoleScope(
            scope_type="organization",
            tenant_id=tenant_id,
            scope_id=source.organization_id,
        )
    else:
        return _quarantine(source, "LEGACY_SCOPE_UNSUPPORTED")

    return LegacyRoleBindingMigrationProposal(
        source=source,
        review_required=True,
        proposed_scope=scope,
    )


def build_role_binding_migration_preview(
    inventory_report: dict[str, Any],
) -> RoleBindingMigrationPreview:
    inventory_report_hash, snapshot = _verified_inventory(inventory_report)
    data = snapshot.get("data")
    rows = data.get("legacy_bindings") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise RoleBindingMigrationPlanError(
            "Inventory does not contain legacy role-binding classifications."
        )
    source_inventory_hash = _canonical_sha256(
        {
            "schema_version": 1,
            "legacy_bindings": _stable_inventory_rows(rows),
        }
    )
    try:
        sources = tuple(
            sorted(
                (_source_from_inventory(row) for row in rows if isinstance(row, dict)),
                key=lambda source: source.binding_id,
            )
        )
    except (DomainValidationError, TypeError, ValueError) as exc:
        raise RoleBindingMigrationPlanError(
            "Inventory contains an invalid legacy role-binding record."
        ) from exc
    if len(sources) != len(rows):
        raise RoleBindingMigrationPlanError(
            "Every legacy role-binding inventory row must be an object."
        )

    duplicate_counts: dict[tuple[str, str, str | None], int] = {}
    for source in sources:
        key = (source.user_id, source.role_id, source.organization_id)
        duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
    records = tuple(
        _proposal_for_source(
            source,
            duplicate=(
                duplicate_counts[
                    (source.user_id, source.role_id, source.organization_id)
                ]
                > 1
            ),
        )
        for source in sources
    )
    preview_hash = _preview_hash(source_inventory_hash, records)
    return RoleBindingMigrationPreview(
        generated_at=datetime.now(timezone.utc),
        inventory_report_sha256=inventory_report_hash,
        source_inventory_sha256=source_inventory_hash,
        records=records,
        preview_sha256=preview_hash,
    )


def build_reviewed_role_binding_migration_plan(
    preview: RoleBindingMigrationPreview,
    review: RoleBindingMigrationReview,
) -> ReviewedRoleBindingMigrationPlan:
    if review.inventory_report_sha256 != preview.inventory_report_sha256:
        raise RoleBindingMigrationPlanError(
            "Review report hash does not match the migration preview."
        )
    if review.source_inventory_sha256 != preview.source_inventory_sha256:
        raise RoleBindingMigrationPlanError(
            "Review source inventory hash does not match the migration preview."
        )
    if review.preview_sha256 != preview.preview_sha256:
        raise RoleBindingMigrationPlanError(
            "Review preview hash does not match the migration preview."
        )
    decision_by_binding = {
        decision.binding_id: decision for decision in review.decisions
    }
    reviewable_ids = {
        proposal.source.binding_id
        for proposal in preview.records
        if proposal.review_required
    }
    if set(decision_by_binding) != reviewable_ids:
        missing = sorted(reviewable_ids - set(decision_by_binding))
        unexpected = sorted(set(decision_by_binding) - reviewable_ids)
        raise RoleBindingMigrationPlanError(
            "Review decisions must cover every review candidate exactly; "
            f"missing={missing}, unexpected={unexpected}."
        )

    reviewed_records: list[ReviewedLegacyRoleBindingRecord] = []
    for proposal in preview.records:
        decision = decision_by_binding.get(proposal.source.binding_id)
        if proposal.review_required and decision is not None:
            approved = decision.decision == "approve"
            status = (
                LEGACY_BINDING_MIGRATION_READY
                if approved
                else LEGACY_BINDING_MIGRATION_QUARANTINED
            )
            resolved_scope = proposal.proposed_scope if approved else None
            quarantine_reason = decision.reason_code if not approved else None
        else:
            status = LEGACY_BINDING_MIGRATION_QUARANTINED
            resolved_scope = None
            quarantine_reason = proposal.quarantine_reason_code
        reviewed_records.append(
            ReviewedLegacyRoleBindingRecord(
                source=proposal.source,
                source_snapshot_sha256=(proposal.source.source_snapshot_sha256),
                status=status,
                quarantine_reason_code=quarantine_reason,
                resolved_scope=resolved_scope,
                reviewed_by=review.reviewer_id,
                reviewed_at=review.reviewed_at,
            )
        )

    records = tuple(reviewed_records)
    ready_count = sum(record.status == "ready" for record in records)
    plan_hash = _reviewed_plan_hash(
        inventory_report_sha256=preview.inventory_report_sha256,
        source_inventory_sha256=preview.source_inventory_sha256,
        preview_sha256=preview.preview_sha256,
        reviewer_id=review.reviewer_id,
        reviewed_at=review.reviewed_at,
        records=records,
    )
    plan = ReviewedRoleBindingMigrationPlan(
        generated_at=datetime.now(timezone.utc),
        inventory_report_sha256=preview.inventory_report_sha256,
        source_inventory_sha256=preview.source_inventory_sha256,
        preview_sha256=preview.preview_sha256,
        reviewer_id=review.reviewer_id,
        reviewed_at=review.reviewed_at,
        record_count=len(records),
        ready_count=ready_count,
        quarantine_count=len(records) - ready_count,
        records=records,
        plan_sha256=plan_hash,
    )
    validate_reviewed_plan_against_preview(plan, preview)
    return plan


def validate_reviewed_plan_against_preview(
    plan: ReviewedRoleBindingMigrationPlan,
    preview: RoleBindingMigrationPreview,
    *,
    require_report_match: bool = True,
) -> None:
    if (
        require_report_match
        and plan.inventory_report_sha256 != preview.inventory_report_sha256
    ):
        raise RoleBindingMigrationPlanError(
            "Reviewed plan report hash does not match the migration preview."
        )
    if plan.source_inventory_sha256 != preview.source_inventory_sha256:
        raise RoleBindingMigrationPlanError(
            "Reviewed plan source hash does not match the migration preview."
        )
    if plan.preview_sha256 != preview.preview_sha256:
        raise RoleBindingMigrationPlanError(
            "Reviewed plan preview hash does not match the migration preview."
        )

    proposals = {
        proposal.source.binding_id: proposal for proposal in preview.records
    }
    records = {record.source.binding_id: record for record in plan.records}
    if set(records) != set(proposals):
        raise RoleBindingMigrationPlanError(
            "Reviewed plan sources do not exactly match the migration preview."
        )
    for binding_id, record in records.items():
        proposal = proposals[binding_id]
        if record.source != proposal.source:
            raise RoleBindingMigrationPlanError(
                f"Reviewed source '{binding_id}' differs from the inventory preview."
            )
        if record.status == LEGACY_BINDING_MIGRATION_READY:
            if (
                not proposal.review_required
                or record.resolved_scope != proposal.proposed_scope
            ):
                raise RoleBindingMigrationPlanError(
                    f"Reviewed scope for '{binding_id}' was not inventory-derived."
                )
        elif (
            not proposal.review_required
            and record.quarantine_reason_code != proposal.quarantine_reason_code
        ):
            raise RoleBindingMigrationPlanError(
                f"Mandatory quarantine for '{binding_id}' was changed."
            )


def load_role_binding_migration_preview(
    path: Path,
) -> RoleBindingMigrationPreview:
    return _load_model(path, RoleBindingMigrationPreview)


def load_role_binding_migration_review(
    path: Path,
) -> RoleBindingMigrationReview:
    return _load_model(path, RoleBindingMigrationReview)


def load_reviewed_role_binding_migration_plan(
    path: Path,
) -> ReviewedRoleBindingMigrationPlan:
    return _load_model(path, ReviewedRoleBindingMigrationPlan)


def _load_model(path: Path, model_type):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except (OSError, ValueError) as exc:
        raise RoleBindingMigrationPlanError(
            f"Invalid role-binding migration artifact '{path}'."
        ) from exc


__all__ = [
    "LegacyRoleBindingMigrationProposal",
    "LegacyRoleBindingSource",
    "ProposedRoleScope",
    "ReviewedLegacyRoleBindingRecord",
    "ReviewedRoleBindingMigrationPlan",
    "RoleBindingMigrationPlanError",
    "RoleBindingMigrationPreview",
    "RoleBindingMigrationReview",
    "RoleBindingMigrationReviewDecision",
    "build_reviewed_role_binding_migration_plan",
    "build_role_binding_migration_preview",
    "load_reviewed_role_binding_migration_plan",
    "load_role_binding_migration_preview",
    "load_role_binding_migration_review",
    "validate_reviewed_plan_against_preview",
]
