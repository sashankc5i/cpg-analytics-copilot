from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class VarianceResult:
    """
    Deterministic comparison between a current value and a
    comparison-period value.
    """

    current_value: float
    comparison_value: float
    absolute_change: float
    percentage_change: Optional[float]
    direction: str

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_variance(
    current_value: float,
    comparison_value: float,
) -> VarianceResult:
    """
    Calculate absolute and percentage variance.

    Formula:

        absolute_change =
            current_value - comparison_value

        percentage_change =
            (absolute_change / comparison_value) * 100

    If the comparison value is zero, percentage_change is None
    because percentage variance is mathematically undefined.
    """

    if not isinstance(current_value, (int, float)):
        raise TypeError(
            "current_value must be a number."
        )

    if not isinstance(comparison_value, (int, float)):
        raise TypeError(
            "comparison_value must be a number."
        )

    absolute_change = (
        float(current_value)
        - float(comparison_value)
    )

    if comparison_value == 0:
        percentage_change = None
    else:
        percentage_change = (
            absolute_change
            / float(comparison_value)
        ) * 100

    if absolute_change > 0:
        direction = "increase"
    elif absolute_change < 0:
        direction = "decrease"
    else:
        direction = "no_change"

    return VarianceResult(
        current_value=float(current_value),
        comparison_value=float(comparison_value),
        absolute_change=round(
            absolute_change,
            2,
        ),
        percentage_change=(
            round(
                percentage_change,
                2,
            )
            if percentage_change is not None
            else None
        ),
        direction=direction,
    )