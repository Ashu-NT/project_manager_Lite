from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_domain_events(ctrl) -> None:

    def _on_domain_event(_payload: object) -> None:
        ctrl._request_domain_refresh()

    for signal in (
        domain_events.inventory_receipts_changed,
        domain_events.inventory_cycle_counts_changed,
    ):
        ctrl._subscribe_domain_signal(signal, _on_domain_event)
