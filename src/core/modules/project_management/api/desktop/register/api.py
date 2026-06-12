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
from src.core.modules.project_management.api.desktop.register.commands.entry_commands import (
    RegisterEntryCreateCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.api.desktop.register.models.entries import (
    RegisterEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.register.models.options import (
    RegisterEntrySeverityDescriptor,
    RegisterEntryStatusDescriptor,
    RegisterEntryTypeDescriptor,
    RegisterProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.register.serializers.entry_serializer import (
    serialize_entry,
)
from src.core.modules.project_management.api.desktop.register.utils.register_enum_utils import (
    coerce_entry_severity,
    coerce_entry_status,
    coerce_entry_type,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


class ProjectManagementRegisterDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        register_service: RegisterService | None = None,
    ) -> None:
        self._project_service = project_service
        self._register_service = register_service

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
    ) -> tuple[RegisterEntryDesktopDto, ...]:
        entries = build_entry_list(
            register_service=self._register_service,
            project_id=project_id,
            entry_type=entry_type,
            status=status,
            severity=severity,
        )
        project_name_by_id = self._project_name_by_id()
        return tuple(
            serialize_entry(entry, project_name_by_id=project_name_by_id)
            for entry in entries
        )

    def create_entry(
        self,
        command: RegisterEntryCreateCommand,
    ) -> RegisterEntryDesktopDto:
        service = self._require_register_service()
        entry = service.create_entry(
            command.project_id,
            entry_type=coerce_entry_type(command.entry_type),
            title=command.title,
            description=command.description,
            severity=coerce_entry_severity(command.severity),
            status=coerce_entry_status(command.status),
            owner_name=command.owner_name,
            due_date=command.due_date,
            impact_summary=command.impact_summary,
            response_plan=command.response_plan,
            code=getattr(command, "code", ""),
        )
        return serialize_entry(entry, project_name_by_id=self._project_name_by_id())

    def update_entry(
        self,
        command: RegisterEntryUpdateCommand,
    ) -> RegisterEntryDesktopDto:
        service = self._require_register_service()
        entry = service.update_entry(
            command.entry_id,
            expected_version=command.expected_version,
            entry_type=coerce_entry_type(command.entry_type),
            title=command.title,
            description=command.description,
            severity=coerce_entry_severity(command.severity),
            status=coerce_entry_status(command.status),
            owner_name=command.owner_name,
            due_date=command.due_date,
            impact_summary=command.impact_summary,
            response_plan=command.response_plan,
            code=getattr(command, "code", ""),
        )
        return serialize_entry(entry, project_name_by_id=self._project_name_by_id())

    def delete_entry(self, entry_id: str) -> None:
        self._require_register_service().delete_entry(entry_id)

    def _project_name_by_id(self) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_projects()
        }

    def _require_register_service(self) -> RegisterService:
        if self._register_service is None:
            raise RuntimeError("Project management register desktop API is not connected.")
        return self._register_service


__all__ = ["ProjectManagementRegisterDesktopApi"]
