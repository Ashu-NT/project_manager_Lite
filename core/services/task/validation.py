from __future__ import annotations

from datetime import date, timedelta

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError


class TaskValidationMixin:
    def _validate_dates(self, start_date, end_date, duration_days):
        if start_date and end_date and end_date < start_date:
            raise ValidationError("Task deadline cannot be before start_date.")

        if duration_days is not None and duration_days < 0:
            raise ValidationError("Task duration_days cannot be negative.")

    def _validate_task_within_project_dates(
        self, project_id: str, task_start: date | None, task_end: date | None
    ):
        if self._project_repo is None:
            return
        proj = self._project_repo.get(project_id)
        if not proj:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        ps = getattr(proj, "start_date", None)
        pe = getattr(proj, "end_date", None)

        if ps and task_start and task_start < ps:
            raise ValidationError(
                f"Task start date ({task_start}) can not be before project start ({ps})",
                code="TASK_INVALID_DATE",
            )
        if pe and task_start and task_start > pe:
            raise ValidationError(
                f"Task start date ({task_start}) can not be after project end ({pe})",
                code="TASK_INVALID_DATE",
            )
        if ps and task_end and task_end < ps:
            raise ValidationError(
                f"Task end date ({task_end}) can not be before project start ({ps})",
                code="TASK_INVALID_DATE",
            )
        if pe and task_end and task_end > pe:
            raise ValidationError(
                f"Task end date ({task_end}) can not be after project end ({pe})",
                code="TASK_INVALID_DATE",
            )

    def _validate_not_self_dependency(self, predecessor_id: str, successor_id: str):
        if predecessor_id == successor_id:
            raise ValidationError("A task cannot depend on itself.")

    def _validate_task_name(self, name: str) -> None:
        if not name.strip():
            raise ValidationError("Task name cannot be empty.", code="TASK_NAME_EMPTY")
        if len(name.strip()) < 3:
            raise ValidationError(
                "Task name must be at least 3 characters.", code="TASK_NAME_TOO_SHORT"
            )
        if any(c in name for c in ["/", "\\", "?", "%", "*", ":", "|", '"', "<", ">"]):
            raise ValidationError(
                "Task name contains invalid characters.", code="TASK_NAME_INVALID_CHARS"
            )

    def _check_no_circular_dependency(
        self, project_id: str, predecessor_id: str, successor_id: str
    ) -> None:
        deps = self._dependency_repo.list_by_project(project_id)
        project_task = {t.id for t in self._task_repo.list_by_project(project_id)}
        deps = [
            d
            for d in deps
            if d.predecessor_task_id in project_task and d.successor_task_id in project_task
        ]

        graph: dict[str, list[str]] = {}
        for d in deps:
            graph.setdefault(d.predecessor_task_id, []).append(d.successor_task_id)
        graph.setdefault(predecessor_id, []).append(successor_id)

        target = predecessor_id
        stack = [successor_id]
        visited = set()

        while stack:
            cur = stack.pop()
            if cur == target:
                raise BusinessRuleError(
                    "Adding this dependency would create a circular dependency.",
                    code="DEPENDENCY_CYCLE",
                )
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in graph.get(cur, []):
                if nxt not in visited:
                    stack.append(nxt)

    def _iter_workdays(self, start: date, end: date):
        if not start or not end:
            return
        if end < start:
            start, end = end, start
        cur = start
        while cur <= end:
            if cur.weekday() < 5:
                yield cur
            cur += timedelta(days=1)

    def _check_resource_overallocation(
        self,
        project_id: str,
        resource_id: str,
        new_task_id: str,
        new_alloc_percent: float,
    ) -> None:
        new_task = self._task_repo.get(new_task_id)
        if not new_task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        ns = getattr(new_task, "start_date", None)
        ne = getattr(new_task, "end_date", None)
        if not ns or not ne:
            return

        assigns = self._assignment_repo.list_by_resource(resource_id)
        if not assigns:
            return

        daily_total: dict[date, float] = {}
        daily_tasks: dict[date, list[str]] = {}

        for a in assigns:
            t = self._task_repo.get(a.task_id)
            if not t or getattr(t, "project_id", None) != project_id:
                continue

            ts = getattr(t, "start_date", None)
            te = getattr(t, "end_date", None)
            if not ts or not te:
                continue

            os = max(ns, ts)
            oe = min(ne, te)
            if oe < os:
                continue

            alloc = float(getattr(a, "allocation_percent", 0.0) or 0.0)
            if alloc <= 0:
                continue

            for d in self._iter_workdays(os, oe):
                daily_total[d] = daily_total.get(d, 0.0) + alloc
                daily_tasks.setdefault(d, []).append(getattr(t, "name", a.task_id))

        for d in self._iter_workdays(ns, ne):
            daily_total[d] = daily_total.get(d, 0.0) + float(new_alloc_percent or 0.0)
            daily_tasks.setdefault(d, []).append(getattr(new_task, "name", new_task_id))

        for d in sorted(daily_total.keys()):
            tot = daily_total[d]
            if tot > 100.0 + 1e-9:
                tasks = daily_tasks.get(d, [])[:6]
                extra = "..." if len(daily_tasks.get(d, [])) > 6 else ""
                msg = (
                    f"Resource would be over-allocated on {d.isoformat()} "
                    f"({tot:.1f}% > 100%).\n"
                    f"Tasks: {', '.join(tasks)}{extra}"
                )
                raise BusinessRuleError(msg, code="RESOURCE_OVERALLOCATED")
