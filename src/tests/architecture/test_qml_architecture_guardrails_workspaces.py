from __future__ import annotations

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
PLATFORM_ADMIN_CONSOLE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "overview" / "admin_console_controller.py"
)
STALE_PLATFORM_ADMIN_DIRECTORY = UI_QML_ROOT / "platform" / "controllers" / "admin"
STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin_console" / "admin_workspace_controller.py"
)


def test_platform_admin_workspace_controller_uses_split_entrypoint() -> None:
    assert PLATFORM_ADMIN_CONSOLE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_DIRECTORY.exists()


def test_pm_workspace_wrapper_files_were_removed_as_dead_code() -> None:
    """Every PM workspace directory used to also carry a thin top-level
    `<Area>Workspace.qml` pass-through (`<Area>WorkspacePage {}`), left over
    from an earlier placeholder-page migration this file used to guard
    (`test_..._no_longer_uses_placeholder_page`). Verified dead: nothing
    imports any of these by qmldir namespace anywhere in the tree -- the
    real routing path is `ProjectManagementWorkspacePage.qml`'s Repeater,
    which loads each area's `*WorkspacePage.qml` directly by file path.
    Phase H removed all eight (Projects, Tasks, Scheduling, Financials,
    Register, Collaboration, Portfolio, Dashboard) rather than leave dead
    wrappers whose original guardrail purpose no longer applies."""
    for area in (
        "collaboration",
        "dashboard",
        "financials",
        "portfolio",
        "projects",
        "register",
        "scheduling",
        "tasks",
    ):
        area_title = area[0].upper() + area[1:]
        wrapper = (
            UI_QML_ROOT
            / "modules"
            / "project_management"
            / "qml"
            / "workspaces"
            / area
            / f"{area_title}Workspace.qml"
        )
        assert not wrapper.exists(), wrapper
