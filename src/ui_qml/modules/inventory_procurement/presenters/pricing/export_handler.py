from __future__ import annotations


def export_stock_status_csv(
    desktop_api,
    output_path: str,
    *,
    site_filter: str,
    storeroom_filter: str,
) -> str:
    return desktop_api.export_stock_status_csv(
        output_path,
        site_id=None if site_filter == "all" else site_filter,
        storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
    )


def export_stock_status_excel(
    desktop_api,
    output_path: str,
    *,
    site_filter: str,
    storeroom_filter: str,
) -> str:
    return desktop_api.export_stock_status_excel(
        output_path,
        site_id=None if site_filter == "all" else site_filter,
        storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
    )


def export_procurement_overview_csv(
    desktop_api,
    output_path: str,
    *,
    site_filter: str,
    storeroom_filter: str,
    supplier_filter: str,
    limit_filter: str,
) -> str:
    return desktop_api.export_procurement_overview_csv(
        output_path,
        site_id=None if site_filter == "all" else site_filter,
        storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
        supplier_party_id=None if supplier_filter == "all" else supplier_filter,
        limit=int(limit_filter),
    )


def export_procurement_overview_excel(
    desktop_api,
    output_path: str,
    *,
    site_filter: str,
    storeroom_filter: str,
    supplier_filter: str,
    limit_filter: str,
) -> str:
    return desktop_api.export_procurement_overview_excel(
        output_path,
        site_id=None if site_filter == "all" else site_filter,
        storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
        supplier_party_id=None if supplier_filter == "all" else supplier_filter,
        limit=int(limit_filter),
    )
