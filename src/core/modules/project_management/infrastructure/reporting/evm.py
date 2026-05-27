"""EVM facade mixin.

Keep ReportingService inheritance stable while EVM logic lives in focused mixins.
"""

from src.core.modules.project_management.infrastructure.reporting.evm_core import (
    ReportingEvmCoreMixin,
)
from src.core.modules.project_management.infrastructure.reporting.evm_series import (
    ReportingEvmSeriesMixin,
)


class ReportingEvmMixin(ReportingEvmCoreMixin, ReportingEvmSeriesMixin):
    pass


__all__ = ["ReportingEvmMixin"]
