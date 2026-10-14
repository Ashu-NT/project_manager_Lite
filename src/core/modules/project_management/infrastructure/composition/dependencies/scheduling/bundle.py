from dataclasses import dataclass

from src.core.modules.project_management.application.scheduling.baselines.commands.lifecycle import (
    BaselineCommandHandler,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)


@dataclass(frozen=True)
class BaselineComposition:
    commands: BaselineCommandHandler
    query: BaselineQueryHandler
