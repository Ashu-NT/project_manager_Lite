"""Persist reviewed legacy role-binding migration plans without applying them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain import AuditEntry
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.contracts import RoleBindingMigrationRepository
from src.core.platform.auth.domain import (
    AuthorizationMigrationBatch,
    LegacyRoleBindingMigrationRecord,
    UserSessionContext,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id

from .role_binding_migration_plan import (
    ReviewedLegacyRoleBindingRecord,
    ReviewedRoleBindingMigrationPlan,
    RoleBindingMigrationPlanError,
    build_role_binding_migration_preview,
    validate_reviewed_plan_against_preview,
)


# RBAC-TRANSITION-ONLY: Remove after canonical backfill, rollback closure, and
# migration-evidence archival. Preparation never writes canonical authority.
@dataclass(frozen=True)
class RoleBindingMigrationPreparationResult:
    batch: AuthorizationMigrationBatch
    records: tuple[LegacyRoleBindingMigrationRecord, ...]
    already_prepared: bool


class RoleBindingMigrationPreparationService:
    def __init__(
        self,
        *,
        session: Session,
        migration_repo: RoleBindingMigrationRepository,
        audit_repo: AuditRepository,
        user_session: UserSessionContext,
        current_inventory_provider: Callable[[], dict[str, Any]],
    ) -> None:
        self._session = session
        self._migration_repo = migration_repo
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._current_inventory_provider = current_inventory_provider

    def prepare(
        self,
        plan: ReviewedRoleBindingMigrationPlan,
        *,
        expected_plan_sha256: str,
    ) -> RoleBindingMigrationPreparationResult:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="prepare reviewed role-binding migration",
        )
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "An authenticated platform operator is required.",
                code="AUTH_MIGRATION_PRINCIPAL_REQUIRED",
            )
        self._require_independent_review(
            reviewer_id=plan.reviewer_id,
            actor_user_id=principal.user_id,
            actor_username=principal.username,
        )

        expected_hash = str(expected_plan_sha256 or "").strip().lower()
        if expected_hash != plan.plan_sha256:
            raise BusinessRuleError(
                "Reviewed migration plan hash does not match the expected hash.",
                code="AUTH_MIGRATION_PLAN_HASH_MISMATCH",
            )

        try:
            live_preview = build_role_binding_migration_preview(
                self._current_inventory_provider()
            )
            validate_reviewed_plan_against_preview(
                plan,
                live_preview,
                require_report_match=False,
            )
        except RoleBindingMigrationPlanError as exc:
            raise BusinessRuleError(
                "Authorization source data changed after migration review.",
                code="AUTH_MIGRATION_SOURCE_DRIFT",
            ) from exc

        try:
            with self._session.begin_nested():
                existing = self._migration_repo.get_batch_by_inventory_sha256(
                    plan.source_inventory_sha256
                )
                if existing is not None:
                    return self._existing_result(existing, plan)

                batch = AuthorizationMigrationBatch.create(
                    source_inventory_sha256=plan.source_inventory_sha256,
                    source_record_count=plan.record_count,
                    reviewed_plan_sha256=plan.plan_sha256,
                    reviewer_id=plan.reviewer_id,
                    reviewed_at=plan.reviewed_at,
                    created_by=principal.user_id,
                )
                prepared_at = batch.created_at
                records = tuple(
                    self._to_record(
                        batch_id=batch.id,
                        reviewed_record=record,
                        prepared_at=prepared_at,
                    )
                    for record in plan.records
                )
                self._migration_repo.add_batch(batch)
                for record in records:
                    self._migration_repo.add_record(record)
                self._audit_repo.add_platform(
                    AuditEntry.create(
                        operation="authorization.migration.prepared",
                        entity_type="authorization_migration_batch",
                        entity_id=batch.id,
                        module="platform.auth",
                        actor_id=principal.user_id,
                        actor_username=principal.username,
                        source="operator_cli",
                        severity="high",
                        compliance_tag="access_control",
                        metadata={
                            "inventory_report_sha256": plan.inventory_report_sha256,
                            "source_inventory_sha256": plan.source_inventory_sha256,
                            "reviewed_plan_sha256": plan.plan_sha256,
                            "reviewer_id": plan.reviewer_id,
                            "record_count": plan.record_count,
                            "ready_count": plan.ready_count,
                            "quarantine_count": plan.quarantine_count,
                        },
                    )
                )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            existing = self._migration_repo.get_batch_by_inventory_sha256(
                plan.source_inventory_sha256
            )
            if existing is not None:
                return self._existing_result(existing, plan)
            raise BusinessRuleError(
                "Role-binding migration was prepared concurrently.",
                code="AUTH_MIGRATION_CONCURRENT_PREPARATION",
            ) from exc
        except Exception:
            self._session.rollback()
            raise

        return RoleBindingMigrationPreparationResult(
            batch=batch,
            records=records,
            already_prepared=False,
        )

    def _existing_result(
        self,
        batch: AuthorizationMigrationBatch,
        plan: ReviewedRoleBindingMigrationPlan,
    ) -> RoleBindingMigrationPreparationResult:
        if batch.reviewed_plan_sha256 != plan.plan_sha256:
            raise BusinessRuleError(
                "This authorization source inventory already has a different reviewed plan.",
                code="AUTH_MIGRATION_PLAN_CONFLICT",
            )
        records = tuple(self._migration_repo.list_records(batch.id))
        if (
            batch.source_record_count != plan.record_count
            or batch.reviewer_id != plan.reviewer_id
            or batch.reviewed_at != plan.reviewed_at
            or len(records) != plan.record_count
            or not self._records_match_plan(records, plan)
        ):
            raise BusinessRuleError(
                "The prepared migration batch does not match its reviewed plan.",
                code="AUTH_MIGRATION_EVIDENCE_MISMATCH",
            )
        return RoleBindingMigrationPreparationResult(
            batch=batch,
            records=records,
            already_prepared=True,
        )

    @staticmethod
    def _records_match_plan(
        records: tuple[LegacyRoleBindingMigrationRecord, ...],
        plan: ReviewedRoleBindingMigrationPlan,
    ) -> bool:
        persisted = {record.legacy_binding_id: record for record in records}
        expected = {record.source.binding_id: record for record in plan.records}
        if len(persisted) != len(records) or set(persisted) != set(expected):
            return False
        for binding_id, reviewed in expected.items():
            record = persisted[binding_id]
            scope = reviewed.resolved_scope
            if (
                record.source_user_id != reviewed.source.user_id
                or record.source_role_id != reviewed.source.role_id
                or record.source_organization_id != reviewed.source.organization_id
                or record.source_snapshot_sha256 != reviewed.source_snapshot_sha256
                or record.status != reviewed.status
                or record.quarantine_reason_code != reviewed.quarantine_reason_code
                or record.resolved_tenant_id
                != (scope.tenant_id if scope is not None else None)
                or record.resolved_scope_type
                != (scope.scope_type if scope is not None else None)
                or record.resolved_scope_id
                != (scope.scope_id if scope is not None else None)
                or record.canonical_binding_id is not None
                or record.reviewed_by != reviewed.reviewed_by
                or record.reviewed_at != reviewed.reviewed_at
            ):
                return False
        return True

    @staticmethod
    def _require_independent_review(
        *,
        reviewer_id: str,
        actor_user_id: str,
        actor_username: str,
    ) -> None:
        reviewer = reviewer_id.strip().casefold()
        actor_identities = {
            actor_user_id.strip().casefold(),
            actor_username.strip().casefold(),
        }
        if reviewer in actor_identities:
            raise BusinessRuleError(
                "The platform operator cannot apply their own migration review.",
                code="AUTH_MIGRATION_INDEPENDENT_REVIEW_REQUIRED",
            )

    @staticmethod
    def _to_record(
        *,
        batch_id: str,
        reviewed_record: ReviewedLegacyRoleBindingRecord,
        prepared_at: datetime,
    ) -> LegacyRoleBindingMigrationRecord:
        scope = reviewed_record.resolved_scope
        return LegacyRoleBindingMigrationRecord(
            id=generate_id(),
            batch_id=batch_id,
            legacy_binding_id=reviewed_record.source.binding_id,
            source_user_id=reviewed_record.source.user_id,
            source_role_id=reviewed_record.source.role_id,
            source_organization_id=reviewed_record.source.organization_id,
            source_snapshot_sha256=reviewed_record.source_snapshot_sha256,
            status=reviewed_record.status,
            quarantine_reason_code=reviewed_record.quarantine_reason_code,
            resolved_tenant_id=scope.tenant_id if scope is not None else None,
            resolved_scope_type=scope.scope_type if scope is not None else None,
            resolved_scope_id=scope.scope_id if scope is not None else None,
            canonical_binding_id=None,
            reviewed_by=reviewed_record.reviewed_by,
            reviewed_at=reviewed_record.reviewed_at,
            created_at=prepared_at,
            updated_at=prepared_at,
        )


__all__ = [
    "RoleBindingMigrationPreparationResult",
    "RoleBindingMigrationPreparationService",
]
