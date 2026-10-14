"""Shared wiring for tests that exercise Auth handlers outside the full graph."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
    build_platform_repositories,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    AuthComposition,
    build_auth_handlers,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)


def platform_user_api(services: Mapping[str, Any]) -> PlatformUserDesktopApi:
    return PlatformUserDesktopApi(
        auth_queries=services["auth_queries"],
        user_directory=services["user_directory_query"],
        registration=services["user_registration"],
        user_administration=services["user_administration_commands"],
        passwords=services["password_commands"],
        session_commands=services["auth_session_commands"],
        role_assignment=services["role_assignment_commands"],
    )


def standalone_auth(
    session: Session,
    repositories: PlatformRepositories | None = None,
    **context: Any,
) -> tuple[AuthComposition, PlatformRepositories]:
    """Auth handlers over `session` with fresh dispatchers and no runtime hooks."""
    resolved = repositories or build_platform_repositories(session)
    auth = build_auth_handlers(
        session=session,
        repositories=resolved,
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        **context,
    )
    return auth, resolved


__all__ = ["platform_user_api", "standalone_auth"]
