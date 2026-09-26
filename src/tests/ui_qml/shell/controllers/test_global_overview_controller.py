from __future__ import annotations

from src.ui_qml.shell.controllers.global_overview.global_overview_controller import (
    GlobalOverviewController,
)
from src.ui_qml.shell.presenters.global_overview_presenter import SectionResult
from src.ui_qml.shell.view_models.global_overview import (
    AttentionCardViewModel,
    GlobalOverviewContextViewModel,
    ModuleCardViewModel,
)


class _FakePresenter:
    def __init__(self) -> None:
        self.context_result = SectionResult(
            ok=True,
            data=GlobalOverviewContextViewModel(
                tenant_name="TECHASH Enterprise",
                organization_name="Shell",
                role_label=None,
                context_line="TECHASH Enterprise · Shell",
            ),
        )
        self.attention_result = SectionResult(
            ok=True,
            data=(
                AttentionCardViewModel(
                    key="all",
                    label="All action items",
                    value=3,
                    supporting_text="3 items",
                    route_id="",
                    filter_key="all",
                ),
            ),
        )
        self.modules_result = SectionResult(
            ok=True,
            data=(
                ModuleCardViewModel(
                    module_code="platform",
                    title="Platform",
                    description="desc",
                    icon_key="platform",
                    summary_text="2 items",
                    route_id="platform",
                ),
            ),
        )
        self.recent_activity_result = SectionResult(ok=True, data=(), empty=True)
        self.action_center_result = SectionResult(ok=True, data=(), empty=True)
        self.quick_actions_result = SectionResult(ok=True, data=(), empty=True)
        self.calls: list[str] = []

    def load_context(self):
        self.calls.append("context")
        return self.context_result

    def load_attention(self):
        self.calls.append("attention")
        return self.attention_result

    def load_modules(self):
        self.calls.append("modules")
        return self.modules_result

    def load_recent_activity(self, *, limit: int = 50):
        self.calls.append("recent_activity")
        return self.recent_activity_result

    def load_action_center(self, *, limit: int = 50):
        self.calls.append("action_center")
        return self.action_center_result

    def load_quick_actions(self):
        self.calls.append("quick_actions")
        return self.quick_actions_result


class _FakeShellContext:
    """Duck-typed stand-in: exposes only what GlobalOverviewController may
    depend on (scopeChanged to subscribe, selectRoute to delegate to)."""

    def __init__(self) -> None:
        self._scope_changed_handlers: list = []
        self.selected_route_ids: list[str] = []

        class _Signal:
            def __init__(self, outer) -> None:
                self._outer = outer

            def connect(self, handler) -> None:
                self._outer._scope_changed_handlers.append(handler)

            def emit(self) -> None:
                for handler in list(self._outer._scope_changed_handlers):
                    handler()

        self.scopeChanged = _Signal(self)

    def selectRoute(self, route_id: str) -> None:
        self.selected_route_ids.append(route_id)


def _controller(presenter=None, shell_context=None) -> GlobalOverviewController:
    return GlobalOverviewController(
        presenter=presenter or _FakePresenter(),
        shell_context=shell_context,
    )


# -- initial section load -------------------------------------------------------------------


def test_reload_loads_every_section_independently():
    presenter = _FakePresenter()
    controller = _controller(presenter)

    controller.reload()

    assert presenter.calls == [
        "context",
        "attention",
        "modules",
        "recent_activity",
        "action_center",
        "quick_actions",
    ]
    assert controller.context["tenantName"] == "TECHASH Enterprise"
    assert controller.attention[0]["value"] == 3
    assert controller.modules[0]["moduleCode"] == "platform"
    assert controller.contextState == {"loading": False, "errorMessage": "", "empty": False}


def test_attention_all_zero_counts_state_is_not_empty_and_cards_carry_interactive_flag():
    presenter = _FakePresenter()
    presenter.attention_result = SectionResult(
        ok=True,
        data=tuple(
            AttentionCardViewModel(
                key=key,
                label=key,
                value=0,
                supporting_text="0 items",
                route_id="",
                filter_key=key,
                interactive=False,
            )
            for key in ("all", "reviews_and_approvals", "assigned_work", "submissions")
        ),
        empty=False,
    )
    controller = _controller(presenter)

    controller.reload()

    assert controller.attentionState == {"loading": False, "errorMessage": "", "empty": False}
    assert len(controller.attention) == 4
    assert all(card["value"] == 0 for card in controller.attention)
    assert all(card["interactive"] is False for card in controller.attention)


def test_recent_activity_empty_state_is_reflected_without_being_an_error():
    controller = _controller()
    controller.reload()

    assert controller.recentActivity == []
    assert controller.recentActivityState["empty"] is True
    assert controller.recentActivityState["errorMessage"] == ""


# -- independent failure isolation ---------------------------------------------------------


def test_recent_activity_failure_does_not_erase_action_center():
    presenter = _FakePresenter()
    presenter.recent_activity_result = SectionResult(
        ok=False, data=None, error_message="Recent activity could not be loaded."
    )
    presenter.action_center_result = SectionResult(
        ok=True,
        data=(),
        empty=True,
    )
    controller = _controller(presenter)

    controller.reload()

    assert controller.recentActivityState["errorMessage"] == "Recent activity could not be loaded."
    assert controller.actionCenterState["errorMessage"] == ""
    assert controller.actionCenter == []


def test_action_center_failure_does_not_erase_modules():
    presenter = _FakePresenter()
    presenter.action_center_result = SectionResult(
        ok=False, data=None, error_message="Action items could not be loaded."
    )
    controller = _controller(presenter)

    controller.reload()

    assert controller.actionCenterState["errorMessage"] == "Action items could not be loaded."
    assert controller.modulesState["errorMessage"] == ""
    assert controller.modules[0]["moduleCode"] == "platform"


def test_a_raising_section_does_not_prevent_other_sections_from_loading():
    presenter = _FakePresenter()

    def _raise():
        raise RuntimeError("boom")

    presenter.load_recent_activity = _raise
    controller = _controller(presenter)

    controller.reload()

    assert controller.recentActivityState["errorMessage"] == "This section could not be loaded."
    assert controller.contextState["errorMessage"] == ""
    assert controller.context["tenantName"] == "TECHASH Enterprise"
    assert controller.modulesState["errorMessage"] == ""
    assert controller.actionCenterState["errorMessage"] == ""


# -- scopeChanged behavior -------------------------------------------------------------------


def test_scope_changed_triggers_a_full_reload():
    presenter = _FakePresenter()
    shell_context = _FakeShellContext()
    controller = _controller(presenter, shell_context)
    presenter.calls.clear()

    shell_context.scopeChanged.emit()

    assert presenter.calls == [
        "context",
        "attention",
        "modules",
        "recent_activity",
        "action_center",
        "quick_actions",
    ]
    assert controller.context["tenantName"] == "TECHASH Enterprise"


def test_scope_changed_clears_stale_prior_scope_values_before_reload_completes():
    presenter = _FakePresenter()
    shell_context = _FakeShellContext()
    controller = _controller(presenter, shell_context)
    controller.reload()
    assert controller.modules[0]["moduleCode"] == "platform"

    # Simulate the new scope having nothing yet: if scopeChanged did not
    # clear the OLD "platform" module card first, a slow/failed reload
    # would still show it as if it belonged to the new organization.
    presenter.modules_result = SectionResult(ok=True, data=(), empty=True)
    observed_during_reload: list[list] = []
    original_load_modules = presenter.load_modules

    def _load_modules_and_observe():
        # At the moment modules reload actually runs, the controller must
        # already have cleared the previous scope's stale card.
        observed_during_reload.append(list(controller.modules))
        return original_load_modules()

    presenter.load_modules = _load_modules_and_observe

    shell_context.scopeChanged.emit()

    assert observed_during_reload == [[]]
    assert controller.modules == []


# -- navigation -------------------------------------------------------------------------


def test_select_route_delegates_to_shell_context():
    shell_context = _FakeShellContext()
    controller = _controller(shell_context=shell_context)

    controller.selectRoute("project_management.tasks")

    assert shell_context.selected_route_ids == ["project_management.tasks"]


def test_select_route_without_shell_context_does_not_raise():
    controller = _controller(shell_context=None)

    controller.selectRoute("project_management.tasks")  # must not raise


def test_select_route_ignores_empty_route_id():
    shell_context = _FakeShellContext()
    controller = _controller(shell_context=shell_context)

    controller.selectRoute("")

    assert shell_context.selected_route_ids == []


# -- structural: no controller -> repository/service shortcuts -----------------------------


def test_controller_imports_presentation_and_desktop_boundary_only():
    import ast
    import inspect

    from src.ui_qml.shell.controllers.global_overview import global_overview_controller

    tree = ast.parse(inspect.getsource(global_overview_controller))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_substrings = ("repositories", "infrastructure.persistence", ".domain.")
    for module_path in imported_modules:
        for forbidden in forbidden_substrings:
            assert forbidden not in module_path, module_path


def test_shell_context_does_not_import_global_overview_controller():
    import ast
    import inspect

    from src.ui_qml.shell import context as shell_context_module

    tree = ast.parse(inspect.getsource(shell_context_module))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("global_overview" in module_path for module_path in imported_modules)
