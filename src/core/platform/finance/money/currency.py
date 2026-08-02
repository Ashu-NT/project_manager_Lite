from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from src.core.platform.common.exceptions import ValidationError


# ISO 4217 List One, published by the SIX Maintenance Agency on 2026-01-01.
# N.A. minor units are represented by None and require an explicit rounding scale.
_TWO_MINOR_UNIT_CODES = """
AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BMD BND BOB BOV BRL BSD BTN
BWP BYN BZD CAD CDF CHF CHE CHW CNY COP COU CRC CUP CVE CZK DKK DOP DZD EGP
ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GTQ GYD HKD HNL HTG HUF IDR ILS INR
IRR JMD KES KGS KHR KPW KYD KZT LAK LBP LKR LRD LSL MAD MDL MGA MKD MMK MNT
MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD PAB PEN PGK PHP
PKR PLN QAR RON RSD RUB SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC
SYP SZL THB TJS TMT TOP TRY TTD TWD TZS UAH USD USN UYU UZS VED VES WST XAD
XCD XCG YER ZAR ZMW ZWG
""".split()
_ZERO_MINOR_UNIT_CODES = "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF".split()
_THREE_MINOR_UNIT_CODES = "BHD IQD JOD KWD LYD OMR TND".split()
_FOUR_MINOR_UNIT_CODES = "CLF UYW".split()
_NO_MINOR_UNIT_CODES = "XAG XAU XBA XBB XBC XBD XDR XPD XPT XSU XTS XUA XXX".split()

ISO_4217_PUBLISHED_DATE = "2026-01-01"
ISO_4217_SOURCE_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
ISO_4217_MINOR_UNITS = MappingProxyType(
    {
        **{code: 2 for code in _TWO_MINOR_UNIT_CODES},
        **{code: 0 for code in _ZERO_MINOR_UNIT_CODES},
        **{code: 3 for code in _THREE_MINOR_UNIT_CODES},
        **{code: 4 for code in _FOUR_MINOR_UNIT_CODES},
        **{code: None for code in _NO_MINOR_UNIT_CODES},
    }
)


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    code: str

    def __post_init__(self) -> None:
        normalized = str(self.code or "").strip().upper()
        if not normalized:
            raise ValidationError("Currency code is required.", code="CURRENCY_CODE_REQUIRED")
        if normalized not in ISO_4217_MINOR_UNITS:
            raise ValidationError(
                f"Currency code '{normalized}' is not active in ISO 4217 List One.",
                code="CURRENCY_CODE_INVALID",
            )
        object.__setattr__(self, "code", normalized)

    @classmethod
    def parse(cls, value: CurrencyCode | str) -> CurrencyCode:
        return value if isinstance(value, cls) else cls(value)

    @property
    def minor_units(self) -> int | None:
        return ISO_4217_MINOR_UNITS[self.code]

    @property
    def has_minor_unit_definition(self) -> bool:
        return self.minor_units is not None

    def minor_unit_quantum(self) -> Decimal:
        if self.minor_units is None:
            raise ValidationError(
                f"Currency code '{self.code}' has no ISO 4217 minor-unit definition.",
                code="CURRENCY_MINOR_UNITS_UNDEFINED",
            )
        return Decimal("1").scaleb(-self.minor_units)

    def __str__(self) -> str:
        return self.code


__all__ = [
    "CurrencyCode",
    "ISO_4217_MINOR_UNITS",
    "ISO_4217_PUBLISHED_DATE",
    "ISO_4217_SOURCE_URL",
]
