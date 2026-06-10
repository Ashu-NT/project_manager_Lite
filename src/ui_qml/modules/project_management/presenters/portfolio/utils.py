from __future__ import annotations

import logging
from time import perf_counter

logger = logging.getLogger(__name__)


def log_build_complete(
    started: float,
    *,
    intake_count: int,
    filtered_intake_count: int,
    template_count: int,
    scenario_count: int,
    heatmap_count: int,
    dependency_count: int,
    filter_value: str,
    scenario_id: str,
) -> None:
    duration_ms = (perf_counter() - started) * 1000
    log_method = logger.warning if duration_ms > 500 else logger.info
    log_method(
        "PM portfolio presenter build complete duration_ms=%.1f intake_count=%s filtered_intake_count=%s template_count=%s scenario_count=%s heatmap_count=%s dependency_count=%s filter=%s scenario=%s",
        duration_ms,
        intake_count,
        filtered_intake_count,
        template_count,
        scenario_count,
        heatmap_count,
        dependency_count,
        filter_value,
        scenario_id,
    )
