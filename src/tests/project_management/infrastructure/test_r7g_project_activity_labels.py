from __future__ import annotations

from sqlalchemy import event


def test_project_activity_resolves_only_page_references_in_bounded_queries(
    services, session,
) -> None:
    project = services["project_service"].create_project("R7G Activity Labels")
    site = services["site_service"].create_site(site_code="R7G-SITE", name="North Yard")
    department = services["department_service"].create_department(
        department_code="R7G-DEPT", name="Operations"
    )
    party = services["party_service"].create_party(
        party_code="R7G-PARTY", party_name="Customer Group"
    )
    employee = services["employee_service"].create_employee(
        employee_code="R7G-EMP", full_name="History Actor", department_id=department.id
    )
    actor_id = services["user_session"].principal.user_id
    services["employee_service"].link_employee_user_account(employee.id, actor_id)

    services["activity_service"].record(
        action="project.update", entity_type="project", entity_id=project.id,
        module="project_management", human_message="Project changed",
        details={"changes": {
            "site_id": {"from": "missing-site", "to": site.id},
            "department_id": {"from": None, "to": department.id},
            "client_party_id": {"from": None, "to": party.id},
            "manager_user_id": {"from": None, "to": actor_id},
        }},
    )
    session.commit()
    statements: list[str] = []

    def track(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", track)
    try:
        page = services["project_service"].query_project_activity_page(project.id)
    finally:
        event.remove(session.bind, "before_cursor_execute", track)

    item = next(row for row in page.items if row.summary == "Project changed")
    assert item.actor_kind == "human"
    assert item.actor_display == "History Actor"
    assert page.reference_labels["user"][actor_id] == "History Actor"
    assert page.reference_labels["site"][site.id] == "North Yard"
    assert "missing-site" not in page.reference_labels["site"]
    assert page.reference_labels["department"][department.id] == "Operations"
    assert page.reference_labels["party"][party.id] == "Customer Group"
    assert sum("FROM users JOIN user_tenants" in sql for sql in statements) == 1
    for table in ("employees", "sites", "departments", "parties"):
        assert sum(f"FROM {table}" in sql for sql in statements) == 1
    assert all("FROM resources" not in sql and "JOIN resources" not in sql for sql in statements)
