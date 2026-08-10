from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.currency_policy import resolve_pm_currency
from src.core.modules.project_management.contracts.repositories.cost import CostRepository
from src.core.modules.project_management.contracts.repositories.financial_configuration import ProjectFinancialProfileRepository
from src.core.modules.project_management.contracts.repositories.legacy_cost_migration import LegacyCostMigrationRepository
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.domain.financials.legacy_migration import (
    LegacyCostMigrationItem,
    LegacyCostMigrationItemStatus,
    LegacyCostMigrationMode,
    LegacyCostMigrationPurpose,
    LegacyCostMigrationRun,
    LegacyCostMigrationRunStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.finance import Money
from src.core.shared.audit import record_audit_entry


@dataclass(frozen=True, slots=True)
class LegacyCostMigrationResult:
    run_id: str
    status: str
    source_row_count: int
    migrated_count: int
    quarantined_count: int
    deferred_count: int
    eligible_count: int
    items: tuple[LegacyCostMigrationItem, ...]


class LegacyCostMigrationService:
    """Governed, restart-safe C.7 CostItem split and reconciliation workflow."""

    def __init__(
        self,
        *,
        session: Session,
        migration_repo: LegacyCostMigrationRepository,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        profile_repo: ProjectFinancialProfileRepository,
        task_repo: TaskRepository,
        cost_entry_service,
        tenant_context_service,
        user_session,
        enterprise_audit_service,
    ) -> None:
        self._session = session
        self._migration_repo = migration_repo
        self._cost_repo = cost_repo
        self._project_repo = project_repo
        self._profile_repo = profile_repo
        self._task_repo = task_repo
        self._cost_entry_service = cost_entry_service
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service

    def run_project(
        self,
        project_id: str,
        *,
        execute: bool,
        fallback_transaction_date: date,
    ) -> LegacyCostMigrationResult:
        require_permission(
            self._user_session,
            "finance.manage",
            operation_label="migrate legacy project finance data",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.manage",
            operation_label="migrate legacy project finance data",
        )
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="migrate legacy project finance data"
        )
        project = self._project_repo.get(project_id)
        if project is None:
            raise BusinessRuleError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._profile_repo.get_by_project(project_id)
        actor_id = self._actor_id()
        mode = LegacyCostMigrationMode.EXECUTE if execute else LegacyCostMigrationMode.DRY_RUN
        run = LegacyCostMigrationRun.start(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            mode=mode,
            fallback_transaction_date=fallback_transaction_date,
            actor_id=actor_id,
        )
        self._migration_repo.add_run(run)
        self._session.flush()

        source_rows = self._cost_repo.list_by_project(project_id)
        results: list[LegacyCostMigrationItem] = []
        for source in source_rows:
            currency = self._resolve_currency(source.currency_code, profile, project)
            decisions = {
                "legacy_version": source.version,
                "legacy_cost_type": source.cost_type.value,
                "legacy_line_code": source.code,
                "currency_resolution": currency,
                "cost_code_mapping": (
                    profile.default_cost_code_id if profile is not None else None
                ),
            }
            responsibilities = (
                (LegacyCostMigrationPurpose.PLANNED, source.planned_amount, source.planned_amount != 0),
                (LegacyCostMigrationPurpose.COMMITMENT, source.committed_amount, source.committed_amount != 0),
                (LegacyCostMigrationPurpose.ACTUAL, source.actual_amount, source.actual_amount != 0),
                (LegacyCostMigrationPurpose.FORECAST, source.forecast_amount or 0, source.forecast_amount is not None),
            )
            for purpose, raw_amount, present in responsibilities:
                if not present:
                    continue
                item = self._process_responsibility(
                    run=run,
                    source=source,
                    purpose=purpose,
                    raw_amount=raw_amount,
                    currency_code=currency,
                    execute=execute,
                    fallback_transaction_date=fallback_transaction_date,
                    default_cost_code_id=(profile.default_cost_code_id if profile else None),
                    decisions=decisions,
                )
                self._migration_repo.save_item(item)
                self._session.commit()
                results.append(item)

        counts = {status: 0 for status in LegacyCostMigrationItemStatus}
        for item in results:
            counts[item.status] += 1
        run.status = (
            LegacyCostMigrationRunStatus.COMPLETED_WITH_QUARANTINE
            if counts[LegacyCostMigrationItemStatus.QUARANTINED]
            else LegacyCostMigrationRunStatus.COMPLETED
        )
        run.completed_at = self._cost_entry_service._clock.now()
        run.summary_json = json.dumps(
            {
                "source_row_count": len(source_rows),
                "migrated_count": counts[LegacyCostMigrationItemStatus.MIGRATED],
                "quarantined_count": counts[LegacyCostMigrationItemStatus.QUARANTINED],
                "deferred_count": counts[LegacyCostMigrationItemStatus.DEFERRED],
                "eligible_count": counts[LegacyCostMigrationItemStatus.ELIGIBLE],
            },
            sort_keys=True,
        )
        self._migration_repo.update_run(run)
        self._record_audit(run)
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return LegacyCostMigrationResult(
            run_id=run.id,
            status=run.status.value,
            source_row_count=len(source_rows),
            migrated_count=counts[LegacyCostMigrationItemStatus.MIGRATED],
            quarantined_count=counts[LegacyCostMigrationItemStatus.QUARANTINED],
            deferred_count=counts[LegacyCostMigrationItemStatus.DEFERRED],
            eligible_count=counts[LegacyCostMigrationItemStatus.ELIGIBLE],
            items=tuple(results),
        )

    def reconciliation(self, project_id: str) -> tuple[LegacyCostMigrationItem, ...]:
        require_permission(self._user_session, "finance.read", operation_label="view legacy finance reconciliation")
        require_project_permission(self._user_session, project_id, "finance.read", operation_label="view legacy finance reconciliation")
        return tuple(self._migration_repo.list_items_for_project(project_id))

    def _process_responsibility(
        self,
        *,
        run,
        source,
        purpose,
        raw_amount,
        currency_code,
        execute,
        fallback_transaction_date,
        default_cost_code_id,
        decisions,
    ) -> LegacyCostMigrationItem:
        previous = self._migration_repo.get_item(source.id, purpose)
        source_decimal = Decimal(str(raw_amount))
        target_money = Money.of(source_decimal, currency_code)
        decision_json = json.dumps(decisions, sort_keys=True)
        if previous is not None and previous.status == LegacyCostMigrationItemStatus.MIGRATED:
            previous.last_run_id = run.id
            previous.updated_at = self._cost_entry_service._clock.now()
            return previous

        status = LegacyCostMigrationItemStatus.ELIGIBLE
        target_type = ""
        target_id = ""
        reason_code = ""
        if purpose in {LegacyCostMigrationPurpose.PLANNED, LegacyCostMigrationPurpose.COMMITMENT}:
            status = LegacyCostMigrationItemStatus.DEFERRED
            reason_code = f"LEGACY_{purpose.value.upper()}_SOURCE_VARIANT_PENDING"
        elif purpose == LegacyCostMigrationPurpose.FORECAST:
            status = LegacyCostMigrationItemStatus.DEFERRED
            reason_code = "LEGACY_FORECAST_PHASE_D_TARGET_PENDING"
        elif not default_cost_code_id:
            status = LegacyCostMigrationItemStatus.QUARANTINED
            reason_code = "LEGACY_DEFAULT_COST_CODE_REQUIRED"
        elif source.task_id and self._invalid_task(source.project_id, source.task_id):
            status = LegacyCostMigrationItemStatus.QUARANTINED
            reason_code = "LEGACY_TASK_PROJECT_MISMATCH"
        elif execute:
            entry = self._cost_entry_service.create_legacy_import_draft(
                project_id=source.project_id,
                legacy_cost_item_id=source.id,
                legacy_version=source.version,
                description=source.description,
                amount=target_money.amount,
                currency_code=target_money.currency.code,
                transaction_date=source.incurred_date or fallback_transaction_date,
                cost_code_id=default_cost_code_id,
                task_id=source.task_id,
            )
            status = LegacyCostMigrationItemStatus.MIGRATED
            target_type = "project_cost_entry"
            target_id = entry.id

        item = previous or LegacyCostMigrationItem.create(
            tenant_id=run.tenant_id,
            organization_id=run.organization_id,
            project_id=source.project_id,
            legacy_cost_item_id=source.id,
            purpose=purpose,
            status=status,
            run_id=run.id,
            source_amount=source_decimal,
            target_amount=target_money.amount,
            rounding_delta=target_money.amount - source_decimal,
            currency_code=target_money.currency.code,
        )
        item.status = status
        item.last_run_id = run.id
        item.source_amount = source_decimal
        item.target_amount = target_money.amount
        item.rounding_delta = target_money.amount - source_decimal
        item.currency_code = target_money.currency.code
        item.target_type = target_type
        item.target_id = target_id
        item.reason_code = reason_code
        item.decision_json = decision_json
        item.updated_at = self._cost_entry_service._clock.now()
        return item

    def _resolve_currency(self, explicit, profile, project) -> str:
        try:
            return resolve_pm_currency(
                tenant_context_service=self._tenant_context_service,
                operation_label="migrate legacy project finance data",
                explicit=explicit,
                project_default=(profile.currency_code if profile else getattr(project, "currency", None)),
            )
        except ValidationError as exc:
            raise BusinessRuleError(
                "Legacy cost currency cannot be resolved.",
                code="LEGACY_COST_CURRENCY_UNRESOLVED",
            ) from exc

    def _invalid_task(self, project_id: str, task_id: str) -> bool:
        task = self._task_repo.get(task_id)
        return task is None or task.project_id != project_id

    def _actor_id(self) -> str:
        actor_id = getattr(getattr(self._user_session, "principal", None), "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for legacy finance migration.",
                code="LEGACY_COST_MIGRATION_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _record_audit(self, run: LegacyCostMigrationRun) -> None:
        try:
            record_audit_entry(
                self,
                operation="project_finance.legacy_cost_migration",
                entity_type="legacy_cost_migration_run",
                entity_id=run.id,
                entity_parent_id=run.project_id,
                module="project_management",
                new_value=run.summary_json,
                workspace_id=run.project_id,
                severity="high",
                compliance_tag="financial",
                metadata={"mode": run.mode.value},
                commit=False,
                fail_closed=True,
            )
        except Exception:
            self._session.rollback()
            raise


__all__ = ["LegacyCostMigrationResult", "LegacyCostMigrationService"]
