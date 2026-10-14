from __future__ import annotations

from src.core.platform.application.notifications.scope import NotificationRecipientScope
from src.core.platform.contract.port.notifications.notification_delivery import NotificationDelivery


class NotificationDeliveryHandler:
    """Explicit authenticated runtime action for draining committed durable work."""

    def __init__(self, *, scope: NotificationRecipientScope, delivery: NotificationDelivery) -> None:
        self._scope = scope
        self._delivery = delivery

    def drain_pending(self) -> int:
        principal = self._scope.require_principal()
        tenant_id, organization_id = self._scope.scope(principal.user_id)
        if not tenant_id:
            return 0
        delivered = self._delivery.drain(tenant_id=tenant_id, organization_id=None)
        if organization_id:
            delivered += self._delivery.drain(tenant_id=tenant_id, organization_id=organization_id)
        return delivered
