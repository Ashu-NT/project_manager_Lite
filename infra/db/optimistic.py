from __future__ import annotations

from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from core.exceptions import ConcurrencyError, NotFoundError


def update_with_version_check(
    session: Session,
    orm_type: type[Any],
    row_id: str,
    expected_version: int,
    values: dict[str, Any],
    *,
    not_found_message: str,
    stale_message: str,
) -> int:
    next_version = int(expected_version) + 1
    stmt = (
        update(orm_type)
        .where(orm_type.id == row_id, orm_type.version == expected_version)
        .values(**values, version=next_version)
    )
    result = session.execute(stmt)
    if result.rowcount == 1:
        return next_version

    if session.get(orm_type, row_id) is None:
        raise NotFoundError(not_found_message)
    raise ConcurrencyError(stale_message, code="STALE_WRITE")

