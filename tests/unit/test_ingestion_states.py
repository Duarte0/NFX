from __future__ import annotations

from datetime import UTC, datetime

import pytest
from nfx.adapters.simulation import FiscalOutcome, FiscalResponse
from nfx.collection.ingestion import (
    UnitOutcome,
    classify_page_response,
    classify_unit_treatments,
)
from nfx.collection.models import (
    IngestionOutcome,
    IngestionPageState,
    IngestionRecovery,
)


@pytest.mark.parametrize(
    ("outcome", "state", "classified", "recovery", "advances"),
    [
        (
            FiscalOutcome.SUCCESS,
            IngestionPageState.EMPTY,
            IngestionOutcome.VALID_EMPTY,
            IngestionRecovery.NONE,
            True,
        ),
        (
            FiscalOutcome.EMPTY,
            IngestionPageState.EMPTY,
            IngestionOutcome.VALID_EMPTY,
            IngestionRecovery.NONE,
            True,
        ),
        (
            FiscalOutcome.NO_COVERAGE,
            IngestionPageState.NO_COVERAGE,
            IngestionOutcome.NO_COVERAGE,
            IngestionRecovery.NONE,
            False,
        ),
        (
            FiscalOutcome.UNAVAILABLE,
            IngestionPageState.UNAVAILABLE,
            IngestionOutcome.UNAVAILABLE,
            IngestionRecovery.RETRY,
            False,
        ),
        (
            FiscalOutcome.TIMEOUT,
            IngestionPageState.RETRY,
            IngestionOutcome.TEMPORARY_FAILURE,
            IngestionRecovery.RETRY,
            False,
        ),
        (
            FiscalOutcome.COOLDOWN,
            IngestionPageState.COOLDOWN,
            IngestionOutcome.COOLDOWN,
            IngestionRecovery.COOLDOWN,
            False,
        ),
        (
            FiscalOutcome.BLOCKED,
            IngestionPageState.BLOCKED,
            IngestionOutcome.PERMANENT_FAILURE,
            IngestionRecovery.BLOCKED,
            False,
        ),
        (
            FiscalOutcome.CONFLICT,
            IngestionPageState.FAILED,
            IngestionOutcome.CONFLICT,
            IngestionRecovery.CONFLICT_REVIEW,
            False,
        ),
        (
            FiscalOutcome.MALFORMED,
            IngestionPageState.FAILED,
            IngestionOutcome.MALFORMED,
            IngestionRecovery.QUARANTINE,
            False,
        ),
        (
            FiscalOutcome.EVENT_WITHOUT_PARENT,
            IngestionPageState.FAILED,
            IngestionOutcome.QUARANTINE,
            IngestionRecovery.QUARANTINE,
            False,
        ),
        (
            FiscalOutcome.REPEATED_CURSOR,
            IngestionPageState.RETRY,
            IngestionOutcome.TEMPORARY_FAILURE,
            IngestionRecovery.RECONCILE,
            False,
        ),
        (
            FiscalOutcome.PARTIAL,
            IngestionPageState.PARTIAL,
            IngestionOutcome.PARTIAL,
            IngestionRecovery.RETRY,
            False,
        ),
    ],
)
def test_response_matrix_is_finite_and_never_advances_unsafe_pages(
    outcome: FiscalOutcome,
    state: IngestionPageState,
    classified: IngestionOutcome,
    recovery: IngestionRecovery,
    advances: bool,
) -> None:
    response = FiscalResponse(
        outcome,
        next_cursor="cursor:next" if outcome not in {FiscalOutcome.COOLDOWN} else None,
        cooldown_until=(
            datetime(2026, 8, 10, tzinfo=UTC) if outcome == FiscalOutcome.COOLDOWN else None
        ),
    )

    result = classify_page_response(response)

    assert result.page_state == state
    assert result.outcome == classified
    assert result.recovery == recovery
    assert result.can_advance is advances


def test_terminal_unit_treatments_preserve_quarantine_and_conflict() -> None:
    result = classify_unit_treatments(
        (UnitOutcome.PERSISTED, UnitOutcome.QUARANTINE, UnitOutcome.CONFLICT)
    )

    assert result.page_state == IngestionPageState.COMPLETE
    assert result.outcome == IngestionOutcome.CONFLICT
    assert result.recovery == IngestionRecovery.CONFLICT_REVIEW
    assert result.can_advance is True


def test_retryable_unit_treatment_keeps_page_partial_and_cursor_safe() -> None:
    result = classify_unit_treatments((UnitOutcome.PERSISTED, UnitOutcome.FAILED))

    assert result.page_state == IngestionPageState.PARTIAL
    assert result.outcome == IngestionOutcome.PARTIAL
    assert result.recovery == IngestionRecovery.RETRY
    assert result.can_advance is False
