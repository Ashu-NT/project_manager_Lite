from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectManagerCandidateFact,
)
from src.core.modules.project_management.domain.enums import ResourceKind, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.platform.domain.master_data.employee import EmployeeLifecycleStatus
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)


def _eligible_manager_statement(*, tenant_id: str, organization_id: str):
    return (
        select(UserORM.id, EmployeeORM.full_name)
        .join(
            UserTenantORM,
            (UserTenantORM.user_id == UserORM.id)
            & (UserTenantORM.tenant_id == tenant_id),
        )
        .join(
            EmployeeORM,
            (EmployeeORM.user_id == UserORM.id)
            & (EmployeeORM.tenant_id == tenant_id)
            & (EmployeeORM.organization_id == organization_id),
        )
        .join(
            ResourceORM,
            (ResourceORM.employee_id == EmployeeORM.id)
            & (ResourceORM.tenant_id == tenant_id)
            & (ResourceORM.organization_id == organization_id),
        )
        .where(
            UserORM.is_active.is_(True),
            UserORM.account_type == "human",
            UserTenantORM.status == "active",
            EmployeeORM.status == EmployeeLifecycleStatus.ACTIVE,
            ResourceORM.is_active.is_(True),
            ResourceORM.kind == ResourceKind.PERSON,
            ResourceORM.worker_type == WorkerType.EMPLOYEE,
        )
    )


def list_eligible_manager_candidates(
    session: Session, *, tenant_id: str, organization_id: str
) -> tuple[ProjectManagerCandidateFact, ...]:
    rows = session.execute(
        _eligible_manager_statement(tenant_id=tenant_id, organization_id=organization_id)
        .order_by(func.lower(EmployeeORM.full_name), UserORM.id)
    ).all()
    return tuple(
        ProjectManagerCandidateFact(user_id=user_id, display_name=full_name)
        for user_id, full_name in rows
    )


def is_eligible_manager(
    session: Session, *, tenant_id: str, organization_id: str, user_id: str
) -> bool:
    statement = _eligible_manager_statement(
        tenant_id=tenant_id, organization_id=organization_id
    ).where(UserORM.id == user_id).limit(1)
    return session.execute(statement).first() is not None


__all__ = ["is_eligible_manager", "list_eligible_manager_candidates"]
