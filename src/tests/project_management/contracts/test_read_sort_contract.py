from src.core.modules.project_management.contracts.reads import (
    ReadSort,
    ReadSortDirection,
)


def test_read_sort_normalizes_supported_direction() -> None:
    sort = ReadSort.normalize(
        key="status",
        direction="descending",
        allowed_keys={"name", "status"},
        default_key="name",
    )

    assert sort == ReadSort("status", ReadSortDirection.DESCENDING)


def test_read_sort_rejects_unknown_key_to_safe_default() -> None:
    sort = ReadSort.normalize(
        key="arbitrary_sql_expression",
        direction="desc",
        allowed_keys={"name", "status"},
        default_key="name",
    )

    assert sort == ReadSort("name", ReadSortDirection.ASCENDING)
