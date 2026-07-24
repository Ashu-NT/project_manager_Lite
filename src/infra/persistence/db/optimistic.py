from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError


def update_with_version_check(
    session: Session,
    orm_type: type[Any],
    row_id: str,
    expected_version: int,
    values: dict[str, Any],
    *,
    not_found_message: str,
    stale_message: str,
    extra_filters: dict[str, Any] | None = None,
) -> int:
    next_version = int(expected_version) + 1

    stmt = update(orm_type).where(
        orm_type.id == row_id,
        orm_type.version == expected_version,
    )

    if extra_filters:
        for attr, val in extra_filters.items():
            stmt = stmt.where(getattr(orm_type, attr) == val)

    result = session.execute(stmt.values(**values, version=next_version))

    if result.rowcount == 1:
        return next_version

    check_stmt = select(orm_type).where(orm_type.id == row_id)

    if extra_filters:
        for attr, val in extra_filters.items():
            check_stmt = check_stmt.where(getattr(orm_type, attr) == val)

    existing = session.execute(check_stmt).scalar_one_or_none()

    if existing is None:
        raise NotFoundError(not_found_message)

    raise ConcurrencyError(stale_message, code="STALE_WRITE")