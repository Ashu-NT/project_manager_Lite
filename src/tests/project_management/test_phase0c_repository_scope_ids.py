from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext


def _context_service(user_session: UserSessionContext) -> tuple[TenantContextService, Mock, Mock]:
    tenant_repo = Mock()
    organization_repo = Mock()
    service = TenantContextService(
        tenant_repo=tenant_repo,
        organization_repo=organization_repo,
        user_session=user_session,
    )
    return service, tenant_repo, organization_repo


def test_active_scope_ids_reads_validated_session_state_without_entity_repositories() -> None:
    user_session = UserSessionContext()
    user_session.set_active_tenant_id("tenant-a")
    user_session.set_active_organization_id("org-a")
    service, tenant_repo, organization_repo = _context_service(user_session)

    assert service.require_active_scope_ids(operation_label="query PM rows") == ActiveScopeIds(
        tenant_id="tenant-a",
        organization_id="org-a",
    )
    tenant_repo.assert_not_called()
    organization_repo.assert_not_called()
    assert not tenant_repo.method_calls
    assert not organization_repo.method_calls


@pytest.mark.parametrize(
    ("tenant_id", "organization_id", "error_code"),
    [
        (None, None, "TENANT_CONTEXT_REQUIRED"),
        ("tenant-a", None, "ORGANIZATION_CONTEXT_REQUIRED"),
    ],
)
def test_active_scope_ids_fails_closed_when_session_scope_is_incomplete(
    tenant_id: str | None,
    organization_id: str | None,
    error_code: str,
) -> None:
    user_session = UserSessionContext()
    user_session.set_active_tenant_id(tenant_id)
    user_session.set_active_organization_id(organization_id)
    service, tenant_repo, organization_repo = _context_service(user_session)

    with pytest.raises(BusinessRuleError) as exc_info:
        service.require_active_scope_ids(operation_label="query PM rows")

    assert exc_info.value.code == error_code
    assert not tenant_repo.method_calls
    assert not organization_repo.method_calls


def test_remaining_direct_pm_repositories_use_the_id_only_scope_contract(session) -> None:
    scope = ActiveScopeIds(tenant_id="tenant-a", organization_id="org-a")
    tenant_context = Mock()
    tenant_context.require_active_scope_ids.return_value = scope
    tenant_context.require_organization_context.side_effect = AssertionError(
        "PM repositories must not hydrate full tenant/organization context"
    )
    repositories = (
        SqlAlchemyProjectRepository(session),
        SqlAlchemyAssignmentRepository(session),
        SqlAlchemyDependencyRepository(session),
    )

    for repository in repositories:
        repository._tenant_context_service = tenant_context
        assert repository._context() == scope

    assert tenant_context.require_active_scope_ids.call_count == len(repositories)
    tenant_context.require_organization_context.assert_not_called()
