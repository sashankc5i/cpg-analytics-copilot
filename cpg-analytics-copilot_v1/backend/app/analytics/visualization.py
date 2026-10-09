from __future__ import annotations

from typing import Any


# These mappings describe analytical result fields, not LLM-generated chart
# instructions. The frontend receives only validated labels and numeric values.
_TOOL_CONFIG: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], str, str]] = {
    "get_monthly_sales_trend": (
        "line", ("month", "period", "date"), ("revenue", "sales", "total_revenue"),
        "Monthly Revenue Trend", "Revenue",
    ),
    "get_sales_by_region": (
        "bar", ("region", "Region"), ("revenue", "sales", "total_revenue"),
        "Revenue by Region", "Revenue",
    ),
    "get_top_products": (
        "bar", ("product_name", "product", "Product Name", "Product"),
        ("revenue", "sales", "total_revenue"), "Top Products by Revenue", "Revenue",
    ),
    "get_sales_by_category": (
        "bar", ("category", "Category"), ("revenue", "sales", "total_revenue"),
        "Revenue by Category", "Revenue",
    ),
    "get_sales_by_customer_segment": (
        "bar", ("customer_segment", "segment", "Customer Segment"),
        ("revenue", "sales", "total_revenue"), "Revenue by Customer Segment", "Revenue",
    ),
}


def _as_rows(result: Any) -> list[dict[str, Any]]:
    """Normalize common analytics result shapes into a list of row dictionaries."""
    if isinstance(result, list):
        return [row for row in result if isinstance(row, dict)]

    if isinstance(result, dict):
        # Support tools that wrap records in a named collection.
        for key in ("rows", "data", "results", "records", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

    return []


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _make_visualization(
    rows: list[dict[str, Any]],
    *,
    chart_type: str,
    label_keys: tuple[str, ...],
    value_keys: tuple[str, ...],
    title: str,
    y_title: str,
) -> dict[str, Any] | None:
    labels: list[str] = []
    values: list[float] = []

    for row in rows:
        label = _first_present(row, label_keys)
        value = _numeric(_first_present(row, value_keys))
        if label is None or value is None:
            continue
        labels.append(str(label))
        values.append(value)

    if not labels or len(labels) != len(values):
        return None

    return {
        "type": chart_type,
        "title": title,
        "x": labels,
        "y": values,
    }


def build_visualization(
    tools_used: list[str],
    tool_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Build chart configuration from deterministic analytics tool results.

    The LLM does not create chart data. Results are inspected newest-first, and
    only known, compatible label/value fields are used for the visualization.
    """
    if not tool_results:
        return None

    for tool_result in reversed(tool_results):
        if not isinstance(tool_result, dict):
            continue

        tool_name = str(tool_result.get("tool", ""))
        rows = _as_rows(tool_result.get("result"))
        if not rows:
            continue

        config = _TOOL_CONFIG.get(tool_name)
        if config:
            chart_type, label_keys, value_keys, title, y_title = config
            visualization = _make_visualization(
                rows,
                chart_type=chart_type,
                label_keys=label_keys,
                value_keys=value_keys,
                title=title,
                y_title=y_title,
            )
            if visualization:
                return visualization

        # Safe fallback for common trend results from an approved analytics
        # tool whose name differs, while still requiring recognized fields.
        first_row = rows[0]
        label_keys: tuple[str, ...] | None = None
        value_keys: tuple[str, ...] | None = None
        title = "Analytics Results"
        chart_type = "bar"

        if any(key in first_row for key in ("month", "period", "date")):
            label_keys = ("month", "period", "date")
            chart_type = "line"
            title = "Revenue Trend"
        elif any(key in first_row for key in ("region", "Region")):
            label_keys = ("region", "Region")
            title = "Revenue by Region"
        elif any(key in first_row for key in ("category", "Category")):
            label_keys = ("category", "Category")
            title = "Revenue by Category"
        elif any(key in first_row for key in ("product_name", "product", "Product")):
            label_keys = ("product_name", "product", "Product")
            title = "Product Performance"

        if label_keys:
            value_keys = ("revenue", "sales", "total_revenue")
            visualization = _make_visualization(
                rows,
                chart_type=chart_type,
                label_keys=label_keys,
                value_keys=value_keys,
                title=title,
                y_title="Revenue",
            )
            if visualization:
                return visualization

    return None
