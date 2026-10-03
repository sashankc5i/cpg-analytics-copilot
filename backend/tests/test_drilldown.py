from unittest.mock import patch

import pytest

from app.analytics.drilldown import (
    get_hierarchical_drilldown,
)


@patch("app.analytics.drilldown.get_overall_sales")
def test_company_drilldown(mock_get_overall_sales):
    mock_get_overall_sales.return_value = {
        "revenue": 1000
    }

    result = get_hierarchical_drilldown(
        level="company"
    )

    assert result["level"] == "company"
    assert result["results"] == [
        {"revenue": 1000}
    ]


@patch("app.analytics.drilldown.get_sales_by_region")
def test_region_drilldown(mock_get_sales_by_region):
    mock_get_sales_by_region.return_value = [
        {"region": "South", "revenue": 500}
    ]

    result = get_hierarchical_drilldown(
        level="region"
    )

    assert result["level"] == "region"
    assert result["results"][0]["region"] == "South"


@patch("app.analytics.drilldown.get_sales_by_category")
def test_category_drilldown_preserves_filters(
    mock_get_sales_by_category,
):
    filters = {
        "region": ["South"],
    }

    mock_get_sales_by_category.return_value = []

    result = get_hierarchical_drilldown(
        level="category",
        filters=filters,
    )

    assert result["filters"] == filters
    mock_get_sales_by_category.assert_called_once_with(
        filters=filters
    )


@patch("app.analytics.drilldown.get_top_products")
def test_product_drilldown(
    mock_get_top_products,
):
    mock_get_top_products.return_value = [
        {
            "product_id": 1,
            "revenue": 500,
        }
    ]

    result = get_hierarchical_drilldown(
        level="product",
        limit=5,
    )

    assert result["level"] == "product"
    assert result["results"][0]["product_id"] == 1

    mock_get_top_products.assert_called_once_with(
        limit=5,
        filters={},
    )


def test_invalid_drilldown_level():
    with pytest.raises(
        ValueError,
        match="Unsupported drill-down level",
    ):
        get_hierarchical_drilldown(
            level="brand"
        )


def test_invalid_drilldown_limit():
    with pytest.raises(
        ValueError,
        match="between 1 and 50",
    ):
        get_hierarchical_drilldown(
            level="product",
            limit=0,
        )
