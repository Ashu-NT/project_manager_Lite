from __future__ import annotations

from src.core.platform.org.domain import Site
from src.core.platform.party.domain import Party


def build_site_lookup(rows: list[Site]) -> dict[str, Site]:
    return {row.id: row for row in rows}


def build_party_lookup(rows: list[Party]) -> dict[str, Party]:
    return {row.id: row for row in rows}


def format_site_label(site_id: str | None, site_lookup: dict[str, Site]) -> str:
    if not site_id:
        return "-"
    site = site_lookup.get(site_id)
    if site is None:
        return site_id
    return f"{site.site_code} - {site.name}"


def format_party_label(party_id: str | None, party_lookup: dict[str, Party]) -> str:
    if not party_id:
        return "-"
    party = party_lookup.get(party_id)
    if party is None:
        return party_id
    return f"{party.party_code} - {party.party_name}"


def build_option_rows(labels_by_id: dict[str, str], *, include_blank: bool = False) -> list[tuple[str, str]]:
    rows = sorted(((label, row_id) for row_id, label in labels_by_id.items()), key=lambda item: item[0].lower())
    if include_blank:
        return [("None", "")] + rows
    return rows


__all__ = [
    "build_option_rows",
    "build_party_lookup",
    "build_site_lookup",
    "format_party_label",
    "format_site_label",
]
