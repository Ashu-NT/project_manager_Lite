from __future__ import annotations

from typing import TypeAlias

FinancialsMap: TypeAlias = dict[str, object]
FinancialsObjectList: TypeAlias = list[dict[str, object]]

def default_overview() -> FinancialsMap:
    return {"title": "", "subtitle": "", "metrics": []}

def default_collection() -> FinancialsMap:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}

def default_detail() -> FinancialsMap:
    return {
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {},
    }

def default_forecast() -> FinancialsMap:
    return {
        "basisLabel": "",
        "budgetLabel": "",
        "actualLabel": "",
        "etcLabel": "",
        "eacLabel": "",
        "vacLabel": "",
        "isOverBudget": False,
        "hasApprovedForecast": False,
        "forecastRevision": None,
        "forecastAsOfLabel": "",
        "alertMessage": "",
        "metrics": [],
    }

def default_commitment_summary() -> FinancialsMap:
    return {
        "approvedBudgetLabel": "",
        "postedActualLabel": "",
        "openCommitmentLabel": "",
        "availableAfterCommitmentLabel": "",
        "commitmentRatePct": 0.0,
    }

__all__ = [
    "FinancialsMap",
    "FinancialsObjectList",
    "default_collection",
    "default_commitment_summary",
    "default_forecast",
    "default_overview",
    "default_detail",
]
