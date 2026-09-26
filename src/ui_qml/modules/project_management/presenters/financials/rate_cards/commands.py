from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialAddRateLineCommand,
    FinancialCreateRateCardCommand,
    FinancialUpdateRateCardCommand,
    FinancialUpdateRateLineCommand,
    FinancialVersionedRateCardCommand,
    FinancialVersionedRateLineCommand,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.commands import (
    _optional_date,
    _optional_decimal_text,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_decimal,
    require_int,
    require_text,
)


def create_rate_card(desktop_api, payload: dict[str, Any]):
    scope = optional_text(payload, "scope") or "project"
    project_id = require_text(
        payload, "projectId", "Select a project before creating a Rate Card."
    )
    return desktop_api.create_rate_card(
        FinancialCreateRateCardCommand(
            name=require_text(payload, "name", "Rate Card name is required."),
            project_id=project_id if scope == "project" else None,
        )
    )


def update_rate_card(desktop_api, payload: dict[str, Any]):
    return desktop_api.update_rate_card(
        FinancialUpdateRateCardCommand(
            rate_card_id=require_text(payload, "rateCardId", "Select a Rate Card."),
            expected_version=require_int(
                payload, "version", "Rate Card version is required."
            ),
            name=require_text(payload, "name", "Rate Card name is required."),
        )
    )


def deactivate_rate_card(desktop_api, payload: dict[str, Any]):
    return desktop_api.deactivate_rate_card(
        FinancialVersionedRateCardCommand(
            rate_card_id=require_text(payload, "rateCardId", "Select a Rate Card."),
            expected_version=require_int(
                payload, "version", "Rate Card version is required."
            ),
        )
    )


def add_rate_line(desktop_api, payload: dict[str, Any]):
    return desktop_api.add_rate_line(
        FinancialAddRateLineCommand(
            rate_card_id=require_text(payload, "rateCardId", "Select a Rate Card."),
            expected_card_version=require_int(
                payload, "cardVersion", "Rate Card version is required."
            ),
            rate_type=require_text(payload, "rateType", "Rate purpose is required."),
            unit=require_text(payload, "unit", "Rate unit is required."),
            rate_amount=format(
                require_decimal(payload, "amount", "Rate amount must be a valid number."),
                "f",
            ),
            rate_currency=require_text(payload, "currency", "Currency is required.").upper(),
            resource_id=optional_text(payload, "resourceId"),
            role=optional_text(payload, "role"),
            skill_code=optional_text(payload, "skillCode"),
            department_id=optional_text(payload, "departmentId"),
            customer_party_id=optional_text(payload, "customerPartyId"),
            contract_reference=optional_text(payload, "contractReference"),
            effective_from=_optional_date(payload, "effectiveFrom"),
            effective_to=_optional_date(payload, "effectiveTo"),
            overtime_multiplier=_optional_decimal_text(payload, "overtimeMultiplier"),
            weekend_multiplier=_optional_decimal_text(payload, "weekendMultiplier"),
            holiday_multiplier=_optional_decimal_text(payload, "holidayMultiplier"),
        )
    )


def update_rate_line(desktop_api, payload: dict[str, Any]):
    return desktop_api.update_rate_line(
        FinancialUpdateRateLineCommand(
            rate_line_id=require_text(payload, "rateLineId", "Select a Rate Line."),
            expected_version=require_int(
                payload, "version", "Rate Line version is required."
            ),
            expected_card_version=require_int(
                payload, "cardVersion", "Rate Card version is required."
            ),
            rate_amount=format(
                require_decimal(payload, "amount", "Rate amount must be a valid number."),
                "f",
            ),
            effective_from=_optional_date(payload, "effectiveFrom"),
            effective_to=_optional_date(payload, "effectiveTo"),
            overtime_multiplier=_optional_decimal_text(payload, "overtimeMultiplier"),
            weekend_multiplier=_optional_decimal_text(payload, "weekendMultiplier"),
            holiday_multiplier=_optional_decimal_text(payload, "holidayMultiplier"),
        )
    )


def deactivate_rate_line(desktop_api, payload: dict[str, Any]):
    return desktop_api.deactivate_rate_line(
        FinancialVersionedRateLineCommand(
            rate_line_id=require_text(payload, "rateLineId", "Select a Rate Line."),
            expected_version=require_int(
                payload, "version", "Rate Line version is required."
            ),
            expected_card_version=require_int(
                payload, "cardVersion", "Rate Card version is required."
            ),
        )
    )
