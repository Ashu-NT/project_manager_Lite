from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.core.platform.exporting import ExportDefinitionRegistry, ExportRuntime, ensure_output_path
from src.core.platform.importing import (
    CsvImportRuntime,
    ImportDefinitionRegistry,
    ImportFieldSpec,
    ImportPreview,
    ImportPreviewRow,
    ImportSourceRow,
    ImportSummary,
)
from src.core.platform.org import SiteService
from src.core.platform.party import PartyService
from src.core.platform.party.domain import PartyType


_SITE_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="site_code", label="Site Code", required=True),
    ImportFieldSpec(key="name", label="Name", required=True),
    ImportFieldSpec(key="description", label="Description"),
    ImportFieldSpec(key="country", label="Country"),
    ImportFieldSpec(key="region", label="Region"),
    ImportFieldSpec(key="city", label="City"),
    ImportFieldSpec(key="address_line_1", label="Address Line 1"),
    ImportFieldSpec(key="address_line_2", label="Address Line 2"),
    ImportFieldSpec(key="postal_code", label="Postal Code"),
    ImportFieldSpec(key="timezone", label="Timezone"),
    ImportFieldSpec(key="currency_code", label="Currency Code"),
    ImportFieldSpec(key="site_type", label="Site Type"),
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="default_calendar_id", label="Default Calendar"),
    ImportFieldSpec(key="default_language", label="Default Language"),
    ImportFieldSpec(key="is_active", label="Is Active"),
    ImportFieldSpec(key="notes", label="Notes"),
)

_PARTY_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="party_code", label="Party Code", required=True),
    ImportFieldSpec(key="party_name", label="Party Name", required=True),
    ImportFieldSpec(key="party_type", label="Party Type"),
    ImportFieldSpec(key="legal_name", label="Legal Name"),
    ImportFieldSpec(key="contact_name", label="Contact Name"),
    ImportFieldSpec(key="email", label="Email"),
    ImportFieldSpec(key="phone", label="Phone"),
    ImportFieldSpec(key="country", label="Country"),
    ImportFieldSpec(key="city", label="City"),
    ImportFieldSpec(key="address_line_1", label="Address Line 1"),
    ImportFieldSpec(key="address_line_2", label="Address Line 2"),
    ImportFieldSpec(key="postal_code", label="Postal Code"),
    ImportFieldSpec(key="website", label="Website"),
    ImportFieldSpec(key="tax_registration_number", label="Tax Registration Number"),
    ImportFieldSpec(key="external_reference", label="External Reference"),
    ImportFieldSpec(key="is_active", label="Is Active"),
    ImportFieldSpec(key="notes", label="Notes"),
)


def _text(value: str | None) -> str:
    return str(value or "").strip()


def _optional_text(value: str | None) -> str | None:
    normalized = _text(value)
    return normalized or None


def _parse_optional_bool(value: str | None) -> bool | None:
    normalized = _text(value).lower()
    if not normalized:
        return None
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError("Value must be a boolean token such as true/false or yes/no.")


def _parse_optional_party_type(value: str | None) -> PartyType | None:
    normalized = _text(value).upper()
    if not normalized:
        return None
    return PartyType(normalized)


@dataclass(frozen=True)
class MasterDataExportRequest:
    output_path: Path
    active_only: bool | None = None


@dataclass(frozen=True)
class _CallbackImportDefinition:
    operation_key: str
    field_specs_value: tuple[ImportFieldSpec, ...]
    preview_handler: Callable[[list[ImportSourceRow]], ImportPreview]
    execute_handler: Callable[[list[ImportSourceRow]], ImportSummary]
    permission_code: str = "settings.manage"
    module_code: str = ""

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return self.field_specs_value

    def preview(self, rows) -> ImportPreview:
        return self.preview_handler(list(rows))

    def execute(self, rows) -> ImportSummary:
        return self.execute_handler(list(rows))


@dataclass(frozen=True)
class _CallbackExportDefinition:
    operation_key: str
    permission_code: str
    export_handler: Callable[[MasterDataExportRequest], Path]
    module_code: str = ""

    def export(self, request: object) -> Path:
        if not isinstance(request, MasterDataExportRequest):
            raise TypeError("MasterDataExportRequest is required.")
        return self.export_handler(request)


class MasterDataExchangeService:
    def __init__(
        self,
        *,
        site_service: SiteService,
        party_service: PartyService,
        user_session=None,
    ) -> None:
        self._site_service = site_service
        self._party_service = party_service
        self._user_session = user_session

        import_registry = ImportDefinitionRegistry()
        import_registry.register(
            _CallbackImportDefinition(
                operation_key="sites",
                field_specs_value=_SITE_FIELDS,
                preview_handler=self._preview_sites,
                execute_handler=self._import_sites,
            )
        )
        import_registry.register(
            _CallbackImportDefinition(
                operation_key="parties",
                field_specs_value=_PARTY_FIELDS,
                preview_handler=self._preview_parties,
                execute_handler=self._import_parties,
            )
        )
        export_registry = ExportDefinitionRegistry()
        export_registry.register(
            _CallbackExportDefinition(
                operation_key="sites",
                permission_code="site.read",
                export_handler=self._export_sites,
            )
        )
        export_registry.register(
            _CallbackExportDefinition(
                operation_key="parties",
                permission_code="party.read",
                export_handler=self._export_parties,
            )
        )
        self._import_runtime = CsvImportRuntime(import_registry, user_session=user_session)
        self._export_runtime = ExportRuntime(export_registry, user_session=user_session)

    def get_import_schema(self, entity_type: str) -> tuple[ImportFieldSpec, ...]:
        return self._import_runtime.get_import_schema(entity_type, user_session=self._user_session)

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        return self._import_runtime.read_csv_columns(file_path)

    def preview_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
    ) -> ImportPreview:
        return self._import_runtime.preview_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
            max_rows=max_rows,
            user_session=self._user_session,
        )

    def import_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
    ) -> ImportSummary:
        return self._import_runtime.import_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
            user_session=self._user_session,
        )

    def export_csv(
        self,
        entity_type: str,
        output_path: str | Path,
        *,
        active_only: bool | None = None,
    ):
        return self._export_runtime.export(
            entity_type,
            MasterDataExportRequest(output_path=Path(output_path), active_only=active_only),
            user_session=self._user_session,
        )

    def _preview_sites(self, rows: list[ImportSourceRow]) -> ImportPreview:
        preview = ImportPreview(entity_type="sites", available_columns=[], mapped_columns={})
        for row in rows:
            code = _text(row.values.get("site_code"))
            name = _text(row.values.get("name"))
            if not code:
                preview.rows.append(self._preview_error_row(row, "Missing site_code."))
                continue
            if not name:
                preview.rows.append(self._preview_error_row(row, "Missing name."))
                continue
            try:
                existing = self._site_service.find_site_by_code(code)
                self._parse_site_payload(row.values, require_name=True)
            except Exception as exc:
                preview.rows.append(self._preview_error_row(row, str(exc)))
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

    def _preview_parties(self, rows: list[ImportSourceRow]) -> ImportPreview:
        preview = ImportPreview(entity_type="parties", available_columns=[], mapped_columns={})
        for row in rows:
            code = _text(row.values.get("party_code"))
            name = _text(row.values.get("party_name"))
            if not code:
                preview.rows.append(self._preview_error_row(row, "Missing party_code."))
                continue
            if not name:
                preview.rows.append(self._preview_error_row(row, "Missing party_name."))
                continue
            try:
                existing = self._party_service.find_party_by_code(code)
                self._parse_party_payload(row.values, require_name=True)
            except Exception as exc:
                preview.rows.append(self._preview_error_row(row, str(exc)))
                continue
            preview.rows.append(
                ImportPreviewRow(
                    line_no=row.line_no,
                    status="READY",
                    action="UPDATE" if existing is not None else "CREATE",
                    message="Will update existing party." if existing is not None else "Will create party.",
                    row=dict(row.values),
                )
            )
            if existing is not None:
                preview.updated_count += 1
            else:
                preview.created_count += 1
        return preview

    def _import_sites(self, rows: list[ImportSourceRow]) -> ImportSummary:
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
                existing = self._site_service.find_site_by_code(code)
                if existing is None:
                    self._site_service.create_site(site_code=code, **payload)
                    summary.created_count += 1
                else:
                    self._site_service.update_site(existing.id, expected_version=existing.version, **payload)
                    summary.updated_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _import_parties(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="parties")
        for row in rows:
            code = _text(row.values.get("party_code"))
            name = _text(row.values.get("party_name"))
            if not code:
                summary.add_row_error(line_no=row.line_no, field_key="party_code", message="party_code is required.")
                continue
            if not name:
                summary.add_row_error(line_no=row.line_no, field_key="party_name", message="party_name is required.")
                continue
            try:
                payload = self._parse_party_payload(row.values, require_name=True)
                existing = self._party_service.find_party_by_code(code)
                if existing is None:
                    self._party_service.create_party(party_code=code, **payload)
                    summary.created_count += 1
                else:
                    self._party_service.update_party(existing.id, expected_version=existing.version, **payload)
                    summary.updated_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _export_sites(self, request: MasterDataExportRequest) -> Path:
        rows = self._site_service.list_sites(active_only=request.active_only)
        output_path = ensure_output_path(request.output_path)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[field.key for field in _SITE_FIELDS])
            writer.writeheader()
            for site in rows:
                writer.writerow(
                    {
                        "site_code": site.site_code,
                        "name": site.name,
                        "description": site.description,
                        "country": site.country,
                        "region": site.region,
                        "city": site.city,
                        "address_line_1": site.address_line_1,
                        "address_line_2": site.address_line_2,
                        "postal_code": site.postal_code,
                        "timezone": site.timezone,
                        "currency_code": site.currency_code,
                        "site_type": site.site_type,
                        "status": site.status,
                        "default_calendar_id": site.default_calendar_id,
                        "default_language": site.default_language,
                        "is_active": str(bool(site.is_active)).lower(),
                        "notes": site.notes,
                    }
                )
        return output_path

    def _export_parties(self, request: MasterDataExportRequest) -> Path:
        rows = self._party_service.list_parties(active_only=request.active_only)
        output_path = ensure_output_path(request.output_path)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[field.key for field in _PARTY_FIELDS])
            writer.writeheader()
            for party in rows:
                writer.writerow(
                    {
                        "party_code": party.party_code,
                        "party_name": party.party_name,
                        "party_type": party.party_type.value,
                        "legal_name": party.legal_name,
                        "contact_name": party.contact_name,
                        "email": party.email,
                        "phone": party.phone,
                        "country": party.country,
                        "city": party.city,
                        "address_line_1": party.address_line_1,
                        "address_line_2": party.address_line_2,
                        "postal_code": party.postal_code,
                        "website": party.website,
                        "tax_registration_number": party.tax_registration_number,
                        "external_reference": party.external_reference,
                        "is_active": str(bool(party.is_active)).lower(),
                        "notes": party.notes,
                    }
                )
        return output_path

    @staticmethod
    def _preview_error_row(row: ImportSourceRow, message: str) -> ImportPreviewRow:
        return ImportPreviewRow(
            line_no=row.line_no,
            status="ERROR",
            action="SKIP",
            message=message,
            row=dict(row.values),
        )

    def _parse_site_payload(self, values: dict[str, str], *, require_name: bool) -> dict[str, object]:
        payload: dict[str, object] = {}
        name = _text(values.get("name"))
        if require_name:
            payload["name"] = name
        elif name:
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
            "status",
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
        is_active = _parse_optional_bool(values.get("is_active"))
        if is_active is not None:
            payload["is_active"] = is_active
        return payload

    def _parse_party_payload(self, values: dict[str, str], *, require_name: bool) -> dict[str, object]:
        payload: dict[str, object] = {}
        party_name = _text(values.get("party_name"))
        if require_name:
            payload["party_name"] = party_name
        elif party_name:
            payload["party_name"] = party_name
        party_type = _parse_optional_party_type(values.get("party_type"))
        if party_type is not None:
            payload["party_type"] = party_type
        for key in (
            "legal_name",
            "contact_name",
            "email",
            "phone",
            "country",
            "city",
            "address_line_1",
            "address_line_2",
            "postal_code",
            "website",
            "tax_registration_number",
            "external_reference",
            "notes",
        ):
            normalized = _optional_text(values.get(key))
            if normalized is not None:
                payload[key] = normalized
        is_active = _parse_optional_bool(values.get("is_active"))
        if is_active is not None:
            payload["is_active"] = is_active
        return payload


__all__ = ["MasterDataExchangeService", "MasterDataExportRequest"]
