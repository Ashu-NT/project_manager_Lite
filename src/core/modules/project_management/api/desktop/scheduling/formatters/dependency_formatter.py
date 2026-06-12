"""Dependency type display formatting."""

from src.core.modules.project_management.domain.enums import DependencyType

_DEPENDENCY_TYPE_LABELS = {
    DependencyType.FINISH_TO_START: "Finish -> Start",
    DependencyType.START_TO_START: "Start -> Start",
    DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
    DependencyType.START_TO_FINISH: "Start -> Finish",
}


def dependency_type_label(value) -> str:
    from src.core.modules.project_management.api.desktop.scheduling.utils.dependency_utils import coerce_dependency_type
    dep_type = value if isinstance(value, DependencyType) else coerce_dependency_type(value)
    return _DEPENDENCY_TYPE_LABELS.get(dep_type, dep_type.value)


__all__ = ["dependency_type_label"]
