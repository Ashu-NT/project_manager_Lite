"""R7B regressions replacing the unsafe R7A comment characterizations."""

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentCriteria,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration.sqlalchemy_workspace_reader import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
    SqlAlchemyApprovalRepository,
)
from src.infra.persistence.db.postgresql_rls import worker_tenant_scope

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture(scope="module")
def governance_rows(postgres_test_environment):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with postgres_test_environment.admin_engine.begin() as connection:
        # Shared by the R7C regression matrix in the same dedicated database.
        if connection.scalar(text("SELECT count(*) FROM projects WHERE id='r7a-project-a'")):
            return
        for suffix in ("a", "b", "o", "p"):
            scope = {
                "tenant": "r7a-tenant-b" if suffix == "b" else "r7a-tenant-a",
                "org": "r7a-org-a" if suffix == "p" else f"r7a-org-{suffix}",
                "project": f"r7a-project-{suffix}",
                "task": f"r7a-task-{suffix}",
            }
            connection.execute(
                text(
                    "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:tenant, :tenant, :tenant, 'active', true, 1) ON CONFLICT DO NOTHING"
                ),
                scope,
            )
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, status, version) "
                    "VALUES (:org, :tenant, :org, :org, 'UTC', 'XAF', 'active', 1) ON CONFLICT DO NOTHING"
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
        _seed_identities(connection, now)


def _seed_identities(connection, now):
    for code in ("collaboration.read", "collaboration.manage", "approval.decide"):
        connection.execute(
            text(
                "INSERT INTO permissions (id, code, description) VALUES (:id, :code, '') ON CONFLICT DO NOTHING"
            ),
            {"id": f"r7b-{code}", "code": code},
        )
    for user, tenant, kind, target, active, member, revoked, expired in (
        ("reviewer", "a", "project", "r7a-project-a", True, "active", False, False),
        ("foreign", "b", "project", "r7a-project-b", True, "active", False, False),
        ("wrongorg", "a", "organization", "r7a-org-o", True, "active", False, False),
        ("wrongproject", "a", "project", "r7a-project-p", True, "active", False, False),
        ("disabled", "a", "project", "r7a-project-a", False, "active", False, False),
        ("suspended", "a", "project", "r7a-project-a", True, "suspended", False, False),
        ("revoked", "a", "project", "r7a-project-a", True, "active", True, False),
        ("expired", "a", "project", "r7a-project-a", True, "active", False, True),
        ("unauthorized", "a", "project", "r7a-project-a", True, "active", False, False),
    ):
        values = {
            "id": f"r7b-{user}",
            "tenant": f"r7a-tenant-{tenant}",
            "kind": kind,
            "target": target,
            "active": active,
            "member": member,
            "now": now,
            "revoked": now if revoked else None,
            "expires": datetime(2020, 1, 1) if expired else None,
        }
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at) "
                "VALUES (:id, :id, 'not-used', 'human', :active, :now, :now)"
            ),
            values,
        )
        connection.execute(
            text(
                "INSERT INTO user_tenants (id, user_id, tenant_id, status, created_at, updated_at) "
                "VALUES (:id, :id, :tenant, :member, :now, :now)"
            ),
            values,
        )
        for copy in range(2 if user == "reviewer" else 1):
            role = f"{values['id']}-role-{copy}"
            values["role"] = role
            connection.execute(
                text(
                    "INSERT INTO roles (id, name, display_name, description, allowed_scope_type, "
                    "is_system, tenant_id, created_at, updated_at) "
                    "VALUES (:role, :role, :role, '', :kind, false, :tenant, :now, :now)"
                ),
                values,
            )
            for permission in (
                "collaboration.read",
                "collaboration.manage",
                "approval.decide",
            ):
                if user == "unauthorized":
                    continue
                connection.execute(
                    text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) "
                        "SELECT :id, :role, id FROM permissions WHERE code=:code"
                    ),
                    {"id": f"{role}-{permission}", "role": role, "code": permission},
                )
            connection.execute(
                text(
                    "INSERT INTO role_bindings (id, principal_type, principal_id, role_id, tenant_id, "
                    "actual_scope_type, actual_scope_id, assigned_at, revoked_at, expires_at) "
                    "VALUES (:role, 'user', :id, :role, :tenant, :kind, :target, :now, :revoked, :expires)"
                ),
                values,
            )
    connection.execute(
        text(
            "INSERT INTO approval_requests (id, tenant_id, organization_id, project_id, request_type, "
            "entity_type, entity_id, payload_json, status, requested_at) VALUES "
            "('r7b-request', 'r7a-tenant-a', 'r7a-org-a', 'r7a-project-a', 'baseline.create', "
            "'project_baseline', 'r7b-target', '{}', 'PENDING', :now)"
        ),
        {"now": now},
    )


@contextmanager
def runtime(environment, user="reviewer", tenant="a", org="a"):
    with worker_tenant_scope(
        tenant_id=f"r7a-tenant-{tenant}",
        organization_id=f"r7a-org-{org}",
        actor_user_id=f"r7b-{user}",
    ):
        with environment.runtime_session(
            tenant_id=None, organization_id=None
        ) as session:
            yield session


def test_runtime_role_has_no_rls_bypass(postgres_test_environment):
    with postgres_test_environment.runtime_session(
        tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
    ) as session:
        role = session.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        assert role == ("app_runtime", False, False, True)
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner=current_user"
                )
            )
            == 0
        )


@pytest.mark.parametrize(
    "table",
    ["approval_requests", "activity_entries", "timesheet_periods", "task_comments"],
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


@pytest.mark.parametrize("table", ["task_presence", "notifications", "document_links"])
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


def test_raw_foreign_comment_and_scoped_reader_both_deny_access(
    postgres_test_environment, governance_rows
):
    with runtime(postgres_test_environment) as session:
        assert (
            session.scalar(
                text("SELECT body FROM task_comments WHERE id='r7a-comment-b'")
            )
            is None
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


def test_deleted_comment_is_a_redacted_tombstone(
    postgres_test_environment, governance_rows
):
    with runtime(postgres_test_environment) as session:
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
        assert retained.body == ""
        assert retained.is_deleted and retained.deleted_at is not None
        assert retained.mentions == retained.mentioned_user_ids == ()


@pytest.mark.parametrize("suffix", ["b", "o", "p"])
def test_raw_foreign_scope_read_update_delete_insert_denied(
    postgres_test_environment, governance_rows, suffix
):
    with runtime(postgres_test_environment) as session:
        assert (
            session.scalar(
                text("SELECT id FROM task_comments WHERE id=:id"),
                {"id": f"r7a-comment-{suffix}"},
            )
            is None
        )
        assert (
            session.execute(
                text("UPDATE task_comments SET body='attack' WHERE id=:id"),
                {"id": f"r7a-comment-{suffix}"},
            ).rowcount
            == 0
        )
        assert (
            session.execute(
                text("DELETE FROM task_comments WHERE id=:id"),
                {"id": f"r7a-comment-{suffix}"},
            ).rowcount
            == 0
        )
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO task_comments (id, task_id, body, created_at) VALUES (:id, :task, 'attack', CURRENT_TIMESTAMP)"
                ),
                {"id": f"r7b-attack-{suffix}", "task": f"r7a-task-{suffix}"},
            )


def test_foreign_reply_parent_rejected_by_database(
    postgres_test_environment, governance_rows
):
    with runtime(postgres_test_environment) as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO task_comments (id, task_id, body, created_at, parent_comment_id) "
                    "VALUES ('r7b-reply', 'r7a-task-a', 'attack', CURRENT_TIMESTAMP, 'r7a-comment-p')"
                )
            )


def test_active_comment_read_and_creation(postgres_test_environment, governance_rows):
    with runtime(postgres_test_environment) as session:
        session.execute(
            text(
                "INSERT INTO task_comments (id, task_id, body, created_at) "
                "VALUES ('r7b-active', 'r7a-task-a', 'Visible', CURRENT_TIMESTAMP)"
            )
        )
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
        active = next(row for row in page.items if row.comment_id == "r7b-active")
        assert active.body == "Visible" and not active.is_deleted


def test_only_active_scoped_reviewers_are_notified_once(
    postgres_test_environment, governance_rows
):
    with runtime(postgres_test_environment) as session:
        repo = SqlAlchemyApprovalRepository(session)
        repo._tenant_context_service = SimpleNamespace(
            require_active_scope_ids=lambda **kw: SimpleNamespace(
                tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
            )
        )
        assert repo.list_notification_recipient_ids(
            "r7b-request", audience="reviewers"
        ) == ("r7b-reviewer",)
        assert (
            repo.list_notification_recipient_ids(
                "r7b-request", audience="reviewers", after_user_id="r7b-reviewer"
            )
            == ()
        )


@pytest.mark.parametrize(
    "user",
    [
        "foreign",
        "wrongorg",
        "wrongproject",
        "disabled",
        "suspended",
        "revoked",
        "expired",
        "unauthorized",
    ],
)
def test_ineligible_identity_cannot_read_local_comments(
    postgres_test_environment, governance_rows, user
):
    with runtime(postgres_test_environment, user=user) as session:
        assert (
            session.scalar(
                text("SELECT count(*) FROM task_comments WHERE task_id='r7a-task-a'")
            )
            == 0
        )


def test_no_principal_context_denies_comments(
    postgres_test_environment, governance_rows
):
    with postgres_test_environment.runtime_session(
        tenant_id=None, organization_id=None
    ) as session:
        assert session.scalar(text("SELECT count(*) FROM task_comments")) == 0


@pytest.mark.parametrize(
    "criteria",
    [
        CollaborationCommentCriteria(search_text="R7A retained content a"),
        CollaborationCommentCriteria(
            principal_mentions_only=True, principal_user_id="r7b-reviewer"
        ),
        CollaborationCommentCriteria(
            unread_only=True, principal_user_id="r7b-reviewer"
        ),
    ],
)
def test_deleted_body_cannot_leak_through_search_or_unread_counts(
    postgres_test_environment, governance_rows, criteria
):
    with runtime(postgres_test_environment) as session:
        page = SqlAlchemyCollaborationWorkspaceReader(
            session=session
        ).read_comment_page(
            tenant_id="r7a-tenant-a",
            organization_id="r7a-org-a",
            accessible_project_ids=("r7a-project-a",),
            criteria=criteria,
            page=1,
            page_size=25,
        )
        assert page.total == 0 and page.items == ()


def _comments(session):
    from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
        SqlAlchemyTaskCommentRepository,
    )

    repo = SqlAlchemyTaskCommentRepository(session)
    repo._tenant_context_service = SimpleNamespace(
        require_active_scope_ids=lambda **kw: SimpleNamespace(
            tenant_id="r7a-tenant-a", organization_id="r7a-org-a"
        )
    )
    return repo


def test_stale_writer_cannot_resurrect_committed_tombstone(
    postgres_test_environment, governance_rows
):
    from src.core.modules.project_management.domain.collaboration import TaskComment
    from src.core.platform.common.exceptions import ConcurrencyError

    comment = TaskComment.create(
        task_id="r7a-task-a",
        author_user_id="r7b-reviewer",
        author_username="reviewer",
        body="Private race body",
    )
    with runtime(postgres_test_environment) as session:
        _comments(session).add(comment)
        session.commit()
    with runtime(postgres_test_environment) as stale_session:
        stale_repo = _comments(stale_session)
        stale = stale_repo.get(comment.id)
        with runtime(postgres_test_environment) as deleting_session:
            repo = _comments(deleting_session)
            deleted = repo.get(comment.id)
            deleted.deleted_at = datetime.now(timezone.utc)
            repo.update(deleted)
            deleting_session.commit()
        stale.body = "Resurrected text"
        with pytest.raises(ConcurrencyError):
            stale_repo.update(stale)
        stale_session.rollback()
        page = SqlAlchemyCollaborationWorkspaceReader(
            session=stale_session
        ).read_comment_page(
            tenant_id="r7a-tenant-a",
            organization_id="r7a-org-a",
            accessible_project_ids=("r7a-project-a",),
            criteria=CollaborationCommentCriteria(),
            page=1,
            page_size=25,
        )
        row = next(item for item in page.items if item.comment_id == comment.id)
        assert row.is_deleted and row.body == ""


def test_scope_change_cannot_move_comment_to_foreign_project(
    postgres_test_environment, governance_rows
):
    with runtime(postgres_test_environment) as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE task_comments SET task_id='r7a-task-p' WHERE id='r7a-comment-a'"
                )
            )


def test_recipient_query_is_single_bounded_statement_and_rechecks_revocation(
    postgres_test_environment, governance_rows
):
    from sqlalchemy import event

    with runtime(postgres_test_environment) as session:
        repo = SqlAlchemyApprovalRepository(session)
        repo._tenant_context_service = _comments(session)._tenant_context_service
        connection = session.connection()
        statements = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(connection, "before_cursor_execute", capture)
        try:
            assert repo.list_notification_recipient_ids(
                "r7b-request", audience="reviewers", limit=1
            ) == ("r7b-reviewer",)
        finally:
            event.remove(connection, "before_cursor_execute", capture)
        assert len(statements) == 1
        assert "LIMIT" in statements[0] and "ORDER BY" in statements[0]
        session.execute(
            text(
                "UPDATE user_tenants SET revoked_at=CURRENT_TIMESTAMP WHERE user_id='r7b-reviewer'"
            )
        )
        assert (
            repo.list_notification_recipient_ids("r7b-request", audience="reviewers")
            == ()
        )
