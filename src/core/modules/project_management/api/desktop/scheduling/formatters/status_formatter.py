"""Status and utilization display formatting."""


def resource_load_status_label(utilization_percent: float) -> str:
    if utilization_percent > 100.0:
        return "Overloaded"
    if utilization_percent >= 85.0:
        return "Hot"
    if utilization_percent > 0.0:
        return "Stable"
    return "Idle"


__all__ = ["resource_load_status_label"]
