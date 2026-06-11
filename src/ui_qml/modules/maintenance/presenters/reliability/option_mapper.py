from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceFailureSymptomOptionViewModel,
)

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


def failure_symptom_options(snapshot) -> tuple:
    return (
        MaintenanceFailureSymptomOptionViewModel(
            value="all",
            label="All failure symptoms",
            failure_code="",
            name="",
            is_active=True,
        ),
    ) + tuple(
        MaintenanceFailureSymptomOptionViewModel(
            value=opt.value,
            label=opt.label,
            failure_code=opt.failure_code,
            name=opt.name,
            is_active=opt.is_active,
        )
        for opt in snapshot.failure_symptom_options
    )


def days_options(snapshot) -> tuple:
    return tuple(option(str(opt.value), opt.label) for opt in snapshot.days_options)


def limit_options(snapshot) -> tuple:
    return tuple(option(str(opt.value), opt.label) for opt in snapshot.limit_options)


def threshold_options(snapshot) -> tuple:
    return tuple(option(str(opt.value), opt.label) for opt in snapshot.threshold_options)


def _option_all(label: str):
    return option("all", label)
