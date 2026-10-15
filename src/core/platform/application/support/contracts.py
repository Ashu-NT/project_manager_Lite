from __future__ import annotations

from typing import Protocol

from src.core.platform.application.support.dto.commands.settings import (
    SupportSettingsUpdateCommand,
)


class SupportSettingsCommands(Protocol):
    def save_settings(self, command: SupportSettingsUpdateCommand) -> None: ...
