from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.analytics.comparison import resolve_comparison_period
from app.analytics.filters import normalize_filters
from app.analytics.products import get_sales_by_category, get_top_products
from app.analytics.sales import get_overall_sales, get_sales_by_region

SUPPORTED_DRIVER_METRICS = {
    "revenue": "revenue",
    "transactions": "transactions",
    "units_sold": "units_sold",
}

SUPPORTED_DRIVER_LEVELS = ("region", "category", "product")


def _period_filters(filters: dict | None, start_date: str, end_date: str) -> dict:
    normalized = normalize_filters(filters)
    result = deepcopy(normalized)
    result["start_date"] = start_date
    result["end_date"] = end_date
    return result


def _rows_for_level(level: str, filters: dict | None) -> list[dict[str, Any]]:
    if level == "region":
        result = get_sales_by_region(filters=filters)
    elif level == "category":
        result = get_sales_by_category(filters=filters)
    elif level == "product":
        result = get_top_products(limit=50, filters=filters)
    else:
        raise ValueError(f"Unsupported driver level: {level}")

    if not isinstance(result, list):
        return []
    return [row for row in result if isinstance(row, dict)]


def _entity_name(level: str, row: dict[str, Any]) -> str:
    keys = {
        "region": ("region", "Region"),
        "category": ("category", "Category"),
        "product": ("product_name", "product", "Product Name", "Product"),
    }
    for key in keys[level]:
        if key in row and row[key] is not None:
            return str(row[key])
    return "Unknown"


def _metric_value(row: dict[str, Any], metric_key: str) -> float:
    value = row.get(metric_key)
    if value is None:
        return 0.0
    return float(value)


def get_driver_decomposition(
    metric_id: str,
    current_start: str,
    current_end: str,
    comparison_type: str = "previous_period",
    level: str = "region",
    filters: dict | None = None,
) -> dict[str, Any]:
    metric = metric_id.strip().lower()
    level = level.strip().lower()
    if metric not in SUPPORTED_DRIVER_METRICS:
        raise ValueError(f"Unsupported driver metric: {metric_id}")
    if level not in SUPPORTED_DRIVER_LEVELS:
        raise ValueError(f"Unsupported driver level: {level}")

    comparison = resolve_comparison_period(
        current_start=current_start,
        current_end=current_end,
        comparison_type=comparison_type,
    )

    current_filters = _period_filters(filters, comparison.current_start, comparison.current_end)
    comparison_filters = _period_filters(filters, comparison.comparison_start, comparison.comparison_end)

    current_rows = _rows_for_level(level, current_filters)
    comparison_rows = _rows_for_level(level, comparison_filters)

    current_by_entity = {
        _entity_name(level, row): _metric_value(row, SUPPORTED_DRIVER_METRICS[metric])
        for row in current_rows
    }
    comparison_by_entity = {
        _entity_name(level, row): _metric_value(row, SUPPORTED_DRIVER_METRICS[metric])
        for row in comparison_rows
    }

    entities = sorted(set(current_by_entity) | set(comparison_by_entity))
    drivers = []
    for entity in entities:
        current_value = current_by_entity.get(entity, 0.0)
        comparison_value = comparison_by_entity.get(entity, 0.0)
        delta = current_value - comparison_value
        drivers.append({
            "entity": entity,
            "current_value": round(current_value, 2),
            "comparison_value": round(comparison_value, 2),
            "absolute_change": round(delta, 2),
            "direction": "increase" if delta > 0 else "decrease" if delta < 0 else "no_change",
        })

    total_current = sum(current_by_entity.values())
    total_comparison = sum(comparison_by_entity.values())
    total_change = total_current - total_comparison

    return {
        "metric": metric,
        "level": level,
        "comparison_type": comparison_type,
        "current_period": {
            "start_date": comparison.current_start,
            "end_date": comparison.current_end,
        },
        "comparison_period": {
            "start_date": comparison.comparison_start,
            "end_date": comparison.comparison_end,
        },
        "filters": normalize_filters(filters),
        "current_total": round(total_current, 2),
        "comparison_total": round(total_comparison, 2),
        "total_change": round(total_change, 2),
        "drivers": drivers,
    }


def get_contribution_analysis(
    metric_id: str,
    current_start: str,
    current_end: str,
    comparison_type: str = "previous_period",
    level: str = "region",
    filters: dict | None = None,
) -> dict[str, Any]:
    decomposition = get_driver_decomposition(
        metric_id=metric_id,
        current_start=current_start,
        current_end=current_end,
        comparison_type=comparison_type,
        level=level,
        filters=filters,
    )

    total_change = decomposition["total_change"]
    drivers = []
    for driver in decomposition["drivers"]:
        delta = driver["absolute_change"]
        contribution = None if total_change == 0 else (delta / total_change) * 100
        item = dict(driver)
        item["contribution_percentage"] = (
            round(contribution, 2) if contribution is not None else None
        )
        drivers.append(item)

    drivers.sort(
        key=lambda item: abs(item["absolute_change"]),
        reverse=True,
    )

    result = dict(decomposition)
    result["drivers"] = drivers
    result["analysis"] = "contribution_to_total_change"
    return result
