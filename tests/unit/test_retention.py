from datetime import UTC, date, datetime

import pytest
from nfx.retention.services import (
    InvalidRetentionParams,
    RetentionState,
    calculate_eligibility_date,
    parse_retention_params,
)


@pytest.mark.parametrize(
    ("family", "emitted_at", "authorized_at", "expected"),
    [
        (
            "nfe",
            datetime(2026, 8, 15, 12, tzinfo=UTC),
            datetime(2026, 8, 15, 12, tzinfo=UTC),
            date(2037, 8, 15),
        ),
        (
            "nfe",
            datetime(2020, 2, 29, 12, tzinfo=UTC),
            datetime(2020, 2, 29, 12, tzinfo=UTC),
            date(2031, 2, 28),
        ),
        ("nfse", datetime(2026, 12, 31, 23, tzinfo=UTC), None, date(2032, 1, 1)),
        ("nfse", datetime(2026, 1, 1, 12, tzinfo=UTC), None, date(2032, 1, 1)),
    ],
)
def test_calculate_eligibility_date_uses_canonical_civil_rules(
    family: str,
    emitted_at: datetime,
    authorized_at: datetime | None,
    expected: date,
) -> None:
    assert calculate_eligibility_date(family, emitted_at, authorized_at) == expected


def test_parse_retention_params_is_bounded_and_allowlisted() -> None:
    params = parse_retention_params(
        {
            "family": "nfe",
            "state": "eligible",
            "as_of": "2037-08-15",
            "limit": "25",
        }
    )

    assert params.family == "nfe"
    assert params.state == RetentionState.ELIGIBLE
    assert params.as_of == date(2037, 8, 15)
    assert params.limit == 25

    with pytest.raises(InvalidRetentionParams):
        parse_retention_params({"limit": "101"})
    with pytest.raises(InvalidRetentionParams):
        parse_retention_params({"delete": "true"})
    with pytest.raises(InvalidRetentionParams):
        parse_retention_params({"family": ["nfe", "nfse"]})
