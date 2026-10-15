from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.platform.access.application.dto.commands.scoped_access import (
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantRemoveCommand,
)
from src.core.platform.api.desktop.access.access import PlatformAccessDesktopApi
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.finance.financial_period import (
    FinancialPeriodDesktopApi,
)
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.core.platform.api.desktop.security.identity.identity import (
    PlatformIdentityDesktopApi,
)
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.application.finance.dto.commands.financial_periods import (
    FinancialPeriodCreateCommand,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.application.security.auth.dto.commands.users import (
    UserCreateCommand,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.core.platform.application.security.identity.dto.commands.service_principals import (
    ApiKeyIssueCommand,
    ServicePrincipalCreateCommand,
)
from src.core.platform.application.support.dto.commands.settings import (
    SupportSettingsUpdateCommand,
)
from src.core.platform.application.tenant.tenancy.dto.commands.tenants import (
    TenantCreateCommand,
)
from src.infra.platform.support_settings import SupportSettingsStore


@pytest.mark.parametrize(
    ("api_type", "dependencies", "authority", "method", "handler_method", "command", "serializer"),
    [
        (PlatformAccessDesktopApi, ("access_service",), "access_service",
         "assign_scope_grant", "assign_scope_grant",
         ScopedAccessGrantAssignCommand("project", "p", "u", "lead"), "_serialize_grant"),
        (PlatformAccessDesktopApi, ("access_service",), "access_service",
         "remove_scope_grant", "remove_scope_grant",
         ScopedAccessGrantRemoveCommand("project", "p", "u"), None),
        (PlatformApprovalDesktopApi, ("approval_commands", "approval_queries"), "approval_commands",
         "approve_and_apply", "approve_and_apply", ApprovalDecisionCommand("r", ""), "_serialize_request"),
        (PlatformApprovalDesktopApi, ("approval_commands", "approval_queries"), "approval_commands",
         "reject", "reject", ApprovalDecisionCommand("r", None), "_serialize_request"),
        (FinancialPeriodDesktopApi, ("financial_period_commands", "financial_period_queries"),
         "financial_period_commands", "create_period", "create_period",
         FinancialPeriodCreateCommand("P1", "January", 2026, 1, "2026-01-01", "2026-01-31"),
         "_serialize"),
        (FinancialPeriodDesktopApi, ("financial_period_commands", "financial_period_queries"),
         "financial_period_commands", "update_period", "update_period",
         FinancialPeriodUpdateCommand("p", 0, name=""), "_serialize"),
        (FinancialPeriodDesktopApi, ("financial_period_commands", "financial_period_queries"),
         "financial_period_commands", "close_period", "close_period",
         FinancialPeriodTransitionCommand("p", 0), "_serialize"),
        (FinancialPeriodDesktopApi, ("financial_period_commands", "financial_period_queries"),
         "financial_period_commands", "lock_period", "lock_period",
         FinancialPeriodTransitionCommand("p", 0), "_serialize"),
        (PlatformUserDesktopApi,
         ("auth_queries", "user_directory", "registration", "user_administration",
          "passwords", "session_commands", "role_assignment"), "registration",
         "create_user", "onboard_tenant_user", UserCreateCommand("u", "secret", is_active=False),
         "_serialize_user"),
        (PlatformUserDesktopApi,
         ("auth_queries", "user_directory", "registration", "user_administration",
          "passwords", "session_commands", "role_assignment"), "user_administration",
         "update_user", "update_user_profile", UserUpdateCommand("u", display_name=""),
         "_serialize_user"),
        (PlatformUserDesktopApi,
         ("auth_queries", "user_directory", "registration", "user_administration",
          "passwords", "session_commands", "role_assignment"), "passwords",
         "reset_password", "reset_user_password", UserPasswordResetCommand("u", "secret"),
         "_serialize_user"),
        (PlatformIdentityDesktopApi, ("service_principal_commands", "service_principal_query"),
         "service_principal_commands", "create_service_principal", "create_service_principal",
         ServicePrincipalCreateCommand("integration"), "_serialize_principal"),
        (PlatformIdentityDesktopApi, ("service_principal_commands", "service_principal_query"),
         "service_principal_commands", "issue_api_key", "issue_api_key",
         ApiKeyIssueCommand("s", "key", (), 0), "_serialize_issued"),
        (PlatformTenantDesktopApi,
         ("tenant_admin_queries", "tenant_lifecycle_commands", "tenant_context_service",
          "tenant_invitation_commands", "tenant_membership_queries"), "tenant_lifecycle_commands",
         "create_tenant", "create_tenant", TenantCreateCommand("TENANT", "Tenant"),
         "_serialize_tenant"),
    ],
)
def test_desktop_mutations_pass_the_same_command_to_injected_authority(
    api_type, dependencies, authority, method, handler_method, command, serializer,
):
    injected = {name: Mock() for name in dependencies}
    handler = getattr(injected[authority], handler_method)
    api = api_type(**injected)
    if serializer is not None:
        serialize = Mock(return_value="serialized")
        setattr(api, serializer, serialize)

    result = getattr(api, method)(command)

    assert result.ok
    handler.assert_called_once_with(command)
    assert handler.call_args.args[0] is command
    if serializer is not None:
        serialize.assert_called_once_with(handler.return_value)
        assert result.data == "serialized"


def test_support_settings_implementation_consumes_application_command():
    settings = Mock()
    store = SupportSettingsStore(settings)
    command = SupportSettingsUpdateCommand("beta", False, "  local-manifest.json  ")

    store.save_settings(command)

    assert settings.setValue.call_args_list == [
        (("updates/channel", "beta"),),
        (("updates/auto_check", False),),
        (("updates/manifest_url", "local-manifest.json"),),
    ]
    assert settings.sync.call_count == 3
