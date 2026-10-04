"""PM approval registration must supply exact reviewer authority per request type."""

from src.core.modules.project_management.contracts.approval import (
    PM_APPROVAL_REVIEW_PERMISSIONS,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_PERMISSIONS,
)
from src.infra.composition.modules.project_registry import (
    _register_project_management_approval_handlers,
)


class _ApprovalRegistration:
    def __init__(self):
        self.apply_permissions = {}
        self.reject_types = set()

    def register_apply_handler(self, request_type, handler, *, dependencies_factory,
                               reviewer_permission):
        self.apply_permissions[request_type] = reviewer_permission

    def register_reject_handler(self, request_type, handler, *, dependencies_factory):
        self.reject_types.add(request_type)


def test_every_registered_pm_approval_has_a_specific_catalog_permission():
    registration = _ApprovalRegistration()
    _register_project_management_approval_handlers(approval_service=registration)

    assert registration.apply_permissions == PM_APPROVAL_REVIEW_PERMISSIONS
    assert registration.reject_types <= registration.apply_permissions.keys()
    assert all(permission != "approval.decide" for permission in registration.apply_permissions.values())
    assert set(registration.apply_permissions.values()) <= DEFAULT_PERMISSIONS.keys()
