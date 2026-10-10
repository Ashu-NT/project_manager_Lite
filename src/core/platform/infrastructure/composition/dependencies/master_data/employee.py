"""Assemble the employee service on the shared Platform event buses."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.documents import DocumentService
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.core.platform.infrastructure.persistence.uow.employee_unit_of_work import (
    SqlAlchemyEmployeeUnitOfWorkFactory,
)
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


def build_employee_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    document_service: DocumentService,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> EmployeeService:
    employee_uow_factory = SqlAlchemyEmployeeUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return EmployeeService(
        session=session,
        employee_repo=repositories.employee_repo,
        site_repo=repositories.site_repo,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        user_repo=repositories.user_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        document_service=document_service,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        headcount_reader=SqlAlchemyEmployeeHeadcountReader(session),
        uow_factory=employee_uow_factory,
        clock=SystemClock(),
    )
