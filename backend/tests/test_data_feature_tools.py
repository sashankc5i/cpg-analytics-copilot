from app.agent.tools import (
    AVAILABLE_FUNCTIONS,
    TOOL_DEFINITIONS,
    _validate_arguments,
)


def _tool_names():
    return {
        item["function"]["name"]
        for item in TOOL_DEFINITIONS
    }


def test_data_feature_tools_are_registered():
    expected = {
        "get_sales_variance",
        "get_hierarchical_drilldown",
        "get_data_quality_indicators",
        "get_data_freshness",
        "get_driver_decomposition",
        "get_contribution_analysis",
    }

    assert expected.issubset(_tool_names())
    assert expected.issubset(
        AVAILABLE_FUNCTIONS.keys()
    )


def test_drilldown_arguments_validate_filters():
    arguments = _validate_arguments(
        {
            "level": "region",
            "filters": {
                "region": ["South"],
            },
        }
    )

    assert arguments["level"] == "region"
    assert arguments["filters"] == {
        "region": ["South"],
    }


def test_variance_allows_omitted_current_period():
    arguments = _validate_arguments(
        {
            "metric_id": "revenue",
            "comparison_type": "previous_month",
        }
    )

    assert arguments == {
        "metric_id": "revenue",
        "comparison_type": "previous_month",
    }


def test_quality_and_freshness_need_no_arguments():
    assert _validate_arguments({}) == {}
