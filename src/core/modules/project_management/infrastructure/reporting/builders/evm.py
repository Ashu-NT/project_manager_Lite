"""EVM facade mixin — combines EVM core + series into one mixin."""

from src.core.modules.project_management.infrastructure.reporting.builders.evm_core import (
    ReportingEvmCoreMixin,
)
from src.core.modules.project_management.infrastructure.reporting.builders.evm_series import (
    ReportingEvmSeriesMixin,
)


class ReportingEvmMixin(ReportingEvmCoreMixin, ReportingEvmSeriesMixin):
    pass


__all__ = ["ReportingEvmMixin"]
