from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    EvmBaselineTaskFact,
    EvmSeriesFacts,
)
from .sqlalchemy_finance_snapshot_reader import SqlAlchemyFinanceSnapshotReader
from .statements.finance_snapshot_statements import (
    evm_baseline_statement,
    evm_baseline_task_facts_statement,
)


class SqlAlchemyEvmSeriesReader:
    """Acquire all scoped source facts needed for an EVM time series."""

    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._finance_reader = SqlAlchemyFinanceSnapshotReader(session=session)

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        baseline_id: str | None,
        as_of: date,
    ) -> EvmSeriesFacts | None:
        finance = self._finance_reader.read_facts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of=as_of,
        )
        if finance is None:
            return None

        resolved_baseline_id = self._session.execute(
            evm_baseline_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                baseline_id=baseline_id,
            )
        ).scalar_one_or_none()
        baseline_tasks: tuple[EvmBaselineTaskFact, ...] = ()
        if resolved_baseline_id is not None:
            baseline_tasks = tuple(
                EvmBaselineTaskFact(
                    task_id=str(row.task_id),
                    baseline_start=row.baseline_start,
                    baseline_finish=row.baseline_finish,
                    baseline_duration_days=int(row.baseline_duration_days or 0),
                    baseline_planned_cost=float(row.baseline_planned_cost or 0.0),
                )
                for row in self._session.execute(
                    evm_baseline_task_facts_statement(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        project_id=project_id,
                        baseline_id=str(resolved_baseline_id),
                    )
                )
            )
        return EvmSeriesFacts(
            finance=finance,
            baseline_id=(None if resolved_baseline_id is None else str(resolved_baseline_id)),
            baseline_tasks=baseline_tasks,
        )


__all__ = ["SqlAlchemyEvmSeriesReader"]
