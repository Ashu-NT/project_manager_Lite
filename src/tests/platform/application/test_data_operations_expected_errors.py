from unittest.mock import Mock

import pytest

from src.core.platform.application.data_operations.exporting.export_definition_registry import (
    ExportDefinitionRegistry,
)
from src.core.platform.application.data_operations.importing.import_definition_registry import (
    ImportDefinitionRegistry,
)
from src.core.platform.application.data_operations.report_runtime.report_definition_registry import (
    ReportDefinitionRegistry,
)
from src.core.platform.application.data_operations.runtime_tracking.commands.execution import (
    RuntimeExecutionCommandHandler,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
    UnsupportedOperationError,
    ValidationError,
)


@pytest.mark.parametrize(
    "registry_type,prefix,key_attribute",
    [
        (ImportDefinitionRegistry, "IMPORT", "operation_key"),
        (ExportDefinitionRegistry, "EXPORT", "operation_key"),
        (ReportDefinitionRegistry, "REPORT", "report_key"),
    ],
)
def test_registry_expected_errors_and_duplicate_invariant(
    registry_type, prefix, key_attribute
):
    registry = registry_type()
    with pytest.raises(ValidationError) as caught:
        registry.get(" ")
    assert caught.value.code == f"{prefix}_KEY_REQUIRED"
    with pytest.raises(UnsupportedOperationError) as caught:
        registry.get("missing")
    assert caught.value.code == f"{prefix}_TYPE_UNSUPPORTED"
    assert isinstance(caught.value.__cause__, KeyError)
    definition = Mock(**{key_attribute: "example"})
    registry.register(definition)
    assert registry.get(" EXAMPLE ") is definition
    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition)


@pytest.mark.parametrize("method", ["request_cancellation", "start_retry"])
def test_missing_runtime_execution_is_not_found(method):
    repository = Mock()
    repository.get.return_value = None
    handler = RuntimeExecutionCommandHandler(
        runtime_execution_repo=repository,
        tenant_context_service=Mock(),
    )
    with pytest.raises(NotFoundError) as caught:
        getattr(handler, method)("missing")
    assert caught.value.code == "RUNTIME_EXECUTION_NOT_FOUND"
    repository.update.assert_not_called()
