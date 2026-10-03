import pytest

from app.agent.tools import (
    AVAILABLE_FUNCTIONS,
    _validate_arguments,
    execute_tool,
    execute_tool_as_json,
)


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError):
        execute_tool(
            "does_not_exist",
            {},
        )


def test_invalid_product_limit_is_rejected():
    with pytest.raises(ValueError):
        execute_tool(
            "get_top_products",
            {"limit": -1},
        )


def test_excessive_product_limit_is_rejected():
    with pytest.raises(ValueError):
        execute_tool(
            "get_top_products",
            {"limit": 1000},
        )


def test_non_integer_product_limit_is_rejected():
    with pytest.raises(ValueError):
        execute_tool(
            "get_top_products",
            {"limit": "100"},
        )


def test_valid_product_limit_is_accepted():
    result = execute_tool(
        "get_top_products",
        {"limit": 5},
    )

    assert len(result) == 5


def test_none_arguments_are_normalized_to_empty_object():
    result = execute_tool(
        "get_overall_sales",
        None,
    )

    assert isinstance(result, dict)


def test_non_object_arguments_are_rejected():
    with pytest.raises(
        ValueError,
        match="Tool arguments must be a JSON object",
    ):
        execute_tool(
            "get_overall_sales",
            [],
        )


def test_string_arguments_are_rejected():
    with pytest.raises(
        ValueError,
        match="Tool arguments must be a JSON object",
    ):
        execute_tool(
            "get_overall_sales",
            "revenue",
        )


def test_integer_arguments_are_rejected():
    with pytest.raises(
        ValueError,
        match="Tool arguments must be a JSON object",
    ):
        execute_tool(
            "get_overall_sales",
            10,
        )


def test_no_argument_tool_accepts_empty_object():
    result = execute_tool(
        "get_sales_by_region",
        {},
    )

    assert isinstance(result, list)


def test_execute_tool_as_json_returns_valid_json():
    result = execute_tool_as_json(
        "get_overall_sales",
        {},
    )

    assert isinstance(result, str)

    import json

    parsed = json.loads(result)

    assert isinstance(parsed, dict)
def test_get_sales_variance_is_registered():
    assert "get_sales_variance" in AVAILABLE_FUNCTIONS
def test_get_sales_variance_allows_omitted_current_period():
    arguments = {
        "metric_id": "revenue",
        "comparison_type": "previous_month",
    }

    validated = _validate_arguments(
        arguments
    )

    assert validated == arguments
def test_get_sales_variance_accepts_explicit_current_period():
    arguments = {
        "metric_id": "revenue",
        "current_start": "2026-09-01",
        "current_end": "2026-09-30",
        "comparison_type": "previous_month",
    }

    validated = _validate_arguments(
        arguments
    )

    assert validated == arguments
def test_get_sales_variance_execution_without_current_period():
    arguments = {
        "metric_id": "revenue",
        "comparison_type": "previous_month",
    }

    result = execute_tool(
        "get_sales_variance",
        arguments,
    )

    assert result["metric"]["id"] == "revenue"
    assert result["comparison_type"] == "previous_month"
    assert "current_period" in result
    assert "comparison_period" in result