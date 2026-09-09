from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.shared.resource_identity.contracts import ResourceIdentityFact


class SqlAlchemyResourceIdentityReader:
    """Neutral user -> Resource identity resolution, shared across modules.

    Deliberately excludes any module-specific eligibility rule (e.g. the
    Timesheets module's time-reporting eligibility policy) -- a caller that
    needs such a rule applies it on top of the resource this resolves,
    keeping this reader a pure identity mapping rather than a policy.
    """

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def resolve_resource_for_user(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> ResourceIdentityFact | None:
        rows = self._session.execute(
            select(ResourceORM.id, ResourceORM.name, ResourceORM.is_active)
            .select_from(ResourceORM)
            .join(EmployeeORM, EmployeeORM.id == ResourceORM.employee_id)
            .where(
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                ResourceORM.is_active.is_(True),
                EmployeeORM.tenant_id == tenant_id,
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.user_id == user_id,
                EmployeeORM.is_active.is_(True),
            )
            .order_by(ResourceORM.id.asc())
            .limit(2)
        ).all()
        if len(rows) != 1:
            return None
        row = rows[0]
        return ResourceIdentityFact(
            resource_id=str(row[0]),
            resource_name=str(row[1] or row[0]),
            identity_user_id=user_id,
            is_active=bool(row[2]),
        )


__all__ = ["SqlAlchemyResourceIdentityReader"]
