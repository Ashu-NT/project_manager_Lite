from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    DesktopApiResult,
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantDto,
    ScopedAccessGrantRemoveCommand,
)
from src.core.platform.access import AccessControlService
from src.core.platform.access.domain import ScopedAccessGrant


class PlatformAccessDesktopApi:
    """Desktop-facing adapter for scoped access administration flows."""

    def __init__(self, *, access_service: AccessControlService) -> None:
        self._access_service = access_service

    def list_scope_role_choices(self, scope_type: str) -> DesktopApiResult[tuple[str, ...]]:
        return execute_desktop_operation(
            lambda: tuple(self._access_service.list_scope_role_choices(scope_type))
        )

    def list_scope_grants(
        self,
        *,
        scope_type: str,
        scope_id: str,
    ) -> DesktopApiResult[tuple[ScopedAccessGrantDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_grant(grant)
                for grant in self._access_service.list_scope_grants(scope_type, scope_id)
            )
        )

    def assign_scope_grant(
        self,
        command: ScopedAccessGrantAssignCommand,
    ) -> DesktopApiResult[ScopedAccessGrantDto]:
        return execute_desktop_operation(
            lambda: self._serialize_grant(
                self._access_service.assign_scope_grant(
                    scope_type=command.scope_type,
                    scope_id=command.scope_id,
                    user_id=command.user_id,
                    scope_role=command.scope_role,
                )
            )
        )

    def remove_scope_grant(self, command: ScopedAccessGrantRemoveCommand) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._access_service.remove_scope_grant(
                scope_type=command.scope_type,
                scope_id=command.scope_id,
                user_id=command.user_id,
            )
        )

    @staticmethod
    def _serialize_grant(grant: ScopedAccessGrant) -> ScopedAccessGrantDto:
        return ScopedAccessGrantDto(
            id=grant.id,
            scope_type=grant.scope_type,
            scope_id=grant.scope_id,
            user_id=grant.user_id,
            scope_role=grant.scope_role,
            permission_codes=tuple(grant.permission_codes or ()),
            created_at=grant.created_at,
        )


__all__ = ["PlatformAccessDesktopApi"]
