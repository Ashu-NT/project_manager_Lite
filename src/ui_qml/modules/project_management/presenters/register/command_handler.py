from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementRegisterDesktopApi,
    RegisterEntryCreateCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)

from .utils import WorkspaceMode
from .validation import optional_date, optional_int, optional_text, require_text


def resolve_entry_type(payload: dict[str, Any], *, workspace_mode: WorkspaceMode) -> str:
    if workspace_mode == "risk":
        return RegisterEntryType.RISK.value
    return optional_text(payload, "entryType") or RegisterEntryType.RISK.value


def suggest_code(
    desktop_api: ProjectManagementRegisterDesktopApi,
    payload: dict[str, Any],
) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    project_id = optional_text(payload, "projectId")
    existing = {
        str(getattr(row, "code", "") or "").upper()
        for row in (
            desktop_api.list_entries(project_id=project_id) if project_id else ()
        )
    }
    name = optional_text(payload, "title")
    return CodeGenerator().generate(
        "register",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )


def create_entry(
    desktop_api: ProjectManagementRegisterDesktopApi,
    payload: dict[str, Any],
    *,
    workspace_mode: WorkspaceMode,
) -> None:
    command = RegisterEntryCreateCommand(
        project_id=require_text(
            payload,
            "projectId",
            "Choose a project before creating a register entry.",
        ),
        entry_type=resolve_entry_type(payload, workspace_mode=workspace_mode),
        title=require_text(payload, "title", "Register title is required."),
        description=optional_text(payload, "description") or "",
        severity=optional_text(payload, "severity") or RegisterEntrySeverity.MEDIUM.value,
        status=optional_text(payload, "status") or RegisterEntryStatus.OPEN.value,
        owner_name=optional_text(payload, "ownerName"),
        due_date=optional_date(payload, "dueDate"),
        impact_summary=optional_text(payload, "impactSummary") or "",
        response_plan=optional_text(payload, "responsePlan") or "",
        code=optional_text(payload, "entryCode") or "",
    )
    desktop_api.create_entry(command)


def update_entry(
    desktop_api: ProjectManagementRegisterDesktopApi,
    payload: dict[str, Any],
    *,
    workspace_mode: WorkspaceMode,
) -> None:
    command = RegisterEntryUpdateCommand(
        entry_id=require_text(
            payload,
            "entryId",
            "Register entry ID is required for updates.",
        ),
        project_id=require_text(
            payload,
            "projectId",
            "Choose a project before saving this register entry.",
        ),
        entry_type=resolve_entry_type(payload, workspace_mode=workspace_mode),
        title=require_text(payload, "title", "Register title is required."),
        description=optional_text(payload, "description") or "",
        severity=optional_text(payload, "severity") or RegisterEntrySeverity.MEDIUM.value,
        status=optional_text(payload, "status") or RegisterEntryStatus.OPEN.value,
        owner_name=optional_text(payload, "ownerName"),
        due_date=optional_date(payload, "dueDate"),
        impact_summary=optional_text(payload, "impactSummary") or "",
        response_plan=optional_text(payload, "responsePlan") or "",
        expected_version=optional_int(payload, "expectedVersion"),
        code=optional_text(payload, "entryCode") or "",
    )
    desktop_api.update_entry(command)


def delete_entry(
    desktop_api: ProjectManagementRegisterDesktopApi,
    entry_id: str,
) -> None:
    normalized_entry_id = (entry_id or "").strip()
    if not normalized_entry_id:
        raise ValueError("Register entry ID is required to delete an entry.")
    desktop_api.delete_entry(normalized_entry_id)
