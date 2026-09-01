from __future__ import annotations

from typing import Any, Callable, TypeVar, cast, overload

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass as pydantic_dataclass

from src.core.platform.common.exceptions import ValidationError

_DEFAULT_VALIDATED_DATACLASS_CONFIG = ConfigDict(validate_assignment=True)

ClassT = TypeVar("ClassT")


@overload
def validated_dataclass(cls: ClassT, /) -> ClassT: ...


@overload
def validated_dataclass(cls: None = None, /, **kwargs: Any) -> Callable[[ClassT], ClassT]: ...


def validated_dataclass(
    cls: ClassT | None = None,
    /,
    **kwargs: Any,
) -> ClassT | Callable[[ClassT], ClassT]:
    config = kwargs.pop("config", _DEFAULT_VALIDATED_DATACLASS_CONFIG)

    def wrap(target: ClassT) -> ClassT:
        return cast(ClassT, pydantic_dataclass(cast(Any, target), config=config, **kwargs))

    if cls is None:
        return wrap
    return wrap(cls)


def normalize_optional_text(value: object) -> str:
    return str(value or "").strip()


def normalize_optional_identifier(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def normalize_required_text(
    value: object,
    *,
    message: str,
    code: str,
) -> str:
    normalized = normalize_optional_text(value)
    if not normalized:
        raise ValidationError(message, code=code)
    return normalized


__all__ = [
    "normalize_optional_identifier",
    "normalize_optional_text",
    "normalize_required_text",
    "validated_dataclass",
]
