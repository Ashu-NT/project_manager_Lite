from __future__ import annotations

from typing import get_type_hints

import pytest

from src.core.platform.application.approval.commands import ApprovalCommandHandler
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.contract.models.approval.contracts import ApprovalDecisionInput
from src.core.platform.contract.port.approval.capabilities import ApprovalCommands


def _grouped_commands(handler: ApprovalCommandHandler) -> ApprovalCommands:
    return handler


def _decision_input(command: ApprovalDecisionCommand) -> ApprovalDecisionInput:
    return command


@pytest.mark.parametrize("note", [None, "", "Approved"])
def test_application_decision_implements_neutral_readonly_input(note: str | None) -> None:
    command = ApprovalDecisionCommand(request_id="request-1", note=note)

    decision = _decision_input(command)

    assert decision is command
    assert decision.request_id == "request-1"
    assert decision.note == note


@pytest.mark.parametrize("method", ["approve_and_apply", "reject"])
def test_grouped_port_and_handler_consume_the_same_neutral_input(method: str) -> None:
    assert get_type_hints(getattr(ApprovalCommands, method))["command"] is ApprovalDecisionInput
    assert get_type_hints(getattr(ApprovalCommandHandler, method))["command"] is ApprovalDecisionInput
