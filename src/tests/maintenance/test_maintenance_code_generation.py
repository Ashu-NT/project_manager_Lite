"""Maintenance asset-library code-generation wiring."""

from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.maintenance.presenters.assets_workspace_presenter import (
    MaintenanceAssetsWorkspacePresenter,
)


class _FakeAssetsApi:
    def __init__(self, *, locations=(), systems=(), assets=(), components=()):
        self._locations = list(locations)
        self._systems = list(systems)
        self._assets = list(assets)
        self._components = list(components)

    def list_locations(self, *, active_only=None, site_id=None):
        return [SimpleNamespace(location_code=c) for c in self._locations]

    def list_systems(self, *, active_only=None, site_id=None, location_id=None):
        return [SimpleNamespace(system_code=c) for c in self._systems]

    def list_assets(self, *, active_only=None, site_id=None, location_id=None, system_id=None):
        return [SimpleNamespace(asset_code=c) for c in self._assets]

    def list_components(self, *, active_only=None, asset_id=None):
        return [SimpleNamespace(component_code=c) for c in self._components]


def _presenter(**kwargs):
    return MaintenanceAssetsWorkspacePresenter(desktop_api=_FakeAssetsApi(**kwargs))


def test_asset_suggest_uses_name():
    assert _presenter().suggest_asset_code({"name": "Conveyor 100"}) == "AST-CONV-0001"


def test_asset_suggest_increments():
    presenter = _presenter(assets=["AST-CONV-0001", "AST-CONV-0002"])
    assert presenter.suggest_asset_code({"name": "Conveyor"}) == "AST-CONV-0003"


def test_component_suggest_prefix():
    assert _presenter().suggest_component_code({"name": "Motor"}) == "CMP-MOTO-0001"


def test_location_suggest_prefix():
    assert _presenter().suggest_location_code({"name": "Plant North"}) == "LOC-PLAN-0001"


def test_system_suggest_prefix():
    assert _presenter().suggest_system_code({"name": "Cooling"}) == "SYS-COOL-0001"


def test_asset_suggest_year_fallback_without_name():
    code = _presenter().suggest_asset_code({})
    assert code.startswith("AST-") and code.endswith("-0001")
