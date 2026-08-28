from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtCore import QObject  # noqa: F401

    _HAS_QT = True
except Exception:
    _HAS_QT = False

pytestmark = pytest.mark.skipif(not _HAS_QT, reason="PySide6 required")


class _Session:
    def __init__(
        self,
        *,
        principal: object | None = None,
        tenant_id: str | None = "tenant-1",
        organization_id: str | None = "org-1",
    ) -> None:
        self.principal = principal
        self.tenant_id = tenant_id
        self.organization_id = organization_id

    def active_tenant_id(self) -> str | None:
        return self.tenant_id

    def active_organization_id(self) -> str | None:
        return self.organization_id


def _ready_session() -> _Session:
    return _Session(principal=SimpleNamespace(user_id="user-1"))


def _build(*, engine=None, session_fn=None):
    from src.ui_qml.modules.project_management.controllers.common.pm_capability_controller import (
        PMCapabilityController,
    )

    return PMCapabilityController(
        auth_engine=engine,
        user_session_provider=session_fn,
    )


def _engine_allowing(*codes: str) -> MagicMock:
    engine = MagicMock()
    engine.has_permission.side_effect = lambda session, code: code in codes
    return engine


def _all_flags(controller) -> tuple[bool, ...]:
    return (
        controller.canApproveBaseline,
        controller.canApplyLeveling,
        controller.canManageSkills,
        controller.canRequestAssignmentOverride,
        controller.canImport,
        controller.canApprovePmRequest,
    )


def test_missing_engine_is_deny_safe() -> None:
    controller = _build(session_fn=_ready_session)

    assert _all_flags(controller) == (False,) * 6
    assert controller.evaluationState == "unavailable"


@pytest.mark.parametrize(
    "session",
    [
        None,
        _Session(principal=None),
        _Session(principal=object(), tenant_id=None),
        _Session(principal=object(), organization_id=None),
    ],
    ids=["missing-session", "missing-principal", "missing-tenant", "missing-org"],
)
def test_incomplete_session_context_is_deny_safe(session) -> None:
    engine = _engine_allowing(
        "baseline.approve",
        "task.manage",
        "resource.manage",
        "approval.request",
        "import.manage",
        "approval.decide",
    )

    controller = _build(engine=engine, session_fn=lambda: session)

    assert _all_flags(controller) == (False,) * 6
    assert controller.evaluationState == "unavailable"
    engine.has_permission.assert_not_called()


def test_known_allowed_and_denied_use_canonical_permissions() -> None:
    engine = _engine_allowing(
        "baseline.approve",
        "resource.manage",
        "import.manage",
    )
    session = _ready_session()

    controller = _build(engine=engine, session_fn=lambda: session)

    assert controller.canApproveBaseline is True
    assert controller.canApplyLeveling is False
    assert controller.canManageSkills is True
    assert controller.canRequestAssignmentOverride is False
    assert controller.canImport is True
    assert controller.canApprovePmRequest is False
    assert controller.evaluationState == "ready"
    assert {call.args[1] for call in engine.has_permission.call_args_list} == {
        "baseline.approve",
        "task.manage",
        "resource.manage",
        "approval.request",
        "import.manage",
        "approval.decide",
    }


def test_evaluation_exception_denies_failed_capability() -> None:
    engine = MagicMock()

    def evaluate(session, permission_code: str) -> bool:
        if permission_code == "import.manage":
            raise RuntimeError("authorization unavailable")
        return True

    engine.has_permission.side_effect = evaluate

    controller = _build(engine=engine, session_fn=_ready_session)

    assert controller.canImport is False
    assert controller.canApproveBaseline is True
    assert controller.evaluationState == "error"


def test_session_provider_exception_denies_every_capability() -> None:
    engine = _engine_allowing("baseline.approve")

    def failed_provider():
        raise RuntimeError("session unavailable")

    controller = _build(engine=engine, session_fn=failed_provider)

    assert _all_flags(controller) == (False,) * 6
    assert controller.evaluationState == "error"
    engine.has_permission.assert_not_called()


def test_refresh_recomputes_after_context_and_permission_changes() -> None:
    session = _ready_session()
    allowed = {"import.manage"}
    engine = MagicMock()
    engine.has_permission.side_effect = lambda current, code: code in allowed
    controller = _build(engine=engine, session_fn=lambda: session)
    assert controller.canImport is True

    session.organization_id = None
    controller.refresh()
    assert controller.canImport is False
    assert controller.evaluationState == "unavailable"

    session.organization_id = "org-2"
    allowed.clear()
    controller.refresh()
    assert controller.canImport is False
    assert controller.evaluationState == "ready"


def test_workspace_catalog_injects_authoritative_capability_dependencies() -> None:
    from src.ui_qml.modules.project_management.context import (
        ProjectManagementWorkspaceCatalog,
    )

    session = _ready_session()
    engine = _engine_allowing("import.manage")
    catalog = ProjectManagementWorkspaceCatalog(
        auth_engine=engine,
        user_session_provider=lambda: session,
    )

    assert catalog.pmCapabilityController.canImport is True
    session.organization_id = None
    catalog.refreshCapabilities()
    assert catalog.pmCapabilityController.canImport is False


def test_assignment_policy_evaluation_failures_are_blocking() -> None:
    from src.ui_qml.modules.project_management.controllers.tasks.pm_assignment_controller import (
        PMAssignmentController,
    )

    presenter = MagicMock()
    presenter.validate_assignment.side_effect = RuntimeError("validation unavailable")
    presenter.preview_assignment.side_effect = RuntimeError("preview unavailable")
    controller = PMAssignmentController(
        presenter=presenter,
        facade_refresh=lambda: None,
        set_is_busy=lambda value: None,
        set_error_message=lambda value: None,
        set_feedback_message=lambda value: None,
    )

    validation = controller.validateAssignment({"taskId": "task-1"})
    preview = controller.previewAssignment({"taskId": "task-1"})

    assert validation["ok"] is False
    assert validation["canAssign"] is False
    assert validation["isBlocked"] is True
    assert preview["ok"] is False
    assert preview["isBlocked"] is True
    assert preview["skillsMatched"] is False
    assert preview["certsValid"] is False


def test_assignment_mutation_reloads_authoritative_page_immediately() -> None:
    from src.ui_qml.modules.project_management.controllers.tasks.pm_assignment_controller import (
        PMAssignmentController,
    )

    presenter = MagicMock()
    presenter.build_task_assignments_page.return_value = {
        "items": [{"id": "assignment-1", "resourceName": "New Resource"}],
        "total": 1,
        "page": 1,
        "pageSize": 25,
        "sortKey": "resourceName",
        "sortDirection": "asc",
    }
    facade_refresh = MagicMock()
    controller = PMAssignmentController(
        presenter=presenter,
        facade_refresh=facade_refresh,
        set_is_busy=lambda _value: None,
        set_error_message=lambda _value: None,
        set_feedback_message=lambda _value: None,
    )
    controller._task_id = "task-1"

    result = controller.createAssignment({"taskId": "task-1"})

    assert result["ok"] is True
    presenter.create_assignment.assert_called_once()
    presenter.build_task_assignments_page.assert_called_once()
    assert controller.assignments["total"] == 1
    assert controller.assignments["items"][0]["id"] == "assignment-1"
    facade_refresh.assert_called_once()


def test_qml_capability_fallbacks_and_row_actions_are_deny_safe() -> None:
    root = Path("src/ui_qml/modules/project_management/qml")
    projects = (root / "workspaces/projects/ProjectsWorkspacePage.qml").read_text(
        encoding="utf-8"
    )
    baselines = (
        root / "workspaces/scheduling/panels/SchedulingBaselinesPanel.qml"
    ).read_text(encoding="utf-8")
    resources = (root / "workspaces/resources/ResourcesWorkspacePage.qml").read_text(
        encoding="utf-8"
    )
    record_list = (root / "ProjectManagement/Widgets/RecordListCard.qml").read_text(
        encoding="utf-8"
    )

    assert "pmCapabilityController.canImport : false" in projects
    assert "pmCapabilityController.canApproveBaseline : false" in baselines
    assert "pmCapabilityController.canManageSkills : false" in resources
    assert "canPrimaryAction ?? false" in record_list
    assert "canSecondaryAction ?? false" in record_list
    assert "canTertiaryAction ?? false" in record_list


def test_resource_capability_inputs_default_to_denied() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/resources")

    for relative_path in (
        "panels/ResourcesDetailPanel.qml",
        "sections/ResourcesSkillsSection.qml",
        "sections/ResourcesCertificationsSection.qml",
    ):
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "property bool canManageSkills: false" in source
