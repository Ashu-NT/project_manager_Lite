"""Reader facts and application results reach presenters without DTO cloning."""

from datetime import date
from unittest.mock import Mock

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.certifications import (
    ResourceAddCertificationCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.skills import (
    ResourceAddSkillCommand,
    ResourceUpdateSkillCommand,
)
from src.core.modules.project_management.application.resources.dto.responses.capabilities import (
    ResourceCertificationResponse,
    ResourceSkillResponse,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceActivityReadPage,
    ResourceAssignmentReadPage,
    ResourceProjectReadPage,
)
from src.ui_qml.modules.project_management.presenters.resources.certifications_builder import (
    add_certification,
    build_certifications_page,
)
from src.ui_qml.modules.project_management.presenters.resources.skills_builder import (
    add_skill,
    build_skills_page,
)


def test_skills_api_returns_original_reader_page_and_command_result(services, monkeypatch):
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Skill boundary"))
    api = build_desktop_api_registry(services).project_management_resources
    command = ResourceAddSkillCommand(resource_id=resource.id, skill_code="PLAN", skill_name="Planning", proficiency="expert")
    response = services["resource_capability_commands"].add_resource_skill(command)
    assert isinstance(response, ResourceSkillResponse)
    commands = services["resource_capability_commands"]
    monkeypatch.setattr(commands, "update_resource_skill", lambda command: response)
    assert api.update_resource_skill(ResourceUpdateSkillCommand(
        skill_id=response.id, expected_version=response.version, skill_code="PLAN", skill_name="Planning", proficiency="expert",
    )) is response
    query = services["resource_capability_query"]
    reader = query._resource_capability_reader
    original = reader.read_skills_page
    captured = []

    def read(**kwargs):
        result = original(**kwargs)
        captured.append(result)
        return result

    monkeypatch.setattr(reader, "read_skills_page", read)
    page = api.list_resource_skills_page(resource.id)
    assert page is captured[-1]
    assert page.items[0] is captured[-1].items[0]
    view = build_skills_page(api, resource.id)
    assert view["items"][0]["id"] == response.id
    assert view["items"][0]["proficiencyLabel"] == "Expert"
    assert view["sortKey"] == page.sort.key


def test_certifications_api_preserves_reader_dates_and_presenter_formats_them(services, monkeypatch):
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Certification boundary"))
    api = build_desktop_api_registry(services).project_management_resources
    response = api.add_resource_certification(ResourceAddCertificationCommand(
        resource_id=resource.id, certification_code="CERT", certification_name="Credential",
        issued_date=date(2026, 1, 2),
    ))
    assert isinstance(response, ResourceCertificationResponse)
    query = services["resource_capability_query"]
    page = query.query_resource_certifications_page(resource.id)
    monkeypatch.setattr(query, "query_resource_certifications_page", lambda *args, **kwargs: page)
    assert api.list_resource_certifications_page(resource.id) is page
    assert page.items[0].issued_date == date(2026, 1, 2)
    assert page.items[0].expiry_date is None
    view = build_certifications_page(api, resource.id)
    row = view["items"][0]
    assert row["id"] == response.id
    assert row["issuedDate"] == "2026-01-02"
    assert row["expiryDate"] == ""
    assert row["metaText"] == "No expiry"
    assert row["certStatus"] == page.items[0].cert_status


def test_presenter_builds_application_command_from_payload():
    api = Mock()
    add_skill(api, "resource", {"skillCode": "PLAN", "skillName": "Planning", "proficiency": "expert"})
    command = api.add_resource_skill.call_args.args[0]
    assert isinstance(command, ResourceAddSkillCommand)
    assert command.resource_id == "resource"
    add_certification(api, "resource", {"certCode": "CERT", "certName": "Credential"})
    command = api.add_resource_certification.call_args.args[0]
    assert isinstance(command, ResourceAddCertificationCommand)
    assert command.certification_name == "Credential"


@pytest.mark.parametrize(("api_method", "reader_slot", "reader_method", "page"), [
    ("list_resource_projects_page", "_resource_projects_reader", "read_projects_page", ResourceProjectReadPage()),
    ("list_resource_assignments_page", "_resource_assignments_reader", "read_assignments_page", ResourceAssignmentReadPage()),
    ("list_resource_activity_page", "_resource_activity_reader", "read_activity_page", ResourceActivityReadPage()),
])
def test_resource_context_pages_preserve_reader_identity_and_scope(services, monkeypatch, api_method, reader_slot, reader_method, page):
    query = services["resource_context_query"]
    reader = getattr(query, reader_slot)
    captured = {}

    def read(**kwargs):
        captured.update(kwargs)
        return page

    monkeypatch.setattr(reader, reader_method, read)
    api = build_desktop_api_registry(services).project_management_resources
    assert getattr(api, api_method)("resource-id") is page
    assert captured["resource_id"] == "resource-id"
    assert captured["tenant_id"] == services["user_session"].stored_active_tenant_id()
    assert captured["organization_id"] == services["user_session"].stored_active_organization_id()
