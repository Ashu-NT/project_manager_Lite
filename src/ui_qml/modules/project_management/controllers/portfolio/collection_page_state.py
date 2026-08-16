from __future__ import annotations


class PortfolioCollectionPageState:
    """Client-side mirror of one authoritative server-paginated Portfolio
    collection page (R3.3/R3.4). Holds only the request parameters and the
    server's last-reported total -- it never slices or filters rows itself;
    that happens server-side in PortfolioService.list_*_page()."""

    def __init__(self, *, page_size: int = 25, sort_key: str = "", sort_direction: str = "asc") -> None:
        self.search_text = ""
        self.page = 1
        self.page_size = page_size
        self.sort_key = sort_key
        self.sort_direction = sort_direction
        self.total_count = 0


__all__ = ["PortfolioCollectionPageState"]
