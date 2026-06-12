from __future__ import annotations

from typing import Callable

from src.ui_qml.modules.project_management.controllers.common import run_mutation
from src.ui_qml.modules.project_management.presenters import (
    ProjectPortfolioWorkspacePresenter,
)

class PortfolioMutationHandler:
    def __init__(
        self,
        presenter: ProjectPortfolioWorkspacePresenter,
        set_is_busy: Callable,
        set_error_message: Callable,
        set_feedback_message: Callable,
        request_domain_refresh: Callable,
    ) -> None:
        self._presenter = presenter
        self._set_is_busy = set_is_busy
        self._set_error_message = set_error_message
        self._set_feedback_message = set_feedback_message
        self._request_domain_refresh = request_domain_refresh

    def _run(self, operation: Callable, success_message: str) -> dict[str, object]:
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def create_template(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.create_template(dict(payload)),
            "Scoring template created.",
        )

    def activate_template(self, template_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.activate_template(template_id),
            "Scoring template activated.",
        )

    def create_intake_item(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.create_intake_item(dict(payload)),
            "Intake item created.",
        )

    def create_scenario(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.create_scenario(dict(payload)),
            "Scenario saved.",
        )

    def create_dependency(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.create_dependency(dict(payload)),
            "Dependency created.",
        )

    def remove_dependency(self, dependency_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.remove_dependency(dependency_id),
            "Dependency removed.",
        )

    def update_intake_item_status(self, item_id: str, status: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.update_intake_item_status(item_id, status),
            "Intake item status updated.",
        )

__all__ = ["PortfolioMutationHandler"]
