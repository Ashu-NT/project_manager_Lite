from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.platform.auth import UserSessionContext
from ui.platform.settings import MainWindowSettingsStore
from src.ui.shell.common import (
    ShellWorkspaceContext,
    WorkspaceDefinition,
    build_shell_workspace_context,
)
from src.ui.shell.inventory_procurement import (
    build_inventory_procurement_workspace_definitions,
)
from src.ui.shell.maintenance_management import (
    build_maintenance_management_workspace_definitions,
)
from src.ui.shell.platform import (
    build_platform_administration_workspace_definitions,
    build_platform_home_workspace_definitions,
)
from src.ui.shell.project_management import (
    build_project_management_workspace_definitions,
)


def build_workspace_definitions(
    *,
    services: dict[str, object],
    settings_store: MainWindowSettingsStore,
    user_session: UserSessionContext | None,
    parent: QWidget | None = None,
) -> list[WorkspaceDefinition]:
    context = build_shell_workspace_context(
        services=services,
        settings_store=settings_store,
        user_session=user_session,
        parent=parent,
    )
    return _build_workspace_definitions_from_context(context)


def _build_workspace_definitions_from_context(
    context: ShellWorkspaceContext,
) -> list[WorkspaceDefinition]:
    definitions: list[WorkspaceDefinition] = []
    definitions.extend(build_platform_home_workspace_definitions(context))
    definitions.extend(build_project_management_workspace_definitions(context))
    definitions.extend(build_inventory_procurement_workspace_definitions(context))
    definitions.extend(build_maintenance_management_workspace_definitions(context))
    definitions.extend(build_platform_administration_workspace_definitions(context))
    return definitions


__all__ = ["WorkspaceDefinition", "build_workspace_definitions"]
