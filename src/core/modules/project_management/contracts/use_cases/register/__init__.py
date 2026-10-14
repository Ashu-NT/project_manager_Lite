"""Register entry use-case contracts."""

from src.core.modules.project_management.contracts.use_cases.register.commands import (
    RegisterEntryCreateCommand,
    RegisterEntryUpdateCommand,
)

__all__ = [
    "RegisterEntryCreateCommand",
    "RegisterEntryUpdateCommand",
]
