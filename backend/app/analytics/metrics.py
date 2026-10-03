from copy import deepcopy


METRIC_REGISTRY = {
    "revenue": {
        "metric_id": "revenue",
        "display_name": "Revenue",
        "definition": (
            "Total sales revenue generated during the selected "
            "period and analytical scope."
        ),
        "calculation": "SUM(sales.revenue)",
        "format": "currency",
        "aliases": [
            "revenue",
            "sales revenue",
            "turnover",
        ],
        "tools": [
    "get_overall_sales",
    "get_sales_by_region",
    "get_monthly_sales_trend",
    "get_sales_variance",
],
    },
    "transactions": {
        "metric_id": "transactions",
        "display_name": "Transactions",
        "definition": (
            "Total number of sales transactions during the "
            "selected period and analytical scope."
        ),
        "calculation": "COUNT(sales.transaction_id)",
        "format": "integer",
        "aliases": [
            "transactions",
            "transaction count",
            "number of transactions",
            "purchases",
            "number of purchases",
        ],
            "tools": [
                "get_overall_sales",
            "get_sales_by_region",
            "get_monthly_sales_trend",
        ],
    },
    "units_sold": {
        "metric_id": "units_sold",
        "display_name": "Units Sold",
        "definition": (
            "Total quantity of products sold during the selected "
            "period and analytical scope."
        ),
        "calculation": "SUM(sales.units_sold)",
        "format": "integer",
        "aliases": [
            "units sold",
            "units",
            "quantity sold",
            "volume sold",
        ],
        "tools": [
    "get_overall_sales",
    "get_sales_by_region",
    "get_monthly_sales_trend",
    "get_sales_variance",
],
    },
    "average_transaction_value": {
        "metric_id": "average_transaction_value",
        "display_name": "Average Transaction Value",
        "definition": (
            "Average revenue generated per sales transaction "
            "during the selected period and analytical scope."
        ),
        "calculation": (
            "SUM(sales.revenue) / COUNT(sales.transaction_id)"
        ),
        "format": "currency",
        "aliases": [
            "average transaction value",
            "atv",
            "average basket value",
            "average purchase value",
        ],
        "tools": [
    "get_overall_sales",
    "get_sales_by_region",
    "get_sales_variance",
],
    },
    "stockout_rate": {
        "metric_id": "stockout_rate",
        "display_name": "Stockout Rate",
        "definition": (
            "Percentage of relevant inventory observations "
            "where the product was unavailable due to stockout."
        ),
        "calculation": (
            "stockout observations / total inventory observations"
        ),
        "format": "percentage",
        "aliases": [
            "stockout rate",
            "stockouts",
            "stockout percentage",
            "out of stock rate",
        ],
        "tools": [
            "get_stockout_rate",
        ],
    },
}


def get_metric(metric_id: str) -> dict:
    """
    Return a copy of a governed metric definition.

    Raises:
        KeyError: If the metric does not exist.
    """

    if not isinstance(metric_id, str):
        raise TypeError(
            "metric_id must be a string."
        )

    normalized_id = metric_id.strip().lower()

    if normalized_id not in METRIC_REGISTRY:
        raise KeyError(
            f"Unknown metric: {metric_id}"
        )

    return deepcopy(
        METRIC_REGISTRY[normalized_id]
    )


def list_metrics() -> list[dict]:
    """
    Return all governed metric definitions.
    """

    return [
        deepcopy(metric)
        for metric in METRIC_REGISTRY.values()
    ]


def resolve_metric_alias(
    text: str,
) -> dict | None:
    """
    Resolve an explicit metric alias.

    This function intentionally performs deterministic matching.
    It does not use an LLM and does not guess between metrics.

    Returns:
        A governed metric definition when exactly one metric
        can be resolved, otherwise None.
    """

    if not isinstance(text, str):
        return None

    normalized_text = (
        " ".join(
            text.strip().lower().split()
        )
    )

    if not normalized_text:
        return None

    matches = []

    for metric in METRIC_REGISTRY.values():
        aliases = metric.get(
            "aliases",
            [],
        )

        for alias in aliases:
            normalized_alias = (
                " ".join(
                    alias.strip().lower().split()
                )
            )

            if not normalized_alias:
                continue

            if normalized_text == normalized_alias:
                matches.append(
                    metric["metric_id"]
                )
                break

    if len(matches) != 1:
        return None

    return get_metric(matches[0])


def resolve_metric_from_text(
    text: str,
) -> dict | None:
    """
    Resolve a governed metric from natural-language text.

    Matching is deterministic and intentionally conservative.

    A metric is returned only when exactly one governed metric
    can be identified from the text.
    """

    if not isinstance(text, str):
        return None

    normalized_text = (
        " ".join(
            text.strip().lower().split()
        )
    )

    if not normalized_text:
        return None

    matches = set()

    for metric in METRIC_REGISTRY.values():
        for alias in metric.get(
            "aliases",
            [],
        ):
            normalized_alias = (
                " ".join(
                    alias.strip().lower().split()
                )
            )

            if not normalized_alias:
                continue

            if normalized_alias in normalized_text:
                matches.add(
                    metric["metric_id"]
                )

    if len(matches) != 1:
        return None

    metric_id = next(
        iter(matches)
    )

    return get_metric(metric_id)