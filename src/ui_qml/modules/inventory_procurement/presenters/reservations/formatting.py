from __future__ import annotations


def build_source_meta(row) -> str:
    source = f"{row.source_reference_type or '-'}: {row.source_reference_id or '-'}"
    requester = row.requested_by_username or "-"
    need_by = row.need_by_date_label or "-"
    return f"Source {source} | Requester {requester} | Need by {need_by}"


def can_operate(row) -> bool:
    return bool(
        row.status in {"ACTIVE", "PARTIALLY_ISSUED"}
        and float(row.remaining_qty or 0.0) > 0
    )
