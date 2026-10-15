import pytest

from src.core.modules.project_management.contracts.reads.financials.snapshot.models.ledger_query import (
    ProjectFinanceLedgerQuery,
)
from src.core.platform.common.exceptions import ValidationError


@pytest.mark.parametrize(
    "offset,limit,code",
    [
        (-1, 100, "FINANCE_LEDGER_OFFSET_INVALID"),
        (0, 0, "FINANCE_LEDGER_LIMIT_INVALID"),
        (0, 501, "FINANCE_LEDGER_LIMIT_INVALID"),
    ],
)
def test_ledger_pagination_uses_domain_validation(offset, limit, code):
    with pytest.raises(ValidationError) as caught:
        ProjectFinanceLedgerQuery(offset=offset, limit=limit)
    assert caught.value.code == code


def test_ledger_pagination_keeps_valid_bounds_and_programmer_type_errors():
    assert ProjectFinanceLedgerQuery(offset=0, limit=1).limit == 1
    assert ProjectFinanceLedgerQuery(offset=10, limit=500).limit == 500
    with pytest.raises(TypeError):
        ProjectFinanceLedgerQuery(offset=None)
