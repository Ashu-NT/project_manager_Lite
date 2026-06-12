from __future__ import annotations


def empty_calendar_detail_context() -> dict[str, object]:
    return {
        "workingRules": [],
        "exceptions": [],
        "recurringEvents": [],
        "assignments": {
            "sites": [],
            "departments": [],
            "employees": [],
            "projects": [],
            "resources": [],
        },
    }


def empty_calendar_assignment_context() -> dict[str, object]:
    return {
        "assignedCalendar": {},
        "sourceChain": [],
    }


__all__ = ["empty_calendar_assignment_context", "empty_calendar_detail_context"]
