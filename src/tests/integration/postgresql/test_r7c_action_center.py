from types import SimpleNamespace

import pytest
from sqlalchemy import event, text

from src.core.global_overview.application.action_center_service import (
    ActionCenterService,
)
from src.core.global_overview.contract.action_center import ActionCenterContext
from src.core.modules.project_management.infrastructure.persistence.reads.global_overview.action_center_reader import (
    SqlAlchemyProjectManagementActionCenterReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.platform.infrastructure.persistence.read.global_overview.action_center_reader import (
    SqlAlchemyPlatformActionCenterReader,
)
from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
    SqlAlchemyApprovalRepository,
)
from src.infra.composition.global_overview_registry import approval_action_target_scope
from src.tests.integration.postgresql.test_r7b_governance_security import (
    governance_rows as governance_rows,
)
from src.tests.integration.postgresql.test_r7b_governance_security import runtime

pytestmark = pytest.mark.postgresql_integration


def service(session):
    identity = SqlAlchemyResourceIdentityReader(session=session)
    timesheets = SqlAlchemyTimesheetWorkspaceReader(session=session, resource_identity_reader=identity)
    return ActionCenterService(contributors=(
        SqlAlchemyPlatformActionCenterReader(session=session, target_scope_predicate=approval_action_target_scope()),
        SqlAlchemyProjectManagementActionCenterReader(session=session, resource_identity_reader=identity, timesheet_workspace_reader=timesheets),
    ))


@pytest.mark.parametrize("volume", [10, 100, 1000])
def test_runtime_bounded_counts_order_and_seek(postgres_test_environment, governance_rows, volume):
    with postgres_test_environment.admin_engine.begin() as connection:
        for code in ("baseline.approve", "project.read"):
            connection.execute(text("INSERT INTO permissions(id,code,description) VALUES(:code,:code,'') ON CONFLICT DO NOTHING"), {"code": code})
            connection.execute(text("INSERT INTO role_permissions(id,role_id,permission_id) SELECT :id, 'r7b-reviewer-role-0',id FROM permissions WHERE code=:code ON CONFLICT DO NOTHING"), {"code": code, "id": "r7c-" + code})
        connection.execute(text("INSERT INTO project_baselines(id,project_id,name,created_at,status,version,submitted_at) SELECT 'r7c-'||lpad(i::text,6,'0'), 'r7a-project-a', 'Review', CURRENT_TIMESTAMP,'submitted',1,DATE '2026-09-01' FROM generate_series(1,:n) i"), {"n": volume})
    try:
        with runtime(postgres_test_environment) as session:
            query = service(session)
            context = ActionCenterContext("r7b-reviewer", "r7a-tenant-a", "r7a-org-a")
            statements = []
            connection = session.connection()
            def capture(conn, cursor, statement, parameters, execution_context, executemany):
                statements.append(statement)
            event.listen(connection, "before_cursor_execute", capture)
            try:
                first = query.build(context, preview_limit=10)
                first_count = len(statements)
                second = query.build(context, preview_limit=10, after=first.next_cursor)
            finally:
                event.remove(connection, "before_cursor_execute", capture)
            assert first.summary.all_action_items == volume + 1
            assert len(first.items) == 10 and first.next_cursor is not None
            assert {item.id for item in first.items}.isdisjoint(item.id for item in second.items)
            assert first_count == 6
            assert len(statements) == 12
            assert len(second.items) <= 10
            if volume == 10:
                assert len(second.items) == 1 and second.next_cursor is None
    finally:
        with postgres_test_environment.admin_engine.begin() as connection:
            connection.execute(text("DELETE FROM project_baselines WHERE id LIKE 'r7c-%'"))


@pytest.mark.parametrize("user", ["foreign", "wrongorg", "wrongproject", "disabled", "suspended", "revoked", "expired", "unauthorized"])
def test_reader_eligibility_rejects_hostile_or_inactive_identity(postgres_test_environment, governance_rows, user):
    with runtime(postgres_test_environment, user=user) as session:
        page = service(session).build(ActionCenterContext(f"r7b-{user}", "r7a-tenant-a", "r7a-org-a"))
        assert page.summary.all_action_items == 0
        assert page.items == ()
        repo = SqlAlchemyApprovalRepository(session)
        repo._tenant_context_service = SimpleNamespace(require_active_scope_ids=lambda **kw: SimpleNamespace(
            tenant_id="r7a-tenant-a", organization_id="r7a-org-a"))
        assert repo.is_reviewer_eligible("r7b-request", f"r7b-{user}") is False


@pytest.mark.parametrize("tenant,org", [("b", "b"), ("a", "o")])
def test_rls_hides_approval_independently_of_reader_filters(postgres_test_environment, governance_rows, tenant, org):
    with runtime(postgres_test_environment, tenant=tenant, org=org) as session:
        assert session.scalar(text("SELECT count(*) FROM approval_requests WHERE id='r7b-request'")) == 0


def test_approval_completed_or_self_requested_is_not_actionable(postgres_test_environment, governance_rows):
    with postgres_test_environment.admin_engine.begin() as connection:
        original = connection.execute(text("SELECT requested_by_user_id FROM approval_requests WHERE id='r7b-request'")).scalar_one()
        connection.execute(text("UPDATE approval_requests SET requested_by_user_id='r7b-reviewer' WHERE id='r7b-request'"))
    try:
        with runtime(postgres_test_environment) as session:
            result = service(session).build(ActionCenterContext("r7b-reviewer", "r7a-tenant-a", "r7a-org-a"))
            assert result.summary.reviews_and_approvals == 0
    finally:
        with postgres_test_environment.admin_engine.begin() as connection:
            connection.execute(text("UPDATE approval_requests SET requested_by_user_id=:original WHERE id='r7b-request'"), {"original": original})
