from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioCapacityResourceDto:
    resource_id: str
    resource_name: str
    peak_load_percent: float
    average_load_percent: float
    overloaded: bool
    demand_entries: tuple[str, ...]


__all__ = ["PortfolioCapacityResourceDto"]
