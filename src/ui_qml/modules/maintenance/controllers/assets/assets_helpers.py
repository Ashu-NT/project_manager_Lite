from __future__ import annotations


def normalize_filter(value: str, default: str = "all") -> str:
    return (value or "").strip() or default


def normalize_id(value: str) -> str:
    return (value or "").strip()


def generate_entity_code(controller, entity_type: str, payload: dict) -> str:
    key = (entity_type or "").strip().lower()
    presenter = controller._assets_workspace_presenter
    generators = {
        "location": presenter.suggest_location_code,
        "system": presenter.suggest_system_code,
        "asset": presenter.suggest_asset_code,
        "component": presenter.suggest_component_code,
    }
    handler = generators.get(key)
    if handler is None:
        return ""
    try:
        return handler(dict(payload))
    except Exception as exc:  # noqa: BLE001
        controller._set_error_message(str(exc))
        return ""
