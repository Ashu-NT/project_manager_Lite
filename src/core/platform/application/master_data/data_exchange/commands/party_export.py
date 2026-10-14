from __future__ import annotations

import csv
from pathlib import Path

from src.core.platform.application.data_operations.exporting import (
    ensure_output_path,
)
from src.core.platform.application.master_data.data_exchange.dto import (
    MasterDataExportRequest,
)
from src.core.platform.application.master_data.data_exchange.schema import _PARTY_FIELDS
from src.core.platform.application.master_data.party import (
    PartyQueryHandler,
)


class PartyExportHandler:
    operation_key = "parties"
    permission_code = "party.read"
    module_code = ""

    def __init__(self, *, query: PartyQueryHandler) -> None:
        self._party_query = query

    def export(self, request: object) -> Path:
        if not isinstance(request, MasterDataExportRequest):
            raise TypeError("MasterDataExportRequest is required.")
        rows = self._party_query.list_parties(active_only=request.active_only)
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
                        "roles": ",".join(role.value for role in party.roles),
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
                        "registration_number": party.registration_number,
                        "tax_identifier": party.tax_identifier,
                        "external_reference": party.external_reference,
                        "status": party.status.value,
                        "notes": party.notes,
                    }
                )
        return output_path

