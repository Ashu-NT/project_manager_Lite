"""Shared wiring for tests that exercise Platform master-data handlers outside the graph."""

from __future__ import annotations

import inspect
from types import ModuleType, SimpleNamespace
from typing import Any

from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationQueryHandler,
    organization_context,
)
from src.core.platform.application.master_data.org.commands import (
    organization_commands,
    organization_lifecycle,
)
from src.core.platform.application.master_data.org.queries import organization_queries

ORGANIZATION_HANDLER_CLASSES = (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationQueryHandler,
)


def organization_modules() -> tuple[ModuleType, ...]:
    return (organization_commands, organization_lifecycle, organization_queries, organization_context)


def organization_source() -> str:
    return "\n".join(inspect.getsource(module) for module in organization_modules())


def organization_has_attr(name: str) -> bool:
    return any(hasattr(cls, name) for cls in ORGANIZATION_HANDLER_CLASSES)


def organization_handlers_for(
    *,
    session: Any,
    organization_repo: Any,
    uow_factory: Any,
    clock: Any,
    user_session: Any,
    default_calendar_writer: Any = None,
    enterprise_audit_service: Any = None,
    overview_rollup_reader: Any = None,
    employee_headcount_reader: Any = None,
    tenant_context_service: Any = None,
) -> SimpleNamespace:
    """The three Organization handlers over one set of dependencies, acting as
    `user_session`, with their public methods exposed together for tests."""
    del tenant_context_service  # Organization handlers resolve tenancy from the session.
    handlers = (
        OrganizationCommandHandler(
            organization_repo=organization_repo,
            uow_factory=uow_factory,
            default_calendar_writer=default_calendar_writer,
            clock=clock,
            user_session=user_session,
        ),
        OrganizationLifecycleCommandHandler(uow_factory=uow_factory, clock=clock, user_session=user_session),
        OrganizationQueryHandler(
            session=session,
            organization_repo=organization_repo,
            user_session=user_session,
            enterprise_audit_service=enterprise_audit_service,
            overview_rollup_reader=overview_rollup_reader,
            employee_headcount_reader=employee_headcount_reader,
        ),
    )
    methods = {
        name: getattr(handler, name)
        for handler in handlers
        for name in dir(handler)
        if not name.startswith("__") and callable(getattr(handler, name))
    }
    return SimpleNamespace(**methods)


__all__ = [
    "ORGANIZATION_HANDLER_CLASSES",
    "organization_handlers_for",
    "organization_has_attr",
    "organization_modules",
    "organization_source",
]
