from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.modules.project_management.domain.financials.budget import BudgetStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetVersionCreated:
    """A new `ProjectBudget` revision was created -- `create_budget` and `create_successor` are
    the same kind of fact (a version now exists), differentiated by `predecessor_budget_id`
    rather than two near-identical classes. `status` is normally DRAFT; it is APPROVED only when
    the version was created by an already-approved Financial Change (`_apply_approved_financial_
    change`), which never persists an intermediate DRAFT/SUBMITTED row for that successor."""

    tenant_id: str
    organization_id: str
    project_id: str
    budget_id: str
    status: BudgetStatus
    predecessor_budget_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetProfileUpdated:
    """`update_budget_header` -- name/notes edited on a mutable DRAFT budget. Distinct from
    `BudgetStatusChanged`/`BudgetLineChanged`: no status transition and no line mutation occurs."""

    tenant_id: str
    organization_id: str
    project_id: str
    budget_id: str
    occurred_at: datetime


class BudgetLineChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetLineChanged:
    """`add_line`/`update_line`/`delete_line` are all the same kind of fact (a `BudgetLine`
    changed), differentiated by `change_type`."""

    tenant_id: str
    organization_id: str
    project_id: str
    budget_id: str
    budget_line_id: str
    change_type: BudgetLineChangeType
    occurred_at: datetime


class BudgetStatusChangeType(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetStatusChanged:
    """A workflow decision advanced the budget's lifecycle stage -- `submit`, `approve`,
    `reject`, `close`, and the implicit `supersede` a competing approval triggers on the
    previously-approved version are all the same kind of fact (the budget's status field
    changed), differentiated by `change_type`. A single `approve_budget`/approval-participant
    decision can legitimately produce two of these -- one per affected `ProjectBudget` row (the
    newly APPROVED version and the previously-approved version now SUPERSEDED)."""

    tenant_id: str
    organization_id: str
    project_id: str
    budget_id: str
    change_type: BudgetStatusChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetRemoved:
    """`delete_budget` -- a DRAFT version was hard-deleted (its lines cascade at the persistence
    layer; no independent `BudgetLineChanged(REMOVED)` is emitted per cascaded line)."""

    tenant_id: str
    organization_id: str
    project_id: str
    budget_id: str
    occurred_at: datetime


__all__ = [
    "BudgetVersionCreated",
    "BudgetProfileUpdated",
    "BudgetLineChangeType",
    "BudgetLineChanged",
    "BudgetStatusChangeType",
    "BudgetStatusChanged",
    "BudgetRemoved",
]
