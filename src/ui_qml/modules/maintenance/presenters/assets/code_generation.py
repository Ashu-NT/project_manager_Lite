from __future__ import annotations

from typing import Any


def _suggest_code(entity_type: str, code_attr: str, rows: Any, payload: dict[str, Any]) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {str(getattr(row, code_attr, "") or "").upper() for row in rows}
    name = str(payload.get("name") or "").strip()
    return CodeGenerator().generate(
        entity_type,
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )


def suggest_location_code(desktop_api, payload: dict[str, Any]) -> str:
    return _suggest_code(
        "location",
        "location_code",
        desktop_api.list_locations(active_only=None),
        dict(payload),
    )


def suggest_system_code(desktop_api, payload: dict[str, Any]) -> str:
    return _suggest_code(
        "system",
        "system_code",
        desktop_api.list_systems(active_only=None),
        dict(payload),
    )


def suggest_asset_code(desktop_api, payload: dict[str, Any]) -> str:
    return _suggest_code(
        "asset",
        "asset_code",
        desktop_api.list_assets(active_only=None),
        dict(payload),
    )


def suggest_component_code(desktop_api, payload: dict[str, Any]) -> str:
    return _suggest_code(
        "component",
        "component_code",
        desktop_api.list_components(active_only=None),
        dict(payload),
    )
