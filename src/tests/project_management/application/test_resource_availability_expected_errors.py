from datetime import date
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.platform.common.exceptions import NotFoundError


@pytest.mark.parametrize("method", ["get_availability", "get_availability_range"])
def test_missing_resource_is_not_found_before_calendar_resolution(method):
    repository, resolver = Mock(), Mock()
    repository.get.return_value = None
    handler = ResourceAvailabilityQueryHandler(resolver, repository)
    today = date(2026, 10, 15)
    kwargs = (
        {"target_date": today}
        if method == "get_availability"
        else {"start": today, "end": today}
    )
    with pytest.raises(NotFoundError) as caught:
        getattr(handler, method)("missing", **kwargs)
    assert caught.value.code == "RESOURCE_NOT_FOUND"
    resolver.resolve_calendar_context.assert_not_called()
