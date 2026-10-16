from __future__ import annotations

from typing import TypedDict

from datetime import date, datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.rate_cards.models.rate_facts import (
    FinanceRateWorkspaceFacts,
    RateCardFact,
    RateLineFact,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Open"


def _datetime_label(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


class FinanceRateViews(TypedDict):
    selected_rate_card_id: str
    selected_rate_card: FinancialsDetailViewModel
    rate_cards: FinancialsCollectionViewModel
    rate_lines: FinancialsCollectionViewModel
    rate_card_sort_key: str
    rate_card_sort_direction: str
    rate_line_sort_key: str
    rate_line_sort_direction: str
    rate_card_search: str
    rate_card_scope: str
    rate_card_status: str
    rate_line_search: str
    rate_line_rate_type: str
    rate_line_status: str
    rate_line_effective_status: str
    can_create_rate_card: bool


def build_rate_workspace_views(
    source: FinanceRateWorkspaceFacts,
    *,
    card_search: str = "",
    card_scope: str = "",
    card_status: str = "",
    line_search: str = "",
    line_rate_type: str = "",
    line_status: str = "",
    line_effective_status: str = "",
) -> FinanceRateViews:
    selected = source.selected_rate_card
    detail = (
        FinancialsDetailViewModel(
            empty_state="Select a Rate Card to inspect its authoritative lines.",
            id=selected.id,
            title=selected.name,
            status_label="Active" if selected.is_active else "Inactive",
            subtitle=f"{_label(selected.scope)} scope",
            fields=tuple(
                FinancialsDetailFieldViewModel(*field)
                for field in (
                    (
                        "Scope",
                        _label(selected.scope),
                        "Organization default or project override",
                    ),
                    (
                        "Rate lines",
                        str(selected.line_count),
                        "Independent of the visible page",
                    ),
                    ("Origin", "Configured Rate Card", ""),
                    (
                        "Version",
                        str(selected.version),
                        "Optimistic-concurrency version",
                    ),
                    ("Updated", _datetime_label(selected.updated_at), ""),
                )
            ),
            state={
                "projectId": selected.project_id or "",
                "scope": selected.scope,
                "version": selected.version,
                "isActive": selected.is_active,
                "canEdit": selected.can_edit,
                "canDeactivate": selected.can_deactivate,
                "canAddLine": selected.can_add_line,
            },
        )
        if selected is not None
        else FinancialsDetailViewModel(
            empty_state="Select a Rate Card to inspect its authoritative lines."
        )
    )
    return {
        "selected_rate_card_id": source.selected_rate_card_id,
        "selected_rate_card": detail,
        "rate_cards": FinancialsCollectionViewModel(
            title="Rate Cards",
            subtitle="Organization default and project override cards visible to this project.",
            empty_state="No Rate Cards match the current filters.",
            items=tuple(_card_record(item) for item in source.cards.items),
            page=source.cards.page,
            page_size=source.cards.page_size,
            total=source.cards.total,
        ),
        "rate_lines": FinancialsCollectionViewModel(
            title="Selected Rate Card Lines",
            subtitle="Effective-dated financial rates; historical postings use immutable snapshots.",
            empty_state=(
                "Select a Rate Card."
                if not source.selected_rate_card_id
                else "No Rate Card Lines match the current filters."
            ),
            items=tuple(_line_record(item) for item in source.lines.items),
            page=source.lines.page,
            page_size=source.lines.page_size,
            total=source.lines.total,
        ),
        "rate_card_sort_key": source.cards.sort_key,
        "rate_card_sort_direction": source.cards.sort_direction,
        "rate_line_sort_key": source.lines.sort_key,
        "rate_line_sort_direction": source.lines.sort_direction,
        "rate_card_search": card_search,
        "rate_card_scope": card_scope,
        "rate_card_status": card_status,
        "rate_line_search": line_search,
        "rate_line_rate_type": line_rate_type,
        "rate_line_status": line_status,
        "rate_line_effective_status": line_effective_status,
        "can_create_rate_card": source.can_create_rate_card,
    }


def _card_record(item: RateCardFact) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=f"{_label(item.scope)} scope",
        supporting_text=f"{item.line_count} rate line{'s' if item.line_count != 1 else ''}",
        meta_text=f"Version {item.version}",
        can_primary_action=item.can_edit,
        can_secondary_action=item.can_deactivate,
        state={
            "projectId": item.project_id or "",
            "scope": item.scope,
            "lineCount": item.line_count,
            "version": item.version,
            "isActive": item.is_active,
            "canEdit": item.can_edit,
            "canDeactivate": item.can_deactivate,
            "canAddLine": item.can_add_line,
        },
    )


def _line_record(item: RateLineFact) -> FinancialsRecordViewModel:
    effective_range = (
        f"{_date_label(item.effective_from)} to {_date_label(item.effective_to)}"
    )
    multipliers = ", ".join(
        f"{label} {format_decimal_amount(value)}x"
        for label, value in (
            ("OT", item.overtime_multiplier),
            ("Weekend", item.weekend_multiplier),
            ("Holiday", item.holiday_multiplier),
        )
        if value is not None
    )
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.selector_label,
        status_label=_label(item.rate_type),
        subtitle=f"{format_money(item.rate_amount, item.rate_currency)} / {item.unit.lower()}",
        supporting_text=f"{_label(item.effective_status)} | {effective_range}",
        meta_text=" | ".join(
            part
            for part in (_label(item.origin), multipliers, f"Version {item.version}")
            if part
        ),
        can_primary_action=item.can_edit,
        can_secondary_action=item.can_deactivate,
        state={
            "rateCardId": item.rate_card_id,
            "selectorKind": item.selector_kind,
            "resourceId": item.resource_id or "",
            "resourceCode": item.resource_code,
            "resourceName": item.resource_name,
            "workerType": item.worker_type,
            "role": item.role,
            "skillCode": item.skill_code,
            "departmentId": item.department_id or "",
            "departmentName": item.department_name,
            "customerPartyId": item.customer_party_id or "",
            "contractReference": item.contract_reference,
            "rateType": item.rate_type,
            "origin": item.origin,
            "amount": str(item.rate_amount),
            "currency": item.rate_currency,
            "unit": item.unit,
            "effectiveFrom": item.effective_from.isoformat()
            if item.effective_from
            else "",
            "effectiveTo": item.effective_to.isoformat() if item.effective_to else "",
            "effectiveStatus": item.effective_status,
            "isActive": item.is_active,
            "version": item.version,
            "isConsumed": item.is_consumed,
            "historicalLockMessage": (
                "This line has historical financial use. Its economic terms are "
                "locked; create a new effective-dated line for future changes."
                if item.is_consumed
                else ""
            ),
            "canEdit": item.can_edit,
            "canDeactivate": item.can_deactivate,
        },
    )


__all__ = ["build_rate_workspace_views"]
