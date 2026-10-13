from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.core.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.global_overview.application.action_center_service import (
    ActionCenterService,
)
from src.core.global_overview.application.global_overview_service import (
    GlobalOverviewService,
)
from src.core.modules.project_management.application.global_overview.pm_action_center_contributor import (
    ProjectManagementActionCenterContributor,
)
from src.core.modules.project_management.application.global_overview.pm_module_overview_contributor import (
    ProjectManagementModuleOverviewContributor,
)
from src.core.modules.project_management.infrastructure.composition.bundle import (
    ProjectManagementServiceBundle,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.global_overview.action_center_reader import (
    SqlAlchemyProjectManagementActionCenterReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.platform.api.desktop.notifications.notification import (
    PlatformNotificationDesktopApi,
)
from src.core.platform.application.global_overview.platform_action_center_contributor import (
    PlatformActionCenterContributor,
)
from src.core.platform.application.global_overview.platform_module_overview_contributor import (
    PlatformModuleOverviewContributor,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)
from src.core.platform.infrastructure.persistence.read.global_overview.action_center_reader import (
    SqlAlchemyPlatformActionCenterReader,
)

# This module is the ONLY place that knows both Platform's and Project
# Management's concrete Global Overview contributor classes at once. Every
# consumer downstream of this bundle (GlobalOverviewService, its DesktopApi)
# depends only on the generic ActionCenterContributor/ModuleSummaryContributor
# Protocols -- never on PlatformActionCenterContributor or
# ProjectManagementActionCenterContributor by name.


@dataclass(frozen=True)
class GlobalOverviewServiceBundle:
    action_center_service: ActionCenterService
    global_overview_service: GlobalOverviewService
    global_overview_desktop_api: GlobalOverviewDesktopApi
    platform_notification_desktop_api: PlatformNotificationDesktopApi


def approval_action_target_scope():
    """Reject inconsistent project parents without making Platform depend on PM."""
    return or_(
        ApprovalRequestORM.project_id.is_(None),
        select(ProjectORM.id).where(
            ProjectORM.id == ApprovalRequestORM.project_id,
            ProjectORM.tenant_id == ApprovalRequestORM.tenant_id,
            ProjectORM.organization_id == ApprovalRequestORM.organization_id,
        ).exists(),
    )


def build_global_overview_service_bundle(
    session: Session,
    platform_services: PlatformServiceBundle,
    project_management_services: ProjectManagementServiceBundle | None,
) -> GlobalOverviewServiceBundle:
    resource_identity_reader = SqlAlchemyResourceIdentityReader(session=session)
    timesheet_workspace_reader = SqlAlchemyTimesheetWorkspaceReader(
        session=session,
        resource_identity_reader=resource_identity_reader,
    )

    action_center_service = ActionCenterService(
        contributors=(
            PlatformActionCenterContributor(
                reader=SqlAlchemyPlatformActionCenterReader(session=session,
                    target_scope_predicate=approval_action_target_scope()),
            ),
            ProjectManagementActionCenterContributor(
                is_accessible=lambda: any(
                    module.code == "project_management"
                    for module in platform_services.platform_runtime_application_service.list_accessible_modules()
                ),
                reader=SqlAlchemyProjectManagementActionCenterReader(session=session,
                    resource_identity_reader=resource_identity_reader,
                    timesheet_workspace_reader=timesheet_workspace_reader),
            ),
        ) if project_management_services is not None else (
            PlatformActionCenterContributor(
                reader=SqlAlchemyPlatformActionCenterReader(
                    session=session,
                    target_scope_predicate=ApprovalRequestORM.project_id.is_(None),
                ),
            ),
        )
    )
    global_overview_service = GlobalOverviewService(
        tenant_context_service=platform_services.tenant_context_service,
        platform_runtime_application_service=(
            platform_services.platform_runtime_application_service
        ),
        activity_service=platform_services.activity_service,
        action_center_service=action_center_service,
        module_summary_contributors=(
            PlatformModuleOverviewContributor(
                approval_service=platform_services.approval_service,
            ),
            ProjectManagementModuleOverviewContributor(
                platform_runtime_application_service=(
                    platform_services.platform_runtime_application_service
                ),
                dashboard_service=project_management_services.dashboard_service,
                project_service=project_management_services.project_service,
            ),
        ) if project_management_services is not None else (
            PlatformModuleOverviewContributor(approval_service=platform_services.approval_service),
        ),
        user_session=platform_services.user_session,
    )
    return GlobalOverviewServiceBundle(
        action_center_service=action_center_service,
        global_overview_service=global_overview_service,
        global_overview_desktop_api=GlobalOverviewDesktopApi(
            global_overview_service=global_overview_service,
        ),
        platform_notification_desktop_api=PlatformNotificationDesktopApi(
            notification_service=platform_services.notification_service,
        ),
    )


__all__ = ["GlobalOverviewServiceBundle", "build_global_overview_service_bundle"]
