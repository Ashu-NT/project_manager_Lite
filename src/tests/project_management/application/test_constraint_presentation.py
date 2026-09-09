"""Phase L (R4.4 constraint pass): one canonical constraint-presentation
map, reused everywhere instead of the three independently-drifting
label treatments the audit found (title-cased, raw snake_case, and a
hand-written panel unrelated to the real enum).
"""
from __future__ import annotations

import pytest

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    CATEGORY_DATE_BOUNDARY,
    CATEGORY_FIXED_DATE,
    CATEGORY_FLEXIBLE,
    EDITABLE_CONSTRAINT_OPTIONS,
    constraint_presentation,
)
from src.core.modules.project_management.domain.enums import ConstraintType


def test_asap_is_the_first_editable_option_and_needs_no_date():
    asap = EDITABLE_CONSTRAINT_OPTIONS[0]
    assert asap.value is None
    assert asap.code == "ASAP"
    assert asap.label == "As Soon As Possible (ASAP)"
    assert asap.requires_date is False
    assert asap.category == CATEGORY_FLEXIBLE


def test_every_editable_option_except_asap_requires_a_date():
    for option in EDITABLE_CONSTRAINT_OPTIONS:
        if option.value is None:
            continue
        assert option.requires_date is True


def test_deadline_is_not_in_the_editable_options():
    assert all(option.value is not ConstraintType.DEADLINE for option in EDITABLE_CONSTRAINT_OPTIONS)


@pytest.mark.parametrize(
    "value,expected_code,expected_category",
    [
        (ConstraintType.START_NO_EARLIER_THAN, "SNET", CATEGORY_DATE_BOUNDARY),
        (ConstraintType.START_NO_LATER_THAN, "SNLT", CATEGORY_DATE_BOUNDARY),
        (ConstraintType.FINISH_NO_EARLIER_THAN, "FNET", CATEGORY_DATE_BOUNDARY),
        (ConstraintType.FINISH_NO_LATER_THAN, "FNLT", CATEGORY_DATE_BOUNDARY),
        (ConstraintType.MUST_START_ON, "MSO", CATEGORY_FIXED_DATE),
        (ConstraintType.MUST_FINISH_ON, "MFO", CATEGORY_FIXED_DATE),
    ],
)
def test_constraint_presentation_resolves_canonical_code_and_category(value, expected_code, expected_category):
    presentation = constraint_presentation(value)
    assert presentation.code == expected_code
    assert presentation.category == expected_category
    assert f"({expected_code})" in presentation.label


def test_constraint_presentation_accepts_a_raw_string_value():
    presentation = constraint_presentation("must_start_on")
    assert presentation.value is ConstraintType.MUST_START_ON
    assert presentation.code == "MSO"


def test_constraint_presentation_of_none_is_asap():
    assert constraint_presentation(None).code == "ASAP"


def test_deadline_has_a_presentation_for_rendering_a_violation_but_is_not_editable():
    presentation = constraint_presentation(ConstraintType.DEADLINE)
    assert presentation.label == "Deadline"
    assert presentation not in EDITABLE_CONSTRAINT_OPTIONS
