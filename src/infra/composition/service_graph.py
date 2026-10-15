from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.composition.bootstrap import (
    ProjectManagementServiceBundle,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle
from src.infra.composition.global_overview_registry import GlobalOverviewServiceBundle
from src.infra.composition.integration.bundle import IntegrationRuntimeBundle


@dataclass(frozen=True)
class ServiceGraph:
    """Aggregate module-owned bundles without forwarding individual capabilities."""

    session: Session
    platform: PlatformServiceBundle
    project_management: ProjectManagementServiceBundle
    integrations: IntegrationRuntimeBundle
    overview: GlobalOverviewServiceBundle

    def as_dict(self) -> dict[str, Any]:
        """Assemble the desktop/runtime dependency map from explicit owner exports."""
        bindings: dict[str, Any] = {"session": self.session}
        for exports in (
            self.platform.runtime_bindings(),
            self.project_management.runtime_bindings(),
            self.integrations.runtime_bindings(),
            self.overview.runtime_bindings(),
        ):
            duplicates = bindings.keys() & exports.keys()
            if duplicates:
                raise ConfigurationError(
                    f"Duplicate runtime dependency names: {', '.join(sorted(duplicates))}",
                    code="DUPLICATE_RUNTIME_DEPENDENCY",
                )
            bindings.update(exports)
        return bindings
