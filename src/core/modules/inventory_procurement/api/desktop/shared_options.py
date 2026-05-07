from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.inventory_procurement.api.desktop._support import clean_text


@dataclass(frozen=True)
class InventorySiteOptionDescriptor:
    value: str
    label: str
    currency_code: str
    is_active: bool


@dataclass(frozen=True)
class InventoryCatalogItemOptionDescriptor:
    value: str
    label: str
    stock_uom: str
    category_code: str
    is_active: bool


@dataclass(frozen=True)
class InventoryStoreroomOptionDescriptor:
    value: str
    label: str
    site_id: str
    site_label: str
    is_active: bool


@dataclass(frozen=True)
class InventoryBusinessPartyOptionDescriptor:
    value: str
    label: str
    party_type: str
    contact: str
    context: str
    is_active: bool


def serialize_site_option(row) -> InventorySiteOptionDescriptor:
    code = clean_text(getattr(row, "site_code", ""))
    name = clean_text(getattr(row, "name", ""))
    return InventorySiteOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        currency_code=clean_text(getattr(row, "currency_code", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_item_option(row) -> InventoryCatalogItemOptionDescriptor:
    code = clean_text(getattr(row, "item_code", ""))
    name = clean_text(getattr(row, "name", ""))
    return InventoryCatalogItemOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        stock_uom=clean_text(getattr(row, "stock_uom", "")),
        category_code=clean_text(getattr(row, "category_code", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_storeroom_option(
    row,
    *,
    site_lookup: dict[str, str],
) -> InventoryStoreroomOptionDescriptor:
    code = clean_text(getattr(row, "storeroom_code", ""))
    name = clean_text(getattr(row, "name", ""))
    site_id = clean_text(getattr(row, "site_id", ""))
    return InventoryStoreroomOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        site_id=site_id,
        site_label=site_lookup.get(site_id, "-"),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_business_party_option(row) -> InventoryBusinessPartyOptionDescriptor:
    party_name = clean_text(getattr(row, "party_name", ""))
    party_code = clean_text(getattr(row, "party_code", ""))
    party_type = getattr(getattr(row, "party_type", None), "value", getattr(row, "party_type", ""))
    label = f"{party_code} - {party_name}" if party_code else party_name
    contact = clean_text(getattr(row, "contact_name", "")) or clean_text(
        getattr(row, "email", ""),
        default="-",
    )
    context_parts = [
        clean_text(getattr(row, "city", "")),
        clean_text(getattr(row, "country", "")),
    ]
    return InventoryBusinessPartyOptionDescriptor(
        value=row.id,
        label=label,
        party_type=str(party_type or ""),
        contact=contact or "-",
        context=", ".join(part for part in context_parts if part) or "-",
        is_active=bool(getattr(row, "is_active", True)),
    )


__all__ = [
    "InventoryBusinessPartyOptionDescriptor",
    "InventoryCatalogItemOptionDescriptor",
    "InventorySiteOptionDescriptor",
    "InventoryStoreroomOptionDescriptor",
    "serialize_business_party_option",
    "serialize_item_option",
    "serialize_site_option",
    "serialize_storeroom_option",
]
