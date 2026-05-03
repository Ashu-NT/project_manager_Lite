from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)


@dataclass(frozen=True)
class RegisterProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntryTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntryStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntrySeverityDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntryDesktopDto:
    id: str
    project_id: str
    project_name: str
    entry_type: str
    entry_type_label: str
    title: str
    description: str
    severity: str
    severity_label: str
    status: str
    status_label: str
    owner_name: str | None
    due_date: date | None
    due_date_label: str
    impact_summary: str
    response_plan: str
    is_overdue: bool
    version: int


@dataclass(frozen=True)
class RegisterEntryCreateCommand:
    project_id: str
    entry_type: str = RegisterEntryType.RISK.value
    title: str = ""
    description: str = ""
    severity: str = RegisterEntrySeverity.MEDIUM.value
    status: str = RegisterEntryStatus.OPEN.value
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""


@dataclass(frozen=True)
class RegisterEntryUpdateCommand:
    entry_id: str
    project_id: str
    entry_type: str = RegisterEntryType.RISK.value
    title: str = ""
    description: str = ""
    severity: str = RegisterEntrySeverity.MEDIUM.value
    status: str = RegisterEntryStatus.OPEN.value
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""
    expected_version: int | None = None


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
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            RegisterProjectOptionDescriptor(
                value=project.id,
                label=project.name,
            )
            for project in projects
        )

    def list_entry_types(self) -> tuple[RegisterEntryTypeDescriptor, ...]:
        return tuple(
            RegisterEntryTypeDescriptor(
                value=entry_type.value,
                label=_format_enum_label(entry_type.value),
            )
            for entry_type in RegisterEntryType
        )

    def list_statuses(self) -> tuple[RegisterEntryStatusDescriptor, ...]:
        return tuple(
            RegisterEntryStatusDescriptor(
                value=status.value,
                label=_format_enum_label(status.value),
            )
            for status in RegisterEntryStatus
        )

    def list_severities(self) -> tuple[RegisterEntrySeverityDescriptor, ...]:
        return tuple(
            RegisterEntrySeverityDescriptor(
                value=severity.value,
                label=_format_enum_label(severity.value),
            )
            for severity in RegisterEntrySeverity
        )

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: str | RegisterEntryType | None = None,
        status: str | RegisterEntryStatus | None = None,
        severity: str | RegisterEntrySeverity | None = None,
    ) -> tuple[RegisterEntryDesktopDto, ...]:
        if self._register_service is None:
            return ()
        entries = sorted(
            self._register_service.list_entries(
                project_id=(project_id or None),
                entry_type=(
                    _coerce_entry_type(entry_type)
                    if entry_type not in (None, "", "all", "ALL")
                    else None
                ),
                status=(
                    _coerce_entry_status(status)
                    if status not in (None, "", "all", "ALL")
                    else None
                ),
                severity=(
                    _coerce_entry_severity(severity)
                    if severity not in (None, "", "all", "ALL")
                    else None
                ),
            ),
            key=lambda entry: (
                _severity_rank(entry.severity),
                0 if _is_overdue(entry.due_date, entry.status) else 1,
                entry.due_date or date.max,
                (entry.title or "").casefold(),
            ),
        )
        project_name_by_id = {
            option.value: option.label
            for option in self.list_projects()
        }
        return tuple(
            self._serialize_entry(entry, project_name_by_id=project_name_by_id)
            for entry in entries
        )

    def create_entry(
        self,
        command: RegisterEntryCreateCommand,
    ) -> RegisterEntryDesktopDto:
        service = self._require_register_service()
        entry = service.create_entry(
            command.project_id,
            entry_type=_coerce_entry_type(command.entry_type),
            title=command.title,
            description=command.description,
            severity=_coerce_entry_severity(command.severity),
            status=_coerce_entry_status(command.status),
            owner_name=command.owner_name,
            due_date=command.due_date,
            impact_summary=command.impact_summary,
            response_plan=command.response_plan,
        )
        project_name_by_id = {
            option.value: option.label
            for option in self.list_projects()
        }
        return self._serialize_entry(entry, project_name_by_id=project_name_by_id)

    def update_entry(
        self,
        command: RegisterEntryUpdateCommand,
    ) -> RegisterEntryDesktopDto:
        service = self._require_register_service()
        entry = service.update_entry(
            command.entry_id,
            expected_version=command.expected_version,
            entry_type=_coerce_entry_type(command.entry_type),
            title=command.title,
            description=command.description,
            severity=_coerce_entry_severity(command.severity),
            status=_coerce_entry_status(command.status),
            owner_name=command.owner_name,
            due_date=command.due_date,
            impact_summary=command.impact_summary,
            response_plan=command.response_plan,
        )
        project_name_by_id = {
            option.value: option.label
            for option in self.list_projects()
        }
        return self._serialize_entry(entry, project_name_by_id=project_name_by_id)

    def delete_entry(self, entry_id: str) -> None:
        self._require_register_service().delete_entry(entry_id)

    def _require_register_service(self) -> RegisterService:
        if self._register_service is None:
            raise RuntimeError("Project management register desktop API is not connected.")
        return self._register_service

    @staticmethod
    def _serialize_entry(
        entry,
        *,
        project_name_by_id: dict[str, str],
    ) -> RegisterEntryDesktopDto:
        entry_type = as_register_entry_type(entry.entry_type)
        severity = as_register_entry_severity(entry.severity)
        status = as_register_entry_status(entry.status)
        return RegisterEntryDesktopDto(
            id=entry.id,
            project_id=entry.project_id,
            project_name=project_name_by_id.get(entry.project_id, entry.project_id),
            entry_type=entry_type.value,
            entry_type_label=_format_enum_label(entry_type.value),
            title=entry.title,
            description=entry.description or "",
            severity=severity.value,
            severity_label=_format_enum_label(severity.value),
            status=status.value,
            status_label=_format_enum_label(status.value),
            owner_name=entry.owner_name,
            due_date=entry.due_date,
            due_date_label=entry.due_date.isoformat() if entry.due_date else "No due date",
            impact_summary=entry.impact_summary or "",
            response_plan=entry.response_plan or "",
            is_overdue=_is_overdue(entry.due_date, status),
            version=int(entry.version or 1),
        )


def build_project_management_register_desktop_api(
    *,
    project_service: ProjectService | None = None,
    register_service: RegisterService | None = None,
) -> ProjectManagementRegisterDesktopApi:
    return ProjectManagementRegisterDesktopApi(
        project_service=project_service,
        register_service=register_service,
    )


def _coerce_entry_type(value: str | RegisterEntryType | None) -> RegisterEntryType:
    if isinstance(value, RegisterEntryType):
        return value
    return as_register_entry_type(value or RegisterEntryType.RISK.value)


def _coerce_entry_status(
    value: str | RegisterEntryStatus | None,
) -> RegisterEntryStatus:
    if isinstance(value, RegisterEntryStatus):
        return value
    return as_register_entry_status(value or RegisterEntryStatus.OPEN.value)


def _coerce_entry_severity(
    value: str | RegisterEntrySeverity | None,
) -> RegisterEntrySeverity:
    if isinstance(value, RegisterEntrySeverity):
        return value
    return as_register_entry_severity(value or RegisterEntrySeverity.MEDIUM.value)


def _format_enum_label(value: str) -> str:
    return value.replace("_", " ").title()


def _severity_rank(value: RegisterEntrySeverity | str) -> int:
    resolved = as_register_entry_severity(value)
    order = {
        RegisterEntrySeverity.CRITICAL: 0,
        RegisterEntrySeverity.HIGH: 1,
        RegisterEntrySeverity.MEDIUM: 2,
        RegisterEntrySeverity.LOW: 3,
    }
    return order.get(resolved, 99)


def _is_overdue(
    due_date: date | None,
    status: RegisterEntryStatus | str,
) -> bool:
    if due_date is None:
        return False
    resolved_status = as_register_entry_status(status)
    if resolved_status in {
        RegisterEntryStatus.APPROVED,
        RegisterEntryStatus.REJECTED,
        RegisterEntryStatus.CLOSED,
    }:
        return False
    return due_date < date.today()


__all__ = [
    "ProjectManagementRegisterDesktopApi",
    "RegisterEntryCreateCommand",
    "RegisterEntryDesktopDto",
    "RegisterEntrySeverityDescriptor",
    "RegisterEntryStatusDescriptor",
    "RegisterEntryTypeDescriptor",
    "RegisterEntryUpdateCommand",
    "RegisterProjectOptionDescriptor",
    "build_project_management_register_desktop_api",
]
