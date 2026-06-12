"""Dependency resolution helpers."""


def get_task_method(task_service, method_name: str):
    if task_service is None:
        return None
    method = getattr(task_service, method_name, None)
    return method if callable(method) else None


def require_task_method(task_service, method_name: str):
    if task_service is None:
        raise RuntimeError("Project management scheduling desktop API is not connected.")
    method = getattr(task_service, method_name, None)
    if not callable(method):
        raise RuntimeError(f"Project management scheduling desktop API does not support {method_name}.")
    return method


def build_tasks_by_id(task_service, project_id: str) -> dict:
    list_fn = get_task_method(task_service, "list_tasks_for_project")
    if list_fn is None or not project_id:
        return {}
    return {t.id: t for t in list_fn(project_id)}


__all__ = ["build_tasks_by_id", "get_task_method", "require_task_method"]
