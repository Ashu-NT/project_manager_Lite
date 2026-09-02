from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from textwrap import dedent

import pytest
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlComponent

from src.core.modules.project_management.api.desktop.financials import (
    FinancialChangeImpactCommand,
    FinancialCreateChangeCommand,
    FinancialRemoveChangeImpactCommand,
    FinancialSubmitChangeCommand,
    FinancialUpdateChangeCommand,
    FinancialUpdateChangeImpactCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.financial_changes.event_handlers.view_invalidation import (
    FINANCIAL_CHANGE_BUDGET_SCOPE_CODE,
    FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE,
    build_financial_change_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
    FinancialChangeEventType,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.ui_qml.shell.qml_engine import create_qml_engine
from src.ui_qml.modules.project_management.presenters.financials.command_handler import (
    _impact_fields,
)


def _change(version: int = 1):
    return SimpleNamespace(
        id="change-1",
        project_id="project-1",
        status=FinancialChangeStatus.DRAFT,
        row_version=version,
        approval_request_id=None,
    )


class _ChangeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._user_session = SimpleNamespace(
            principal=SimpleNamespace(user_id="user-1")
        )
        self.change = _change()

    def get_change(self, _change_id):
        return self.change

    def create_change(self, *args, **kwargs):
        self.calls.append(("create_change", args, kwargs))
        return self.change

    def update_change(self, *args, **kwargs):
        self.calls.append(("update_change", args, kwargs))
        self.change = _change(2)
        return self.change

    def add_impact(self, *args, **kwargs):
        self.calls.append(("add_impact", args, kwargs))
        self.change = _change(2)
        return SimpleNamespace(
            id="impact-1", change_request_id="change-1", row_version=1
        )

    def update_impact(self, *args, **kwargs):
        self.calls.append(("update_impact", args, kwargs))
        self.change = _change(3)
        return SimpleNamespace(
            id="impact-1", change_request_id="change-1", row_version=2
        )

    def remove_impact(self, *args, **kwargs):
        self.calls.append(("remove_impact", args, kwargs))
        return _change(4)

    def submit_change(self, *args, **kwargs):
        self.calls.append(("submit_change", args, kwargs))
        result = _change(5)
        result.status = FinancialChangeStatus.PENDING_APPROVAL
        result.approval_request_id = "approval-1"
        return result


class _Boundary:
    def __init__(self) -> None:
        self.service = _ChangeService()

    def financial_change(self, command, *, project_id=None):
        return command(self.service)


def test_typed_financial_change_commands_route_through_one_governance_boundary() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary  # type: ignore[arg-type]
    )
    created = api.create_financial_change(
        FinancialCreateChangeCommand(
            project_id="project-1",
            title="Scope change",
            reason="Client direction",
            effective_date="2026-09-02",
        )
    )
    updated = api.update_financial_change(
        FinancialUpdateChangeCommand(
            change_id=created.change_id,
            expected_version=created.row_version,
            title="Scope change revised",
            reason="Client direction",
            effective_date="2026-09-03",
        )
    )
    impact = api.add_financial_change_impact(
        FinancialChangeImpactCommand(
            change_id=created.change_id,
            expected_change_version=updated.row_version,
            impact_type="budget",
            description="Additional engineering",
            amount="125.50",
            currency_code="XAF",
            cost_code_id="code-1",
        )
    )
    edited_impact = api.update_financial_change_impact(
        FinancialUpdateChangeImpactCommand(
            impact_id=impact.impact_id,
            expected_impact_version=impact.impact_row_version,
            change_id=created.change_id,
            expected_change_version=impact.row_version,
            impact_type="budget",
            description="Revised engineering",
            amount="150",
            currency_code="XAF",
            cost_code_id="code-1",
        )
    )
    api.remove_financial_change_impact(
        FinancialRemoveChangeImpactCommand(
            impact_id=impact.impact_id,
            expected_impact_version=edited_impact.impact_row_version,
            expected_change_version=edited_impact.row_version,
        )
    )
    submitted = api.submit_financial_change(
        FinancialSubmitChangeCommand(change_id=created.change_id, expected_version=4)
    )

    assert submitted.approval_request_id == "approval-1"
    assert [call[0] for call in boundary.service.calls] == [
        "create_change",
        "update_change",
        "add_impact",
        "update_impact",
        "remove_impact",
        "submit_change",
    ]
    add_call = boundary.service.calls[2]
    assert add_call[2]["impact_type"] is FinancialChangeImpactType.BUDGET
    assert add_call[2]["amount"] == Decimal("125.50")


def test_financial_change_presenter_emits_canonical_decimal_string() -> None:
    fields = _impact_fields(
        {
            "changeId": "change-1",
            "changeVersion": 2,
            "impactType": "budget",
            "description": "Additional scope",
            "amount": "1E+2",
        }
    )

    assert fields["amount"] == "100"
    assert isinstance(fields["amount"], str)


def test_financial_change_event_invalidation_is_typed_and_effect_specific() -> None:
    channel = SimpleNamespace(hints=[])
    channel.notify = channel.hints.append
    handler = build_financial_change_view_invalidation_handler(channel)
    event = FinancialChangeChanged(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        change_id="change-1",
        change_type=FinancialChangeEventType.APPLIED,
        occurred_at=datetime.now(timezone.utc),
        applied_effects=("budget",),
    )

    handler(event, DomainEventContext(correlation_id="command-1"))

    assert [hint.scope_code for hint in channel.hints] == [
        FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE,
        FINANCIAL_CHANGE_BUDGET_SCOPE_CODE,
    ]


def test_qml_financial_change_commands_use_central_dialog_host_and_typed_slots() -> None:
    controller = Path(
        "src/ui_qml/modules/project_management/controllers/financials/"
        "financials_workspace_controller.py"
    ).read_text(encoding="utf-8")
    host = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs/"
        "FinancialsDialogHost.qml"
    ).read_text(encoding="utf-8")

    for slot in (
        "createFinancialChange",
        "updateFinancialChange",
        "addFinancialChangeImpact",
        "updateFinancialChangeImpact",
        "removeFinancialChangeImpact",
        "submitFinancialChange",
        "decideFinancialChange",
    ):
        assert f"def {slot}(" in controller
        assert f"workspaceController.{slot}(" in host
    assert "FinancialChangeRequestDialog" in host
    assert "FinancialChangeImpactDialog" in host
    assert "FinancialChangeLifecycleDialog" in host


@pytest.mark.parametrize(
    "dialog_type",
    (
        "FinancialChangeRequestDialog",
        "FinancialChangeImpactDialog",
        "FinancialChangeLifecycleDialog",
    ),
)
@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_financial_change_dialogs_fit_supported_viewports(
    qapp, dialog_type: str, width: int, height: int
) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    dialog_url = (
        Path(
            "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs"
        ).resolve()
        / f"{dialog_type}.qml"
    ).as_uri()
    component.setData(
        dedent(
            f"""
            import QtQuick
            import QtQuick.Controls
            ApplicationWindow {{
                width: {width}
                height: {height}
                visible: true
                readonly property var changeDialog: dialogLoader.item
                Loader {{
                    id: dialogLoader
                    source: "{dialog_url}"
                    onLoaded: item.open()
                }}
            }}
            """
        ).encode("utf-8"),
        f"r6c-{dialog_type}-{width}x{height}.qml",
    )
    root = component.create()
    assert root is not None, "\n".join(
        error.toString() for error in component.errors()
    )
    qapp.processEvents()
    dialog = root.property("changeDialog")
    assert dialog is not None
    assert 0 < float(dialog.property("width")) <= width
    assert 0 < float(dialog.property("height")) <= height
    assert dialog.findChild(QObject, "dialogCancelButton") is not None
    assert dialog.findChild(QObject, "dialogSubmitButton") is not None
    dialog.close()
    root.deleteLater()
    qapp.processEvents()
