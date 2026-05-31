"""Platform admin code-generation wiring (Organization reference slice)."""

from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.platform.presenters.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)


class _FakeRuntimeApi:
    def __init__(self, codes):
        self._codes = list(codes)

    def list_organizations(self, *, active_only=None):
        return SimpleNamespace(
            ok=True,
            data=[SimpleNamespace(organization_code=code) for code in self._codes],
        )


def test_org_suggest_code_uses_display_name_token():
    presenter = PlatformOrganizationCatalogPresenter(runtime_api=_FakeRuntimeApi([]))
    assert presenter.suggest_code({"displayName": "ACME Corp"}) == "ORG-ACME-0001"


def test_org_suggest_code_increments_against_existing_codes():
    presenter = PlatformOrganizationCatalogPresenter(
        runtime_api=_FakeRuntimeApi(["ORG-ACME-0001", "ORG-ACME-0002"])
    )
    assert presenter.suggest_code({"displayName": "ACME Corp"}) == "ORG-ACME-0003"


def test_org_suggest_code_falls_back_to_year_without_name():
    presenter = PlatformOrganizationCatalogPresenter(runtime_api=_FakeRuntimeApi([]))
    code = presenter.suggest_code({})
    assert code.startswith("ORG-")
    assert code.endswith("-0001")
    # middle segment is a 4-digit year
    assert len(code.split("-")[1]) == 4 and code.split("-")[1].isdigit()


def test_org_suggest_code_handles_missing_runtime_api():
    presenter = PlatformOrganizationCatalogPresenter(runtime_api=None)
    code = presenter.suggest_code({"displayName": "ACME"})
    assert code == "ORG-ACME-0001"


# ── other admin entities (prefix + name token + uniqueness wiring) ───────────
class _FakeListApi:
    """Generic fake exposing one list_* method returning rows with a code attr."""

    def __init__(self, method_name, code_attr, codes):
        self._method_name = method_name
        self._code_attr = code_attr
        self._codes = list(codes)
        setattr(self, method_name, self._list)

    def _list(self, *, active_only=None):
        return SimpleNamespace(
            ok=True,
            data=[SimpleNamespace(**{self._code_attr: code}) for code in self._codes],
        )


def test_site_suggest_code():
    from src.ui_qml.platform.presenters.site_catalog_presenter import (
        PlatformSiteCatalogPresenter,
    )

    api = _FakeListApi("list_sites", "site_code", ["SITE-PLAN-0001"])
    presenter = PlatformSiteCatalogPresenter(site_api=api)
    assert presenter.suggest_code({"name": "Plant North"}) == "SITE-PLAN-0002"


def test_party_suggest_code_uses_party_name():
    from src.ui_qml.platform.presenters.party_catalog_presenter import (
        PlatformPartyCatalogPresenter,
    )

    api = _FakeListApi("list_parties", "party_code", [])
    presenter = PlatformPartyCatalogPresenter(party_api=api)
    assert presenter.suggest_code({"partyName": "ACME Corp"}) == "PTY-ACME-0001"


def test_document_suggest_code_uses_title():
    from src.ui_qml.platform.presenters.document_catalog_presenter import (
        PlatformDocumentCatalogPresenter,
    )

    api = _FakeListApi("list_documents", "document_code", [])
    presenter = PlatformDocumentCatalogPresenter(document_api=api)
    assert presenter.suggest_code({"title": "Method Statement"}) == "DOC-METH-0001"


def test_document_structure_suggest_code_prefix():
    from src.ui_qml.platform.presenters.document_management_presenter import (
        PlatformDocumentManagementPresenter,
    )

    api = _FakeListApi("list_document_structures", "structure_code", [])
    presenter = PlatformDocumentManagementPresenter(document_api=api)
    assert presenter.suggest_code({"name": "Quality Manual"}) == "DST-QUAL-0001"
