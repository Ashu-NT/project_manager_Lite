from __future__ import annotations

from .options import option


def site_options(snapshot) -> tuple:
    return (_option_all("All sites"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.site_options
    )


def asset_options(snapshot) -> tuple:
    return (_option_all("All assets"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.asset_options
    )


def system_options(snapshot) -> tuple:
    return (_option_all("All systems"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.system_options
    )


def location_options(snapshot) -> tuple:
    return (_option_all("All locations"),) + tuple(
        option(opt.value, opt.label) for opt in snapshot.location_options
    )


def window_options(snapshot) -> tuple:
    return tuple(option(str(opt.value), opt.label) for opt in snapshot.window_options)


def _option_all(label: str):
    return option("all", label)
