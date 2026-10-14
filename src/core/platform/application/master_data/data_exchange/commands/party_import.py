from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.core.platform.application.master_data.data_exchange.schema import (
    _PARTY_FIELDS,
    _optional_text,
    _parse_legacy_party_type_role,
    _parse_optional_bool,
    _parse_optional_party_type,
    _text,
    preview_error_row,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.party.dto import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.domain.data_operations.importing import (
    ImportFieldSpec,
    ImportPreview,
    ImportPreviewRow,
    ImportSourceRow,
    ImportSummary,
)
from src.core.platform.domain.master_data.party import (
    PartyLifecycleStatus,
)


class PartyImportHandler:
    """Validate and apply party CSV rows through guarded application commands."""

    operation_key = "parties"
    permission_code = "settings.manage"
    module_code = ""

    def __init__(self, *, commands: PartyCommandHandler, query: PartyQueryHandler) -> None:
        self._party_commands = commands
        self._party_query = query

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return _PARTY_FIELDS

    def preview(self, rows: Sequence[ImportSourceRow]) -> ImportPreview:
        preview = ImportPreview(entity_type="parties", available_columns=[], mapped_columns={})
        for row in rows:
            code = _text(row.values.get("party_code"))
            name = _text(row.values.get("party_name"))
            if not code:
                preview.rows.append(preview_error_row(row, "Missing party_code."))
                continue
            if not name:
                preview.rows.append(preview_error_row(row, "Missing party_name."))
                continue
            try:
                existing = self._party_query.find_party_by_code(code)
                self._parse_party_payload(row.values, require_name=True)
            except Exception as exc:  # noqa: BLE001
                preview.rows.append(preview_error_row(row, str(exc)))
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

    def execute(self, rows: Sequence[ImportSourceRow]) -> ImportSummary:
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
                existing = self._party_query.find_party_by_code(code)
                if existing is None:
                    party = self._party_commands.create_party(PartyCreateCommand(party_code=code, **payload))
                    summary.created_count += 1
                else:
                    party = self._party_commands.update_party(PartyUpdateCommand(party_id=existing.id, expected_version=existing.version, **payload))
                    summary.updated_count += 1
                self._reconcile_party_status(party, row.values.get("status"), row.values.get("is_active"))
            except Exception as exc:  # noqa: BLE001
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _parse_party_payload(self, values: dict[str, str], *, require_name: bool) -> dict[str, Any]:
        # Heterogeneous keyword bag for PartyCommandHandler.create_party/update_party.
        payload: dict[str, Any] = {}
        party_name = _text(values.get("party_name"))
        if require_name or party_name:
            payload["party_name"] = party_name
        party_type = _parse_optional_party_type(values.get("party_type"))
        if party_type is not None:
            payload["party_type"] = party_type

        role_tokens = [part.strip() for part in _text(values.get("roles")).split(",") if part.strip()]
        legacy_role = _parse_legacy_party_type_role(values.get("party_type"))
        if legacy_role is not None:
            role_tokens.append(legacy_role.value)
        if role_tokens:
            payload["roles"] = role_tokens

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
            "external_reference",
            "notes",
        ):
            normalized = _optional_text(values.get(key))
            if normalized is not None:
                payload[key] = normalized

        # registration_number carries a legacy export's tax_registration_number
        # column forward when the canonical column isn't present.
        registration_number = _optional_text(values.get("registration_number"))
        if registration_number is None:
            registration_number = _optional_text(values.get("tax_registration_number"))
        if registration_number is not None:
            payload["registration_number"] = registration_number

        tax_identifier = _optional_text(values.get("tax_identifier"))
        if tax_identifier is not None:
            payload["tax_identifier"] = tax_identifier

        return payload

    def _reconcile_party_status(
        self, party, requested_status: str | None, requested_is_active: str | None
    ) -> None:
        """status is the real lifecycle column; a legacy export's is_active
        boolean column is accepted as a fallback when status isn't present."""
        target: PartyLifecycleStatus | None = None
        normalized_status = _text(requested_status).lower()
        if normalized_status:
            target = PartyLifecycleStatus(normalized_status)
        else:
            is_active = _parse_optional_bool(requested_is_active)
            if is_active is not None:
                target = PartyLifecycleStatus.ACTIVE if is_active else PartyLifecycleStatus.INACTIVE
        if target is None or target == party.status:
            return
        if target == PartyLifecycleStatus.ACTIVE:
            self._party_commands.activate_party(party.id)
        else:
            self._party_commands.deactivate_party(party.id)

