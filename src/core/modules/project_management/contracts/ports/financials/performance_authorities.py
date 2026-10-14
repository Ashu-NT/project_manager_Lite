from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol


class EarnedValueReadAuthority(Protocol):
    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> object: ...


class BaselineVarianceReadAuthority(Protocol):
    def list_baselines(self, project_id: str) -> Sequence[object]: ...

    def list_variance_records(
        self,
        baseline_id: str,
        *,
        expected_project_id: str | None = None,
    ) -> Sequence[object]: ...


__all__ = ["BaselineVarianceReadAuthority", "EarnedValueReadAuthority"]
