from __future__ import annotations

from datetime import date

import pytest
from matplotlib.axes import Axes
from matplotlib.dates import date2num

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.infrastructure.reporting import api as reporting_api
from src.core.modules.project_management.infrastructure.reporting.models import EvmSeriesPoint


def test_gantt_export_inclusive_duration_for_one_day_tasks(services, tmp_path, monkeypatch):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Gantt One Day", "")
    pid = project.id
    ts.create_task(pid, "One Day Task", start_date=date(2023, 11, 6), duration_days=1)

    widths = []
    original_barh = Axes.barh

    def _spy_barh(self, *args, **kwargs):
        width = args[1] if len(args) > 1 else kwargs.get("width")
        widths.append(width)
        return original_barh(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "barh", _spy_barh)

    output = tmp_path / "gantt.png"
    reporting_api.generate_gantt_png(services["reporting_service"], pid, output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert any(float(w) >= 0.5 for w in widths if w is not None)


def test_gantt_render_uses_day_cell_alignment_for_inclusive_finish(services, tmp_path, monkeypatch):
    ps = services["project_service"]
    ts = services["task_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Gantt Day Cell Alignment", "")
    pid = project.id
    task = ts.create_task(pid, "Aligned Task", start_date=date(2023, 11, 6), duration_days=3)

    calls = []
    original_barh = Axes.barh

    def _spy_barh(self, *args, **kwargs):
        calls.append((args, kwargs))
        return original_barh(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "barh", _spy_barh)

    output = tmp_path / "gantt_aligned.png"
    reporting_api.generate_gantt_png(services["reporting_service"], pid, output)

    assert output.exists()
    bars = rp.get_gantt_data(pid)
    bar = next(b for b in bars if b.task_id == task.id)

    # Main bars have dark edge color; progress overlays do not.
    main = next(
        (entry for entry in calls if entry[1].get("edgecolor") == "#0F172A"),
        None,
    )
    assert main is not None
    args, kwargs = main
    width = float(args[1])
    left = float(kwargs.get("left"))

    right = left + width
    start_num = date2num(bar.start)
    end_num = date2num(bar.end)

    # Point-to-point rendering: bar starts at start tick and ends near end tick.
    assert start_num <= left < (start_num + 0.2)
    assert (end_num - 0.05) <= right <= (end_num + 0.2)


def test_evm_export_png_is_skipped_when_no_series_data(tmp_path):
    class EmptySeriesService:
        def get_evm_series(self, _project_id, baseline_id=None, as_of=None):
            return []

    output = tmp_path / "evm_empty.png"
    result = reporting_api.generate_evm_png(EmptySeriesService(), "p1", output)

    assert result == output
    assert not output.exists()


def test_evm_export_png_is_skipped_when_baseline_is_missing(tmp_path):
    class NoBaselineService:
        def get_evm_series(self, _project_id, baseline_id=None, as_of=None):
            raise BusinessRuleError("No baseline found.", code="NO_BASELINE")

    output = tmp_path / "evm_no_baseline.png"
    result = reporting_api.generate_evm_png(NoBaselineService(), "p1", output)

    assert result == output
    assert not output.exists()


def test_evm_export_png_generates_image_when_series_exists(tmp_path):
    class SeriesService:
        def get_evm_series(self, _project_id, baseline_id=None, as_of=None):
            return [
                EvmSeriesPoint(
                    period_end=date(2023, 11, 30),
                    PV=100.0,
                    EV=80.0,
                    AC=90.0,
                    BAC=120.0,
                    CPI=0.89,
                    SPI=0.80,
                ),
                EvmSeriesPoint(
                    period_end=date(2023, 12, 31),
                    PV=120.0,
                    EV=110.0,
                    AC=115.0,
                    BAC=120.0,
                    CPI=0.96,
                    SPI=0.92,
                ),
            ]

    output = tmp_path / "evm.png"
    result = reporting_api.generate_evm_png(SeriesService(), "p1", output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0
