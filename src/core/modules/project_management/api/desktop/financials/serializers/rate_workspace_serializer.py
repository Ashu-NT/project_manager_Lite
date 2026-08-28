from __future__ import annotations

from datetime import date, datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.rates import (
    FinancialRateCardDetailDto,
    FinancialRateTableRecordDto,
    FinancialRateWorkspaceDto,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    FinanceRateWorkspaceFacts,
)


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Open"


def _datetime_label(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def serialize_finance_rate_workspace(
    source: FinanceRateWorkspaceFacts,
    *,
    card_search: str = "",
    card_scope: str = "",
    card_status: str = "",
    line_search: str = "",
    line_rate_type: str = "",
    line_status: str = "",
    line_effective_status: str = "",
    as_of: date | None = None,
) -> FinancialRateWorkspaceDto:
    selected = source.selected_rate_card
    detail = (
        FinancialRateCardDetailDto(
            id=selected.id,
            title=selected.name,
            status_label="Active" if selected.is_active else "Inactive",
            subtitle=f"{_label(selected.scope)} scope",
            fields=(
                ("Scope", _label(selected.scope), "Organization default or project override"),
                ("Rate lines", str(selected.line_count), "Independent of the visible page"),
                ("Origin", "Configured Rate Card", ""),
                ("Version", str(selected.version), "Optimistic-concurrency version"),
                ("Updated", _datetime_label(selected.updated_at), ""),
            ),
        )
        if selected is not None
        else FinancialRateCardDetailDto()
    )
    return FinancialRateWorkspaceDto(
        selected_rate_card_id=source.selected_rate_card_id,
        selected_rate_card=detail,
        cards=tuple(_card_record(item) for item in source.cards.items),
        card_page=source.cards.page,
        card_page_size=source.cards.page_size,
        card_total=source.cards.total,
        card_sort_key=source.cards.sort_key,
        card_sort_direction=source.cards.sort_direction,
        lines=tuple(_line_record(item) for item in source.lines.items),
        line_page=source.lines.page,
        line_page_size=source.lines.page_size,
        line_total=source.lines.total,
        line_sort_key=source.lines.sort_key,
        line_sort_direction=source.lines.sort_direction,
        card_search=card_search,
        card_scope=card_scope,
        card_status=card_status,
        line_search=line_search,
        line_rate_type=line_rate_type,
        line_status=line_status,
        line_effective_status=line_effective_status,
        as_of=(as_of.isoformat() if as_of else ""),
    )


def _card_record(item) -> FinancialRateTableRecordDto:
    return FinancialRateTableRecordDto(
        id=item.id,
        title=item.name,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=f"{_label(item.scope)} scope",
        supporting_text=f"{item.line_count} rate line{'s' if item.line_count != 1 else ''}",
        meta_text=f"Version {item.version}",
        state={
            "projectId": item.project_id or "",
            "scope": item.scope,
            "lineCount": item.line_count,
            "version": item.version,
        },
    )


def _line_record(item) -> FinancialRateTableRecordDto:
    effective_range = f"{_date_label(item.effective_from)} to {_date_label(item.effective_to)}"
    multipliers = ", ".join(
        f"{label} {format_decimal_amount(value)}x"
        for label, value in (
            ("OT", item.overtime_multiplier),
            ("Weekend", item.weekend_multiplier),
            ("Holiday", item.holiday_multiplier),
        )
        if value is not None
    )
    return FinancialRateTableRecordDto(
        id=item.id,
        title=item.selector_label,
        status_label=_label(item.rate_type),
        subtitle=f"{format_money(item.rate_amount, item.rate_currency)} / {item.unit.lower()}",
        supporting_text=f"{_label(item.effective_status)} | {effective_range}",
        meta_text=" | ".join(
            part for part in (_label(item.origin), multipliers, f"Version {item.version}") if part
        ),
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
            "effectiveFrom": item.effective_from.isoformat() if item.effective_from else "",
            "effectiveTo": item.effective_to.isoformat() if item.effective_to else "",
            "effectiveStatus": item.effective_status,
            "isActive": item.is_active,
            "version": item.version,
        },
    )


__all__ = ["serialize_finance_rate_workspace"]
