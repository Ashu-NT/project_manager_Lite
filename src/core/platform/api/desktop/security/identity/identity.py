from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    ApiKeyCredentialDto,
    ApiKeyIssueCommand,
    DesktopApiResult,
    IssuedApiKeyDto,
    ServicePrincipalCreateCommand,
    ServicePrincipalDto,
)
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.domain.security.identity.service_principal import ApiKeyCredential, IssuedApiKey, ServicePrincipal


class PlatformIdentityDesktopApi:
    def __init__(self, *, service_principal_service: ServicePrincipalService) -> None:
        self._service = service_principal_service

    def list_service_principals(self) -> DesktopApiResult[tuple[ServicePrincipalDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_principal(row)
                for row in self._service.list_service_principals()
            )
        )

    def create_service_principal(
        self,
        command: ServicePrincipalCreateCommand,
    ) -> DesktopApiResult[ServicePrincipalDto]:
        return execute_desktop_operation(
            lambda: self._serialize_principal(
                self._service.create_service_principal(
                    name=command.name,
                    description=command.description,
                    initial_role_name=command.initial_role_name,
                )
            )
        )

    def disable_service_principal(
        self,
        principal_id: str,
    ) -> DesktopApiResult[ServicePrincipalDto]:
        return execute_desktop_operation(
            lambda: self._serialize_principal(
                self._service.disable_service_principal(principal_id)
            )
        )

    def list_api_keys(
        self,
        principal_id: str,
    ) -> DesktopApiResult[tuple[ApiKeyCredentialDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_credential(row)
                for row in self._service.list_api_keys(principal_id)
            )
        )

    def issue_api_key(self, command: ApiKeyIssueCommand) -> DesktopApiResult[IssuedApiKeyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_issued(
                self._service.issue_api_key(
                    command.service_principal_id,
                    name=command.name,
                    permission_scopes=command.permission_scopes,
                    expires_in_days=command.expires_in_days,
                )
            )
        )

    def rotate_api_key(
        self,
        credential_id: str,
        *,
        expires_in_days: int = 90,
    ) -> DesktopApiResult[IssuedApiKeyDto]:
        return execute_desktop_operation(
            lambda: self._serialize_issued(
                self._service.rotate_api_key(
                    credential_id,
                    expires_in_days=expires_in_days,
                )
            )
        )

    def revoke_api_key(self, credential_id: str) -> DesktopApiResult[ApiKeyCredentialDto]:
        return execute_desktop_operation(
            lambda: self._serialize_credential(
                self._service.revoke_api_key(credential_id)
            )
        )

    @staticmethod
    def _serialize_principal(row: ServicePrincipal) -> ServicePrincipalDto:
        return ServicePrincipalDto(
            id=row.id,
            tenant_id=row.tenant_id,
            organization_id=row.organization_id,
            user_id=row.user_id,
            name=row.name,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _serialize_credential(row: ApiKeyCredential) -> ApiKeyCredentialDto:
        return ApiKeyCredentialDto(
            id=row.id,
            service_principal_id=row.service_principal_id,
            name=row.name,
            key_prefix=row.key_prefix,
            permission_scopes=row.permission_scopes,
            expires_at=row.expires_at,
            last_used_at=row.last_used_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
        )

    @classmethod
    def _serialize_issued(cls, row: IssuedApiKey) -> IssuedApiKeyDto:
        return IssuedApiKeyDto(
            credential=cls._serialize_credential(row.credential),
            token=row.token,
        )


__all__ = ["PlatformIdentityDesktopApi"]
