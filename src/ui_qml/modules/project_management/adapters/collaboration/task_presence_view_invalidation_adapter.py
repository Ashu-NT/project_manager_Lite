from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    TASK_PRESENCE_CATEGORY,
    TASK_PRESENCE_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class TaskPresenceViewInvalidationAdapter(QObject):
    taskPresenceStale = Signal(str)  # task_id

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        organization_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        self._subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category != TASK_PRESENCE_CATEGORY:
            return
        if hint.scope_code == TASK_PRESENCE_SCOPE_CODE:
            self.taskPresenceStale.emit(hint.entity_id or "")

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["TaskPresenceViewInvalidationAdapter"]
