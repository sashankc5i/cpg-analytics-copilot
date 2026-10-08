import pytest

from app.agent.tools import execute_tool
from tests.evaluation_cases import EVALUATION_CASES


TOOL_FUNCTIONS = {
    "get_overall_sales": lambda: execute_tool(
        "get_overall_sales",
        {},
    ),
    "get_sales_by_region": lambda: execute_tool(
        "get_sales_by_region",
        {},
    ),
    "get_monthly_sales_trend": lambda: execute_tool(
        "get_monthly_sales_trend",
        {},
    ),
    "get_top_products": lambda: execute_tool(
        "get_top_products",
        {"limit": 10},
    ),
    "get_sales_by_category": lambda: execute_tool(
        "get_sales_by_category",
        {},
    ),
    "get_customer_segment_performance": lambda: execute_tool(
        "get_customer_segment_performance",
        {},
    ),
    "get_promotion_impact": lambda: execute_tool(
        "get_promotion_impact",
        {},
    ),
    "get_stockout_rate": lambda: execute_tool(
        "get_stockout_rate",
        {},
    ),
}


@pytest.mark.parametrize(
    "case",
    EVALUATION_CASES,
    ids=[
        case["id"]
        for case in EVALUATION_CASES
    ],
)
def test_expected_tools_are_available(case):
    """
    Verify that every tool required by the
    evaluation dataset exists and produces data.
    """

    for tool_name in case["expected_tools"]:
        assert tool_name in TOOL_FUNCTIONS

        result = TOOL_FUNCTIONS[
            tool_name
        ]()

        assert result is not None


@pytest.mark.parametrize(
    "case",
    EVALUATION_CASES,
    ids=[
        case["id"]
        for case in EVALUATION_CASES
    ],
)
def test_expected_tools_return_valid_results(case):
    """
    Verify that the deterministic analytics tools
    provide usable results for each evaluation case.
    """

    for tool_name in case["expected_tools"]:
        result = TOOL_FUNCTIONS[
            tool_name
        ]()

        assert result is not None

        if isinstance(result, list):
            assert len(result) > 0

        if isinstance(result, dict):
            assert len(result) > 0