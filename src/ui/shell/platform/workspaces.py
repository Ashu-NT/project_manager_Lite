from __future__ import annotations

from src.ui.platform.workspaces.admin.access.tab import AccessTab
from src.ui.platform.workspaces.admin.documents.tab import DocumentAdminTab
from src.ui.platform.workspaces.admin.departments.tab import DepartmentAdminTab
from src.ui.platform.workspaces.admin.employees.tab import EmployeeAdminTab
from src.ui.platform.workspaces.admin.modules.tab import ModuleLicensingTab
from src.ui.platform.workspaces.admin.organizations.tab import OrganizationAdminTab
from src.ui.platform.workspaces.admin.parties.tab import PartyAdminTab
from src.ui.platform.workspaces.admin.sites.tab import SiteAdminTab
from src.ui.platform.workspaces.admin.support.tab import SupportTab
from src.ui.platform.workspaces.admin.users.tab import UserAdminTab
from src.ui.platform.workspaces.control.approvals.tab import ApprovalControlTab
from src.ui.platform.workspaces.control.audit.tab import AuditLogTab
from src.ui.shell.common import (
    PLATFORM_MODULE_CODE,
    PLATFORM_MODULE_LABEL,
    ShellWorkspaceContext,
    WorkspaceDefinition,
    has_any_permission,
    has_permission,
)
from src.ui.shell.platform.home import PlatformHomeTab


def build_platform_home_workspace_definitions(context: ShellWorkspaceContext) -> list[WorkspaceDefinition]:
    if not bool(context.user_session is not None and context.user_session.is_authenticated()):
        return []
    return [
        WorkspaceDefinition(
            module_code=PLATFORM_MODULE_CODE,
            module_label=PLATFORM_MODULE_LABEL,
            group_label="Shared Services",
            label="Home",
            widget=PlatformHomeTab(
                platform_runtime_api=context.platform_runtime_desktop_api,
                user_session=context.user_session,
                parent=context.parent,
            ),
        )
    ]


def build_platform_administration_workspace_definitions(
    context: ShellWorkspaceContext,
) -> list[WorkspaceDefinition]:
    definitions: list[WorkspaceDefinition] = []

    if has_any_permission(context.user_session, "auth.read", "auth.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Users",
                widget=UserAdminTab(
                    platform_user_api=context.platform_user_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_any_permission(context.user_session, "employee.read", "employee.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Employees",
                widget=EmployeeAdminTab(
                    platform_employee_api=context.platform_employee_desktop_api,
                    platform_site_api=context.platform_site_desktop_api,
                    platform_department_api=context.platform_department_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_permission(context.user_session, "settings.manage"):
        definitions.extend(
            [
                WorkspaceDefinition(
                    module_code=PLATFORM_MODULE_CODE,
                    module_label=PLATFORM_MODULE_LABEL,
                    group_label="Administration",
                    label="Organizations",
                    widget=OrganizationAdminTab(
                        platform_runtime_api=context.platform_runtime_desktop_api,
                        user_session=context.user_session,
                        parent=context.parent,
                    ),
                ),
                WorkspaceDefinition(
                    module_code=PLATFORM_MODULE_CODE,
                    module_label=PLATFORM_MODULE_LABEL,
                    group_label="Administration",
                label="Sites",
                widget=SiteAdminTab(
                    platform_site_api=context.platform_site_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
                ),
                WorkspaceDefinition(
                    module_code=PLATFORM_MODULE_CODE,
                    module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Departments",
                widget=DepartmentAdminTab(
                    platform_department_api=context.platform_department_desktop_api,
                    platform_site_api=context.platform_site_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
                ),
                WorkspaceDefinition(
                    module_code=PLATFORM_MODULE_CODE,
                    module_label=PLATFORM_MODULE_LABEL,
                    group_label="Administration",
                    label="Documents",
                    widget=DocumentAdminTab(
                        platform_document_api=context.platform_document_desktop_api,
                        user_session=context.user_session,
                        parent=context.parent,
                    ),
                ),
                WorkspaceDefinition(
                    module_code=PLATFORM_MODULE_CODE,
                    module_label=PLATFORM_MODULE_LABEL,
                    group_label="Administration",
                    label="Parties",
                    widget=PartyAdminTab(
                        platform_party_api=context.platform_party_desktop_api,
                        user_session=context.user_session,
                        parent=context.parent,
                    ),
                ),
            ]
        )

    if has_permission(context.user_session, "access.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Access",
                widget=AccessTab(
                    platform_access_api=context.platform_access_desktop_api,
                    platform_user_api=context.platform_user_desktop_api,
                    scope_type_choices=context.access_scope_type_choices,
                    scope_option_loaders=context.access_scope_option_loaders,
                    scope_disabled_hints=context.access_scope_disabled_hints,
                    show_access_tab=True,
                    show_security_tab=False,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_any_permission(context.user_session, "auth.manage", "security.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Security",
                widget=AccessTab(
                    platform_access_api=context.platform_access_desktop_api,
                    platform_user_api=context.platform_user_desktop_api,
                    show_access_tab=False,
                    show_security_tab=True,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_any_permission(context.user_session, "approval.request", "approval.decide"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Control",
                label="Approvals",
                widget=ApprovalControlTab(
                    platform_approval_api=context.platform_approval_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_permission(context.user_session, "audit.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Control",
                label="Audit",
                widget=AuditLogTab(
                    platform_audit_api=context.platform_audit_desktop_api,
                    parent=context.parent,
                ),
            )
        )

    if has_permission(context.user_session, "support.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Support",
                widget=SupportTab(
                    settings_store=context.settings_store,
                    user_session=context.user_session,
                ),
            )
        )

    if has_permission(context.user_session, "settings.manage") and context.platform_runtime_desktop_api is not None:
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Modules",
                widget=ModuleLicensingTab(
                    platform_runtime_api=context.platform_runtime_desktop_api,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    return definitions


__all__ = [
    "build_platform_administration_workspace_definitions",
    "build_platform_home_workspace_definitions",
]
