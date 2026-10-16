from dataclasses import dataclass

from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)


@dataclass(frozen=True)
class ApprovalRequestDto(ApprovalRequestResponse):
    module_label: str = ""
    context_label: str = ""
    display_label: str = ""
