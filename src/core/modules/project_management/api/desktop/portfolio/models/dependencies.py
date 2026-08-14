from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioDependencyDesktopDto:
    dependency_id: str
    predecessor_project_id: str
    predecessor_project_name: str
    predecessor_project_status_label: str
    successor_project_id: str
    successor_project_name: str
    successor_project_status_label: str
    dependency_type: str
    dependency_type_label: str
    summary: str
    pressure_label: str
    created_at_label: str


@dataclass(frozen=True)
class PortfolioDependencyPageDto:
    items: tuple[PortfolioDependencyDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "updatedAt"
    sort_direction: str = "desc"
    search_text: str = ""


__all__ = ["PortfolioDependencyDesktopDto", "PortfolioDependencyPageDto"]
