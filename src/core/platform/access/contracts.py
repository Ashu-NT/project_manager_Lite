from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.access.domain import ProjectMembership, ScopedAccessGrant


class ProjectMembershipRepository(ABC):
    @abstractmethod
    def add(self, membership: ProjectMembership) -> None: ...

    @abstractmethod
    def update(self, membership: ProjectMembership) -> None: ...

    @abstractmethod
    def get(self, membership_id: str) -> ProjectMembership | None: ...

    @abstractmethod
    def get_for_project_user(self, project_id: str, user_id: str) -> ProjectMembership | None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[ProjectMembership]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> list[ProjectMembership]: ...

    def list_by_user_for_context(
        self,
        user_id: str,
        *,
        tenant_id: str,
        organization_id: str | None = None,
    ) -> list[ProjectMembership]:
        """Read memberships against an explicit target context.

        Runtime principal construction must not infer this scope from mutable
        session state. Repositories without an explicit implementation are not
        safe for that path.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, membership_id: str) -> None: ...


class ScopedAccessGrantRepository(ABC):
    @abstractmethod
    def add(self, grant: ScopedAccessGrant) -> None: ...

    @abstractmethod
    def update(self, grant: ScopedAccessGrant) -> None: ...

    @abstractmethod
    def get(self, grant_id: str) -> ScopedAccessGrant | None: ...

    @abstractmethod
    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> ScopedAccessGrant | None: ...

    @abstractmethod
    def list_by_scope(self, scope_type: str, scope_id: str) -> list[ScopedAccessGrant]: ...

    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> list[ScopedAccessGrant]: ...

    def list_by_user_for_context(
        self,
        user_id: str,
        *,
        tenant_id: str,
        organization_id: str | None = None,
        scope_type: str | None = None,
    ) -> list[ScopedAccessGrant]:
        """Read grants against an explicit target context."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, grant_id: str) -> None: ...


__all__ = ["ProjectMembershipRepository", "ScopedAccessGrantRepository"]
