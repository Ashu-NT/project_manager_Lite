from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PATH_REWRITE_EXACT = {
    "core/domain/__init__.py": "core/modules/project_management/domain/__init__.py",
    "core/models.py": "core/platform/common/models.py",
    "core/interfaces.py": "core/platform/common/interfaces.py",
    "core/exceptions.py": "core/platform/common/exceptions.py",
    "infra/services.py": "infra/platform/services.py",
    "infra/db/repositories.py": "infra/platform/db/repositories.py",
    "infra/db/mappers.py": "infra/platform/db/mappers.py",
    "ui/main_window.py": "ui/platform/shell/main_window.py",
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
    ("ui/shell/", "ui/platform/shell/"),
    ("ui/styles/", "ui/platform/shared/styles/"),
    ("ui/support/", "ui/platform/admin/support/"),
    ("ui/task/", "ui/modules/project_management/task/"),
    ("ui/timesheet/", "ui/modules/project_management/timesheet/"),
    ("core/domain/", "core/modules/project_management/domain/"),
    ("core/events/", "core/platform/notifications/"),
    ("core/reporting/", "core/modules/project_management/reporting/"),
    ("core/services/access/", "core/platform/access/"),
    ("core/services/approval/", "core/platform/approval/"),
    ("core/services/audit/", "core/platform/audit/"),
    ("core/services/auth/", "core/platform/auth/"),
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
    ("infra/db/access/", "infra/platform/db/access/"),
    ("infra/db/approval/", "infra/platform/db/approval/"),
    ("infra/db/audit/", "infra/platform/db/audit/"),
    ("infra/db/auth/", "infra/platform/db/auth/"),
    ("infra/db/baseline/", "infra/modules/project_management/db/baseline/"),
    ("infra/db/collaboration/", "infra/modules/project_management/db/collaboration/"),
    ("infra/db/cost_calendar/", "infra/modules/project_management/db/cost_calendar/"),
    ("infra/db/portfolio/", "infra/modules/project_management/db/portfolio/"),
    ("infra/db/project/", "infra/modules/project_management/db/project/"),
    ("infra/db/register/", "infra/modules/project_management/db/register/"),
    ("infra/db/resource/", "infra/modules/project_management/db/resource/"),
    ("infra/db/task/", "infra/modules/project_management/db/task/"),
    ("infra/db/timesheet/", "infra/modules/project_management/db/timesheet/"),
    ("infra/db/repositories_approval.py", "infra/platform/db/repositories_approval.py"),
    ("infra/db/repositories_audit.py", "infra/platform/db/repositories_audit.py"),
    ("infra/db/repositories_auth.py", "infra/platform/db/repositories_auth.py"),
    ("infra/db/repositories_baseline.py", "infra/modules/project_management/db/repositories_baseline.py"),
    ("infra/db/repositories_cost_calendar.py", "infra/modules/project_management/db/repositories_cost_calendar.py"),
    ("infra/db/repositories_project.py", "infra/modules/project_management/db/repositories_project.py"),
    ("infra/db/repositories_register.py", "infra/modules/project_management/db/repositories_register.py"),
    ("infra/db/repositories_resource.py", "infra/modules/project_management/db/repositories_resource.py"),
    ("infra/db/repositories_task.py", "infra/modules/project_management/db/repositories_task.py"),
    ("infra/db/repositories_timesheet.py", "infra/modules/project_management/db/repositories_timesheet.py"),
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
