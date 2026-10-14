"""Document-level access: document permissions replace `settings.manage`, CONFIDENTIAL
needs `document.confidential.read`, RESTRICTED is visible only through a rule registered
by the module that owns the linked entity, and visibility is enforced in SQL so page
totals never reveal hidden documents."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_CONFIDENTIAL_READ_PERMISSION,
    DOCUMENT_MANAGE_PERMISSION,
    DOCUMENT_READ_PERMISSION,
    DOCUMENT_STRUCTURE_MANAGE_PERMISSION,
)
from src.core.platform.application.master_data.documents.dto import (
    DocumentCreateCommand,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    RestrictedDocumentGrant,
)
from src.core.platform.domain.master_data.documents import DocumentClassification
from src.core.platform.domain.master_data.documents.classification import (
    stored_document_classification,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
)

_EMPLOYEE_CONTRACT = ("platform", "employee_contract")


class _EmployeeContractRule:
    entity_type = _EMPLOYEE_CONTRACT[1]

    def __init__(self, entity_ids: frozenset[str] | None) -> None:
        self._entity_ids = entity_ids

    def grant_for(self, principal):
        return RestrictedDocumentGrant(entity_type=self.entity_type, entity_ids=self._entity_ids)


def _seed(services) -> dict[str, str]:
    commands = services["document_commands"]
    ids: dict[str, str] = {}
    for level in ("PUBLIC", "INTERNAL", "CONFIDENTIAL"):
        document = commands.create_document(DocumentCreateCommand(document_code=f"ACL-{level}", title=f"{level.title()} document", storage_uri=f"C:/docs/{level.lower()}.pdf", confidentiality_level=level))
        ids[level] = document.id
    # RESTRICTED documents are created by the owning module already linked to their
    # entity: no role can see an unlinked RESTRICTED document, not even its creator.
    (restricted,) = services["document_attachment_commands"].register_entity_attachments(
        required_permission=DOCUMENT_MANAGE_PERMISSION,
        operation_label="file employee contract",
        module_code=_EMPLOYEE_CONTRACT[0],
        entity_type=_EMPLOYEE_CONTRACT[1],
        entity_id="emp-1",
        attachments=["C:/docs/contract.pdf"],
        confidentiality_level=DocumentClassification.RESTRICTED,
    )
    assert restricted.confidentiality_level == "RESTRICTED"
    ids["RESTRICTED"] = restricted.id
    return ids


def _act_as(services, *permissions: str) -> None:
    user_session = services["user_session"]
    principal = user_session.principal
    user_session.set_principal(
        replace(
            principal,
            permissions=frozenset({"organization.access", *permissions}),
            scoped_access={},
            project_access={},
        )
    )


def _visible(services, ids: dict[str, str]) -> set[str]:
    """Classification labels of the seeded documents the page shows; totals must agree."""
    organization = services["tenant_context_service"].get_active_organization()
    page = services["document_query"].list_documents_page_for_organization(organization.id, page=1, page_size=25)
    assert page.filtered_total == len(page.items)
    labels = {document_id: label for label, document_id in ids.items()}
    return {labels[document.id] for document in page.items if document.id in labels}


def test_tenant_and_org_admin_get_document_permissions_security_admin_does_not():
    roles = DEFAULT_ROLE_PERMISSIONS
    document_permissions = {
        DOCUMENT_READ_PERMISSION,
        DOCUMENT_MANAGE_PERMISSION,
        DOCUMENT_STRUCTURE_MANAGE_PERMISSION,
        DOCUMENT_CONFIDENTIAL_READ_PERMISSION,
    }
    assert document_permissions <= set(roles["tenant_admin"])
    assert document_permissions <= set(roles["org_admin"])
    assert not document_permissions & set(roles["security_admin"])
    assert not document_permissions & set(roles["auditor"])


def test_settings_manage_alone_no_longer_grants_document_access(services):
    _seed(services)
    _act_as(services, "settings.manage")

    with pytest.raises(BusinessRuleError, match="document.read"):
        services["document_query"].list_documents()
    with pytest.raises(BusinessRuleError, match="document.manage"):
        services["document_commands"].create_document(DocumentCreateCommand(document_code="ACL-DENIED", title="Denied", storage_uri="C:/docs/denied.pdf"))


def test_document_read_sees_public_and_internal_only(services):
    ids = _seed(services)
    _act_as(services, DOCUMENT_READ_PERMISSION)

    assert _visible(services, ids) == {"PUBLIC", "INTERNAL"}
    with pytest.raises(NotFoundError):
        services["document_query"].get_document(ids["CONFIDENTIAL"])


def test_confidential_read_adds_confidential_but_never_restricted(services):
    ids = _seed(services)
    _act_as(services, DOCUMENT_READ_PERMISSION, DOCUMENT_CONFIDENTIAL_READ_PERMISSION)

    assert _visible(services, ids) == {"PUBLIC", "INTERNAL", "CONFIDENTIAL"}
    with pytest.raises(NotFoundError):
        services["document_query"].get_document(ids["RESTRICTED"])


def test_restricted_documents_are_visible_only_through_a_module_rule(services):
    ids = _seed(services)
    _act_as(services, DOCUMENT_READ_PERMISSION)
    services["document_access_policy"].register_rule(_EmployeeContractRule(frozenset({"emp-2"})))

    assert "RESTRICTED" not in _visible(services, ids)

    policy = services["document_access_policy"]
    policy._rules.clear()
    policy.register_rule(_EmployeeContractRule(frozenset({"emp-1"})))

    assert "RESTRICTED" in _visible(services, ids)
    assert services["document_query"].get_document(ids["RESTRICTED"]).id == ids["RESTRICTED"]


def test_duplicate_rule_for_the_same_entity_type_is_rejected(services):
    policy = services["document_access_policy"]
    policy.register_rule(_EmployeeContractRule(None))
    with pytest.raises(ValueError, match="already registered"):
        policy.register_rule(_EmployeeContractRule(None))


def test_writes_reject_unknown_classifications(services):
    with pytest.raises(ValidationError) as excinfo:
        services["document_commands"].create_document(DocumentCreateCommand(document_code="ACL-BAD", title="Bad label", storage_uri="C:/docs/bad.pdf", confidentiality_level="Secret-ish"))
    assert excinfo.value.code == "DOCUMENT_CONFIDENTIALITY_INVALID"


def test_blank_classification_defaults_to_internal_and_unknown_stored_labels_fail_closed(services):
    document = services["document_commands"].create_document(DocumentCreateCommand(document_code="ACL-DEFAULT", title="Default", storage_uri="C:/docs/default.pdf"))
    assert document.confidentiality_level == DocumentClassification.INTERNAL.value
    assert stored_document_classification("legacy free text") is DocumentClassification.CONFIDENTIAL
    assert stored_document_classification("") is DocumentClassification.INTERNAL
