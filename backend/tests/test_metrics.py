import pytest

from app.analytics.metrics import (
    get_metric,
    list_metrics,
    resolve_metric_alias,
    resolve_metric_from_text,
)


def test_get_revenue_metric():
    metric = get_metric(
        "revenue"
    )

    assert metric["metric_id"] == "revenue"
    assert metric["display_name"] == "Revenue"
    assert metric["format"] == "currency"


def test_get_metric_is_case_insensitive():
    metric = get_metric(
        "REVENUE"
    )

    assert metric["metric_id"] == "revenue"


def test_get_unknown_metric_raises():
    with pytest.raises(
        KeyError,
        match="Unknown metric",
    ):
        get_metric(
            "unknown_metric"
        )


def test_get_metric_returns_copy():
    metric = get_metric(
        "revenue"
    )

    metric["display_name"] = (
        "Changed"
    )

    original = get_metric(
        "revenue"
    )

    assert (
        original["display_name"]
        == "Revenue"
    )


def test_list_metrics_returns_governed_metrics():
    metrics = list_metrics()

    metric_ids = {
        metric["metric_id"]
        for metric in metrics
    }

    assert "revenue" in metric_ids
    assert "transactions" in metric_ids
    assert "units_sold" in metric_ids
    assert (
        "average_transaction_value"
        in metric_ids
    )
    assert "stockout_rate" in metric_ids


def test_resolve_exact_revenue_alias():
    metric = resolve_metric_alias(
        "revenue"
    )

    assert metric is not None
    assert metric["metric_id"] == "revenue"


def test_resolve_revenue_alias():
    metric = resolve_metric_alias(
        "turnover"
    )

    assert metric is not None
    assert metric["metric_id"] == "revenue"


def test_resolve_units_alias():
    metric = resolve_metric_alias(
        "units sold"
    )

    assert metric is not None
    assert metric["metric_id"] == "units_sold"


def test_resolve_transaction_alias():
    metric = resolve_metric_alias(
        "number of purchases"
    )

    assert metric is not None
    assert metric["metric_id"] == "transactions"


def test_resolve_metric_from_sentence():
    metric = resolve_metric_from_text(
        "What is our total revenue?"
    )

    assert metric is not None
    assert metric["metric_id"] == "revenue"


def test_resolve_metric_from_sales_sentence():
    metric = resolve_metric_from_text(
        "Show me the sales revenue for South."
    )

    assert metric is not None
    assert metric["metric_id"] == "revenue"


def test_resolve_metric_from_units_sentence():
    metric = resolve_metric_from_text(
        "How many units were sold?"
    )

    assert metric is not None
    assert metric["metric_id"] == "units_sold"


def test_resolve_metric_from_transaction_sentence():
    metric = resolve_metric_from_text(
        "How many purchases did we have?"
    )

    assert metric is not None
    assert metric["metric_id"] == "transactions"


def test_unknown_metric_returns_none():
    metric = resolve_metric_from_text(
        "How strong is our market position?"
    )

    assert metric is None


def test_empty_text_returns_none():
    assert (
        resolve_metric_from_text("")
        is None
    )


def test_non_string_returns_none():
    assert (
        resolve_metric_from_text(None)
        is None
    )