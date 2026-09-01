from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFinancialProfileUpdated:
    tenant_id: str
    organization_id: str
    project_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFinancialProfileTransitioned:
    tenant_id: str
    organization_id: str
    project_id: str
    status: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostCodeCreated:
    tenant_id: str
    organization_id: str
    cost_code_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostCodeProfileUpdated:
    tenant_id: str
    organization_id: str
    cost_code_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostCodeActivated:
    tenant_id: str
    organization_id: str
    cost_code_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostCodeDeactivated:
    tenant_id: str
    organization_id: str
    cost_code_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCostCodeRestrictionAdded:
    tenant_id: str
    organization_id: str
    project_id: str
    cost_code_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCostCodeRestrictionRemoved:
    tenant_id: str
    organization_id: str
    project_id: str
    cost_code_id: str
    occurred_at: datetime


__all__ = [
    "ProjectFinancialProfileUpdated",
    "ProjectFinancialProfileTransitioned",
    "CostCodeCreated",
    "CostCodeProfileUpdated",
    "CostCodeActivated",
    "CostCodeDeactivated",
    "ProjectCostCodeRestrictionAdded",
    "ProjectCostCodeRestrictionRemoved",
]
