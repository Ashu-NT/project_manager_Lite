"""Concrete contributor dependencies for the shell's generic Action Center adapter."""

from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
    PROJECT_CATEGORY,
    PROJECT_LIST_SCOPE_CODE,
)
from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
    RESOURCE_CATEGORY,
    RESOURCE_LIST_SCOPE_CODE,
)
from src.core.modules.project_management.application.scheduling.baselines.event_handlers.view_invalidation import (
    BASELINE_CATEGORY,
    BASELINE_PROJECT_SCOPE_CODE,
)
from src.core.modules.project_management.application.tasks.event_handlers.view_invalidation import (
    TASK_ASSIGNMENTS_SCOPE_CODE,
    TASK_CATEGORY,
    TASK_LIST_SCOPE_CODE,
)
from src.core.platform.application.approval.event_handlers.view_invalidation import (
    APPROVAL_CATEGORY,
    APPROVAL_REQUESTS_SCOPE_CODE,
)
from src.core.platform.application.master_data.employee.event_handlers.view_invalidation import (
    EMPLOYEE_CATEGORY,
    EMPLOYEE_LIST_SCOPE_CODE,
)
from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    AUTHORIZATION_CONTEXT_CATEGORY,
    AUTHORIZATION_CONTEXT_SCOPE_CODE,
    ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE,
    ROLE_BINDING_CATEGORY,
)
from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    MODULE_ENTITLEMENT_CATEGORY,
    MODULE_ENTITLEMENTS_SCOPE_CODE,
)
from src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation import (
    TENANT_MEMBERSHIP_CATEGORY,
    TENANT_MEMBERSHIPS_SCOPE_CODE,
)
from src.core.platform.application.time_management.time.event_handlers.view_invalidation import (
    TIMESHEET_CATEGORY,
    TIMESHEET_WORKSPACE_SCOPE_CODE,
)

ACTION_CENTER_INVALIDATION_TARGETS = frozenset({
    (PROJECT_CATEGORY, PROJECT_LIST_SCOPE_CODE),
    (RESOURCE_CATEGORY, RESOURCE_LIST_SCOPE_CODE),
    (BASELINE_CATEGORY, BASELINE_PROJECT_SCOPE_CODE),
    (TASK_CATEGORY, TASK_LIST_SCOPE_CODE),
    (TASK_CATEGORY, TASK_ASSIGNMENTS_SCOPE_CODE),
    (APPROVAL_CATEGORY, APPROVAL_REQUESTS_SCOPE_CODE),
    (EMPLOYEE_CATEGORY, EMPLOYEE_LIST_SCOPE_CODE),
    (ROLE_BINDING_CATEGORY, ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE),
    (AUTHORIZATION_CONTEXT_CATEGORY, AUTHORIZATION_CONTEXT_SCOPE_CODE),
    (MODULE_ENTITLEMENT_CATEGORY, MODULE_ENTITLEMENTS_SCOPE_CODE),
    (TENANT_MEMBERSHIP_CATEGORY, TENANT_MEMBERSHIPS_SCOPE_CODE),
    (TIMESHEET_CATEGORY, TIMESHEET_WORKSPACE_SCOPE_CODE),
})
