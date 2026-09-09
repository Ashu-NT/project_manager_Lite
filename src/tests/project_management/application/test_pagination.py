"""Unit tests for PageRequest and PaginatedResult."""
from __future__ import annotations

import pytest

from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    PaginatedResult,
)


class TestPageRequest:
    def test_defaults(self):
        p = PageRequest()
        assert p.page == 1
        assert p.page_size == 50

    def test_page_clamped_to_one(self):
        p = PageRequest(page=0)
        assert p.page == 1

    def test_page_size_clamped_to_one(self):
        p = PageRequest(page_size=0)
        assert p.page_size == 1

    def test_page_size_clamped_to_max(self):
        p = PageRequest(page_size=10000)
        assert p.page_size == p.MAX_PAGE_SIZE

    def test_offset_calculation(self):
        p = PageRequest(page=3, page_size=20)
        assert p.offset == 40

    def test_first_helper(self):
        p = PageRequest.first(page_size=25)
        assert p.page == 1
        assert p.page_size == 25
        assert p.offset == 0


class TestPaginatedResult:
    def test_has_more_with_total(self):
        r = PaginatedResult(items=list(range(10)), page=1, page_size=10, total=25)
        assert r.has_more

    def test_no_more_when_on_last_page(self):
        r = PaginatedResult(items=list(range(5)), page=3, page_size=10, total=25)
        assert not r.has_more

    def test_has_more_inferred_from_full_page(self):
        r = PaginatedResult(items=list(range(50)), page=1, page_size=50, total=None)
        assert r.has_more

    def test_no_more_when_partial_page(self):
        r = PaginatedResult(items=list(range(30)), page=1, page_size=50, total=None)
        assert not r.has_more

    def test_total_pages(self):
        r = PaginatedResult(items=[], page=1, page_size=10, total=25)
        assert r.total_pages == 3

    def test_total_pages_exact(self):
        r = PaginatedResult(items=[], page=1, page_size=10, total=30)
        assert r.total_pages == 3

    def test_total_pages_none_when_no_total(self):
        r = PaginatedResult(items=[], page=1, page_size=10, total=None)
        assert r.total_pages is None

    def test_single_page_helper(self):
        items = [1, 2, 3]
        r = PaginatedResult.single_page(items)
        assert r.total == 3
        assert r.page == 1
        assert not r.has_more

    def test_has_more_with_next_cursor(self):
        r = PaginatedResult(items=[1, 2], page=1, page_size=50, next_cursor="abc123")
        assert r.has_more
