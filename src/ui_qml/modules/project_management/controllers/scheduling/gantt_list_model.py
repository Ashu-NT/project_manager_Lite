"""Compact indexed Qt model for the complete disposable Gantt projection."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    Property,
    Qt,
    Signal,
    Slot,
)

from src.core.modules.project_management.api.desktop.scheduling.models import (
    GanttBaselineOverlayDto,
    GanttBaselineTaskSnapshotDto,
    GanttDependencyEdgeDto,
    GanttProjectionDto,
    GanttTaskRowDto,
)


class GanttListModel(QAbstractListModel):
    TaskIdRole = Qt.UserRole + 1
    RowDataRole = Qt.UserRole + 2
    CodeRole = Qt.UserRole + 3
    NameRole = Qt.UserRole + 4
    WbsCodeRole = Qt.UserRole + 5
    ParentTaskIdRole = Qt.UserRole + 6
    DepthRole = Qt.UserRole + 7
    IsSummaryRole = Qt.UserRole + 8
    ChildCountRole = Qt.UserRole + 9
    IsExpandedRole = Qt.UserRole + 10
    StartDayRole = Qt.UserRole + 11
    FinishDayRole = Qt.UserRole + 12
    IsMilestoneRole = Qt.UserRole + 13
    IsCriticalRole = Qt.UserRole + 14
    IsInfeasibleRole = Qt.UserRole + 15
    ProgressRole = Qt.UserRole + 16
    StatusRole = Qt.UserRole + 17
    BaselineDataRole = Qt.UserRole + 18

    rowCountChanged = Signal()
    projectionChanged = Signal()
    hierarchyModeChanged = Signal()
    baselineOverlayChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._projection: GanttProjectionDto | None = None
        self._all_rows: tuple[GanttTaskRowDto, ...] = ()
        self._effective_rows: tuple[GanttTaskRowDto, ...] = ()
        self._row_by_task_id: dict[str, GanttTaskRowDto] = {}
        self._effective_index_by_task_id: dict[str, int] = {}
        self._edge_by_id: dict[str, GanttDependencyEdgeDto] = {}
        self._edge_ids_by_task_id: dict[str, tuple[str, ...]] = {}
        self._baseline_id = ""
        self._baseline_by_task_id: dict[str, GanttBaselineTaskSnapshotDto] = {}
        self._baseline_orphan_count = 0
        self._timeline_start_day = -1
        self._timeline_finish_day = -1
        self._expanded_summary_ids: set[str] = set()
        self._search_text = ""
        self._status_filter = "all"
        self._critical_only = False
        self._delayed_only = False
        self._sort_key = "schedule"
        self._sort_descending = False
        self._hierarchy_mode = True

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.TaskIdRole: QByteArray(b"taskId"),
            self.RowDataRole: QByteArray(b"rowData"),
            self.CodeRole: QByteArray(b"code"),
            self.NameRole: QByteArray(b"name"),
            self.WbsCodeRole: QByteArray(b"wbsCode"),
            self.ParentTaskIdRole: QByteArray(b"parentTaskId"),
            self.DepthRole: QByteArray(b"depth"),
            self.IsSummaryRole: QByteArray(b"isSummary"),
            self.ChildCountRole: QByteArray(b"childCount"),
            self.IsExpandedRole: QByteArray(b"isExpanded"),
            self.StartDayRole: QByteArray(b"startDayOrdinal"),
            self.FinishDayRole: QByteArray(b"finishDayOrdinal"),
            self.IsMilestoneRole: QByteArray(b"isMilestone"),
            self.IsCriticalRole: QByteArray(b"isCritical"),
            self.IsInfeasibleRole: QByteArray(b"isInfeasible"),
            self.ProgressRole: QByteArray(b"percentComplete"),
            self.StatusRole: QByteArray(b"status"),
            self.BaselineDataRole: QByteArray(b"baselineData"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else len(self._effective_rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # type: ignore[override]
        if not index.isValid() or not 0 <= index.row() < len(self._effective_rows):
            return None
        row = self._effective_rows[index.row()]
        if role == self.TaskIdRole:
            return row.task_id
        if role == self.RowDataRole:
            return self.serialize_row(row)
        if role == self.CodeRole:
            return row.code
        if role in (self.NameRole, Qt.DisplayRole):
            return row.name
        if role == self.WbsCodeRole:
            return row.wbs_code
        if role == self.ParentTaskIdRole:
            return row.parent_task_id or ""
        if role == self.DepthRole:
            return row.depth if self._hierarchy_mode else 0
        if role == self.IsSummaryRole:
            return row.is_summary
        if role == self.ChildCountRole:
            return row.child_count
        if role == self.IsExpandedRole:
            return row.task_id in self._expanded_summary_ids
        if role == self.StartDayRole:
            return row.start_day_ordinal
        if role == self.FinishDayRole:
            return row.finish_day_ordinal
        if role == self.IsMilestoneRole:
            return row.is_milestone
        if role == self.IsCriticalRole:
            return row.is_critical
        if role == self.IsInfeasibleRole:
            return row.is_infeasible
        if role == self.ProgressRole:
            return row.percent_complete
        if role == self.StatusRole:
            return row.status
        if role == self.BaselineDataRole:
            snapshot = None if row.is_summary else self._baseline_by_task_id.get(row.task_id)
            return self.serialize_baseline(snapshot)
        return None

    @Property(int, notify=rowCountChanged)
    def rowCountValue(self) -> int:
        return len(self._effective_rows)

    @Property(bool, notify=hierarchyModeChanged)
    def hierarchyMode(self) -> bool:
        return self._hierarchy_mode

    @Property(str, notify=projectionChanged)
    def projectId(self) -> str:
        return self._projection.project_id if self._projection else ""

    @Property(str, notify=projectionChanged)
    def scheduleAuthority(self) -> str:
        return self._projection.schedule_authority if self._projection else ""

    @Property(int, notify=projectionChanged)
    def timelineStartDay(self) -> int:
        return self._timeline_start_day

    @Property(int, notify=projectionChanged)
    def timelineFinishDay(self) -> int:
        return self._timeline_finish_day

    @Property("QVariantList", notify=projectionChanged)
    def criticalAttentionRows(self) -> list[dict[str, object]]:
        return [
            self.serialize_row(row)
            for row in self._all_rows
            if not row.is_summary and (row.is_critical or row.is_infeasible)
        ]

    @Property(str, notify=baselineOverlayChanged)
    def selectedBaselineId(self) -> str:
        return self._baseline_id

    @Property(int, notify=baselineOverlayChanged)
    def baselineTaskCount(self) -> int:
        return len(self._baseline_by_task_id)

    @Property(int, notify=baselineOverlayChanged)
    def baselineMatchedTaskCount(self) -> int:
        return len(self._baseline_by_task_id) - self._baseline_orphan_count

    @Property(int, notify=baselineOverlayChanged)
    def baselineOrphanTaskCount(self) -> int:
        return self._baseline_orphan_count

    @property
    def projection(self) -> GanttProjectionDto | None:
        return self._projection

    @property
    def all_rows(self) -> tuple[GanttTaskRowDto, ...]:
        return self._all_rows

    @property
    def effective_rows(self) -> tuple[GanttTaskRowDto, ...]:
        return self._effective_rows

    def set_projection(self, projection: GanttProjectionDto | None) -> None:
        self.beginResetModel()
        self._projection = projection
        self._all_rows = projection.rows if projection else ()
        self._row_by_task_id = {row.task_id: row for row in self._all_rows}
        self._edge_by_id = {
            edge.dependency_id: edge
            for edge in (projection.dependency_edges if projection else ())
        }
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in self._edge_by_id.values():
            adjacency[edge.predecessor_task_id].append(edge.dependency_id)
            adjacency[edge.successor_task_id].append(edge.dependency_id)
        self._edge_ids_by_task_id = {
            task_id: tuple(sorted(edge_ids))
            for task_id, edge_ids in adjacency.items()
        }
        self._baseline_by_task_id = {
            snapshot.task_id: snapshot
            for snapshot in (projection.baseline_snapshots if projection else ())
        }
        self._baseline_id = str(projection.selected_baseline_id or "") if projection else ""
        self._recount_baseline_matches()
        range_start = projection.range_start_day_ordinal if projection else None
        range_finish = projection.range_finish_day_ordinal if projection else None
        self._timeline_start_day = int(range_start) if range_start is not None else -1
        self._timeline_finish_day = int(range_finish) if range_finish is not None else -1
        self._expanded_summary_ids = {
            row.task_id
            for row in self._all_rows
            if row.is_summary and row.depth <= 1
        }
        self._effective_rows = self._build_effective_rows()
        self._rebuild_effective_index()
        self.endResetModel()
        self.rowCountChanged.emit()
        self.projectionChanged.emit()
        self.baselineOverlayChanged.emit()

    def set_baseline_overlay(self, overlay: GanttBaselineOverlayDto | None) -> None:
        if overlay is not None:
            projection = self._projection
            if projection is None or (
                overlay.tenant_id != projection.tenant_id
                or overlay.organization_id != projection.organization_id
                or overlay.project_id != projection.project_id
            ):
                raise ValueError("The Gantt baseline overlay belongs to another scope.")
        self._baseline_id = overlay.baseline_id if overlay else ""
        self._baseline_by_task_id = {
            snapshot.task_id: snapshot
            for snapshot in (overlay.snapshots if overlay else ())
        }
        self._recount_baseline_matches()
        if self._effective_rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._effective_rows) - 1, 0),
                [self.BaselineDataRole],
            )
        self.baselineOverlayChanged.emit()

    def apply_view(
        self,
        *,
        search_text: str,
        status_filter: str,
        critical_only: bool,
        delayed_only: bool,
        sort_key: str,
        sort_descending: bool,
    ) -> None:
        previous_hierarchy_mode = self._hierarchy_mode
        self._search_text = str(search_text or "").strip().casefold()
        self._status_filter = str(status_filter or "all").strip().casefold() or "all"
        self._critical_only = bool(critical_only)
        self._delayed_only = bool(delayed_only)
        self._sort_key = str(sort_key or "schedule").strip() or "schedule"
        self._sort_descending = bool(sort_descending)
        self._hierarchy_mode = self._sort_key in {"schedule", "wbs"}
        next_rows = self._build_effective_rows()
        if next_rows != self._effective_rows:
            self.beginResetModel()
            self._effective_rows = next_rows
            self._rebuild_effective_index()
            self.endResetModel()
            self.rowCountChanged.emit()
        if self._hierarchy_mode != previous_hierarchy_mode:
            self.hierarchyModeChanged.emit()

    def set_expanded(self, task_id: str, expanded: bool) -> None:
        row = self._row_by_task_id.get(str(task_id or "").strip())
        if row is None or not row.is_summary:
            return
        if expanded:
            self._expanded_summary_ids.add(row.task_id)
        else:
            self._expanded_summary_ids.discard(row.task_id)
        self.apply_view(
            search_text=self._search_text,
            status_filter=self._status_filter,
            critical_only=self._critical_only,
            delayed_only=self._delayed_only,
            sort_key=self._sort_key,
            sort_descending=self._sort_descending,
        )

    def row_for_task(self, task_id: str) -> GanttTaskRowDto | None:
        return self._row_by_task_id.get(str(task_id or "").strip())

    @Slot(str, result=int)
    def indexOfTask(self, task_id: str) -> int:
        return self._effective_index_by_task_id.get(str(task_id or "").strip(), -1)

    @Slot(int, result=str)
    def taskIdAt(self, index: int) -> str:
        if 0 <= index < len(self._effective_rows):
            return self._effective_rows[index].task_id
        return ""

    @Slot(int, result=bool)
    def isSummaryAt(self, index: int) -> bool:
        return (
            0 <= index < len(self._effective_rows)
            and self._effective_rows[index].is_summary
        )

    @Slot(int, result=bool)
    def isExpandedAt(self, index: int) -> bool:
        return (
            0 <= index < len(self._effective_rows)
            and self._effective_rows[index].task_id in self._expanded_summary_ids
        )

    @Slot(int, result=str)
    def parentTaskIdAt(self, index: int) -> str:
        if 0 <= index < len(self._effective_rows):
            return str(self._effective_rows[index].parent_task_id or "")
        return ""

    def contains_effective_task(self, task_id: str) -> bool:
        normalized = str(task_id or "").strip()
        return normalized in self._effective_index_by_task_id

    def contains_filtered_task(self, task_id: str) -> bool:
        row = self.row_for_task(task_id)
        return row is not None and self._matches(row)

    def incident_edge_ids(self, task_id: str) -> tuple[str, ...]:
        return self._edge_ids_by_task_id.get(str(task_id or "").strip(), ())

    @Slot(int, int, str, int, result="QVariantMap")
    def dependencyWindow(
        self,
        first_index: int,
        last_index: int,
        selected_task_id: str,
        normal_edge_limit: int,
    ) -> dict[str, object]:
        """Return complete edges whose endpoints are in one bounded row window."""
        if not self._effective_rows:
            return _empty_dependency_window(self.projectId)
        first = max(0, int(first_index))
        last = min(len(self._effective_rows) - 1, int(last_index))
        if first > last:
            return _empty_dependency_window(self.projectId)

        row_indexes = {
            row.task_id: index
            for index, row in enumerate(self._effective_rows[first : last + 1], first)
        }
        candidate_ids: set[str] = set()
        for task_id in row_indexes:
            candidate_ids.update(self._edge_ids_by_task_id.get(task_id, ()))
        complete_ids = tuple(
            edge_id
            for edge_id in sorted(candidate_ids)
            if (
                (edge := self._edge_by_id.get(edge_id)) is not None
                and edge.predecessor_task_id in row_indexes
                and edge.successor_task_id in row_indexes
            )
        )
        positionable_ids = tuple(
            edge_id
            for edge_id in complete_ids
            if self._edge_has_positionable_endpoints(self._edge_by_id[edge_id])
        )
        limit = max(0, int(normal_edge_limit))
        suppressed = limit > 0 and len(positionable_ids) > limit
        normalized_selection = str(selected_task_id or "").strip()
        selected_ids = set(self._edge_ids_by_task_id.get(normalized_selection, ()))
        rendered_ids = (
            tuple(edge_id for edge_id in positionable_ids if edge_id in selected_ids)
            if suppressed
            else positionable_ids
        )
        edges = [
            self._serialize_dependency_edge(
                self._edge_by_id[edge_id],
                row_indexes=row_indexes,
                selected_edge_ids=selected_ids,
            )
            for edge_id in rendered_ids
        ]
        return {
            "projectId": self.projectId,
            "firstRowIndex": first,
            "lastRowIndex": last,
            "candidateEdgeCount": len(complete_ids),
            "unpositionedEdgeCount": len(complete_ids) - len(positionable_ids),
            "suppressed": suppressed,
            "edges": edges,
        }

    def _edge_has_positionable_endpoints(
        self, edge: GanttDependencyEdgeDto
    ) -> bool:
        predecessor = self._row_by_task_id[edge.predecessor_task_id]
        successor = self._row_by_task_id[edge.successor_task_id]
        return all(
            value is not None
            for value in (
                predecessor.start_day_ordinal,
                predecessor.finish_day_ordinal,
                successor.start_day_ordinal,
                successor.finish_day_ordinal,
            )
        )

    def baseline_for_task(self, task_id: str) -> GanttBaselineTaskSnapshotDto | None:
        return self._baseline_by_task_id.get(str(task_id or "").strip())

    def _recount_baseline_matches(self) -> None:
        current_ids = set(self._row_by_task_id)
        self._baseline_orphan_count = sum(
            task_id not in current_ids for task_id in self._baseline_by_task_id
        )

    def _serialize_dependency_edge(
        self,
        edge: GanttDependencyEdgeDto,
        *,
        row_indexes: dict[str, int],
        selected_edge_ids: set[str],
    ) -> dict[str, object]:
        predecessor = self._row_by_task_id[edge.predecessor_task_id]
        successor = self._row_by_task_id[edge.successor_task_id]
        return {
            "dependencyId": edge.dependency_id,
            "predecessorTaskId": edge.predecessor_task_id,
            "predecessorTaskName": edge.predecessor_task_name,
            "successorTaskId": edge.successor_task_id,
            "successorTaskName": edge.successor_task_name,
            "dependencyType": edge.dependency_type,
            "dependencyTypeLabel": edge.dependency_type_label,
            "lagDays": edge.lag_days,
            "predecessorRowIndex": row_indexes[edge.predecessor_task_id],
            "successorRowIndex": row_indexes[edge.successor_task_id],
            "predecessorStartDay": predecessor.start_day_ordinal,
            "predecessorFinishDay": predecessor.finish_day_ordinal,
            "successorStartDay": successor.start_day_ordinal,
            "successorFinishDay": successor.finish_day_ordinal,
            "predecessorIsCritical": predecessor.is_critical,
            "successorIsCritical": successor.is_critical,
            "predecessorIsInfeasible": predecessor.is_infeasible,
            "successorIsInfeasible": successor.is_infeasible,
            "predecessorIsMilestone": predecessor.is_milestone,
            "successorIsMilestone": successor.is_milestone,
            "selected": edge.dependency_id in selected_edge_ids,
        }

    def _rebuild_effective_index(self) -> None:
        self._effective_index_by_task_id = {
            row.task_id: index for index, row in enumerate(self._effective_rows)
        }

    def filtered_leaf_rows(self) -> tuple[GanttTaskRowDto, ...]:
        rows = tuple(row for row in self._all_rows if not row.is_summary and self._matches(row))
        if not self._hierarchy_mode:
            return self._sort_flat_rows(rows)
        return rows

    def _build_effective_rows(self) -> tuple[GanttTaskRowDto, ...]:
        matching = tuple(row for row in self._all_rows if self._matches(row))
        if not self._hierarchy_mode:
            return self._sort_flat_rows(matching)
        filtering = bool(
            self._search_text
            or self._status_filter != "all"
            or self._critical_only
            or self._delayed_only
        )
        if filtering:
            included_ids = {
                task_id
                for row in matching
                for task_id in (*row.ancestor_ids, row.task_id)
            }
            return tuple(row for row in self._all_rows if row.task_id in included_ids)
        return tuple(
            row
            for row in self._all_rows
            if all(
                ancestor_id in self._expanded_summary_ids
                for ancestor_id in row.ancestor_ids
            )
        )

    def _matches(self, row: GanttTaskRowDto) -> bool:
        if self._status_filter != "all" and row.status.casefold() != self._status_filter:
            return False
        if self._critical_only and not row.is_critical:
            return False
        if self._delayed_only and not ((row.late_by_days or 0) > 0):
            return False
        if not self._search_text:
            return True
        return any(
            self._search_text in value.casefold()
            for value in (row.task_id, row.code, row.name, row.wbs_code, row.description)
        )

    def _sort_flat_rows(
        self, rows: tuple[GanttTaskRowDto, ...]
    ) -> tuple[GanttTaskRowDto, ...]:
        populated = [row for row in rows if self._flat_sort_value(row) is not None]
        missing = [row for row in rows if self._flat_sort_value(row) is None]
        # Stable ID ordering keeps equal values deterministic in both directions.
        populated.sort(key=lambda row: row.task_id)
        populated.sort(
            key=self._flat_sort_value,
            reverse=self._sort_descending,
        )
        missing.sort(key=lambda row: row.task_id)
        return tuple((*populated, *missing))

    def _flat_sort_value(self, row: GanttTaskRowDto) -> object | None:
        accessors = {
            "taskName": row.name.casefold(),
            "start": row.start_date,
            "finish": row.finish_date,
            "duration": row.duration_days,
            "remainingDuration": row.remaining_duration_days,
            "float": row.total_float_days,
            "critical": row.is_critical,
            "constraint": row.constraint_type_label.casefold(),
            "progress": row.percent_complete,
            "status": row.status_label.casefold(),
        }
        return accessors.get(self._sort_key, row.wbs_code.casefold())

    @staticmethod
    def serialize_row(row: GanttTaskRowDto) -> dict[str, object]:
        return {
            "taskId": row.task_id,
            "code": row.code,
            "name": row.name,
            "description": row.description,
            "parentTaskId": row.parent_task_id or "",
            "wbsCode": row.wbs_code,
            "sortOrder": row.sort_order,
            "depth": row.depth,
            "isSummary": row.is_summary,
            "childCount": row.child_count,
            "ancestorIds": list(row.ancestor_ids),
            "startDate": _iso(row.start_date),
            "finishDate": _iso(row.finish_date),
            "startDayOrdinal": row.start_day_ordinal,
            "finishDayOrdinal": row.finish_day_ordinal,
            "latestStart": _iso(row.latest_start),
            "latestFinish": _iso(row.latest_finish),
            "durationDays": row.duration_days,
            "remainingDurationDays": row.remaining_duration_days,
            "status": row.status,
            "statusLabel": row.status_label,
            "percentComplete": row.percent_complete,
            "isMilestone": row.is_milestone,
            "isCritical": row.is_critical,
            "isInfeasible": row.is_infeasible,
            "totalFloatDays": row.total_float_days,
            "hasCanonicalSchedule": row.has_canonical_schedule,
            "constraintType": row.constraint_type,
            "constraintTypeLabel": row.constraint_type_label,
            "constraintDate": _iso(row.constraint_date),
            "actualStart": _iso(row.actual_start),
            "actualFinish": _iso(row.actual_finish),
            "actualStartDayOrdinal": row.actual_start_day_ordinal,
            "actualFinishDayOrdinal": row.actual_finish_day_ordinal,
            "deadline": _iso(row.deadline),
            "lateByDays": row.late_by_days,
            "priority": row.priority,
        }

    @staticmethod
    def serialize_baseline(
        snapshot: GanttBaselineTaskSnapshotDto | None,
    ) -> dict[str, object]:
        if snapshot is None:
            return {}
        return {
            "baselineId": snapshot.baseline_id,
            "taskId": snapshot.task_id,
            "startDate": _iso(snapshot.baseline_start),
            "finishDate": _iso(snapshot.baseline_finish),
            "startDayOrdinal": snapshot.baseline_start_day_ordinal,
            "finishDayOrdinal": snapshot.baseline_finish_day_ordinal,
            "durationDays": snapshot.baseline_duration_days,
            "isMilestone": snapshot.baseline_is_milestone,
        }


def _iso(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


def _empty_dependency_window(project_id: str) -> dict[str, object]:
    return {
        "projectId": project_id,
        "firstRowIndex": -1,
        "lastRowIndex": -1,
        "candidateEdgeCount": 0,
        "unpositionedEdgeCount": 0,
        "suppressed": False,
        "edges": [],
    }


__all__ = ["GanttListModel"]
