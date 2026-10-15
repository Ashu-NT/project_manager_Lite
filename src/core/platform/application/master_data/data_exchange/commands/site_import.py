from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.core.platform.application.master_data.data_exchange.schema import (
    _SITE_FIELDS,
    _optional_text,
    _text,
    preview_error_row,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.master_data.site.dto.commands.site import (
    SiteCreateCommand,
    SiteUpdateCommand,
)
from src.core.platform.domain.data_operations.importing import (
    ImportFieldSpec,
    ImportPreview,
    ImportPreviewRow,
    ImportSourceRow,
    ImportSummary,
)
from src.core.platform.domain.master_data.site import (
    SITE_STATUS_ACTIVE,
    SITE_STATUS_ARCHIVED,
    SITE_STATUS_INACTIVE,
    normalize_site_status,
)


class SiteImportHandler:
    """Validate and apply site CSV rows through guarded application commands."""

    operation_key = "sites"
    permission_code = "settings.manage"
    module_code = ""

    def __init__(self, *, commands: SiteCommandHandler, query: SiteQueryHandler) -> None:
        self._site_commands = commands
        self._site_query = query

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return _SITE_FIELDS

    def preview(self, rows: Sequence[ImportSourceRow]) -> ImportPreview:
        preview = ImportPreview(entity_type="sites", available_columns=[], mapped_columns={})
        for row in rows:
            code = _text(row.values.get("site_code"))
            name = _text(row.values.get("name"))
            if not code:
                preview.rows.append(preview_error_row(row, "Missing site_code."))
                continue
            if not name:
                preview.rows.append(preview_error_row(row, "Missing name."))
                continue
            try:
                existing = self._site_query.find_site_by_code(code)
                self._parse_site_payload(row.values, require_name=True)
            except Exception as exc:  # noqa: BLE001
                preview.rows.append(preview_error_row(row, str(exc)))
                continue
            preview.rows.append(
                ImportPreviewRow(
                    line_no=row.line_no,
                    status="READY",
                    action="UPDATE" if existing is not None else "CREATE",
                    message="Will update existing site." if existing is not None else "Will create site.",
                    row=dict(row.values),
                )
            )
            if existing is not None:
                preview.updated_count += 1
            else:
                preview.created_count += 1
        return preview

    def execute(self, rows: Sequence[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="sites")
        for row in rows:
            code = _text(row.values.get("site_code"))
            name = _text(row.values.get("name"))
            if not code:
                summary.add_row_error(line_no=row.line_no, field_key="site_code", message="site_code is required.")
                continue
            if not name:
                summary.add_row_error(line_no=row.line_no, field_key="name", message="name is required.")
                continue
            try:
                payload = self._parse_site_payload(row.values, require_name=True)
                requested_status = _optional_text(row.values.get("status"))
                existing = self._site_query.find_site_by_code(code)
                if existing is None:
                    site = self._site_commands.create_site(SiteCreateCommand(site_code=code, **payload))
                    summary.created_count += 1
                else:
                    site = self._site_commands.update_site(SiteUpdateCommand(site_id=existing.id, expected_version=existing.version, **payload))
                    summary.updated_count += 1
                self._reconcile_site_status(site, requested_status)
            except Exception as exc:  # noqa: BLE001
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _parse_site_payload(self, values: dict[str, str], *, require_name: bool) -> dict[str, Any]:
        """Pure profile fields only -- lifecycle (status) is never part of
        create_site/update_site's payload; see _reconcile_site_status, which
        applies the CSV's status column afterward through the guarded
        activate_site/deactivate_site/archive_site transitions."""
        # Keyword bag for SiteCommandHandler.create_site/update_site.
        payload: dict[str, Any] = {}
        name = _text(values.get("name"))
        if require_name or name:
            payload["name"] = name
        for key in (
            "description",
            "country",
            "region",
            "city",
            "address_line_1",
            "address_line_2",
            "postal_code",
            "site_type",
            "default_calendar_id",
            "default_language",
            "notes",
        ):
            normalized = _optional_text(values.get(key))
            if normalized is not None:
                payload[key] = normalized
        timezone_name = _optional_text(values.get("timezone"))
        if timezone_name is not None:
            payload["timezone_name"] = timezone_name
        currency_code = _optional_text(values.get("currency_code"))
        if currency_code is not None:
            payload["currency_code"] = currency_code
        return payload

    def _reconcile_site_status(self, site, requested_status: str | None) -> None:
        if not requested_status:
            return
        target = normalize_site_status(requested_status)
        if target == site.status:
            return
        if target == SITE_STATUS_ACTIVE:
            self._site_commands.activate_site(site.id)
        elif target == SITE_STATUS_INACTIVE:
            self._site_commands.deactivate_site(site.id)
        elif target == SITE_STATUS_ARCHIVED:
            self._site_commands.archive_site(site.id)

