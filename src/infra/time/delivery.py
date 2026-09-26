from datetime import datetime, timezone


class SystemDeliveryClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


__all__ = ["SystemDeliveryClock"]
