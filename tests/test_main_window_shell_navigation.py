from __future__ import annotations

from tests.ui_runtime_helpers import make_settings_store, register_and_login
from ui.main_window import MainWindow


def test_main_window_runtime_uses_grouped_sidebar_navigation(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-shell")
    monkeypatch.setattr("ui.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    assert window.tabs.tabBar().isHidden() is True
    assert window.shell_navigation.tree.topLevelItemCount() == 5
    assert [window.shell_navigation.tree.topLevelItem(i).text(0) for i in range(5)] == [
        "Home",
        "Delivery",
        "Team",
        "Control",
        "Admin",
    ]

    delivery_section = window.shell_navigation.tree.topLevelItem(1)
    assert [delivery_section.child(i).text(0) for i in range(delivery_section.childCount())] == [
        "Calendar",
        "Resources",
        "Projects",
        "Tasks",
        "Costs",
    ]

    control_section = window.shell_navigation.tree.topLevelItem(3)
    portfolio_item = next(
        control_section.child(i)
        for i in range(control_section.childCount())
        if control_section.child(i).text(0) == "Portfolio"
    )
    window.shell_navigation.tree.setCurrentItem(portfolio_item)

    assert window.tabs.tabText(window.tabs.currentIndex()) == "Portfolio"

    projects_index = next(
        index for index in range(window.tabs.count()) if window.tabs.tabText(index) == "Projects"
    )
    window.tabs.setCurrentIndex(projects_index)

    assert window.shell_navigation.tree.currentItem() is not None
    assert window.shell_navigation.tree.currentItem().text(0) == "Projects"


def test_main_window_runtime_hides_empty_sections_for_viewer_navigation(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    register_and_login(services, username_prefix="viewer-shell", role_names=("viewer",))
    store = make_settings_store(repo_workspace, prefix="main-window-viewer-shell")
    monkeypatch.setattr("ui.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    section_labels = [
        window.shell_navigation.tree.topLevelItem(i).text(0)
        for i in range(window.shell_navigation.tree.topLevelItemCount())
    ]

    assert "Delivery" in section_labels
    assert "Team" in section_labels
    assert "Admin" not in section_labels
