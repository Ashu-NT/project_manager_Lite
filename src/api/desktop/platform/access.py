from __future__ import annotations

from collections.abc import Callable, Mapping

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    DesktopApiResult,
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantDto,
    ScopedAccessGrantRemoveCommand,
    ScopeTargetDto,
    ScopeTypeChoiceDto,
)
from src.core.platform.access import AccessControlService
from src.core.platform.access.domain import ScopedAccessGrant


class PlatformAccessDesktopApi:
    """Desktop-facing adapter for scoped access administration flows."""

    def __init__(
        self,
        *,
        access_service: AccessControlService,
        scope_type_choices: tuple[tuple[str, str], ...] | None = None,
        scope_option_loaders: Mapping[str, Callable[[], list[tuple[str, str]]]] | None = None,
        scope_disabled_hints: Mapping[str, str] | None = None,
    ) -> None:
        self._access_service = access_service
        self._scope_type_choices = tuple(scope_type_choices or ())
        self._scope_option_loaders = dict(scope_option_loaders or {})
        self._scope_disabled_hints = dict(scope_disabled_hints or {})

    def list_scope_types(self) -> DesktopApiResult[tuple[ScopeTypeChoiceDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                ScopeTypeChoiceDto(
                    label=label,
                    value=value,
                    enabled=value in self._scope_option_loaders,
                    supporting_text=self._scope_disabled_hints.get(value, ""),
                )
                for label, value in self._scope_type_choices
            )
        )

    def list_scope_targets(self, scope_type: str) -> DesktopApiResult[tuple[ScopeTargetDto, ...]]:
        def _load_targets() -> tuple[ScopeTargetDto, ...]:
            loader = self._scope_option_loaders.get(scope_type.strip().lower())
            if loader is None:
                return ()
            return tuple(
                ScopeTargetDto(
                    id=value,
                    label=label,
                    scope_type=scope_type.strip().lower(),
                )
                for label, value in loader()
            )

        return execute_desktop_operation(_load_targets)

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
