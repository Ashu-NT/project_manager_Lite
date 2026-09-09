from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.application.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.application.global_overview.services.action_center_service import ActionCenterService
from src.core.application.global_overview.services.global_overview_service import (
    GlobalOverviewService,
)
from src.core.modules.project_management.application.global_overview.pm_action_center_contributor import (
    ProjectManagementActionCenterContributor,
)
from src.core.modules.project_management.application.global_overview.pm_module_overview_contributor import (
    ProjectManagementModuleOverviewContributor,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.platform.api.desktop.events.notifications.notification import (
    PlatformNotificationDesktopApi,
)
from src.core.platform.application.global_overview.platform_action_center_contributor import (
    PlatformActionCenterContributor,
)
from src.core.platform.application.global_overview.platform_module_overview_contributor import (
    PlatformModuleOverviewContributor,
)
from src.infra.composition.platform_registry import PlatformServiceBundle
from src.infra.composition.project_registry import ProjectManagementServiceBundle

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


def build_global_overview_service_bundle(
    session: Session,
    platform_services: PlatformServiceBundle,
    project_management_services: ProjectManagementServiceBundle,
) -> GlobalOverviewServiceBundle:
    resource_identity_reader = SqlAlchemyResourceIdentityReader(session=session)
    timesheet_workspace_reader = SqlAlchemyTimesheetWorkspaceReader(
        session=session,
        resource_identity_reader=resource_identity_reader,
    )

    action_center_service = ActionCenterService(
        contributors=(
            PlatformActionCenterContributor(
                approval_service=platform_services.approval_service,
                platform_runtime_application_service=(
                    platform_services.platform_runtime_application_service
                ),
            ),
            ProjectManagementActionCenterContributor(
                task_service=project_management_services.task_service,
                baseline_service=project_management_services.baseline_service,
                project_service=project_management_services.project_service,
                resource_identity_reader=resource_identity_reader,
                timesheet_workspace_reader=timesheet_workspace_reader,
                user_session=platform_services.user_session,
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
