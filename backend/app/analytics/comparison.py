from dataclasses import asdict, dataclass
from datetime import date, timedelta


SUPPORTED_COMPARISON_TYPES = (
    "previous_period",
    "previous_month",
    "year_over_year",
)


@dataclass(frozen=True)
class ComparisonPeriod:
    """
    Represents the current analytical period and the period used for
    comparison.

    Dates are stored as ISO YYYY-MM-DD strings so the object remains
    compatible with the existing governed filter contract.
    """

    current_start: str
    current_end: str
    comparison_start: str
    comparison_end: str
    comparison_type: str

    def to_dict(self) -> dict:
        """
        Return a JSON-serializable representation.
        """
        return asdict(self)


def _parse_date(value: str, field_name: str) -> date:
    """
    Parse a YYYY-MM-DD date.

    Raises:
        ValueError: if the value is not a valid ISO date.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string in YYYY-MM-DD format."
        )

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid date in YYYY-MM-DD format."
        ) from exc


def _validate_current_period(
    current_start: str,
    current_end: str,
) -> tuple[date, date]:
    """
    Validate and parse the current analytical period.
    """
    start = _parse_date(
        current_start,
        "current_start",
    )
    end = _parse_date(
        current_end,
        "current_end",
    )

    if start > end:
        raise ValueError(
            "current_start must be on or before current_end."
        )

    return start, end


def _previous_period(
    current_start: date,
    current_end: date,
) -> tuple[date, date]:
    """
    Resolve a period of identical length immediately preceding the
    current period.

    Example:

        Current:
        2026-09-01 → 2026-09-30

        Previous period:
        2026-08-02 → 2026-08-31
    """
    period_length = (
        current_end - current_start
    ).days + 1

    comparison_end = (
        current_start - timedelta(days=1)
    )

    comparison_start = (
        comparison_end
        - timedelta(days=period_length - 1)
    )

    return comparison_start, comparison_end


def _previous_month(
    current_start: date,
    current_end: date,
) -> tuple[date, date]:
    """
    Resolve the calendar month immediately before the current month.

    The current period must fall entirely inside one calendar month.

    Example:

        Current:
        2026-09-01 → 2026-09-30

        Previous month:
        2026-08-01 → 2026-08-31
    """
    if (
        current_start.year != current_end.year
        or current_start.month != current_end.month
    ):
        raise ValueError(
            "previous_month requires the current period to "
            "fall within a single calendar month."
        )

    if current_start.month == 1:
        comparison_year = current_start.year - 1
        comparison_month = 12
    else:
        comparison_year = current_start.year
        comparison_month = current_start.month - 1

    comparison_start = date(
        comparison_year,
        comparison_month,
        1,
    )

    if comparison_month == 12:
        next_month = date(
            comparison_year + 1,
            1,
            1,
        )
    else:
        next_month = date(
            comparison_year,
            comparison_month + 1,
            1,
        )

    comparison_end = next_month - timedelta(days=1)

    return comparison_start, comparison_end


def _same_period_previous_year(
    current_start: date,
    current_end: date,
) -> tuple[date, date]:
    """
    Resolve the equivalent calendar period one year earlier.

    February 29 is clamped to February 28 when the previous year
    is not a leap year.
    """

    def shift_year(value: date) -> date:
        try:
            return value.replace(
                year=value.year - 1
            )
        except ValueError:
            # The only expected invalid case here is February 29
            # shifting into a non-leap year.
            if value.month == 2 and value.day == 29:
                return date(
                    value.year - 1,
                    2,
                    28,
                )

            raise

    return (
        shift_year(current_start),
        shift_year(current_end),
    )


def resolve_comparison_period(
    current_start: str,
    current_end: str,
    comparison_type: str,
) -> ComparisonPeriod:
    """
    Resolve a deterministic comparison period.

    Supported comparison types:

    - previous_period
    - previous_month
    - year_over_year

    Args:
        current_start:
            Current analytical period start date.

        current_end:
            Current analytical period end date.

        comparison_type:
            Governed comparison type.

    Returns:
        ComparisonPeriod

    Raises:
        ValueError:
            If the current period or comparison type is invalid.
    """
    current_start_date, current_end_date = (
        _validate_current_period(
            current_start=current_start,
            current_end=current_end,
        )
    )

    if not isinstance(comparison_type, str):
        raise ValueError(
            "comparison_type must be a string."
        )

    normalized_type = comparison_type.strip().lower()

    if normalized_type not in SUPPORTED_COMPARISON_TYPES:
        raise ValueError(
            "Unsupported comparison type: "
            f"{comparison_type}. "
            f"Supported types: "
            f"{', '.join(SUPPORTED_COMPARISON_TYPES)}."
        )

    if normalized_type == "previous_period":
        comparison_start, comparison_end = (
            _previous_period(
                current_start=current_start_date,
                current_end=current_end_date,
            )
        )

    elif normalized_type == "previous_month":
        comparison_start, comparison_end = (
            _previous_month(
                current_start=current_start_date,
                current_end=current_end_date,
            )
        )

    else:
        comparison_start, comparison_end = (
            _same_period_previous_year(
                current_start=current_start_date,
                current_end=current_end_date,
            )
        )

    return ComparisonPeriod(
        current_start=current_start_date.isoformat(),
        current_end=current_end_date.isoformat(),
        comparison_start=comparison_start.isoformat(),
        comparison_end=comparison_end.isoformat(),
        comparison_type=normalized_type,
    )
def build_comparison_context(
    current_start: str,
    current_end: str,
    comparison_type: str,
) -> dict:
    """
    Resolve the requested comparison and return the structured
    comparison context used by downstream analytics.
    """

    comparison = resolve_comparison_period(
        current_start=current_start,
        current_end=current_end,
        comparison_type=comparison_type,
    )

    return {
        "current_period": {
            "start_date": comparison.current_start,
            "end_date": comparison.current_end,
        },
        "comparison_period": {
            "start_date": comparison.comparison_start,
            "end_date": comparison.comparison_end,
        },
        "comparison_type": comparison.comparison_type,
    }