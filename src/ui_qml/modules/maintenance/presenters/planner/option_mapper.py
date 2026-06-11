from __future__ import annotations

from .options import option


def site_options(snapshot) -> tuple:
    return (_all("All sites"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.site_options
    )


def asset_options(snapshot) -> tuple:
    return (_all("All assets"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.asset_options
    )


def system_options(snapshot) -> tuple:
    return (_all("All systems"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.system_options
    )


def request_queue_options(snapshot) -> tuple:
    return tuple(option(opt.value, opt.label) for opt in snapshot.request_queue_options)


def work_order_queue_options(snapshot) -> tuple:
    return tuple(option(opt.value, opt.label) for opt in snapshot.work_order_queue_options)


def _all(label: str):
    return option("all", label)
