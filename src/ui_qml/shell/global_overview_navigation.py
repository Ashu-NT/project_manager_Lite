from __future__ import annotations


def navigate_action(item, *, shell_context, platform_catalog, pm_catalog) -> None:
    """Use canonical module entry points, never retired global workspace routes."""
    route = item["routeId"]
    destination = item["destinationId"]
    if route == "platform.workspace":
        platform_catalog.selectDestination(destination)
    elif route == "project_management.workspace":
        if item["kind"] == "pm_task":
            pm_catalog.pmNavigation.openEntity(destination, str(item["id"]), "")
        else:
            # Enter the owning workflow without silently changing project pinning.
            pm_catalog.pmNavigation.selectWorkspace(destination)
    else:
        return
    shell_context.selectRoute(route)
