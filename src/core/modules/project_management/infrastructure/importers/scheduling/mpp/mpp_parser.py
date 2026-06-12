"""Microsoft Project XML (.mpp/.xml) parser."""

from __future__ import annotations

from typing import Any

from src.core.modules.project_management.infrastructure.importers.models.import_models import (
    ImportFieldMapping,
    ImportMappingProfile,
    ImportParser,
    ImportRow,
)

class MSProjectXmlParser(ImportParser):
    """
    Microsoft Project XML (.xml) parser.

    Reads the MS Project XML schema and maps Task elements into ImportRows.
    Null/deleted tasks (IsNull=1) and the project-summary row (UID=0) are
    silently skipped. Predecessor links are serialised as a semicolon-separated
    string in the ``predecessors`` mapped field.

    When no mapping profile is supplied the parser auto-maps the 17 canonical
    MS Project field names to lowercase PM domain keys.
    """

    _NS = "http://schemas.microsoft.com/project"

    _DEFAULT_MAP: dict[str, str] = {
        "UID": "uid",
        "ID": "id",
        "Name": "name",
        "Type": "task_type",
        "Duration": "duration",
        "Start": "start_date",
        "Finish": "end_date",
        "PercentComplete": "percent_complete",
        "Priority": "priority",
        "Summary": "is_summary",
        "OutlineLevel": "outline_level",
        "OutlineNumber": "outline_number",
        "ActualStart": "actual_start",
        "ActualFinish": "actual_end",
        "Deadline": "deadline",
        "Notes": "description",
        "Cost": "cost",
    }

    @property
    def source_format(self) -> str:
        return "ms_project_xml"

    @property
    def display_name(self) -> str:
        return "Microsoft Project XML"

    def parse(
        self,
        source: bytes | str,
        mapping: ImportMappingProfile | None = None,
    ) -> list[ImportRow]:
        import xml.etree.ElementTree as ET

        text = source if isinstance(source, str) else source.decode("utf-8-sig")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError(f"MS Project XML parse error: {exc}") from exc

        ns = {"p": self._NS}
        tasks_el = root.find("p:Tasks", ns)
        if tasks_el is None:
            return []

        rows: list[ImportRow] = []
        row_number = 0

        for task_el in tasks_el.findall("p:Task", ns):
            uid_text = (task_el.findtext("p:UID", default="", namespaces=ns) or "").strip()
            is_null = (task_el.findtext("p:IsNull", default="0", namespaces=ns) or "0").strip()

            if uid_text == "0" or is_null == "1":
                continue

            row_number += 1
            source_data: dict[str, Any] = {}

            for child in task_el:
                local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if local == "PredecessorLink":
                    continue
                source_data[local] = (child.text or "").strip()

            pred_tokens: list[str] = []
            for link in task_el.findall("p:PredecessorLink", ns):
                pred_uid = link.findtext("p:PredecessorUID", default="", namespaces=ns) or ""
                link_type = link.findtext("p:Type", default="0", namespaces=ns) or "0"
                lag = link.findtext("p:LinkLag", default="0", namespaces=ns) or "0"
                pred_tokens.append(f"{pred_uid.strip()}:{link_type.strip()}:{lag.strip()}")
            if pred_tokens:
                source_data["Predecessors"] = ";".join(pred_tokens)

            mapped = self._apply_mapping(source_data, mapping)
            rows.append(ImportRow(row_number=row_number, source_data=source_data, mapped_data=mapped))

        return rows

    def detect_headers(self, source: bytes | str) -> list[str]:
        import xml.etree.ElementTree as ET

        text = source if isinstance(source, str) else source.decode("utf-8-sig")
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return list(self._DEFAULT_MAP)

        ns = {"p": self._NS}
        tasks_el = root.find("p:Tasks", ns)
        if tasks_el is None:
            return list(self._DEFAULT_MAP)

        seen: list[str] = []
        for task_el in tasks_el.findall("p:Task", ns):
            for child in task_el:
                local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if local not in seen and local != "PredecessorLink":
                    seen.append(local)
            break
        return seen or list(self._DEFAULT_MAP)

    def _apply_mapping(
        self,
        source_data: dict[str, Any],
        mapping: ImportMappingProfile | None,
    ) -> dict[str, Any]:
        if mapping is not None:
            result: dict[str, Any] = {}
            for fm in mapping.field_mappings:
                result[fm.target_field] = source_data.get(fm.source_field, fm.default_value)
            return result
        result = {}
        for src_key, value in source_data.items():
            target = self._DEFAULT_MAP.get(src_key, src_key.lower())
            result[target] = value
        return result

__all__ = ["MSProjectXmlParser"]
