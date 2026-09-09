from __future__ import annotations

from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT


QML_ROOT = REPO_ROOT / "src" / "ui_qml" / "modules" / "project_management" / "qml"


DETAIL_TABLE_SECTIONS = (
    QML_ROOT / "workspaces/projects/sections/ProjectsTasksSection.qml",
    QML_ROOT / "workspaces/projects/sections/ProjectsResourcesSection.qml",
    QML_ROOT / "workspaces/projects/sections/ProjectsActivitySection.qml",
    QML_ROOT / "workspaces/tasks/sections/TasksAssignmentsSection.qml",
    QML_ROOT / "workspaces/tasks/sections/TasksDependenciesSection.qml",
    QML_ROOT / "workspaces/tasks/sections/TasksActivitySection.qml",
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_upgraded_detail_tables_use_main_workspace_footer_geometry() -> None:
    for path in DETAIL_TABLE_SECTIONS:
        source = _source(path)
        assert "AppWidgets.TablePaginationBar" in source, path
        assert "anchors.bottom: parent.bottom" in source, path
        assert ".top" in source and "anchors.bottom:" in source, path
        assert "property real availableHeight: 0" in source, path
        assert "Math.max(" in source and "root.availableHeight" in source, path
        assert "implicitHeight: 500" not in source, path
        assert "implicitHeight: 520" not in source, path


def test_project_and_task_detail_pages_pass_remaining_viewport_to_tables() -> None:
    projects_page = _source(QML_ROOT / "workspaces/projects/ProjectsWorkspacePage.qml")
    projects_panel = _source(
        QML_ROOT / "workspaces/projects/panels/ProjectsDetailPanel.qml"
    )
    tasks_page = _source(QML_ROOT / "workspaces/tasks/TasksWorkspacePage.qml")
    tasks_panel = _source(QML_ROOT / "workspaces/tasks/panels/TasksDetailPanel.qml")

    for source in (projects_page, tasks_page):
        assert "contentBottomPadding:" in source
        assert "_detailContentViewportHeight = contentViewportHeight" in source
        assert "availableHeight: Math.max(0, root._detailContentViewportHeight - y)" in source

    for section in ("Tasks", "Resources", "Activity"):
        assert f'section === "{section}"' in projects_page
    for section in ("Assignments", "Dependencies", "Activity"):
        assert f'section === "{section}"' in tasks_page

    assert projects_panel.count("availableHeight: root.availableHeight") == 3
    assert tasks_panel.count("availableHeight: root._tableSectionAvailableHeight") == 3
