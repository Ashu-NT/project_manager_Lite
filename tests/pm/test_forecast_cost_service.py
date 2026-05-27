"""Unit tests for ForecastCostService — uses in-memory stubs, no DB."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.modules.project_management.application.financials.forecast_cost_service import (
    EACMethod,
    ForecastCostService,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.cost import CommitmentStatus, CostItem

_PERM_PATCH = "src.core.modules.project_management.application.financials.forecast_cost_service"


def _noop(*args, **kwargs):
    pass


def _item(planned, actual=0.0, committed=0.0, cost_type=CostType.OVERHEAD,
          commitment_status=CommitmentStatus.UNCOMMITTED, forecast=None):
    c = CostItem.create(
        project_id="p1",
        description="item",
        planned_amount=planned,
        cost_type=cost_type,
        actual_amount=actual,
        committed_amount=committed,
        commitment_status=commitment_status,
        forecast_amount=forecast,
    )
    return c


def _service(items):
    cost_repo = MagicMock()
    cost_repo.list_by_project.return_value = items
    project_repo = MagicMock()
    project_repo.get.return_value = MagicMock(id="p1", name="Test Project")

    # bypass permission checks
    svc = ForecastCostService.__new__(ForecastCostService)
    svc._costs = cost_repo
    svc._projects = project_repo
    svc._user_session = None
    svc._module_catalog_service = None
    return svc


class TestCommitmentSummary:
    def test_totals_by_status(self):
        items = [
            _item(1000, commitment_status=CommitmentStatus.UNCOMMITTED),
            _item(2000, committed=2000, commitment_status=CommitmentStatus.COMMITTED),
            _item(500, committed=500, commitment_status=CommitmentStatus.INVOICED),
            _item(300, actual=300, commitment_status=CommitmentStatus.PAID),
        ]
        svc = _service(items)
        summary = svc._build_commitment_summary("p1", items)
        assert summary.planned_total == 3800.0
        assert summary.uncommitted_total == 1000.0
        assert summary.committed_total == 2000.0
        assert summary.invoiced_total == 500.0
        assert summary.paid_total == 300.0

    def test_exposure_is_committed_minus_actual(self):
        items = [_item(2000, actual=800.0, committed=2000, commitment_status=CommitmentStatus.COMMITTED)]
        svc = _service(items)
        summary = svc._build_commitment_summary("p1", items)
        assert summary.exposure == pytest.approx(1200.0)


class TestMaterialRollup:
    def test_filters_to_material_only(self):
        items = [
            _item(500, cost_type=CostType.MATERIAL),
            _item(300, cost_type=CostType.LABOR),
            _item(200, cost_type=CostType.MATERIAL),
        ]
        svc = _service(items)
        with patch(f"{_PERM_PATCH}.require_permission", _noop), \
             patch(f"{_PERM_PATCH}.require_project_permission", _noop):
            rollup = svc.get_material_rollup("p1")
        assert rollup.planned == 700.0
        assert len(rollup.items) == 2

    def test_variance_positive_when_over_budget(self):
        items = [_item(500, cost_type=CostType.MATERIAL, forecast=600.0)]
        svc = _service(items)
        with patch(f"{_PERM_PATCH}.require_permission", _noop), \
             patch(f"{_PERM_PATCH}.require_project_permission", _noop):
            rollup = svc.get_material_rollup("p1")
        assert rollup.variance == pytest.approx(100.0)


class TestComputeForecast:
    def _run(self, items, method, pct_complete=0.5):
        svc = _service(items)
        with patch(f"{_PERM_PATCH}.require_permission", _noop), \
             patch(f"{_PERM_PATCH}.require_project_permission", _noop):
            return svc.compute_forecast("p1", pct_complete, method=method)

    def test_bac_over_cpi_with_good_cpi(self):
        # BAC=1000, AC=400, EV=500 (50%), CPI=1.25, EAC=800
        items = [_item(1000, actual=400.0)]
        result = self._run(items, EACMethod.BAC_OVER_CPI, pct_complete=0.5)
        assert result.bac == pytest.approx(1000.0)
        assert result.ac == pytest.approx(400.0)
        assert result.ev == pytest.approx(500.0)
        assert result.cpi == pytest.approx(1.25)
        assert result.eac == pytest.approx(800.0)
        assert not result.is_over_budget

    def test_bac_over_cpi_poor_cpi_exceeds_threshold(self):
        # BAC=1000, AC=600, EV=500 (50%), CPI=0.833, EAC=1200
        items = [_item(1000, actual=600.0)]
        result = self._run(items, EACMethod.BAC_OVER_CPI, pct_complete=0.5)
        assert result.eac == pytest.approx(1200.0, rel=0.01)
        assert result.is_over_budget
        assert result.exceeds_threshold  # default 10%: 1200 > 1100

    def test_ac_plus_etc_at_plan(self):
        # BAC=1000, AC=400, EV=500, ETC=BAC-EV=500, EAC=900
        items = [_item(1000, actual=400.0)]
        result = self._run(items, EACMethod.AC_PLUS_ETC_AT_PLAN, pct_complete=0.5)
        assert result.eac == pytest.approx(900.0)
        assert result.vac == pytest.approx(100.0)

    def test_manual_uses_forecast_amount(self):
        # planned=1000, actual=400, forecast_amount=700 → ETC=300, EAC=700
        items = [_item(1000, actual=400.0, forecast=700.0)]
        result = self._run(items, EACMethod.MANUAL, pct_complete=0.5)
        assert result.eac == pytest.approx(700.0)
        assert result.etc == pytest.approx(300.0)

    def test_zero_actual_cpi_is_zero(self):
        items = [_item(1000, actual=0.0)]
        result = self._run(items, EACMethod.BAC_OVER_CPI, pct_complete=0.0)
        assert result.cpi == 0.0


class TestCheckCostThreshold:
    def _check(self, items, eac, threshold=10.0):
        svc = _service(items)
        with patch(f"{_PERM_PATCH}.require_permission", _noop), \
             patch(f"{_PERM_PATCH}.require_project_permission", _noop):
            return svc.check_cost_threshold("p1", eac, threshold_percent=threshold)

    def test_returns_false_below_threshold(self):
        assert not self._check([_item(1000)], 1050.0)

    def test_returns_true_above_threshold(self):
        assert self._check([_item(1000)], 1150.0)

    def test_zero_bac_always_false(self):
        assert not self._check([], 9999.0)
