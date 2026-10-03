from app.analytics.filters import normalize_filters
from app.analytics.sales import (
    get_overall_sales,
    get_sales_by_region,
)
from app.analytics.products import (
    get_sales_by_category,
    get_top_products,
)


SUPPORTED_DRILLDOWN_LEVELS = (
    "company",
    "region",
    "category",
    "product",
)

DEFAULT_PRODUCT_LIMIT = 10
MAX_PRODUCT_LIMIT = 50


def get_hierarchical_drilldown(
    level: str,
    filters: dict | None = None,
    limit: int = DEFAULT_PRODUCT_LIMIT,
) -> dict:
    """
    Return deterministic CPG results at the requested hierarchy level.

    Supported hierarchy:
        company -> region -> category -> product

    Existing governed filters are preserved so a drill-down can be
    performed inside an already selected analytical scope.
    """

    if not isinstance(level, str):
        raise TypeError("Drill-down level must be a string.")

    normalized_level = level.strip().lower()

    if normalized_level not in SUPPORTED_DRILLDOWN_LEVELS:
        raise ValueError(
            "Unsupported drill-down level. "
            f"Supported levels: {', '.join(SUPPORTED_DRILLDOWN_LEVELS)}."
        )

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Drill-down limit must be an integer.")

    if limit < 1 or limit > MAX_PRODUCT_LIMIT:
        raise ValueError(
            "Drill-down limit must be between 1 and 50."
        )

    normalized_filters = normalize_filters(filters)

    if normalized_level == "company":
        result = get_overall_sales(
            filters=normalized_filters,
        )

        results = [result]

    elif normalized_level == "region":
        results = get_sales_by_region(
            filters=normalized_filters,
        )

    elif normalized_level == "category":
        results = get_sales_by_category(
            filters=normalized_filters,
        )

    else:
        results = get_top_products(
            limit=limit,
            filters=normalized_filters,
        )

    return {
        "hierarchy": [
            "company",
            "region",
            "category",
            "product",
        ],
        "level": normalized_level,
        "filters": normalized_filters,
        "results": results,
    }
