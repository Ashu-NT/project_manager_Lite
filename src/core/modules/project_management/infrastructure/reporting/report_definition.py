from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.modules.project_management.domain.identifiers import generate_id


class ColumnDataType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CURRENCY = "currency"
    PERCENT = "percent"
    DURATION = "duration"
    STATUS = "status"


class FilterOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class GroupingFunction(str, Enum):
    NONE = "none"
    SUM = "sum"
    AVERAGE = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ReportVisibility(str, Enum):
    PRIVATE = "private"       # only visible to owner
    SHARED = "shared"         # visible to org members with report access
    PUBLIC = "public"         # visible to all org members


@dataclass
class ReportColumn:
    """
    Defines a single column in a metadata-driven report.

    field_key maps to the source field/expression.
    display_label is the user-facing column header.
    """
    id: str
    field_key: str
    display_label: str
    data_type: ColumnDataType = ColumnDataType.TEXT
    sortable: bool = True
    visible: bool = True
    width_hint: int = 150        # display width hint in pixels
    grouping_fn: GroupingFunction = GroupingFunction.NONE
    format_pattern: str = ""     # e.g. "0.00", "YYYY-MM-DD"
    sort_direction: Optional[SortDirection] = None
    sort_priority: int = 0       # lower = higher sort priority when multi-sort

    @staticmethod
    def create(
        field_key: str,
        display_label: str,
        data_type: ColumnDataType = ColumnDataType.TEXT,
        **kwargs: Any,
    ) -> "ReportColumn":
        return ReportColumn(id=generate_id(), field_key=field_key, display_label=display_label, data_type=data_type, **kwargs)


@dataclass
class ReportFilter:
    """
    A single filter criterion in a metadata-driven report.

    value and value_end hold the filter operands (value_end used for BETWEEN).
    """
    id: str
    field_key: str
    operator: FilterOperator
    value: Any = None
    value_end: Any = None       # second bound for BETWEEN
    display_label: str = ""
    is_required: bool = False   # required filters must be supplied at run time

    @staticmethod
    def create(
        field_key: str,
        operator: FilterOperator,
        value: Any = None,
        **kwargs: Any,
    ) -> "ReportFilter":
        return ReportFilter(id=generate_id(), field_key=field_key, operator=operator, value=value, **kwargs)


@dataclass
class ReportGrouping:
    """
    Defines how report rows are grouped.

    Multiple groupings compose a hierarchy (sort by priority).
    """
    id: str
    field_key: str
    display_label: str
    priority: int = 0           # lower = outer group
    collapsed_by_default: bool = False
    subtotal_row: bool = True

    @staticmethod
    def create(field_key: str, display_label: str, **kwargs: Any) -> "ReportGrouping":
        return ReportGrouping(id=generate_id(), field_key=field_key, display_label=display_label, **kwargs)


@dataclass
class ReportDefinition:
    """
    Metadata-driven report definition.

    Describes the report structure without baking in a specific data source or format.
    Application services use this to build queries and render output.

    Supports:
    - configurable columns (order, visibility, type, format)
    - multi-level groupings with subtotals
    - composable filters
    - sort order
    - role-aware visibility
    - saved-view variants via SavedReportView
    """
    id: str
    report_key: str             # machine identifier e.g. "pm.task_status_report"
    display_name: str
    description: str = ""
    module_code: str = "project_management"
    permission_code: str = "report.view"
    visibility: ReportVisibility = ReportVisibility.PRIVATE
    owner_id: Optional[str] = None
    columns: List[ReportColumn] = field(default_factory=list)
    filters: List[ReportFilter] = field(default_factory=list)
    groupings: List[ReportGrouping] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1

    @staticmethod
    def create(
        report_key: str,
        display_name: str,
        description: str = "",
        module_code: str = "project_management",
        permission_code: str = "report.view",
        visibility: ReportVisibility = ReportVisibility.PRIVATE,
        owner_id: Optional[str] = None,
    ) -> "ReportDefinition":
        now = datetime.utcnow()
        return ReportDefinition(
            id=generate_id(),
            report_key=report_key,
            display_name=display_name,
            description=description,
            module_code=module_code,
            permission_code=permission_code,
            visibility=visibility,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
        )

    def add_column(self, column: ReportColumn) -> "ReportDefinition":
        self.columns.append(column)
        return self

    def add_filter(self, report_filter: ReportFilter) -> "ReportDefinition":
        self.filters.append(report_filter)
        return self

    def add_grouping(self, grouping: ReportGrouping) -> "ReportDefinition":
        self.groupings.append(grouping)
        return self

    @property
    def visible_columns(self) -> List[ReportColumn]:
        return [c for c in self.columns if c.visible]

    @property
    def required_filters(self) -> List[ReportFilter]:
        return [f for f in self.filters if f.is_required]


@dataclass
class SavedReportView:
    """
    A named snapshot of a ReportDefinition with a specific column/filter/grouping state.

    Users can save their current view configuration as a named view and restore it later.
    The base ReportDefinition is unchanged; this stores the override state.
    """
    id: str
    report_definition_id: str
    name: str
    owner_id: str
    visibility: ReportVisibility = ReportVisibility.PRIVATE
    column_overrides: List[ReportColumn] = field(default_factory=list)   # ordered visible columns
    filter_overrides: List[ReportFilter] = field(default_factory=list)
    grouping_overrides: List[ReportGrouping] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1

    @staticmethod
    def create(
        report_definition_id: str,
        name: str,
        owner_id: str,
        visibility: ReportVisibility = ReportVisibility.PRIVATE,
    ) -> "SavedReportView":
        now = datetime.utcnow()
        return SavedReportView(
            id=generate_id(),
            report_definition_id=report_definition_id,
            name=name,
            owner_id=owner_id,
            visibility=visibility,
            created_at=now,
            updated_at=now,
        )


__all__ = [
    "ColumnDataType",
    "FilterOperator",
    "GroupingFunction",
    "ReportColumn",
    "ReportDefinition",
    "ReportFilter",
    "ReportGrouping",
    "ReportVisibility",
    "SavedReportView",
    "SortDirection",
]
