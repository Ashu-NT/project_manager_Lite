"""Unit tests for AsyncThresholdGuard."""
from __future__ import annotations

import pytest

from src.core.modules.project_management.application.common.async_threshold import (
    AsyncThresholdGuard,
    AsyncThresholds,
    WorkloadScale,
)


@pytest.fixture
def guard():
    return AsyncThresholdGuard()


class TestClassifySchedule:
    def test_small(self, guard):
        assert guard.classify_schedule(50) == WorkloadScale.SMALL

    def test_medium(self, guard):
        assert guard.classify_schedule(300) == WorkloadScale.MEDIUM

    def test_large(self, guard):
        assert guard.classify_schedule(600) == WorkloadScale.LARGE

    def test_xlarge(self, guard):
        assert guard.classify_schedule(2500) == WorkloadScale.XLARGE


class TestClassifyReport:
    def test_small(self, guard):
        assert guard.classify_report(100) == WorkloadScale.SMALL

    def test_large(self, guard):
        assert guard.classify_report(3000) == WorkloadScale.LARGE

    def test_xlarge(self, guard):
        assert guard.classify_report(15000) == WorkloadScale.XLARGE


class TestShouldRunAsync:
    def test_small_is_sync(self, guard):
        assert not guard.should_run_async(WorkloadScale.SMALL)

    def test_medium_is_sync(self, guard):
        assert not guard.should_run_async(WorkloadScale.MEDIUM)

    def test_large_is_async(self, guard):
        assert guard.should_run_async(WorkloadScale.LARGE)

    def test_xlarge_is_async(self, guard):
        assert guard.should_run_async(WorkloadScale.XLARGE)


class TestCustomThresholds:
    def test_custom_thresholds_applied(self):
        custom = AsyncThresholds(schedule_large=10, schedule_xlarge=50)
        guard = AsyncThresholdGuard(thresholds=custom)
        assert guard.classify_schedule(15) == WorkloadScale.LARGE
        assert guard.classify_schedule(60) == WorkloadScale.XLARGE
