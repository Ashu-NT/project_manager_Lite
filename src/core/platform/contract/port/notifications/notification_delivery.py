from typing import Protocol


class NotificationDelivery(Protocol):
    def drain(self, *, tenant_id: str, organization_id: str | None, limit: int = 50) -> int: ...
