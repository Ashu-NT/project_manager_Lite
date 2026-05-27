from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.platform.access.domain import ProjectMembership, ScopedAccessGrant


class ProjectMembershipRepository(ABC):
    @abstractmethod
    def add(self, membership: ProjectMembership) -> None: ...

    @abstractmethod
    def update(self, membership: ProjectMembership) -> None: ...

    @abstractmethod
    def get(self, membership_id: str) -> Optional[ProjectMembership]: ...

    @abstractmethod
    def get_for_project_user(self, project_id: str, user_id: str) -> Optional[ProjectMembership]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[ProjectMembership]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[ProjectMembership]: ...

    @abstractmethod
    def delete(self, membership_id: str) -> None: ...


class ScopedAccessGrantRepository(ABC):
    @abstractmethod
    def add(self, grant: ScopedAccessGrant) -> None: ...

    @abstractmethod
    def update(self, grant: ScopedAccessGrant) -> None: ...

    @abstractmethod
    def get(self, grant_id: str) -> Optional[ScopedAccessGrant]: ...

    @abstractmethod
    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> Optional[ScopedAccessGrant]: ...

    @abstractmethod
    def list_by_scope(self, scope_type: str, scope_id: str) -> List[ScopedAccessGrant]: ...

    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> List[ScopedAccessGrant]: ...

    @abstractmethod
    def delete(self, grant_id: str) -> None: ...


__all__ = ["ProjectMembershipRepository", "ScopedAccessGrantRepository"]
