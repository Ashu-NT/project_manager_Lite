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
        user_session = services["user_session"]
        admin = services["authentication"].authenticate("admin", "ChangeMe123!")
        user_session.set_principal(services["principal_builder"].build(admin))

        project = services['project_create'].create_project("SQLite Finance")
        boundary = services["finance_governance_commands"]
        budget = boundary.budget_lifecycle(
            lambda service: service.create_budget(project.id, "Draft", "XAF"),
        )

        services["finance_workspace_query"].get_budget_workspace(
            project.id,
            selected_budget_id=budget.id,
        )
        # Reproduce the runtime condition: another operation has left the
        # process-wide desktop session holding SQLite's writer reservation.
        shared_session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        boundary.budget_lifecycle(
            lambda service: service.delete_budget(
                budget.id,
                expected_version=budget.row_version,
            )
        )
    finally:
        shared_session.rollback()
        shared_session.close()
        engine.dispose()
