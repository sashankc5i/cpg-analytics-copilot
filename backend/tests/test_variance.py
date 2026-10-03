import pytest

from app.analytics.variance import (
    VarianceResult,
    calculate_variance,
)


def test_positive_variance():
    result = calculate_variance(
        current_value=110,
        comparison_value=100,
    )

    assert isinstance(result, VarianceResult)
    assert result.current_value == 110
    assert result.comparison_value == 100
    assert result.absolute_change == 10
    assert result.percentage_change == 10
    assert result.direction == "increase"


def test_negative_variance():
    result = calculate_variance(
        current_value=90,
        comparison_value=100,
    )

    assert result.absolute_change == -10
    assert result.percentage_change == -10
    assert result.direction == "decrease"


def test_no_change():
    result = calculate_variance(
        current_value=100,
        comparison_value=100,
    )

    assert result.absolute_change == 0
    assert result.percentage_change == 0
    assert result.direction == "no_change"


def test_zero_comparison_value():
    result = calculate_variance(
        current_value=100,
        comparison_value=0,
    )

    assert result.absolute_change == 100
    assert result.percentage_change is None
    assert result.direction == "increase"


def test_zero_values():
    result = calculate_variance(
        current_value=0,
        comparison_value=0,
    )

    assert result.absolute_change == 0
    assert result.percentage_change is None
    assert result.direction == "no_change"


def test_percentage_is_calculated_from_comparison_value():
    result = calculate_variance(
        current_value=125,
        comparison_value=100,
    )

    assert result.percentage_change == 25


def test_decimal_values_are_rounded():
    result = calculate_variance(
        current_value=113.4567,
        comparison_value=100.1234,
    )

    assert result.absolute_change == 13.33
    assert result.percentage_change == 13.32


def test_integer_inputs_are_normalized_to_float():
    result = calculate_variance(
        current_value=110,
        comparison_value=100,
    )

    assert result.current_value == 110.0
    assert result.comparison_value == 100.0


def test_to_dict():
    result = calculate_variance(
        current_value=120,
        comparison_value=100,
    )

    assert result.to_dict() == {
        "current_value": 120.0,
        "comparison_value": 100.0,
        "absolute_change": 20.0,
        "percentage_change": 20.0,
        "direction": "increase",
    }


def test_invalid_current_value():
    with pytest.raises(
        TypeError,
        match="current_value must be a number",
    ):
        calculate_variance(
            current_value="120",
            comparison_value=100,
        )


def test_invalid_comparison_value():
    with pytest.raises(
        TypeError,
        match="comparison_value must be a number",
    ):
        calculate_variance(
            current_value=120,
            comparison_value="100",
        )


def test_negative_values_are_supported():
    result = calculate_variance(
        current_value=-80,
        comparison_value=-100,
    )

    assert result.absolute_change == 20
    assert result.percentage_change == -20
    assert result.direction == "increase"