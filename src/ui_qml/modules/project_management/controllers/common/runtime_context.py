from __future__ import annotations


def resolve_active_organization_id_from_runtime_api(
    runtime_api: object | None,
) -> str | None:
    if runtime_api is None:
        return None
    runtime_context = _load_runtime_context(runtime_api)
    data = getattr(runtime_context, "data", runtime_context)
    organization = getattr(data, "active_organization", None)
    normalized = str(getattr(organization, "id", "") or "").strip()
    return normalized or None


def _load_runtime_context(runtime_api: object):
    get_runtime_context = getattr(runtime_api, "get_runtime_context", None)
    if callable(get_runtime_context):
        return get_runtime_context()
    snapshot = getattr(runtime_api, "snapshot", None)
    if callable(snapshot):
        return snapshot()
    return None


__all__ = ["resolve_active_organization_id_from_runtime_api"]
