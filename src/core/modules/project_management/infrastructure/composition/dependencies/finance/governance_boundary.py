from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernanceOperations,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)

logger = logging.getLogger(__name__)


def _prepare_finance_command_session(session: Session) -> None:
    """Release a retained SQLite read transaction before opening a fresh Finance UoW."""
    bind = session.get_bind()
    if bind.dialect.name != "sqlite" or not session.in_transaction():
        return
    logger.debug("Releasing shared SQLite session transaction before Finance command")
    session.rollback()


def build_finance_governance_boundary(
    session: Session,
    uow_factory: SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
    operations_factory: Callable[[SqlAlchemyFinanceGovernanceUnitOfWork], FinanceGovernanceOperations],
) -> FinanceGovernanceCommandBoundary:
    def build_operations(uow: FinanceGovernanceUnitOfWork) -> FinanceGovernanceOperations:
        if not isinstance(uow, SqlAlchemyFinanceGovernanceUnitOfWork):
            raise TypeError("Finance command boundary requires its configured UoW")
        return operations_factory(uow)

    return FinanceGovernanceCommandBoundary(
        uow_factory=uow_factory,
        operations_factory=build_operations,
        prepare_command=lambda: _prepare_finance_command_session(session),
    )
