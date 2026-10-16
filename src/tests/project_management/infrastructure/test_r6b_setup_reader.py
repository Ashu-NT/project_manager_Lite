from __future__ import annotations

import inspect
from contextlib import contextmanager

from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.cost_codes import (
    FinancialCreateCostCodeCommand,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.financial_profile import (
    FinancialUpdateProfileCommand,
)
from src.core.modules.project_management.application.financials.configuration.queries import (
    ConfigurationWorkspaceQueries,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)


@contextmanager
def _statement_count(session):
    statements: list[str] = []

    def before_cursor_execute(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", before_cursor_execute)


def test_setup_reader_returns_one_scoped_immutable_projection(services) -> None:
    project = services["project_create"].create_project(
        ProjectCreateCommand(name="R6B Finance Setup", financial_currency_code="XAF")
    )
    configuration = services["financial_configuration_query"]
    boundary = services["finance_governance_commands"]
    cost_code = boundary.cost_code(
        lambda handler: handler.create_cost_code(
            FinancialCreateCostCodeCommand(
                code="R6B-SETUP",
                name="Setup default",
                project_id=project.id,
            )
        )
    )
    profile = configuration.get_profile(project.id)
    boundary.financial_profile(
        lambda handler: handler.configure_profile(
            FinancialUpdateProfileCommand(
                project_id=project.id,
                expected_version=profile.version,
                default_cost_code_id=cost_code.id,
            )
        )
    )
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test Finance Setup Reader"
    )
    reader = services["finance_workspace_query"]._setup_reader

    with _statement_count(services["session"]) as statements:
        facts = reader.get_setup(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
        )

    assert len(statements) == 1
    assert facts is not None
    assert facts.project_id == project.id
    assert facts.currency_code == "XAF"
    assert facts.default_cost_code == "R6B-SETUP - Setup default"
    assert not hasattr(facts, "__dict__")


def test_setup_reader_denies_explicit_wrong_scope_and_desktop_returns_facts(
    services,
) -> None:
    project = services["project_create"].create_project(
        ProjectCreateCommand(
            name="R6B Finance Setup Scope", financial_currency_code="USD"
        )
    )
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test Finance Setup scope"
    )
    reader = services["finance_workspace_query"]._setup_reader

    assert (
        reader.get_setup(
            tenant_id="foreign-tenant",
            organization_id=scope.organization_id,
            project_id=project.id,
        )
        is None
    )
    assert (
        reader.get_setup(
            tenant_id=scope.tenant_id,
            organization_id="foreign-organization",
            project_id=project.id,
        )
        is None
    )

    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )
    workspace = desktop.get_financial_setup_workspace(project.id)
    assert workspace is not None
    assert workspace.profile.project_id == project.id
    assert workspace.profile.currency_code == "USD"
    assert workspace.profile.default_cost_code == ""


def test_setup_workspace_query_has_no_aggregate_repository_read_path() -> None:
    source = inspect.getsource(ConfigurationWorkspaceQueries)

    assert "profile_repo" not in source
    assert "cost_code_repo" not in source
    assert "_profile_repo" not in source
    assert "_cost_code_repo" not in source
    assert "self._setup_reader.get_setup(" in source
