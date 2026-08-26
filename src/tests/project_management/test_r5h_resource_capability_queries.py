from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from src.core.modules.project_management.contracts.reads import ReadSort


ROOT = Path(__file__).resolve().parents[2]


def test_time_entry_version_migration_repairs_stamped_local_database(tmp_path) -> None:
    database = tmp_path / "r5h-time-entry-repair.db"
    config = Config(str(ROOT / "infra/persistence/migrations/alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "d72f4a8c91be")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.begin() as connection:
        connection.execute(sa.text("ALTER TABLE time_entries DROP COLUMN version"))
    engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    columns = {
        column["name"]: column
        for column in sa.inspect(engine).get_columns("time_entries")
    }
    assert columns["version"]["nullable"] is False
    engine.dispose()


def test_resource_skills_are_server_paged_filtered_sorted_and_scoped(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource("Capability Reader")
    resource_service.add_resource_skill(
        resource.id, "z-plan", "Zulu Planning", proficiency="beginner"
    )
    resource_service.add_resource_skill(
        resource.id, "a-build", "Alpha Building", proficiency="expert"
    )

    first = resource_service.query_resource_skills_page(
        resource.id, page=1, page_size=1, sort_key="skillName", sort_direction="asc"
    )
    second = resource_service.query_resource_skills_page(
        resource.id, page=2, page_size=1, sort_key="skillName", sort_direction="asc"
    )
    descending = resource_service.query_resource_skills_page(
        resource.id, page=1, page_size=1, sort_key="skillName", sort_direction="desc"
    )
    filtered = resource_service.query_resource_skills_page(
        resource.id, search_text="build", proficiency="expert"
    )

    assert first.filtered_total == 2
    assert [first.items[0].skill_name, second.items[0].skill_name] == [
        "Alpha Building",
        "Zulu Planning",
    ]
    assert descending.items[0].skill_name == "Zulu Planning"
    assert [item.skill_code for item in filtered.items] == ["a-build"]

    reader = resource_service._resource_capability_reader
    organization_id = services["user_session"].stored_active_organization_id()
    wrong_scope = reader.read_skills_page(
        tenant_id="other-tenant",
        organization_id=organization_id,
        resource_id=resource.id,
        search_text="",
        proficiency=None,
        page=1,
        page_size=25,
        sort=ReadSort("skillName"),
    )
    assert wrong_scope.filtered_total == 0


def test_resource_certifications_use_authoritative_status_filter_and_sort(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource("Certification Reader")
    today = date.today()
    resource_service.add_resource_certification(
        resource.id,
        "VALID",
        "Valid Credential",
        expiry_date=today + timedelta(days=60),
        issuer="Authority Z",
    )
    resource_service.add_resource_certification(
        resource.id,
        "EXPIRING",
        "Expiring Credential",
        expiry_date=today + timedelta(days=10),
        issuer="Authority A",
    )
    resource_service.add_resource_certification(
        resource.id,
        "OPEN",
        "No Expiry Credential",
        issuer="Authority M",
    )

    expiring = resource_service.query_resource_certifications_page(
        resource.id, status="expiring-soon"
    )
    first = resource_service.query_resource_certifications_page(
        resource.id,
        page=1,
        page_size=1,
        sort_key="issuer",
        sort_direction="asc",
    )
    last = resource_service.query_resource_certifications_page(
        resource.id,
        page=1,
        page_size=1,
        sort_key="issuer",
        sort_direction="desc",
    )

    assert [item.certification_code for item in expiring.items] == ["expiring"]
    assert first.items[0].issuer == "Authority A"
    assert last.items[0].issuer == "Authority Z"


def test_capability_qml_uses_authoritative_tables_and_required_fields() -> None:
    sections = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/resources/sections"
    )
    dialogs = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/resources/dialogs"
    )
    skills = (sections / "ResourcesSkillsSection.qml").read_text(encoding="utf-8")
    certs = (sections / "ResourcesCertificationsSection.qml").read_text(
        encoding="utf-8"
    )
    skill_dialog = (dialogs / "ResourceSkillEditorDialog.qml").read_text(
        encoding="utf-8"
    )
    cert_dialog = (dialogs / "ResourceCertificationEditorDialog.qml").read_text(
        encoding="utf-8"
    )

    for source in (skills, certs):
        assert 'sortingMode: "server"' in source
        assert "TablePaginationBar" in source
        assert "TableToolbar" in source
    assert "setResourceSkillsSort" in skills
    assert "setResourceCertificationsSort" in certs
    assert "Complete the required skill fields." in skill_dialog
    assert "Complete the required certification fields." in cert_dialog
    assert "fieldErrors" in skill_dialog
    assert "fieldErrors" in cert_dialog
