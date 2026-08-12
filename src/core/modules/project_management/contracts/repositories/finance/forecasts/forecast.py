from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ForecastSourceDecision,
    ProjectForecast,
)


class ProjectForecastRepository(ABC):
    @abstractmethod
    def add(self, forecast: ProjectForecast) -> None: ...

    @abstractmethod
    def get(self, forecast_id: str) -> ProjectForecast | None: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> list[ProjectForecast]: ...

    @abstractmethod
    def get_latest_for_project(self, project_id: str) -> ProjectForecast | None: ...

    @abstractmethod
    def get_approved_for_project(self, project_id: str) -> ProjectForecast | None: ...

    @abstractmethod
    def has_open_for_project(self, project_id: str) -> bool: ...

    @abstractmethod
    def update(self, forecast: ProjectForecast, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def delete(self, forecast_id: str, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def add_line(self, line: ForecastLine) -> None: ...

    @abstractmethod
    def get_line(self, line_id: str) -> ForecastLine | None: ...

    @abstractmethod
    def update_line(self, line: ForecastLine, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def delete_line(self, line_id: str, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def list_lines(self, forecast_id: str) -> list[ForecastLine]: ...

    @abstractmethod
    def add_decisions(self, decisions: list[ForecastSourceDecision]) -> None: ...

    @abstractmethod
    def list_decisions(self, forecast_id: str) -> list[ForecastSourceDecision]: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["ProjectForecastRepository"]
