from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.labor_posting import ApprovedTimeLaborPostingRepository
from src.core.modules.project_management.domain.financials.labor_posting import ApprovedTimeLaborPosting
from src.core.modules.project_management.infrastructure.persistence.orm.labor_posting import ApprovedTimeLaborPostingORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import TenantScopedRepositorySupport


def _aware(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class SqlAlchemyApprovedTimeLaborPostingRepository(TenantScopedRepositorySupport, ApprovedTimeLaborPostingRepository):
    _repository_label = "Approved Time labor posting repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, posting: ApprovedTimeLaborPosting) -> None:
        ctx = self._context(operation_label="record approved time labor posting")
        if posting.tenant_id != ctx.tenant_id or posting.organization_id != ctx.organization_id:
            raise ValueError("Approved Time labor posting is outside the active scope.")
        self.session.add(ApprovedTimeLaborPostingORM(**posting.__dict__))

    def get_latest(self, time_entry_id: str, *, for_update: bool = False) -> ApprovedTimeLaborPosting | None:
        ctx = self._context(operation_label="access approved time labor posting")
        stmt = select(ApprovedTimeLaborPostingORM).where(
            ApprovedTimeLaborPostingORM.tenant_id == ctx.tenant_id,
            ApprovedTimeLaborPostingORM.organization_id == ctx.organization_id,
            ApprovedTimeLaborPostingORM.time_entry_id == time_entry_id,
        ).order_by(ApprovedTimeLaborPostingORM.source_revision.desc()).limit(1)
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        for field in ("rate_resolved_at", "approved_at", "created_at"):
            values[field] = _aware(values[field])
        return ApprovedTimeLaborPosting(**values)

    def flush(self) -> None:
        self.session.flush()


__all__ = ["SqlAlchemyApprovedTimeLaborPostingRepository"]
