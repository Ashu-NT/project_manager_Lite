from __future__ import annotations


def matches_search(search_text: str, *values: str) -> bool:
    normalized = search_text.casefold()
    return any(normalized in str(value or "").casefold() for value in values)


def requisition_matches(
    row,
    search_text: str,
    site_filter: str,
    storeroom_filter: str,
) -> bool:
    if site_filter != "all" and row.requesting_site_id != site_filter:
        return False
    if storeroom_filter != "all" and row.requesting_storeroom_id != storeroom_filter:
        return False
    if not search_text:
        return True
    return matches_search(
        search_text,
        row.requisition_number,
        row.purpose,
        row.priority,
        row.requester_username,
        row.status,
        row.status_label,
        row.requesting_site_label,
        row.requesting_storeroom_label,
    )


def purchase_order_matches(
    row,
    search_text: str,
    site_filter: str,
    supplier_filter: str,
) -> bool:
    if site_filter != "all" and row.site_id != site_filter:
        return False
    if supplier_filter != "all" and row.supplier_party_id != supplier_filter:
        return False
    if not search_text:
        return True
    return matches_search(
        search_text,
        row.po_number,
        row.supplier_reference,
        row.currency_code,
        row.status,
        row.status_label,
        row.site_label,
        row.supplier_label,
        row.source_requisition_label,
    )


def normalize_filter(filter_value: str, options) -> str:
    normalized_input = (filter_value or "").strip().casefold()
    for option in options:
        if str(option.value or "").casefold() == normalized_input:
            return option.value
    return options[0].value if options else "all"
