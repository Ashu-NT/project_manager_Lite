"""R7A evidence, not security acceptance tests.

The exclusion and deleted-comment assertions document defects to replace with
deny-safe assertions during R7B/R7E. They must not preserve unsafe behavior.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentCriteria,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration.sqlalchemy_workspace_reader import (
    SqlAlchemyCollaborationWorkspaceReader,
)

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture(scope="module")
def governance_rows(postgres_test_environment):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with postgres_test_environment.admin_engine.begin() as connection:
        for suffix in ("a", "b"):
            scope = {
                "tenant": f"r7a-tenant-{suffix}",
                "org": f"r7a-org-{suffix}",
                "project": f"r7a-project-{suffix}",
                "task": f"r7a-task-{suffix}",
            }
            connection.execute(
                text(
                    "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:tenant, :tenant, :tenant, 'active', true, 1)"
                ),
                scope,
            )
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, status, version) "
                    "VALUES (:org, :tenant, :org, :org, 'UTC', 'XAF', 'active', 1)"
                ),
                scope,
            )
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id, tenant_id, organization_id, project_code, name, description, status, version) "
                    "VALUES (:project, :tenant, :org, :project, :project, '', 'ACTIVE', 1)"
                ),
                scope,
            )
            connection.execute(
                text(
                    "INSERT INTO tasks "
                    "(id, project_id, task_code, wbs_code, sort_order, name, description, status, "
                    "priority, percent_complete, is_milestone, version) "
                    "VALUES (:task, :project, :task, '1', 1, :task, '', 'TODO', 0, 0, false, 1)"
                ),
                scope,
            )
            connection.execute(
                text(
                    "INSERT INTO task_comments "
                    "(id, task_id, body, created_at, deleted_at) "
                    "VALUES (:id, :task, :body, :now, :deleted)"
                ),
                {
                    "id": f"r7a-comment-{suffix}",
                    "task": scope["task"],
                    "body": f"R7A retained content {suffix}",
                    "now": now,
                    "deleted": now if suffix == "a" else None,
                },
            )


def test_runtime_role_has_no_rls_bypass(postgres_test_environment):
    with postgres_test_environment.runtime_session(
        tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
    ) as session:
        role = session.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        assert role == ("app_runtime", False, False)
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner=current_user"
                )
            )
            == 0
        )


@pytest.mark.parametrize(
    "table", ["approval_requests", "activity_entries", "timesheet_periods"]
)
def test_governed_tables_force_rls(postgres_test_environment, table):
    with postgres_test_environment.runtime_session(
        tenant_id=None, organization_id=None
    ) as session:
        assert session.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid=to_regclass(:name)"
            ),
            {"name": table},
        ).one() == (True, True)
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename=:name"
                ),
                {"name": table},
            )
            > 0
        )


@pytest.mark.parametrize(
    "table", ["task_comments", "task_presence", "notifications", "document_links"]
)
def test_current_intentional_exclusions_are_not_rls_protected(
    postgres_test_environment, table
):
    with postgres_test_environment.runtime_session(
        tenant_id=None, organization_id=None
    ) as session:
        assert session.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid=to_regclass(:name)"
            ),
            {"name": table},
        ).one() == (False, False)


def test_raw_foreign_comment_is_visible_but_reader_parent_join_denies_it(
    postgres_test_environment, governance_rows
):
    with postgres_test_environment.runtime_session(
        tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
    ) as session:
        assert (
            session.scalar(
                text("SELECT body FROM task_comments WHERE id='r7a-comment-b'")
            )
            == "R7A retained content b"
        )
        page = SqlAlchemyCollaborationWorkspaceReader(
            session=session
        ).read_comment_page(
            tenant_id="r7a-tenant-a",
            organization_id="r7a-org-a",
            accessible_project_ids=("r7a-project-b",),
            criteria=CollaborationCommentCriteria(),
            page=1,
            page_size=25,
        )
        assert page.total == 0
        assert page.items == ()


def test_deleted_comment_remains_in_current_workspace_projection(
    postgres_test_environment, governance_rows
):
    with postgres_test_environment.runtime_session(
        tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
    ) as session:
        page = SqlAlchemyCollaborationWorkspaceReader(
            session=session
        ).read_comment_page(
            tenant_id="r7a-tenant-a",
            organization_id="r7a-org-a",
            accessible_project_ids=("r7a-project-a",),
            criteria=CollaborationCommentCriteria(),
            page=1,
            page_size=25,
        )
        retained = next(row for row in page.items if row.comment_id == "r7a-comment-a")
        assert retained.body == "R7A retained content a"
        assert not hasattr(retained, "deleted_at")
