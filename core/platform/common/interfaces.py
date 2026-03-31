from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.platform.access.domain import ProjectMembership, ScopedAccessGrant
from core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from core.platform.audit.domain import AuditLogEntry
from core.platform.auth.domain import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
)
from core.platform.org.domain import Department, Employee, Organization, Site
from core.platform.time.interfaces import TimeEntryRepository, TimesheetPeriodRepository


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


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: UserAccount) -> None: ...

    @abstractmethod
    def update(self, user: UserAccount) -> None: ...

    @abstractmethod
    def get(self, user_id: str) -> Optional[UserAccount]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserAccount]: ...

    @abstractmethod
    def get_by_federated_identity(
        self,
        identity_provider: str,
        federated_subject: str,
    ) -> Optional[UserAccount]: ...

    @abstractmethod
    def list_all(self) -> List[UserAccount]: ...


class AuthSessionRepository(ABC):
    @abstractmethod
    def add(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def update(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> Optional[AuthSession]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[AuthSession]: ...


class EmployeeRepository(ABC):
    @abstractmethod
    def add(self, employee: Employee) -> None: ...

    @abstractmethod
    def update(self, employee: Employee) -> None: ...

    @abstractmethod
    def get(self, employee_id: str) -> Optional[Employee]: ...

    @abstractmethod
    def get_by_code(self, employee_code: str) -> Optional[Employee]: ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> List[Employee]: ...


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None: ...

    @abstractmethod
    def update(self, organization: Organization) -> None: ...

    @abstractmethod
    def get(self, organization_id: str) -> Optional[Organization]: ...

    @abstractmethod
    def get_by_code(self, organization_code: str) -> Optional[Organization]: ...

    @abstractmethod
    def get_active(self) -> Optional[Organization]: ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> List[Organization]: ...


class SiteRepository(ABC):
    @abstractmethod
    def add(self, site: Site) -> None: ...

    @abstractmethod
    def update(self, site: Site) -> None: ...

    @abstractmethod
    def get(self, site_id: str) -> Optional[Site]: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, site_code: str) -> Optional[Site]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> List[Site]: ...


class DepartmentRepository(ABC):
    @abstractmethod
    def add(self, department: Department) -> None: ...

    @abstractmethod
    def update(self, department: Department) -> None: ...

    @abstractmethod
    def get(self, department_id: str) -> Optional[Department]: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, department_code: str) -> Optional[Department]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> List[Department]: ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> None: ...

    @abstractmethod
    def get(self, role_id: str) -> Optional[Role]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Role]: ...

    @abstractmethod
    def list_all(self) -> List[Role]: ...


class PermissionRepository(ABC):
    @abstractmethod
    def add(self, permission: Permission) -> None: ...

    @abstractmethod
    def get(self, permission_id: str) -> Optional[Permission]: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Permission]: ...

    @abstractmethod
    def list_all(self) -> List[Permission]: ...


class UserRoleRepository(ABC):
    @abstractmethod
    def add(self, binding: UserRoleBinding) -> None: ...

    @abstractmethod
    def delete(self, user_id: str, role_id: str) -> None: ...

    @abstractmethod
    def exists(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def list_role_ids(self, user_id: str) -> List[str]: ...


class RolePermissionRepository(ABC):
    @abstractmethod
    def add(self, binding: RolePermissionBinding) -> None: ...

    @abstractmethod
    def delete(self, role_id: str, permission_id: str) -> None: ...

    @abstractmethod
    def exists(self, role_id: str, permission_id: str) -> bool: ...

    @abstractmethod
    def list_permission_ids(self, role_id: str) -> List[str]: ...


class AuditLogRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditLogEntry) -> None: ...

    @abstractmethod
    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> List[AuditLogEntry]: ...


class ApprovalRepository(ABC):
    @abstractmethod
    def add(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def update(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def get(self, request_id: str) -> Optional[ApprovalRequest]: ...

    @abstractmethod
    def list_by_status(
        self,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
    ) -> List[ApprovalRequest]: ...


__all__ = [
    "ApprovalRepository",
    "AuthSessionRepository",
    "AuditLogRepository",
    "DepartmentRepository",
    "EmployeeRepository",
    "OrganizationRepository",
    "PermissionRepository",
    "ProjectMembershipRepository",
    "RolePermissionRepository",
    "RoleRepository",
    "ScopedAccessGrantRepository",
    "SiteRepository",
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
    "UserRepository",
    "UserRoleRepository",
]
