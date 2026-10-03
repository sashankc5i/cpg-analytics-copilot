import pytest

from app.analytics.comparison import (
    ComparisonPeriod,
    build_comparison_context,
    resolve_comparison_period,
)

def test_previous_period_for_full_month():
    result = resolve_comparison_period(
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_period",
    )

    assert isinstance(result, ComparisonPeriod)

    assert result.current_start == "2026-09-01"
    assert result.current_end == "2026-09-30"

    assert result.comparison_start == "2026-08-02"
    assert result.comparison_end == "2026-08-31"

    assert result.comparison_type == "previous_period"


def test_previous_period_preserves_exact_period_length():
    result = resolve_comparison_period(
        current_start="2026-09-10",
        current_end="2026-09-15",
        comparison_type="previous_period",
    )

    assert result.comparison_start == "2026-09-04"
    assert result.comparison_end == "2026-09-09"


def test_previous_month_from_september():
    result = resolve_comparison_period(
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result.comparison_start == "2026-08-01"
    assert result.comparison_end == "2026-08-31"


def test_previous_month_from_january():
    result = resolve_comparison_period(
        current_start="2026-01-01",
        current_end="2026-01-31",
        comparison_type="previous_month",
    )

    assert result.comparison_start == "2025-12-01"
    assert result.comparison_end == "2025-12-31"


def test_previous_month_handles_february():
    result = resolve_comparison_period(
        current_start="2026-02-01",
        current_end="2026-02-28",
        comparison_type="previous_month",
    )

    assert result.comparison_start == "2026-01-01"
    assert result.comparison_end == "2026-01-31"


def test_previous_month_requires_single_calendar_month():
    with pytest.raises(
        ValueError,
        match="single calendar month",
    ):
        resolve_comparison_period(
            current_start="2026-08-15",
            current_end="2026-09-15",
            comparison_type="previous_month",
        )


def test_year_over_year_for_full_month():
    result = resolve_comparison_period(
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="year_over_year",
    )

    assert result.comparison_start == "2025-09-01"
    assert result.comparison_end == "2025-09-30"


def test_year_over_year_for_custom_period():
    result = resolve_comparison_period(
        current_start="2026-04-10",
        current_end="2026-04-20",
        comparison_type="year_over_year",
    )

    assert result.comparison_start == "2025-04-10"
    assert result.comparison_end == "2025-04-20"


def test_year_over_year_handles_february_29():
    result = resolve_comparison_period(
        current_start="2024-02-29",
        current_end="2024-02-29",
        comparison_type="year_over_year",
    )

    assert result.comparison_start == "2023-02-28"
    assert result.comparison_end == "2023-02-28"


def test_invalid_comparison_type():
    with pytest.raises(
        ValueError,
        match="Unsupported comparison type",
    ):
        resolve_comparison_period(
            current_start="2026-09-01",
            current_end="2026-09-30",
            comparison_type="random_comparison",
        )


def test_invalid_current_start():
    with pytest.raises(
        ValueError,
        match="current_start must be a valid date",
    ):
        resolve_comparison_period(
            current_start="2026-99-01",
            current_end="2026-09-30",
            comparison_type="previous_month",
        )


def test_invalid_current_end():
    with pytest.raises(
        ValueError,
        match="current_end must be a valid date",
    ):
        resolve_comparison_period(
            current_start="2026-09-01",
            current_end="2026-99-30",
            comparison_type="previous_month",
        )


def test_current_start_cannot_be_after_current_end():
    with pytest.raises(
        ValueError,
        match="current_start must be on or before current_end",
    ):
        resolve_comparison_period(
            current_start="2026-09-30",
            current_end="2026-09-01",
            comparison_type="previous_period",
        )


def test_non_string_comparison_type():
    with pytest.raises(
        ValueError,
        match="comparison_type must be a string",
    ):
        resolve_comparison_period(
            current_start="2026-09-01",
            current_end="2026-09-30",
            comparison_type=None,
        )


def test_comparison_period_serializes_to_dict():
    result = resolve_comparison_period(
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result.to_dict() == {
        "current_start": "2026-09-01",
        "current_end": "2026-09-30",
        "comparison_start": "2026-08-01",
        "comparison_end": "2026-08-31",
        "comparison_type": "previous_month",
    }
def test_build_comparison_context():
    result = build_comparison_context(
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
    )

    assert result == {
        "current_period": {
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        "comparison_period": {
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
        "comparison_type": "previous_month",
    }