from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.platform.common.exceptions import BusinessRuleError


class _GuardedService(ProjectManagementModuleGuardMixin):
    def __init__(self, module_catalog_service) -> None:
        self._module_catalog_service = module_catalog_service

    def create_task(self) -> str:
        return "created"

    def set_approved_time_dispatcher(self, dispatcher) -> None:
        self._dispatcher = dispatcher

    def consume_last_overallocation_warning(self) -> str | None:
        return None


def _module_catalog(*, runtime_enabled: bool) -> SimpleNamespace:
    entitlement = SimpleNamespace(
        runtime_enabled=runtime_enabled, label="Project Management", lifecycle_status="inactive",
    )
    return SimpleNamespace(get_entitlement=lambda _module_code: entitlement)


def test_business_methods_are_blocked_when_the_module_is_disabled() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.create_task()


def test_business_methods_are_allowed_when_the_module_is_enabled() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=True))
    assert service.create_task() == "created"


def test_composition_root_wiring_setters_are_exempt_from_the_module_gate() -> None:
    """set_approved_time_dispatcher is called unconditionally during service
    composition at application startup, before any tenant-scoped module
    entitlement should matter -- gating it behind module enablement made the
    whole application fail to start on any installation with Project
    Management disabled."""
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    service.set_approved_time_dispatcher(lambda: None)
    assert service._dispatcher is not None


def test_consume_last_overallocation_warning_remains_exempt() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    assert service.consume_last_overallocation_warning() is None
