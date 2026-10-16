from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.security.identity import (
    ServicePrincipalCommandHandler,
    ServicePrincipalQueryHandler,
)
from src.core.platform.application.security.identity.dto.commands.service_principals import (
    ApiKeyIssueCommand,
    ServicePrincipalCreateCommand,
)
from src.core.platform.application.security.identity.dto.responses.identity import (
    ApiKeyCredentialDto,
    IssuedApiKeyDto,
    ServicePrincipalDto,
)


class PlatformIdentityDesktopApi:
    def __init__(
        self, *, service_principal_commands: ServicePrincipalCommandHandler,
        service_principal_query: ServicePrincipalQueryHandler,
    ) -> None:
        self._commands = service_principal_commands
        self._query = service_principal_query

    def list_service_principals(self) -> DesktopApiResult[tuple[ServicePrincipalDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                row
                for row in self._query.list_service_principals()
            )
        )

    def create_service_principal(
        self,
        command: ServicePrincipalCreateCommand,
    ) -> DesktopApiResult[ServicePrincipalDto]:
        return execute_desktop_operation(
            lambda: self._commands.create_service_principal(command)
        )

    def disable_service_principal(
        self,
        principal_id: str,
    ) -> DesktopApiResult[ServicePrincipalDto]:
        return execute_desktop_operation(
            lambda: self._commands.disable_service_principal(principal_id)
        )

    def list_api_keys(
        self,
        principal_id: str,
    ) -> DesktopApiResult[tuple[ApiKeyCredentialDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                row
                for row in self._query.list_api_keys(principal_id)
            )
        )

    def issue_api_key(self, command: ApiKeyIssueCommand) -> DesktopApiResult[IssuedApiKeyDto]:
        return execute_desktop_operation(
            lambda: self._commands.issue_api_key(command)
        )

    def rotate_api_key(
        self,
        credential_id: str,
        *,
        expires_in_days: int = 90,
    ) -> DesktopApiResult[IssuedApiKeyDto]:
        return execute_desktop_operation(
            lambda: self._commands.rotate_api_key(
                    credential_id,
                    expires_in_days=expires_in_days,
                )
        )

    def revoke_api_key(self, credential_id: str) -> DesktopApiResult[ApiKeyCredentialDto]:
        return execute_desktop_operation(
            lambda: self._commands.revoke_api_key(credential_id)
        )





__all__ = ["PlatformIdentityDesktopApi"]
