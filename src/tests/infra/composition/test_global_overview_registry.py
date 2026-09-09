from __future__ import annotations

import inspect

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
from src.core.platform.api.desktop.events.notifications.notification import (
    PlatformNotificationDesktopApi,
)
from src.core.platform.application.global_overview.platform_action_center_contributor import (
    PlatformActionCenterContributor,
)


def test_registry_wires_the_expected_concrete_types(services):
    assert isinstance(services["action_center_service"], ActionCenterService)
    assert isinstance(services["global_overview_service"], GlobalOverviewService)
    assert isinstance(services["global_overview_desktop_api"], GlobalOverviewDesktopApi)
    assert isinstance(
        services["platform_notification_desktop_api"], PlatformNotificationDesktopApi
    )


def test_action_center_service_receives_both_platform_and_pm_contributors(services):
    contributors = services["action_center_service"]._contributors

    assert any(isinstance(c, PlatformActionCenterContributor) for c in contributors)
    assert any(isinstance(c, ProjectManagementActionCenterContributor) for c in contributors)


def test_global_overview_desktop_api_methods_all_succeed_end_to_end(services):
    api = services["global_overview_desktop_api"]

    assert api.get_context().ok is True
    assert api.get_attention_summary().ok is True
    assert api.list_module_summaries().ok is True
    assert api.list_action_center(limit=10).ok is True
    assert api.list_recent_activity(limit=10).ok is True


def test_platform_global_overview_contributors_never_import_project_management():
    """Guards the dependency-direction rule that only the composition root
    (global_overview_registry.py) may know both Platform's and Project
    Management's concrete Global Overview contributor classes at once --
    Platform's own contributors must never reference project_management."""
    import src.core.platform.application.global_overview.platform_action_center_contributor as platform_action_center_module
    import src.core.platform.application.global_overview.platform_module_overview_contributor as platform_module_overview_module

    for module in (platform_action_center_module, platform_module_overview_module):
        source = inspect.getsource(module)
        assert "project_management" not in source
