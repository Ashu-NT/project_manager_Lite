from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class PortfolioProjectOptionDescriptor:
    value: str
    label: str


__all__ = ["PortfolioOptionDescriptor", "PortfolioProjectOptionDescriptor"]
