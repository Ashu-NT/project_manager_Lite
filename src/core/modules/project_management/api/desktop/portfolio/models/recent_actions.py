from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRecentActionDesktopDto:
    occurred_at_label: str
    project_name: str
    actor_username: str
    action_label: str
    summary: str


__all__ = ["PortfolioRecentActionDesktopDto"]
