from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class PageRequest:
    """
    Cursor-first pagination descriptor.

    Use page/page_size for offset-based pagination (simple list endpoints).
    Use cursor for keyset pagination (large sorted datasets, timeline views).
    page and cursor are mutually exclusive — cursor takes precedence when set.
    """
    page: int = 1            # 1-indexed; ignored when cursor is set
    page_size: int = 50      # maximum rows per page; capped at MAX_PAGE_SIZE
    cursor: Optional[str] = None  # opaque keyset cursor (id or encoded sort key)

    MAX_PAGE_SIZE: int = field(default=500, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 1
        if self.page_size > self.MAX_PAGE_SIZE:
            self.page_size = self.MAX_PAGE_SIZE

    @property
    def offset(self) -> int:
        """SQL OFFSET value for offset-based pagination."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    @staticmethod
    def first(page_size: int = 50) -> "PageRequest":
        return PageRequest(page=1, page_size=page_size)


@dataclass
class PaginatedResult(Generic[T]):
    """
    Typed wrapper for a single page of results.

    total is the full count across all pages (may be None when the caller
    chose not to issue a COUNT query for performance reasons).
    next_cursor is set when cursor-based pagination is in use.
    """
    items: List[T]
    page: int
    page_size: int
    total: Optional[int] = None
    next_cursor: Optional[str] = None

    @property
    def has_more(self) -> bool:
        if self.next_cursor is not None:
            return True
        if self.total is not None:
            return (self.page * self.page_size) < self.total
        return len(self.items) == self.page_size

    @property
    def total_pages(self) -> Optional[int]:
        if self.total is None:
            return None
        return max(1, -(-self.total // self.page_size))  # ceiling division

    @staticmethod
    def single_page(items: List[T]) -> "PaginatedResult[T]":
        """Convenience wrapper when pagination is not required."""
        return PaginatedResult(items=items, page=1, page_size=len(items), total=len(items))


__all__ = ["PageRequest", "PaginatedResult"]
