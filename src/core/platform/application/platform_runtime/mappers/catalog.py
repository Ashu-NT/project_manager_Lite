from src.core.platform.application.platform_runtime.dto.responses.catalog import (
    CountryDto,
    TimezoneDto,
)


def country_response(code: str, name: str) -> CountryDto:
    return CountryDto(code=code, name=name)

def timezone_response(name: str) -> TimezoneDto:
    return TimezoneDto(name=name)
