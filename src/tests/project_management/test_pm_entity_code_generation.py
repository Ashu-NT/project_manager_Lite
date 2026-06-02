"""Auto-generated codes for Task / Resource / Cost / Register (Phase A+B backend)."""

from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.risk.register import RegisterEntryType
from src.core.platform.common.exceptions import ValidationError


def _project(services):
    return services["project_service"].create_project("Plant Upgrade", "")


# ── Task (TSK, per-project) ──────────────────────────────────────────────────
def test_task_autogenerates_code(services):
    pid = _project(services).id
    task = services["task_service"].create_task(pid, "Cable Pull", duration_days=2)
    assert task.code == "TSK-CABL-0001"


def test_task_code_is_per_project_scoped(services):
    ts = services["task_service"]
    ps = services["project_service"]
    p1 = ps.create_project("Project One", "").id
    p2 = ps.create_project("Project Two", "").id
    a = ts.create_task(p1, "Cabling Run", duration_days=1)
    b = ts.create_task(p2, "Cabling Run", duration_days=1)
    # same token in two projects -> both 0001 (per-project uniqueness)
    assert a.code == "TSK-CABL-0001"
    assert b.code == "TSK-CABL-0001"


def test_task_manual_duplicate_blocked_within_project(services):
    ts = services["task_service"]
    pid = _project(services).id
    ts.create_task(pid, "Alpha", duration_days=1, code="TSK-DUP-1")
    with pytest.raises(ValidationError) as exc:
        ts.create_task(pid, "Beta", duration_days=1, code="TSK-DUP-1")
    assert exc.value.code == "CODE_DUPLICATE"


# ── Resource (RES, global) ───────────────────────────────────────────────────
def test_resource_autogenerates_code(services):
    resource = services["resource_service"].create_resource("Electrical Crew", "Lead")
    assert resource.code == "RES-ELEC-0001"


# ── Cost (CST, per-project) ──────────────────────────────────────────────────
def test_cost_autogenerates_code(services):
    pid = _project(services).id
    cost = services["cost_service"].add_cost_item(pid, "Cabling Materials", 1000.0, cost_type=CostType.MATERIAL)
    assert cost.code == "CST-CABL-0001"


# ── Register (REG, per-project) ──────────────────────────────────────────────
def test_register_autogenerates_code(services):
    pid = _project(services).id
    entry = services["register_service"].create_entry(
        pid,
        entry_type=RegisterEntryType.RISK,
        title="Supplier delay",
        due_date=date(2026, 6, 1),
    )
    assert entry.code == "REG-SUPP-0001"
