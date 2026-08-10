from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.pydantic import validated_dataclass
from src.core.platform.finance import MONEY_STORAGE


class LegacyCostMigrationMode(str, Enum):
    DRY_RUN = "dry_run"
    EXECUTE = "execute"


class LegacyCostMigrationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_QUARANTINE = "completed_with_quarantine"
    FAILED = "failed"


class LegacyCostMigrationPurpose(str, Enum):
    PLANNED = "planned"
    COMMITMENT = "commitment"
    ACTUAL = "actual"
    FORECAST = "forecast"


class LegacyCostMigrationItemStatus(str, Enum):
    ELIGIBLE = "eligible"
    MIGRATED = "migrated"
    QUARANTINED = "quarantined"
    DEFERRED = "deferred"
    SKIPPED = "skipped"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@validated_dataclass
class LegacyCostMigrationRun:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    mode: LegacyCostMigrationMode
    status: LegacyCostMigrationRunStatus
    fallback_transaction_date: date
    started_by: str
    started_at: datetime = field(default_factory=_now)
    completed_at: datetime | None = None
    summary_json: str = "{}"

    @classmethod
    def start(
        cls,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        mode: LegacyCostMigrationMode,
        fallback_transaction_date: date,
        actor_id: str,
    ) -> "LegacyCostMigrationRun":
        return cls(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            mode=mode,
            status=LegacyCostMigrationRunStatus.RUNNING,
            fallback_transaction_date=fallback_transaction_date,
            started_by=actor_id,
        )


@validated_dataclass
class LegacyCostMigrationItem:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    legacy_cost_item_id: str
    purpose: LegacyCostMigrationPurpose
    status: LegacyCostMigrationItemStatus
    last_run_id: str
    source_amount: Decimal
    target_amount: Decimal
    rounding_delta: Decimal
    currency_code: str
    target_type: str = ""
    target_id: str = ""
    reason_code: str = ""
    decision_json: str = "{}"
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.source_amount = MONEY_STORAGE.validate(self.source_amount)
        self.target_amount = MONEY_STORAGE.validate(self.target_amount)
        self.rounding_delta = MONEY_STORAGE.validate(self.rounding_delta)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        legacy_cost_item_id: str,
        purpose: LegacyCostMigrationPurpose,
        status: LegacyCostMigrationItemStatus,
        run_id: str,
        source_amount: Decimal,
        target_amount: Decimal,
        rounding_delta: Decimal,
        currency_code: str,
        target_type: str = "",
        target_id: str = "",
        reason_code: str = "",
        decision_json: str = "{}",
    ) -> "LegacyCostMigrationItem":
        return cls(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            legacy_cost_item_id=legacy_cost_item_id,
            purpose=purpose,
            status=status,
            last_run_id=run_id,
            source_amount=source_amount,
            target_amount=target_amount,
            rounding_delta=rounding_delta,
            currency_code=currency_code,
            target_type=target_type,
            target_id=target_id,
            reason_code=reason_code,
            decision_json=decision_json,
        )


__all__ = [
    "LegacyCostMigrationItem",
    "LegacyCostMigrationItemStatus",
    "LegacyCostMigrationMode",
    "LegacyCostMigrationPurpose",
    "LegacyCostMigrationRun",
    "LegacyCostMigrationRunStatus",
]
