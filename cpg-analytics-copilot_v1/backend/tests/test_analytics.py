from app.analytics.sales import (
    get_overall_sales,
    get_sales_by_region,
    get_monthly_sales_trend,
)

from app.analytics.products import (
    get_top_products,
)

from app.analytics.customers import (
    get_customer_segment_performance,
)

from app.analytics.promotions import (
    get_promotion_impact,
)

from app.analytics.inventory import (
    get_stockout_rate,
)


def test_overall_sales():

    result = get_overall_sales()

    assert result["transactions"] > 0
    assert result["units_sold"] > 0
    assert result["revenue"] > 0


def test_sales_by_region():

    result = get_sales_by_region()

    assert len(result) > 0
    assert "region" in result[0]
    assert "revenue" in result[0]


def test_monthly_sales():

    result = get_monthly_sales_trend()

    assert len(result) > 0
    assert "month" in result[0]


def test_top_products():

    result = get_top_products()

    assert len(result) == 10
    assert "product_name" in result[0]


def test_customer_segments():

    result = get_customer_segment_performance()

    assert len(result) > 0


def test_promotions():

    result = get_promotion_impact()

    assert len(result) == 2


def test_inventory():

    result = get_stockout_rate()

    assert len(result) > 0