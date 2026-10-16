from __future__ import annotations

from typing import Protocol


class NotificationDeliveryRuntime(Protocol):
    def drain_pending(self) -> int: ...
