from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from src.core.platform.domain.master_data.org import Organization


class OrganizationDefaultCalendarWriter(Protocol):
    """Write the required calendar in the caller's organization transaction."""

    def add_default_calendar(self, session: Session, organization: Organization) -> None: ...
