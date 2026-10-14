"""Auto-generated codes for Task, Resource, and Register entities."""

from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.risk.register import RegisterEntryType
from src.core.platform.common.exceptions import ValidationError


def _project(services):
    return services['project_create'].create_project("Plant Upgrade", "")


# ── Task (TSK, per-project) ──────────────────────────────────────────────────
def test_task_autogenerates_code(services):
    pid = _project(services).id
    task = services['task_lifecycle_commands'].create_task(pid, "Cable Pull", duration_days=2)
    assert task.code == "TSK-CABL-0001"


def test_task_code_is_per_project_scoped(services):
    services['task_lookup_query']
    services['project_query']
    p1 = services['project_create'].create_project("Project One", "").id
    p2 = services['project_create'].create_project("Project Two", "").id
    a = services['task_lifecycle_commands'].create_task(p1, "Cabling Run", duration_days=1)
    b = services['task_lifecycle_commands'].create_task(p2, "Cabling Run", duration_days=1)
    # same token in two projects -> both 0001 (per-project uniqueness)
    assert a.code == "TSK-CABL-0001"
    assert b.code == "TSK-CABL-0001"


def test_task_manual_duplicate_blocked_within_project(services):
    services['task_lookup_query']
    pid = _project(services).id
    services['task_lifecycle_commands'].create_task(pid, "Alpha", duration_days=1, code="TSK-DUP-1")
    with pytest.raises(ValidationError) as exc:
        services['task_lifecycle_commands'].create_task(pid, "Beta", duration_days=1, code="TSK-DUP-1")
    assert exc.value.code == "CODE_DUPLICATE"


# ── Resource (RES, global) ───────────────────────────────────────────────────
def test_resource_autogenerates_code(services):
    resource = services["resource_master_commands"].create_resource("Electrical Crew", "Lead")
    assert resource.code == "RES-ELEC-0001"


# ── Register (REG, per-project) ──────────────────────────────────────────────
def test_register_autogenerates_code(services):
    pid = _project(services).id
    entry = services["register_lifecycle_commands"].create_entry(
        pid,
        entry_type=RegisterEntryType.RISK,
        title="Supplier delay",
        due_date=date(2026, 6, 1),
    )
    assert entry.code == "REG-SUPP-0001"
