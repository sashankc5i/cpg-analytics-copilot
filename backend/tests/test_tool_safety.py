import pytest

from app.agent.tools import execute_tool


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