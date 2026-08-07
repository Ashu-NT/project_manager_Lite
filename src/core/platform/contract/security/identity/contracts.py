from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.platform.domain.security.identity.service_principal import ApiKeyCredential, ServicePrincipal


class ServicePrincipalRepository(ABC):
    @abstractmethod
    def add(self, principal: ServicePrincipal) -> None: ...

    @abstractmethod
    def update(self, principal: ServicePrincipal) -> None: ...

    @abstractmethod
    def get(self, principal_id: str) -> ServicePrincipal | None: ...

    @abstractmethod
    def get_for_authentication(
        self,
        principal_id: str,
        tenant_id: str,
    ) -> ServicePrincipal | None: ...

    @abstractmethod
    def list_all(self) -> list[ServicePrincipal]: ...


class ApiKeyCredentialRepository(ABC):
    @abstractmethod
    def add(self, credential: ApiKeyCredential) -> None: ...

    @abstractmethod
    def update(self, credential: ApiKeyCredential) -> None: ...

    @abstractmethod
    def update_for_authentication(self, credential: ApiKeyCredential) -> None: ...

    @abstractmethod
    def get(self, credential_id: str) -> ApiKeyCredential | None: ...

    @abstractmethod
    def get_for_authentication(
        self,
        tenant_id: str,
        key_prefix: str,
    ) -> ApiKeyCredential | None: ...

    @abstractmethod
    def list_for_principal(self, principal_id: str) -> list[ApiKeyCredential]: ...

    @abstractmethod
    def revoke_all_for_principal(self, principal_id: str, *, revoked_at: datetime) -> int: ...


__all__ = ["ApiKeyCredentialRepository", "ServicePrincipalRepository"]
