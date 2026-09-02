from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from src.infra.composition.app_container import build_service_dict
from src.infra.persistence.db.engine import create_database_engine
from src.infra.persistence.orm.base import Base


def test_budget_command_uses_fresh_uow_after_shared_session_reads(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'finance.db').as_posix()}")
    sessions = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    shared_session = sessions()
    try:
        services = build_service_dict(shared_session)
        auth = services["auth_service"]
        user_session = services["user_session"]
        admin = auth.authenticate("admin", "ChangeMe123!")
        user_session.set_principal(auth.build_principal(admin))

        project = services["project_service"].create_project("SQLite Finance")
        boundary = services["finance_governance_commands"]
        budget = boundary.budget(
            lambda service: service.create_budget(project.id, "Draft", "XAF"),
            project_id=project.id,
        )

        services["finance_workspace_query"].get_budget_workspace(
            project.id,
            selected_budget_id=budget.id,
        )
        # Reproduce the runtime condition: another operation has left the
        # process-wide desktop session holding SQLite's writer reservation.
        shared_session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        boundary.budget(
            lambda service: service.delete_budget(
                budget.id,
                expected_version=budget.row_version,
            )
        )
    finally:
        shared_session.rollback()
        shared_session.close()
        engine.dispose()
