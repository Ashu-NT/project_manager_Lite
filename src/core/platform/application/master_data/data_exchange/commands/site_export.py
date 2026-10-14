from __future__ import annotations

import csv
from pathlib import Path

from src.core.platform.application.data_operations.exporting import (
    ensure_output_path,
)
from src.core.platform.application.master_data.data_exchange.dto import (
    MasterDataExportRequest,
)
from src.core.platform.application.master_data.data_exchange.schema import _SITE_FIELDS
from src.core.platform.application.master_data.site import (
    SiteQueryHandler,
)


class SiteExportHandler:
    operation_key = "sites"
    permission_code = "site.read"
    module_code = ""

    def __init__(self, *, query: SiteQueryHandler) -> None:
        self._site_query = query

    def export(self, request: object) -> Path:
        if not isinstance(request, MasterDataExportRequest):
            raise TypeError("MasterDataExportRequest is required.")
        rows = self._site_query.list_sites(active_only=request.active_only)
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
                        "notes": site.notes,
                    }
                )
        return output_path

