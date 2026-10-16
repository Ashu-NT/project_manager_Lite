from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.projects.import_preview import (
    execute_import,
    preview_import,
)
from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.application.projects.dto.responses.import_preview import (ImportPreviewModel, ImportValidationIssue, ImportValidationSeverity)
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConfigurationError,
    DomainError,
    NotFoundError,
    UnsupportedOperationError,
    ValidationError,
)


@pytest.mark.parametrize(
    "method,argument,code",
    [
        (
            "add_project_resource",
            SimpleNamespace(project_id=" ", resource_id="r"),
            "PROJECT_ID_REQUIRED",
        ),
        (
            "add_project_resource",
            SimpleNamespace(project_id="p", resource_id=" "),
            "RESOURCE_ID_REQUIRED",
        ),
        (
            "update_project_resource",
            SimpleNamespace(project_resource_id=" "),
            "PROJECT_RESOURCE_ID_REQUIRED",
        ),
        ("remove_project_resource", " ", "PROJECT_RESOURCE_ID_REQUIRED"),
    ],
)
def test_project_input_errors(method, argument, code):
    api = ProjectManagementProjectsDesktopApi()
    with pytest.raises(ValidationError) as caught:
        getattr(api, method)(argument)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "method",
    ["recalculate_schedule", "build_gantt_projection", "apply_resource_leveling"],
)
def test_scheduling_requires_project(method):
    with pytest.raises(ValidationError) as caught:
        getattr(ProjectManagementSchedulingDesktopApi(), method)(" ")
    assert caught.value.code == "PROJECT_ID_REQUIRED"


def test_baseline_selection_and_leveling_prerequisite_are_distinct():
    api = ProjectManagementSchedulingDesktopApi()
    for project, baseline, code in [
        ("", "b", "PROJECT_ID_REQUIRED"),
        ("p", "", "BASELINE_ID_REQUIRED"),
    ]:
        with pytest.raises(ValidationError) as caught:
            api.build_gantt_baseline_overlay(project, baseline)
        assert caught.value.code == code
    with pytest.raises(BusinessRuleError) as caught:
        api.apply_resource_leveling("p")
    assert caught.value.code == "LEVELING_PREVIEW_REQUIRED"


@pytest.mark.parametrize(
    "method,argument,code",
    [
        ("mark_task_mentions_read", " ", "TASK_ID_REQUIRED"),
        ("touch_task_presence", " ", "TASK_ID_REQUIRED"),
        ("clear_task_presence", " ", "TASK_ID_REQUIRED"),
        ("post_task_comment", SimpleNamespace(task_id=" "), "TASK_ID_REQUIRED"),
        ("edit_task_comment", SimpleNamespace(comment_id=" "), "COMMENT_ID_REQUIRED"),
        ("delete_task_comment", SimpleNamespace(comment_id=" "), "COMMENT_ID_REQUIRED"),
        (
            "react_to_task_comment",
            SimpleNamespace(comment_id=" "),
            "COMMENT_ID_REQUIRED",
        ),
        (
            "remove_task_comment_reaction",
            SimpleNamespace(comment_id=" "),
            "COMMENT_ID_REQUIRED",
        ),
    ],
)
def test_collaboration_input_errors(method, argument, code):
    with pytest.raises(ValidationError) as caught:
        getattr(ProjectManagementCollaborationDesktopApi(), method)(argument)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "operation",
    [
        lambda: ProjectManagementProjectsDesktopApi().delete_project("p"),
        lambda: ProjectManagementProjectsDesktopApi()._require_project_query(),
        lambda: (
            ProjectManagementProjectsDesktopApi()._require_project_resource_commands()
        ),
        lambda: ProjectManagementCollaborationDesktopApi().touch_task_presence("t"),
        lambda: ProjectManagementSchedulingDesktopApi()._require_gantt_project_scope(
            "p"
        ),
        lambda: ProjectManagementSchedulingDesktopApi()._require_scheduling_engine(),
        lambda: ProjectManagementSchedulingDesktopApi()._require_work_calendar_engine(),
        lambda: ProjectManagementSchedulingDesktopApi()._require_baseline_query(),
        lambda: ProjectManagementSchedulingDesktopApi()._require_baseline_commands(),
        lambda: (
            ProjectManagementSchedulingDesktopApi()._require_baseline_compare_report()
        ),
    ],
)
def test_missing_wiring_uses_configuration_error(operation):
    with pytest.raises(ConfigurationError) as caught:
        operation()
    assert caught.value.code == "CONFIGURATION_ERROR"
    assert not isinstance(caught.value, BusinessRuleError)
    result = execute_desktop_operation(operation)
    assert not result.ok
    assert result.error.code == "CONFIGURATION_ERROR"
    assert result.error.category == "domain"


def test_configuration_override_and_project_reload_invariant():
    assert ConfigurationError("missing", code="CUSTOM").code == "CUSTOM"
    query = Mock()
    query.get_project.return_value = None
    api = ProjectManagementProjectsDesktopApi(
        project_status=Mock(), project_query=query
    )
    with pytest.raises(RuntimeError, match="could not be reloaded") as caught:
        api.set_project_status("p", "ACTIVE")
    assert not isinstance(caught.value, DomainError)


def test_unsupported_project_resource_operation_is_not_missing_wiring():
    api = ProjectManagementProjectsDesktopApi(project_resource_commands=object())
    with pytest.raises(UnsupportedOperationError):
        api.remove_project_resource("assignment")


def test_import_errors_are_canonical_and_filesystem_message_is_safe(tmp_path):
    path = tmp_path / "private-file.csv"
    with pytest.raises(ValidationError) as caught:
        preview_import({}, file_path=str(path), source_format="unknown")
    assert caught.value.code == "IMPORT_FORMAT_UNSUPPORTED"
    with pytest.raises(ValidationError) as caught:
        preview_import({}, file_path=str(path), source_format="csv")
    assert caught.value.code == "IMPORT_FILE_UNREADABLE"
    assert isinstance(caught.value.__cause__, OSError)
    assert str(path) not in str(caught.value)
    assert path.name not in str(caught.value)
    with pytest.raises(NotFoundError) as caught:
        execute_import({}, session_id="expired")
    assert caught.value.code == "IMPORT_SESSION_NOT_FOUND"


def test_invalid_import_preview_is_business_rejection_and_retains_session():
    preview = ImportPreviewModel(
        session_id="s",
        total_rows=1,
        valid_rows=0,
        error_rows=1,
        warning_rows=0,
        issues=[
            ImportValidationIssue(
                1, ImportValidationSeverity.ERROR, None, "Invalid row"
            )
        ],
    )
    sessions = {"s": preview}
    with pytest.raises(BusinessRuleError) as caught:
        execute_import(sessions, session_id="s")
    assert caught.value.code == "IMPORT_PREVIEW_HAS_ERRORS"
    assert sessions["s"] is preview
    preview.issues.clear()
    assert execute_import(sessions, session_id="s")["ok"]
    assert not sessions
