from __future__ import annotations


def sync_work_orders_table(table_model, catalog_dict: dict) -> None:
    table_model.set_rows(catalog_dict.get("items", []))
