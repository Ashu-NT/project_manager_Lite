from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.risk.queries.register_query import (
    RegisterQueryHandler,
)


@dataclass(frozen=True)
class RegisterComposition:
    query: RegisterQueryHandler
    lifecycle: RegisterLifecycleHandler
