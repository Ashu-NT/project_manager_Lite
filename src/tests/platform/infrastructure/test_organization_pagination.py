"""`OrganizationService.list_organizations_page` / `OrganizationRepository.
list_page_for_tenant` -- real SQL LIMIT/OFFSET pagination, page-size
clamping to the standard 25/50/100 set, and the total/filtered_total
distinction used to tell a genuinely empty dataset apart from a search that
matched nothing."""

from __future__ import annotations

from src.core.platform.application.master_data.org.organization_service import (
    ORGANIZATION_PAGE_SIZE_OPTIONS,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _seed(organization_service, *, count: int, name_prefix: str) -> None:
    for i in range(count):
        organization_service.create_organization(
            organization_code=_unique_code(name_prefix),
            display_name=f"{name_prefix} Org {i:03d}",
        )


def test_default_page_size_is_25(services):
    organization_service = services["organization_service"]
    page = organization_service.list_organizations_page()
    assert page.page_size == 25
    assert page.page == 1


def test_page_size_options_are_exactly_25_50_100():
    assert ORGANIZATION_PAGE_SIZE_OPTIONS == (25, 50, 100)


def test_invalid_page_size_falls_back_to_default(services):
    organization_service = services["organization_service"]
    page = organization_service.list_organizations_page(page_size=17)
    assert page.page_size == 25


def test_page_boundary_crossing_and_last_partial_page(services):
    organization_service = services["organization_service"]
    prefix = "PAGEBOUND"
    _seed(organization_service, count=26, name_prefix=prefix)

    first_page = organization_service.list_organizations_page(page=1, page_size=25, search=prefix)
    assert len(first_page.items) == 25
    assert first_page.filtered_total == 26

    second_page = organization_service.list_organizations_page(page=2, page_size=25, search=prefix)
    assert len(second_page.items) == 1
    assert second_page.filtered_total == 26

    # No overlap between the two pages.
    first_ids = {row.id for row in first_page.items}
    second_ids = {row.id for row in second_page.items}
    assert first_ids.isdisjoint(second_ids)


def test_exact_page_size_boundary_has_no_second_page_items(services):
    organization_service = services["organization_service"]
    prefix = "EXACT25"
    _seed(organization_service, count=25, name_prefix=prefix)

    first_page = organization_service.list_organizations_page(page=1, page_size=25, search=prefix)
    assert len(first_page.items) == 25
    assert first_page.filtered_total == 25

    second_page = organization_service.list_organizations_page(page=2, page_size=25, search=prefix)
    assert len(second_page.items) == 0
    assert second_page.filtered_total == 25


def test_search_distinguishes_filtered_empty_from_true_empty(services):
    organization_service = services["organization_service"]
    prefix = "SEARCHABLE"
    _seed(organization_service, count=3, name_prefix=prefix)

    matching = organization_service.list_organizations_page(search=prefix)
    assert matching.filtered_total == 3
    assert matching.total >= 3

    no_match = organization_service.list_organizations_page(search="DOES-NOT-EXIST-ANYWHERE")
    assert no_match.filtered_total == 0
    # The tenant's real (unfiltered) total is unaffected by an unmatched search.
    assert no_match.total == matching.total


def test_page_size_50_and_100_return_correct_counts(services):
    organization_service = services["organization_service"]
    prefix = "SIZED"
    _seed(organization_service, count=60, name_prefix=prefix)

    page_50 = organization_service.list_organizations_page(page=1, page_size=50, search=prefix)
    assert len(page_50.items) == 50
    assert page_50.filtered_total == 60

    page_100 = organization_service.list_organizations_page(page=1, page_size=100, search=prefix)
    assert len(page_100.items) == 60
    assert page_100.filtered_total == 60
