"""Role command handlers."""

from src.core.platform.application.security.authorization.roles.commands.role_assignment import (
    RoleAssignmentHandler,
)
from src.core.platform.application.security.authorization.roles.commands.role_governance import (
    RoleGovernanceCommandHandler,
)
from src.core.platform.application.security.authorization.roles.commands.role_policy_reconciliation import (
    RolePolicyReconciliationCommandHandler,
)
from src.core.platform.application.security.authorization.roles.commands.scope_delegation_provisioning import (
    ScopeDelegationProvisioningCommandHandler,
)
from src.core.platform.application.security.authorization.roles.commands.tenant_role_commands import (
    TenantRoleCommandHandler,
)

__all__ = [
    "RoleAssignmentHandler",
    "RoleGovernanceCommandHandler",
    "RolePolicyReconciliationCommandHandler",
    "ScopeDelegationProvisioningCommandHandler",
    "TenantRoleCommandHandler",
]
