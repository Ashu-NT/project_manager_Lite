from __future__ import annotations

import csv
from pathlib import Path

from src.core.platform.common.runtime_access import enforce_runtime_access
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.importing.application.import_definition_registry import (
    ImportDefinitionRegistry,
)
from src.core.platform.importing.domain import (
    ImportFieldSpec,
    ImportPreview,
    ImportSourceRow,
    ImportSummary,
)
from src.core.platform.modules import SupportsModuleEntitlements
from src.core.platform.runtime_tracking import RuntimeExecutionService


class CsvImportRuntime:
    def __init__(
        self,
        registry: ImportDefinitionRegistry,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
        runtime_execution_service: RuntimeExecutionService | None = None,
    ) -> None:
        self._registry = registry
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._runtime_execution_service = runtime_execution_service

    def get_import_schema(
        self,
        operation_key: str,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> tuple[ImportFieldSpec, ...]:
        definition = self._registry.get(operation_key)
        self._authorize(
            definition,
            operation_label=f"view {self._humanize_key(definition.operation_key)} import schema",
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        )
        return tuple(definition.field_specs())

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        columns, _rows = self._load_csv_source(file_path)
        return columns

    def preview_csv(
        self,
        operation_key: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> ImportPreview:
        normalized = self._registry.normalize_key(operation_key)
        definition = self._registry.get(normalized)
        self._authorize(
            definition,
            operation_label=f"preview {self._humanize_key(normalized)} import",
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        )
        columns, rows, mapping = self._prepare_rows(
            definition,
            file_path,
            column_mapping=column_mapping,
        )
        preview = definition.preview(rows[: max(1, int(max_rows))])
        preview.entity_type = normalized
        preview.available_columns = columns
        preview.mapped_columns = mapping
        return preview

    def import_csv(
        self,
        operation_key: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> ImportSummary:
        normalized = self._registry.normalize_key(operation_key)
        definition = self._registry.get(normalized)
        self._authorize(
            definition,
            operation_label=f"run {self._humanize_key(normalized)} import",
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        )
        execution = (
            self._runtime_execution_service.start_execution(
                operation_type="import",
                operation_key=normalized,
                module_code=definition.module_code,
                input_path=file_path,
            )
            if self._runtime_execution_service is not None
            else None
        )
        try:
            _columns, rows, _mapping = self._prepare_rows(
                definition,
                file_path,
                column_mapping=column_mapping,
            )
            summary = definition.execute(rows)
            summary.entity_type = normalized
            if execution is not None:
                self._runtime_execution_service.complete_execution(
                    execution,
                    created_count=getattr(summary, "created_count", 0),
                    updated_count=getattr(summary, "updated_count", 0),
                    error_count=len(getattr(summary, "row_errors", ()) or ()),
                )
            return summary
        except Exception as exc:
            if execution is not None:
                self._runtime_execution_service.fail_execution(execution, error_message=str(exc))
            raise

    def _prepare_rows(
        self,
        definition,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None,
    ) -> tuple[list[str], list[ImportSourceRow], dict[str, str | None]]:
        columns, raw_rows = self._load_csv_source(file_path)
        mapping = self._effective_mapping(tuple(definition.field_specs()), columns, column_mapping)
        rows = [
            ImportSourceRow(
                line_no=line_no,
                values={
                    key: str(raw.get(source or "", "") or "").strip() if source else ""
                    for key, source in mapping.items()
                },
            )
            for line_no, raw in raw_rows
        ]
        return columns, rows, mapping

    def _authorize(
        self,
        definition,
        *,
        operation_label: str,
        user_session: UserSessionContext | None,
        module_catalog_service: SupportsModuleEntitlements | None,
    ) -> None:
        enforce_runtime_access(
            module_catalog_service=(
                module_catalog_service
                if module_catalog_service is not None
                else self._module_catalog_service
            ),
            user_session=user_session if user_session is not None else self._user_session,
            module_code=definition.module_code,
            permission_code=definition.permission_code,
            operation_label=operation_label,
        )

    @staticmethod
    def _humanize_key(value: str) -> str:
        return str(value or "").strip().replace("_", " ") or "data"

    @staticmethod
    def _effective_mapping(
        field_specs: tuple[ImportFieldSpec, ...],
        available_columns: list[str],
        mapping: dict[str, str | None] | None,
    ) -> dict[str, str | None]:
        normalized_input = {
            str(key or "").strip().lower(): (
                str(value or "").strip().lower() if value not in (None, "") else None
            )
            for key, value in (mapping or {}).items()
        }
        available = {column.lower() for column in available_columns}
        resolved: dict[str, str | None] = {}
        for field in field_specs:
            selected = normalized_input.get(field.key)
            if selected is None and field.key in available:
                selected = field.key
            resolved[field.key] = selected if selected in available else None
        return resolved

    @staticmethod
    def _load_csv_source(file_path: str | Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
        path = Path(file_path)
        # SECURITY: Validate file path to prevent directory traversal
        resolved_path = path.resolve()
        if not str(resolved_path).startswith(str(Path(file_path).parent.resolve())):
            raise ValueError(f"Invalid file path: {file_path}")

        rows: list[tuple[int, dict[str, str]]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = [
                str(field or "").strip().lower()
                for field in (reader.fieldnames or [])
                if str(field or "").strip()
            ]
            for idx, raw in enumerate(reader, start=2):
                normalized = {
                    str(key or "").strip().lower(): str(value or "").strip()
                    for key, value in (raw or {}).items()
                    if str(key or "").strip()
                }
                if any(normalized.values()):
                    rows.append((idx, normalized))
        return columns, rows


__all__ = ["CsvImportRuntime"]
