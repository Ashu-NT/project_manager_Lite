from __future__ import annotations


def bind_domain_events(ctrl) -> None:
    ctrl._subscribe_domain_change(scope_code="inventory_procurement")
    ctrl._subscribe_domain_change("site", scope_code="platform")
