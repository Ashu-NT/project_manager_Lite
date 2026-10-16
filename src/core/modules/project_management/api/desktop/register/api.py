from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.builders.entry_list_builder import (
    build_entry_list,
)
from src.core.modules.project_management.api.desktop.register.builders.option_builder import (
    build_entry_type_options,
    build_project_options,
    build_severity_options,
    build_status_options,
)
from src.core.modules.project_management.api.desktop.register.models.options import (
    RegisterEntrySeverityDescriptor,
    RegisterEntryStatusDescriptor,
    RegisterEntryTypeDescriptor,
    RegisterProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.register.utils.register_enum_utils import (
    coerce_entry_severity,
    coerce_entry_status,
    coerce_entry_type,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.risk.dto.commands.register_entries import (
    RegisterEntryBulkStatusCommand,
    RegisterEntryCreateCommand,
    RegisterEntryDeleteCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.application.risk.dto.responses.entries import (
    RegisterEntryResponseDto,
    RegisterCatalogResponseDto,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


class ProjectManagementRegisterDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectQueryHandler | None = None,
        register_query: RegisterQueryHandler | None = None,
        register_lifecycle_commands: RegisterLifecycleHandler | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> None:
        self._project_service = project_service
        self._register_query = register_query
        self._register_lifecycle_commands = register_lifecycle_commands
        self._module_catalog_service = module_catalog_service

    def list_projects(self) -> tuple[RegisterProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_entry_types(self) -> tuple[RegisterEntryTypeDescriptor, ...]:
        return build_entry_type_options()

    def list_statuses(self) -> tuple[RegisterEntryStatusDescriptor, ...]:
        return build_status_options()

    def list_severities(self) -> tuple[RegisterEntrySeverityDescriptor, ...]:
        return build_severity_options()

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: str | RegisterEntryType | None = None,
        status: str | RegisterEntryStatus | None = None,
        severity: str | RegisterEntrySeverity | None = None,
    ) -> tuple[RegisterEntryResponseDto, ...]:
        entries = build_entry_list(
            register_query=self._register_query,
            project_id=project_id,
            entry_type=entry_type,
            status=status,
            severity=severity,
        )
        return entries

    def list_entry_page(
        self,
        *,
        project_id: str = "all",
        entry_type: str = "all",
        status: str = "all",
        severity: str = "all",
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "triage",
        sort_direction: str = "asc",
    ) -> RegisterCatalogResponseDto:
        query = self._require_register_query()
        result = query.query_catalog_page(
            project_id=None if project_id in ("", "all", "ALL") else project_id,
            entry_type=(
                None if entry_type in ("", "all", "ALL") else coerce_entry_type(entry_type)
            ),
            status=None if status in ("", "all", "ALL") else coerce_entry_status(status),
            severity=(
                None if severity in ("", "all", "ALL") else coerce_entry_severity(severity)
            ),
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

        return result

    def create_entry(
        self,
        command: RegisterEntryCreateCommand,
    ) -> RegisterEntryResponseDto:
        commands = self._require_register_lifecycle_commands()
        return commands.create_entry(command)

    def update_entry(
        self,
        command: RegisterEntryUpdateCommand,
    ) -> RegisterEntryResponseDto:
        commands = self._require_register_lifecycle_commands()
        return commands.update_entry(command)

    def delete_entry(self, command: RegisterEntryDeleteCommand) -> None:
        self._require_register_lifecycle_commands().delete_entry(command)

    def bulk_set_entry_status(
        self, command: RegisterEntryBulkStatusCommand
    ) -> tuple[RegisterEntryResponseDto, ...]:
        commands = self._require_register_lifecycle_commands()
        return tuple(commands.bulk_set_entry_status(command))

    def _require_register_query(self) -> RegisterQueryHandler:
        if self._register_query is None:
            raise ConfigurationError("Project management register desktop API is not connected.")
        return self._register_query

    def _require_register_lifecycle_commands(self) -> RegisterLifecycleHandler:
        if self._register_lifecycle_commands is None:
            raise ConfigurationError("Project management register commands are not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="manage register",
        )
        return self._register_lifecycle_commands


__all__ = ["ProjectManagementRegisterDesktopApi"]
