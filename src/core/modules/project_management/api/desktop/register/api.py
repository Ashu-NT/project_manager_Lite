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
    RegisterCatalogPageDesktopDto,
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
    ) -> RegisterCatalogPageDesktopDto:
        service = self._require_register_service()
        result = service.query_catalog_page(
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
        )

        def serialize_item(item) -> RegisterEntryDesktopDto:
            return serialize_entry(
                item.entry,
                project_name_by_id={item.entry.project_id: item.project_name},
            )

        return RegisterCatalogPageDesktopDto(
            items=tuple(serialize_item(item) for item in result.items),
            urgent_items=tuple(serialize_item(item) for item in result.urgent_items),
            filtered_total=result.filtered_total,
            scope_total=result.summary.scope_total,
            scope_risk_total=result.summary.scope_risk_total,
            open_risks=result.summary.open_risks,
            open_issues=result.summary.open_issues,
            pending_changes=result.summary.pending_changes,
            active=result.summary.active,
            critical=result.summary.critical,
            overdue=result.summary.overdue,
            due_soon=result.summary.due_soon,
            page=result.page,
            page_size=result.page_size,
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
