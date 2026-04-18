from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PATH_REWRITE_EXACT = {
    "core/domain/__init__.py": "core/modules/project_management/domain/__init__.py",
    "core/interfaces.py": "core/platform/common/interfaces.py",
    "core/exceptions.py": "core/platform/common/exceptions.py",
    "core/services/access/authorization.py": "src/core/platform/access/authorization.py",
    "core/services/access/domain.py": "src/core/platform/access/domain/access_scope.py",
    "core/services/access/policies.py": "src/core/platform/access/domain/feature_access.py",
    "core/services/access/service.py": "src/core/platform/access/application/access_control_service.py",
    "core/platform/access/service.py": "src/core/platform/access/application/access_control_service.py",
    "core/services/auth/query.py": "src/core/platform/auth/application/auth_query.py",
    "core/services/auth/service.py": "src/core/platform/auth/application/auth_service.py",
    "core/services/auth/validation.py": "src/core/platform/auth/application/auth_validation.py",
    "core/platform/org/__init__.py": "src/core/platform/org/__init__.py",
    "core/platform/org/domain.py": "src/core/platform/org/domain/__init__.py",
    "core/platform/org/interfaces.py": "src/core/platform/org/contracts.py",
    "core/platform/org/service.py": "src/core/platform/org/__init__.py",
    "core/platform/org/organization_service.py": "src/core/platform/org/application/organization_service.py",
    "core/platform/org/site_service.py": "src/core/platform/org/application/site_service.py",
    "core/platform/org/department_service.py": "src/core/platform/org/application/department_service.py",
    "core/platform/org/employee_service.py": "src/core/platform/org/application/employee_service.py",
    "core/platform/org/employee_support.py": "src/core/platform/org/application/employee_support.py",
    "core/platform/org/support.py": "src/core/platform/org/support.py",
    "core/platform/org/access_policy.py": "src/core/platform/org/access_policy.py",
    "core/platform/party/__init__.py": "src/core/platform/party/__init__.py",
    "core/platform/party/domain.py": "src/core/platform/party/domain/party.py",
    "core/platform/party/interfaces.py": "src/core/platform/party/contracts.py",
    "core/platform/party/service.py": "src/core/platform/party/application/party_service.py",
    "core/platform/modules/__init__.py": "src/core/platform/modules/__init__.py",
    "core/platform/modules/authorization.py": "src/core/platform/modules/application/authorization.py",
    "core/platform/modules/catalog_context.py": "src/core/platform/modules/application/module_catalog_context.py",
    "core/platform/modules/catalog_models.py": "src/core/platform/modules/domain/__init__.py",
    "core/platform/modules/catalog_mutation.py": "src/core/platform/modules/application/module_catalog_mutation.py",
    "core/platform/modules/catalog_query.py": "src/core/platform/modules/application/module_catalog_query.py",
    "core/platform/modules/contracts.py": "src/core/platform/modules/contracts.py",
    "core/platform/modules/defaults.py": "src/core/platform/modules/domain/defaults.py",
    "core/platform/modules/guard.py": "src/core/platform/modules/application/guard.py",
    "core/platform/modules/module_codes.py": "src/core/platform/modules/domain/module_codes.py",
    "core/platform/modules/repository.py": "src/core/platform/modules/contracts.py",
    "core/platform/modules/service.py": "src/core/platform/modules/application/module_catalog_service.py",
    "infra/platform/service_registration/platform_bundle.py": "src/infra/composition/platform_registry.py",
    "infra/platform/service_registration/project_management_bundle.py": "src/infra/composition/project_registry.py",
    "infra/platform/service_registration/inventory_procurement_bundle.py": "src/infra/composition/inventory_registry.py",
    "infra/platform/service_registration/maintenance_management_bundle.py": "src/infra/composition/maintenance_registry.py",
    "infra/services.py": "src/infra/composition/app_container.py",
    "ui/main_window.py": "src/ui/shell/main_window.py",
    "ui/admin/audit_tab.py": "ui/platform/control/audit/tab.py",
}

PATH_REWRITE_PREFIXES = (
    ("ui/access/", "ui/platform/admin/access/"),
    ("ui/admin/", "ui/platform/admin/"),
    ("ui/auth/", "ui/platform/shared/auth/"),
    ("ui/calendar/", "ui/modules/project_management/calendar/"),
    ("ui/collaboration/", "ui/modules/project_management/collaboration/"),
    ("ui/cost/", "ui/modules/project_management/cost/"),
    ("ui/dashboard/", "ui/modules/project_management/dashboard/"),
    ("ui/governance/", "ui/modules/project_management/governance/"),
    ("ui/portfolio/", "ui/modules/project_management/portfolio/"),
    ("ui/project/", "ui/modules/project_management/project/"),
    ("ui/register/", "ui/modules/project_management/register/"),
    ("ui/report/", "ui/modules/project_management/report/"),
    ("ui/resource/", "ui/modules/project_management/resource/"),
    ("ui/settings/", "ui/platform/settings/"),
    ("ui/shared/", "ui/platform/shared/"),
    ("ui/platform/shell/", "src/ui/shell/"),
    ("ui/shell/", "src/ui/shell/"),
    ("ui/styles/", "ui/platform/shared/styles/"),
    ("ui/support/", "ui/platform/admin/support/"),
    ("ui/task/", "ui/modules/project_management/task/"),
    ("ui/timesheet/", "ui/modules/project_management/timesheet/"),
    ("core/domain/", "core/modules/project_management/domain/"),
    ("core/events/", "core/platform/notifications/"),
    ("core/reporting/", "core/modules/project_management/reporting/"),
    ("core/services/access/", "src/core/platform/access/"),
    ("core/services/approval/", "core/platform/approval/"),
    ("core/services/audit/", "core/platform/audit/"),
    ("core/services/baseline/", "core/modules/project_management/services/baseline/"),
    ("core/services/calendar/", "core/modules/project_management/services/calendar/"),
    ("core/services/collaboration/", "core/modules/project_management/services/collaboration/"),
    ("core/services/common/", "core/modules/project_management/services/common/"),
    ("core/services/cost/", "core/modules/project_management/services/cost/"),
    ("core/services/dashboard/", "core/modules/project_management/services/dashboard/"),
    ("core/services/finance/", "core/modules/project_management/services/finance/"),
    ("core/services/import_service/", "core/modules/project_management/services/import_service/"),
    ("core/services/portfolio/", "core/modules/project_management/services/portfolio/"),
    ("core/services/project/", "core/modules/project_management/services/project/"),
    ("core/services/register/", "core/modules/project_management/services/register/"),
    ("core/services/reporting/", "core/modules/project_management/services/reporting/"),
    ("core/services/resource/", "core/modules/project_management/services/resource/"),
    ("core/services/scheduling/", "core/modules/project_management/services/scheduling/"),
    ("core/services/task/", "core/modules/project_management/services/task/"),
    ("core/services/timesheet/", "core/modules/project_management/services/timesheet/"),
    ("core/services/work_calendar/", "core/modules/project_management/services/work_calendar/"),
    ("infra/db/access/", "src/infra/persistence/db/platform/access/"),
    ("infra/db/approval/", "src/infra/persistence/db/platform/approval/"),
    ("infra/db/audit/", "src/infra/persistence/db/platform/audit/"),
    ("infra/db/auth/", "src/infra/persistence/db/platform/auth/"),
    ("infra/db/documents/", "src/infra/persistence/db/platform/documents/"),
    ("infra/db/modules/", "src/infra/persistence/db/platform/modules/"),
    ("infra/db/org/", "src/infra/persistence/db/platform/org/"),
    ("infra/db/party/", "src/infra/persistence/db/platform/party/"),
    ("infra/db/runtime_tracking/", "src/infra/persistence/db/platform/runtime_tracking/"),
    ("infra/db/time/", "src/infra/persistence/db/platform/time/"),
    ("infra/db/baseline/", "infra/modules/project_management/db/baseline/"),
    ("infra/db/collaboration/", "infra/modules/project_management/db/collaboration/"),
    ("infra/db/cost_calendar/", "infra/modules/project_management/db/cost_calendar/"),
    ("infra/db/portfolio/", "infra/modules/project_management/db/portfolio/"),
    ("infra/db/project/", "infra/modules/project_management/db/project/"),
    ("infra/db/register/", "infra/modules/project_management/db/register/"),
    ("infra/db/resource/", "infra/modules/project_management/db/resource/"),
    ("infra/db/task/", "infra/modules/project_management/db/task/"),
    ("infra/db/timesheet/", "infra/modules/project_management/db/timesheet/"),
    ("infra/db/repositories_approval.py", "src/infra/persistence/db/platform/approval/repository.py"),
    ("infra/db/repositories_audit.py", "src/infra/persistence/db/platform/audit/repository.py"),
    ("infra/db/repositories_auth.py", "src/infra/persistence/db/platform/auth/repository.py"),
    ("infra/db/repositories_baseline.py", "infra/modules/project_management/db/baseline/repository.py"),
    ("infra/db/repositories_cost_calendar.py", "infra/modules/project_management/db/cost_calendar/repository.py"),
    ("infra/db/repositories_project.py", "infra/modules/project_management/db/project/repository.py"),
    ("infra/db/repositories_register.py", "infra/modules/project_management/db/register/repository.py"),
    ("infra/db/repositories_resource.py", "infra/modules/project_management/db/resource/repository.py"),
    ("infra/db/repositories_task.py", "infra/modules/project_management/db/task/repository.py"),
    ("infra/db/repositories_timesheet.py", "src/infra/persistence/db/platform/time/repository.py"),
)


def resolve_repo_path(path: Path) -> Path:
    try:
        relative = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path
    if relative in PATH_REWRITE_EXACT:
        return REPO_ROOT / PATH_REWRITE_EXACT[relative]
    for old_prefix, new_prefix in PATH_REWRITE_PREFIXES:
        trimmed = old_prefix.rstrip("/")
        if relative == trimmed:
            return REPO_ROOT / new_prefix.rstrip("/")
        if relative.startswith(old_prefix):
            return REPO_ROOT / (new_prefix + relative[len(old_prefix) :])
    return path


__all__ = [
    "PATH_REWRITE_EXACT",
    "PATH_REWRITE_PREFIXES",
    "REPO_ROOT",
    "resolve_repo_path",
]
