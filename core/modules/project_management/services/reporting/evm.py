"""EVM facade mixin.

Keep ReportingService inheritance stable while EVM logic lives in focused mixins.
"""

from core.modules.project_management.services.reporting.evm_core import ReportingEvmCoreMixin
from core.modules.project_management.services.reporting.evm_series import ReportingEvmSeriesMixin


class ReportingEvmMixin(ReportingEvmCoreMixin, ReportingEvmSeriesMixin):
    pass


__all__ = ["ReportingEvmMixin"]
