"""Oracle Primavera P6 XER parser."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.modules.project_management.infrastructure.importers.models.import_models import (
    ImportMappingProfile,
    ImportParser,
    ImportRow,
)


class P6Parser(ImportParser):
    """
    Oracle Primavera P6 XER parser.

    XER is a tab-delimited, multi-table text export. Each section is delimited
    by header markers::

        %T  <TABLE_NAME>
        %F  <col1>\\t<col2>\\t...
        %R  <val1>\\t<val2>\\t...
        %E

    This parser extracts the TASK table and returns one ImportRow per activity.
    TASKPRED rows are collected and appended as a ``predecessors`` field
    (``<pred_task_id>:<link_type>:<lag_hr>`` tokens, semicolon-separated)
    on the matching TASK row.
    """

    @property
    def source_format(self) -> str:
        return "p6_xer"

    @property
    def display_name(self) -> str:
        return "Oracle Primavera P6 (XER)"

    def parse(
        self,
        source: bytes | str,
        mapping: Optional[ImportMappingProfile] = None,
    ) -> List[ImportRow]:
        text = source.decode("latin-1") if isinstance(source, bytes) else source
        tables = self._parse_xer_tables(text)

        task_rows = tables.get("TASK", [])
        pred_rows = tables.get("TASKPRED", [])

        pred_map: Dict[str, List[str]] = {}
        for pr in pred_rows:
            tid = pr.get("task_id", "")
            pred_id = pr.get("pred_task_id", "")
            link_type = pr.get("pred_type", "PR_FS")
            lag = pr.get("lag_hr_cnt", "0")
            if tid:
                pred_map.setdefault(tid, []).append(f"{pred_id}:{link_type}:{lag}")

        rows: List[ImportRow] = []
        for i, record in enumerate(task_rows, start=1):
            source_data = dict(record)
            task_id = source_data.get("task_id", "")
            if task_id in pred_map:
                source_data["predecessors"] = ";".join(pred_map[task_id])
            mapped = self._apply_mapping(source_data, mapping)
            rows.append(ImportRow(row_number=i, source_data=source_data, mapped_data=mapped))

        return rows

    def detect_headers(self, source: bytes | str) -> List[str]:
        text = source.decode("latin-1") if isinstance(source, bytes) else source
        tables = self._parse_xer_tables(text)
        task_rows = tables.get("TASK", [])
        if task_rows:
            return list(task_rows[0].keys())
        return [
            "task_id", "proj_id", "task_code", "task_name", "task_type",
            "status_code", "start_date", "end_date", "target_start_date",
            "target_end_date", "act_start_date", "act_end_date",
            "phys_complete_pct", "remain_drtn_hr_cnt",
        ]

    @staticmethod
    def _parse_xer_tables(text: str) -> Dict[str, List[Dict[str, str]]]:
        tables: Dict[str, List[Dict[str, str]]] = {}
        current_table: Optional[str] = None
        current_headers: List[str] = []

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\r")
            if not line:
                continue

            if line.startswith("%T"):
                current_table = line[2:].strip()
                current_headers = []
                tables[current_table] = []
            elif line.startswith("%F"):
                current_headers = line[2:].strip().split("\t")
            elif line.startswith("%R") and current_table and current_headers:
                values = line[2:].strip().split("\t")
                while len(values) < len(current_headers):
                    values.append("")
                row = dict(zip(current_headers, values[: len(current_headers)]))
                tables[current_table].append(row)
            elif line.startswith("%E"):
                current_table = None
                current_headers = []

        return tables

    def _apply_mapping(
        self,
        source_data: Dict[str, Any],
        mapping: Optional[ImportMappingProfile],
    ) -> Dict[str, Any]:
        if mapping is None:
            return dict(source_data)
        result: Dict[str, Any] = {}
        for fm in mapping.field_mappings:
            result[fm.target_field] = source_data.get(fm.source_field, fm.default_value)
        return result


__all__ = ["P6Parser"]
