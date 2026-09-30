"""Unsafe recipient selection evidence; replace with scoped rejection in R7B."""

from types import SimpleNamespace
from unittest.mock import Mock

from src.core.platform.application.approval.approval_service import ApprovalService


def test_current_recipient_lookup_includes_other_tenant_role_bindings():
    service = ApprovalService.__new__(ApprovalService)
    service._permission_repo = Mock()
    service._permission_repo.get_by_code.return_value = SimpleNamespace(id="permission")
    service._role_permission_repo = Mock()
    service._role_permission_repo.list_role_ids_for_permission.return_value = [
        "reviewer"
    ]
    service._role_binding_repo = Mock()
    service._role_binding_repo.list_active_for_role_across_tenants.return_value = [
        SimpleNamespace(
            principal_type="user", principal_id="foreign-user", tenant_id="foreign"
        )
    ]
    service._role_binding_repo.list_active_for_role.return_value = [
        SimpleNamespace(
            principal_type="user", principal_id="local-user", tenant_id="local"
        )
    ]
    assert service._list_users_with_permission(
        "approval.decide", tenant_id="local"
    ) == {"local-user", "foreign-user"}
