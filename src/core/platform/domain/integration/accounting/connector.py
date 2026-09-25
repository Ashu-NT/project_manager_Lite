from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]


class AccountingConnectorConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str = Field(min_length=1)
    organization_id: str = Field(min_length=1)
    adapter_id: Identifier
    connection_id: Identifier
    secret_reference: Identifier
    enabled: bool
    version: int = Field(ge=1)


class AccountingHandoffDenial(StrEnum):
    ADAPTER_NOT_INSTALLED = "adapter_not_installed"
    MODULE_NOT_ENABLED = "module_not_enabled"
    INTEGRATION_NOT_CONFIGURED = "integration_not_configured"
    PERMISSION_DENIED = "permission_denied"
    BUSINESS_PRECONDITION_FAILED = "business_precondition_failed"


class AccountingHandoffCapability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    reason: AccountingHandoffDenial | None

    @property
    def message(self) -> str:
        return {
            AccountingHandoffDenial.ADAPTER_NOT_INSTALLED: "Accounting integration is not installed.",
            AccountingHandoffDenial.MODULE_NOT_ENABLED: "Accounting integration is not enabled.",
            AccountingHandoffDenial.INTEGRATION_NOT_CONFIGURED: "Accounting integration is not configured.",
            AccountingHandoffDenial.PERMISSION_DENIED: "You do not have permission to request Accounting handoff.",
            AccountingHandoffDenial.BUSINESS_PRECONDITION_FAILED: "Billing Preparation is not eligible for Accounting handoff.",
            None: "",
        }[self.reason]
