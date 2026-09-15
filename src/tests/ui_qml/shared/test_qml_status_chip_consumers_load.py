from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

UI_QML_ROOT = REPO_ROOT / "src" / "ui_qml"

# Direct page/panel/section-level StatusChip consumers (each carries its own
# small, explicit tone mapping -- see the individual QML files).
_GROUP_A_CONSUMERS = [
    "platform/qml/support/sections/AdminSupportRuntimePanel.qml",
    "platform/qml/support/sections/AdminSupportActivityPanel.qml",
    "platform/qml/organization/sites/AdminSiteDetailPage.qml",
    "modules/project_management/qml/workspaces/tasks/sections/TasksSkillsSection.qml",
    "modules/project_management/qml/workspaces/tasks/sections/TasksScheduleImpactSection.qml",
    "modules/project_management/qml/workspaces/tasks/sections/TaskCommentCard.qml",
    "modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml",
    "platform/qml/organization/organizations/AdminOrganizationDetailPage.qml",
    "platform/qml/identity_access/access/AccessSecurityPanel.qml",
    "platform/qml/documents/DocumentDetailPanel.qml",
    "platform/qml/Platform/Components/AdminEntityDetailPage.qml",
    "modules/project_management/qml/workspaces/projects/sections/ProjectsOverviewSection.qml",
    "modules/project_management/qml/workspaces/collaboration/panels/CollaborationDetailPanel.qml",
    "modules/project_management/qml/workspaces/portfolio/panels/PortfolioDetailPanel.qml",

    "modules/project_management/qml/workspaces/portfolio/tabs/ExecutiveTab.qml",
    "modules/project_management/qml/workspaces/resources/sections/ResourcesOverviewSection.qml",
    "modules/project_management/qml/workspaces/resources/sections/ResourcesAvailabilitySection.qml",
    "modules/project_management/qml/workspaces/dashboard/components/DashboardHealthCard.qml",
    "modules/project_management/qml/workspaces/dashboard/components/DashboardAttentionPanel.qml",
    "modules/project_management/qml/workspaces/register/sections/RegisterDetailSection.qml",
]

# Shared, domain-neutral StatusChip consumers -- these accept an optional
# caller-supplied tone and must never regress to inferring one from text.
_SHARED_CONSUMERS = [
    "shared/qml/App/Widgets/ActivityFeed.qml",
    "shared/qml/App/Widgets/ActionCenterRow.qml",
    "shared/qml/App/Widgets/InspectorPanel.qml",
    "modules/project_management/qml/ProjectManagement/Widgets/RecordListCard.qml",
]


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["status-chip-consumers-test"])


@pytest.mark.parametrize("relative_path", _GROUP_A_CONSUMERS + _SHARED_CONSUMERS)
def test_status_chip_consumer_loads_offscreen(relative_path: str) -> None:
    _ensure_qgui_application()
    engine = create_qml_engine()
    qml_path = UI_QML_ROOT / relative_path
    assert qml_path.exists(), qml_path
    load_qml(engine, qml_path)
    assert len(engine.rootObjects()) == 1
