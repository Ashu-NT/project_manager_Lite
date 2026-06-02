"""Unit tests for MSProjectXmlParser and P6Parser — no DB, no Qt."""
from __future__ import annotations

import textwrap

import pytest

from src.core.modules.project_management.infrastructure.importers.import_parser import (
    ImportFieldMapping,
    ImportMappingProfile,
    MSProjectXmlParser,
    P6Parser,
)


# ── MS Project XML ────────────────────────────────────────────────────────────

_MSP_NS = "http://schemas.microsoft.com/project"

_MSP_XML = textwrap.dedent(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="{_MSP_NS}">
  <Tasks>
    <Task>
      <UID>0</UID>
      <ID>0</ID>
      <Name>Project Summary</Name>
      <IsNull>0</IsNull>
      <Summary>1</Summary>
    </Task>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Design Phase</Name>
      <IsNull>0</IsNull>
      <Duration>PT40H0M0S</Duration>
      <Start>2026-06-01T08:00:00</Start>
      <Finish>2026-06-05T17:00:00</Finish>
      <PercentComplete>50</PercentComplete>
      <Priority>500</Priority>
      <OutlineLevel>1</OutlineLevel>
      <OutlineNumber>1</OutlineNumber>
      <Summary>0</Summary>
    </Task>
    <Task>
      <UID>2</UID>
      <ID>2</ID>
      <Name>Development</Name>
      <IsNull>0</IsNull>
      <Duration>PT80H0M0S</Duration>
      <Start>2026-06-08T08:00:00</Start>
      <Finish>2026-06-19T17:00:00</Finish>
      <PercentComplete>0</PercentComplete>
      <Priority>500</Priority>
      <OutlineLevel>1</OutlineLevel>
      <OutlineNumber>2</OutlineNumber>
      <Summary>0</Summary>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>0</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>3</UID>
      <ID>3</ID>
      <Name>Deleted Task</Name>
      <IsNull>1</IsNull>
    </Task>
  </Tasks>
</Project>
""")

_MSP_INVALID_XML = "not xml at all <<<"


@pytest.fixture
def msp_parser():
    return MSProjectXmlParser()


class TestMSProjectXmlParserParse:
    def test_returns_two_rows_skips_uid0_and_null(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        assert len(rows) == 2

    def test_row_numbers_are_sequential(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        assert [r.row_number for r in rows] == [1, 2]

    def test_source_data_contains_raw_xml_values(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        assert rows[0].source_data["Name"] == "Design Phase"
        assert rows[0].source_data["UID"] == "1"

    def test_default_mapping_lowercases_fields(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        assert rows[0].mapped_data["name"] == "Design Phase"
        assert rows[0].mapped_data["start_date"] == "2026-06-01T08:00:00"
        assert rows[0].mapped_data["percent_complete"] == "50"

    def test_predecessor_link_serialised(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        dev_row = rows[1]
        # source_data preserves original XML casing; mapped_data lowercases it
        assert "Predecessors" in dev_row.source_data
        assert dev_row.source_data["Predecessors"] == "1:0:0"
        assert dev_row.mapped_data["predecessors"] == "1:0:0"

    def test_no_predecessor_on_first_task(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML)
        assert "predecessors" not in rows[0].source_data

    def test_parses_bytes_input(self, msp_parser):
        rows = msp_parser.parse(_MSP_XML.encode("utf-8"))
        assert len(rows) == 2

    def test_empty_tasks_element_returns_empty(self, msp_parser):
        xml = f'<Project xmlns="{_MSP_NS}"><Tasks></Tasks></Project>'
        assert msp_parser.parse(xml) == []

    def test_invalid_xml_raises_value_error(self, msp_parser):
        with pytest.raises(ValueError, match="parse error"):
            msp_parser.parse(_MSP_INVALID_XML)

    def test_custom_mapping_profile_applied(self, msp_parser):
        profile = ImportMappingProfile.create("custom", "ms_project_xml")
        profile.field_mappings.append(
            ImportFieldMapping(source_field="Name", target_field="task_name")
        )
        profile.field_mappings.append(
            ImportFieldMapping(source_field="UID", target_field="external_id")
        )
        rows = msp_parser.parse(_MSP_XML, mapping=profile)
        assert rows[0].mapped_data["task_name"] == "Design Phase"
        assert rows[0].mapped_data["external_id"] == "1"
        # un-mapped fields are NOT present when a profile is provided
        assert "name" not in rows[0].mapped_data


class TestMSProjectXmlParserDetectHeaders:
    def test_returns_fields_from_first_task(self, msp_parser):
        headers = msp_parser.detect_headers(_MSP_XML)
        assert "Name" in headers
        assert "UID" in headers
        # PredecessorLink elements should not appear directly
        assert "PredecessorLink" not in headers

    def test_invalid_xml_falls_back_to_defaults(self, msp_parser):
        headers = msp_parser.detect_headers(_MSP_INVALID_XML)
        assert "Name" in headers


# ── P6 XER ───────────────────────────────────────────────────────────────────

_P6_XER = textwrap.dedent("""\
ERMHDR\t19.12\t2026-05-27\tProject\tadmin\tadmin\t25\tC

%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name
%R\tPRJ-001\tMYPROJ\tMy Project
%E

%T\tTASK
%F\ttask_id\tproj_id\ttask_code\ttask_name\ttask_type\tstatus_code\tstart_date\tend_date\tphys_complete_pct\tremain_drtn_hr_cnt
%R\tTSK-001\tPRJ-001\tA1000\tDesign Phase\tTT_Task\tTK_NotStart\t2026-06-01 08:00\t2026-06-05 17:00\t0\t40
%R\tTSK-002\tPRJ-001\tA1010\tDevelopment\tTT_Task\tTK_NotStart\t2026-06-08 08:00\t2026-06-19 17:00\t0\t80
%E

%T\tTASKPRED
%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt
%R\tTPRED-001\tTSK-002\tTSK-001\tPR_FS\t0
%E
""")

_P6_XER_EMPTY_TASK = textwrap.dedent("""\
%T\tTASK
%F\ttask_id\ttask_name
%E
""")


@pytest.fixture
def p6_parser():
    return P6Parser()


class TestP6ParserParse:
    def test_returns_two_task_rows(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        assert len(rows) == 2

    def test_row_numbers_sequential(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        assert [r.row_number for r in rows] == [1, 2]

    def test_source_data_fields(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        assert rows[0].source_data["task_name"] == "Design Phase"
        assert rows[0].source_data["task_code"] == "A1000"
        assert rows[0].source_data["start_date"] == "2026-06-01 08:00"

    def test_predecessor_appended_to_successor(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        dev_row = rows[1]
        assert "predecessors" in dev_row.source_data
        assert "TSK-001:PR_FS:0" in dev_row.source_data["predecessors"]

    def test_no_predecessor_on_first_task(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        assert "predecessors" not in rows[0].source_data

    def test_parses_bytes_with_latin1(self, p6_parser):
        rows = p6_parser.parse(_P6_XER.encode("latin-1"))
        assert len(rows) == 2

    def test_empty_task_table_returns_empty(self, p6_parser):
        assert p6_parser.parse(_P6_XER_EMPTY_TASK) == []

    def test_default_mapping_passes_through_fields(self, p6_parser):
        rows = p6_parser.parse(_P6_XER)
        # with no mapping, mapped_data mirrors source_data
        assert rows[0].mapped_data["task_name"] == "Design Phase"

    def test_custom_mapping_profile(self, p6_parser):
        profile = ImportMappingProfile.create("p6 custom", "p6_xer")
        profile.field_mappings.append(
            ImportFieldMapping(source_field="task_name", target_field="name")
        )
        profile.field_mappings.append(
            ImportFieldMapping(source_field="task_code", target_field="wbs_code")
        )
        rows = p6_parser.parse(_P6_XER, mapping=profile)
        assert rows[0].mapped_data["name"] == "Design Phase"
        assert rows[0].mapped_data["wbs_code"] == "A1000"
        assert "task_name" not in rows[0].mapped_data


class TestP6ParserDetectHeaders:
    def test_returns_task_columns(self, p6_parser):
        headers = p6_parser.detect_headers(_P6_XER)
        assert "task_id" in headers
        assert "task_name" in headers
        assert "start_date" in headers

    def test_empty_xer_returns_canonical_defaults(self, p6_parser):
        headers = p6_parser.detect_headers("")
        assert "task_id" in headers
