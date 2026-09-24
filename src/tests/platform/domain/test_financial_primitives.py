from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.finance import (
    EXCHANGE_RATE_STORAGE,
    MONEY_STORAGE,
    PERCENTAGE_STORAGE,
    QUANTITY_STORAGE,
    RATE_STORAGE,
    CurrencyCode,
    CurrencySource,
    DecimalQuantity,
    DecimalQuantityPayload,
    MonetaryRate,
    MonetaryRatePayload,
    Money,
    MoneyPayload,
    RoundingMode,
    RoundingPolicy,
    resolve_currency_code,
)
from src.core.platform.finance.money.currency import ISO_4217_MINOR_UNITS


def test_currency_code_uses_current_iso_list_and_minor_units() -> None:
    assert len(ISO_4217_MINOR_UNITS) > 150
    assert CurrencyCode(" eur ").code == "EUR"
    assert CurrencyCode("JPY").minor_units == 0
    assert CurrencyCode("BHD").minor_units == 3
    assert CurrencyCode("CLF").minor_units == 4
    assert CurrencyCode("XDR").minor_units is None
    assert CurrencyCode("XCG").minor_units == 2
    assert CurrencyCode("ZWG").minor_units == 2

    with pytest.raises(ValidationError) as historic:
        CurrencyCode("BGN")
    assert historic.value.code == "CURRENCY_CODE_INVALID"


def test_money_rejects_binary_float() -> None:
    with pytest.raises(ValidationError) as exc:
        Money.of(0.1, "EUR")
    assert exc.value.code == "DECIMAL_BINARY_FLOAT_FORBIDDEN"

def test_money_supports_signed_exact_arithmetic_and_rejects_currency_mismatch() -> None:
    original = Money.of("125.40", "EUR")
    reversal = -original

    assert reversal.amount == Decimal("-125.40")
    assert original + reversal == Money.zero("EUR")
    assert original - Money.of("25.40", "EUR") == Money.of("100", "EUR")
    assert original * "2.5" == Money.of("313.500", "EUR")

    with pytest.raises(BusinessRuleError) as exc:
        original + Money.of("1", "USD")
    assert exc.value.code == "MONEY_CURRENCY_MISMATCH"


def test_money_rounds_only_at_named_currency_boundary() -> None:
    half_even = RoundingPolicy(RoundingMode.HALF_EVEN)

    assert Money.of("2.345", "EUR").rounded(half_even).amount == Decimal("2.34")
    assert Money.of("2.355", "EUR").rounded(half_even).amount == Decimal("2.36")
    assert Money.of("125.5", "JPY").rounded(half_even).amount == Decimal("126")

    with pytest.raises(ValidationError) as exc:
        Money.of("1", "XDR").rounded()
    assert exc.value.code == "CURRENCY_MINOR_UNITS_UNDEFINED"


def test_money_allocation_preserves_positive_and_negative_totals() -> None:
    positive = Money.of("10", "EUR").allocate(("1", "1", "1"))
    negative = Money.of("-10", "EUR").allocate(("1", "1", "1"))

    assert [part.amount for part in positive] == [
        Decimal("3.34"),
        Decimal("3.33"),
        Decimal("3.33"),
    ]
    assert [part.amount for part in negative] == [
        Decimal("-3.34"),
        Decimal("-3.33"),
        Decimal("-3.33"),
    ]
    assert sum((part.amount for part in positive), Decimal("0")) == Decimal("10.00")
    assert sum((part.amount for part in negative), Decimal("0")) == Decimal("-10.00")


def test_quantity_and_rate_are_decimal_and_unit_safe() -> None:
    hours = DecimalQuantity.of("7.5", "hour")
    rate = MonetaryRate(Money.of("125.25", "EUR"), "HOUR")

    assert rate.apply(hours) == Money.of("939.375", "EUR")
    assert hours + DecimalQuantity.of("0.5", "HOUR") == DecimalQuantity.of("8", "HOUR")

    with pytest.raises(BusinessRuleError) as exc:
        rate.apply(DecimalQuantity.of("1", "DAY"))
    assert exc.value.code == "MONETARY_RATE_UNIT_MISMATCH"


def test_pydantic_payloads_use_canonical_decimal_strings() -> None:
    money_payload = MoneyPayload(amount="00125.4000", currency=" eur ")
    quantity_payload = DecimalQuantityPayload(value="8.000", unit="hour")
    rate_payload = MonetaryRatePayload(
        amount="125.2500",
        currency="eur",
        per_unit="hour",
    )

    assert money_payload.model_dump(mode="json") == {
        "amount": "125.4",
        "currency": "EUR",
    }
    assert quantity_payload.model_dump(mode="json") == {"value": "8", "unit": "HOUR"}
    assert MoneyPayload.from_domain(money_payload.to_domain()) == money_payload
    assert DecimalQuantityPayload.from_domain(quantity_payload.to_domain()) == quantity_payload
    assert MonetaryRatePayload.from_domain(rate_payload.to_domain()) == rate_payload
    assert '"amount":"125.4"' in money_payload.model_dump_json()
    restored = MoneyPayload.model_validate_json(money_payload.model_dump_json())
    assert restored.to_domain() == Money.of("125.4", "EUR")

    with pytest.raises(PydanticValidationError):
        MoneyPayload(amount=1.25, currency="EUR")
    with pytest.raises(PydanticValidationError):
        MoneyPayload(amount="1.25", currency="EUR", unexpected="value")


def test_currency_resolution_is_ordered_and_never_silently_defaults() -> None:
    explicit = resolve_currency_code(
        explicit="USD",
        project_default="GBP",
        organization_default="EUR",
    )
    project = resolve_currency_code(project_default="GBP", organization_default="EUR")
    organization = resolve_currency_code(organization_default="EUR")

    assert (explicit.currency.code, explicit.source) == ("USD", CurrencySource.EXPLICIT)
    assert (project.currency.code, project.source) == ("GBP", CurrencySource.PROJECT)
    assert (organization.currency.code, organization.source) == (
        "EUR",
        CurrencySource.ORGANIZATION,
    )

    with pytest.raises(ValidationError) as missing:
        resolve_currency_code()
    assert missing.value.code == "CURRENCY_RESOLUTION_REQUIRED"
    with pytest.raises(ValidationError) as invalid:
        resolve_currency_code(explicit="ZZZ", organization_default="EUR")
    assert invalid.value.code == "CURRENCY_CODE_INVALID"


def test_numeric_precision_conventions_have_reviewed_limits() -> None:
    assert MONEY_STORAGE.maximum == Decimal("999999999999999.9999")
    assert RATE_STORAGE.maximum == Decimal("99999999999.99999999")
    assert QUANTITY_STORAGE.maximum == Decimal("9999999999999.999999")
    assert PERCENTAGE_STORAGE.maximum == Decimal("999.999999")
    assert EXCHANGE_RATE_STORAGE.maximum == Decimal("999999999999.999999999999")

    assert MONEY_STORAGE.accepts("-999999999999999.9999")
    assert not MONEY_STORAGE.accepts("1000000000000000")
    assert not MONEY_STORAGE.accepts("1.00001")


@pytest.mark.parametrize(
    ("amount", "weights"),
    [
        ("0.01", ("1", "1", "1")),
        ("999999.99", ("5", "3", "2")),
        ("-999999.99", ("5", "3", "2")),
        ("123.45", ("0", "7", "11", "13")),
    ],
)
def test_money_allocation_property_preserves_rounded_total(
    amount: str,
    weights: tuple[str, ...],
) -> None:
    source = Money.of(amount, "EUR")
    parts = source.allocate(weights)

    assert len(parts) == len(weights)
    assert all(part.currency == source.currency for part in parts)
    assert sum((part.amount for part in parts), Decimal("0")) == source.rounded().amount
