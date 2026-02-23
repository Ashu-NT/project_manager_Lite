from __future__ import annotations

from core.exceptions import BusinessRuleError
from core.services.dashboard.models import DashboardEVM
from core.services.reporting.models import EarnedValueMetrics
from core.services.reporting.service import ReportingService


class DashboardEvmMixin:
    _reporting: ReportingService

    def _build_evm(self, project_id: str, baseline_id: str | None = None) -> DashboardEVM | None:
        try:
            evm = self._reporting.get_earned_value(project_id, baseline_id=baseline_id)
            status = self._interpret_evm(evm)
            return DashboardEVM(
                as_of=evm.as_of,
                baseline_id=evm.baseline_id,
                BAC=evm.BAC,
                PV=evm.PV,
                EV=evm.EV,
                AC=evm.AC,
                CPI=evm.CPI,
                SPI=evm.SPI,
                EAC=evm.EAC,
                VAC=evm.VAC,
                TCPI_to_BAC=getattr(evm, "TCPI_to_BAC", None),
                TCPI_to_EAC=getattr(evm, "TCPI_to_EAC", None),
                status_text=status,
            )
        except BusinessRuleError:
            return None

    def _interpret_evm(self, evm: EarnedValueMetrics) -> str:
        parts = []

        if evm.CPI is None:
            parts.append("CPI: not available (no actual cost yet).")
        elif evm.CPI >= 1.05:
            parts.append("Cost: under budget (good).")
        elif evm.CPI >= 0.95:
            parts.append("Cost: roughly on budget.")
        else:
            parts.append("Cost: over budget (needs action).")

        if evm.SPI is None:
            parts.append("SPI: not available.")
        elif evm.SPI >= 1.05:
            parts.append("Schedule: ahead.")
        elif evm.SPI >= 0.95:
            parts.append("Schedule: on track.")
        else:
            parts.append("Schedule: behind (recover plan).")

        if evm.EAC is not None and evm.VAC is not None:
            if evm.VAC >= 0:
                parts.append("Forecast: within budget at completion.")
            else:
                parts.append("Forecast: likely over budget at completion.")
        else:
            parts.append("VAC: not available.")

        if evm.TCPI_to_BAC is not None:
            if evm.TCPI_to_BAC < 0.5:
                parts.append("TCPI(BAC): unusually low; verify budget and progress data.")
            elif evm.TCPI_to_BAC <= 1.05:
                parts.append("TCPI(BAC): achievable efficiency to hit budget.")
            elif evm.TCPI_to_BAC <= 1.15:
                parts.append("TCPI(BAC): challenging; requires efficiency improvement.")
            else:
                parts.append("TCPI(BAC): severely over budget or BAC is unrealistic.")
        else:
            parts.append("TCPI(BAC): total planned budget exceeded.")

        return " ".join(parts)
