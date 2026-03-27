from __future__ import annotations

from ui.platform.shared.styles.theme_tokens import DARK_THEME, LIGHT_THEME

from tests.ui_runtime_helpers import make_settings_store, register_and_login
from ui.platform.shell.main_window import MainWindow


def _child_labels(item) -> list[str]:
    return [item.child(i).text(0) for i in range(item.childCount())]


def test_main_window_runtime_uses_grouped_sidebar_navigation(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-shell")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    assert window.tabs.tabBar().isHidden() is True
    assert window.shell_navigation.tree.topLevelItemCount() == 6
    assert [window.shell_navigation.tree.topLevelItem(i).text(0) for i in range(6)] == [
        "Platform",
        "Project Management",
        "Inventory & Procurement",
        "Maintenance Management",
        "QHSE",
        "HR Management",
    ]

    platform_section = window.shell_navigation.tree.topLevelItem(0)
    assert _child_labels(platform_section) == ["Shared Services", "Administration", "Control"]
    shared_services_group = platform_section.child(0)
    administration_group = platform_section.child(1)
    control_group = platform_section.child(2)
    assert _child_labels(shared_services_group) == ["Home"]
    assert _child_labels(administration_group) == [
        "Users",
        "Employees",
        "Organizations",
        "Sites",
        "Departments",
        "Documents",
        "Parties",
        "Access",
        "Security",
        "Support",
        "Modules",
    ]
    assert _child_labels(control_group) == ["Audit"]

    project_management_section = window.shell_navigation.tree.topLevelItem(1)
    assert _child_labels(project_management_section) == [
        "Overview",
        "Execution",
        "Operations",
        "Control",
    ]
    overview_group = project_management_section.child(0)
    execution_group = project_management_section.child(1)
    operations_group = project_management_section.child(2)
    control_group = project_management_section.child(3)
    assert _child_labels(overview_group) == ["Dashboard", "Reports", "Portfolio"]
    assert _child_labels(execution_group) == ["Projects", "Tasks", "Calendar", "Collaboration"]
    assert _child_labels(operations_group) == ["Resources", "Costs"]
    assert _child_labels(control_group) == ["Register", "Governance"]

    portfolio_item = next(
        overview_group.child(i)
        for i in range(overview_group.childCount())
        if overview_group.child(i).text(0) == "Portfolio"
    )
    window.shell_navigation.tree.setCurrentItem(portfolio_item)

    assert window.tabs.tabText(window.tabs.currentIndex()) == "Portfolio"

    projects_index = next(
        index for index in range(window.tabs.count()) if window.tabs.tabText(index) == "Projects"
    )
    window.tabs.setCurrentIndex(projects_index)

    assert window.shell_navigation.tree.currentItem() is not None
    assert window.shell_navigation.tree.currentItem().text(0) == "Projects"


def test_main_window_runtime_supports_sidebar_toggle_and_auto_hide(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-shell-toggle")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    window.show()
    qapp.processEvents()

    assert window.shell_navigation.isVisible() is True
    assert window.btn_toggle_navigation.text() == "Hide Menu"

    window.btn_toggle_navigation.click()
    qapp.processEvents()
    assert window.shell_navigation.isVisible() is False
    assert window.btn_toggle_navigation.text() == "Show Menu"

    next_theme_index = 0 if window.theme_combo.currentData() == "light" else 1
    window.theme_combo.setCurrentIndex(next_theme_index)
    qapp.processEvents()
    assert window.shell_navigation.isVisible() is False
    assert window.btn_toggle_navigation.text() == "Show Menu"

    window.btn_toggle_navigation.click()
    qapp.processEvents()
    assert window.shell_navigation.isVisible() is True

    window.resize(980, window.height())
    qapp.processEvents()
    assert window.shell_navigation.isVisible() is False
    assert window.btn_toggle_navigation.text() == "Show Menu"

    window.resize(1280, window.height())
    qapp.processEvents()
    assert window.shell_navigation.isVisible() is True
    assert window.btn_toggle_navigation.text() == "Hide Menu"


def test_main_window_workspace_stack_uses_flat_hidden_tab_pane(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-workspace-stack-style")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    assert window.tabs.documentMode() is True
    assert "QTabWidget#workspaceStack::pane" in window.tabs.styleSheet()
    assert "background: transparent;" in window.tabs.styleSheet()
    assert "border-radius: 0px;" in window.tabs.styleSheet()
    assert "top: 0px;" in window.tabs.styleSheet()
    assert "QWidget#qt_tabwidget_stackedwidget" in window.tabs.styleSheet()


def test_main_window_theme_switch_refreshes_shell_without_rebuilding_tabs(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-shell-theme-refresh")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    window.show()
    qapp.processEvents()

    current_index = window.tabs.currentIndex()
    current_widget = window.tabs.currentWidget()
    initial_navigation_style = window.shell_navigation.styleSheet()
    initial_mode = str(window.theme_combo.currentData())
    next_theme_index = 0 if initial_mode == "light" else 1
    expected_shell_surface = (
        DARK_THEME["COLOR_BG_SURFACE"] if initial_mode == "light" else LIGHT_THEME["COLOR_BG_SURFACE"]
    )

    window.theme_combo.setCurrentIndex(next_theme_index)
    qapp.processEvents()

    assert window.tabs.currentIndex() == current_index
    assert window.tabs.currentWidget() is current_widget
    assert window.shell_navigation.styleSheet() != initial_navigation_style
    assert expected_shell_surface in window.shell_navigation.styleSheet()


def test_main_window_runtime_hides_empty_sections_for_viewer_navigation(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    register_and_login(services, username_prefix="viewer-shell", role_names=("viewer",))
    store = make_settings_store(repo_workspace, prefix="main-window-viewer-shell")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    section_labels = [
        window.shell_navigation.tree.topLevelItem(i).text(0)
        for i in range(window.shell_navigation.tree.topLevelItemCount())
    ]

    assert section_labels == [
        "Platform",
        "Project Management",
        "Inventory & Procurement",
        "Maintenance Management",
        "QHSE",
        "HR Management",
    ]

    platform_section = window.shell_navigation.tree.topLevelItem(0)
    assert _child_labels(platform_section) == ["Shared Services"]
    assert _child_labels(platform_section.child(0)) == ["Home"]


def test_main_window_focus_workspace_selects_existing_tab(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-focus-workspace")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)

    assert window.focus_workspace("Sites") is True
    assert window.tabs.tabText(window.tabs.currentIndex()) == "Sites"
    assert window.focus_workspace("Missing Workspace") is False


def test_main_window_rebuild_tabs_batches_tab_change_side_effects(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-rebuild-batch")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    target_index = min(2, window.tabs.count() - 1)
    window.tabs.setCurrentIndex(target_index)
    qapp.processEvents()

    saved_indexes: list[int] = []
    monkeypatch.setattr(window._settings_store, "save_tab_index", lambda index: saved_indexes.append(index))

    window._rebuild_tabs(current_index=target_index)

    assert window.tabs.currentIndex() == target_index
    assert saved_indexes == []
