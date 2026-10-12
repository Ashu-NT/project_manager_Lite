from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.risk.register_service import (
    RegisterService,
)


@dataclass(frozen=True)
class RegisterComposition:
    service: RegisterService
    lifecycle: RegisterLifecycleHandler
