from typing import Any


def build_visualization(
    tools_used: list[str],
    tool_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Convert deterministic analytics results into a
    frontend-friendly visualization configuration.

    The backend provides data.
    React owns the actual rendering through Plotly.
    """

    if not tool_results:
        return None

    # Most recent analytical result is usually the
    # most relevant result for visualization.
    for tool_result in reversed(tool_results):

        tool_name = tool_result.get("tool")
        result = tool_result.get("result")

        if not isinstance(result, list):
            continue

        if not result:
            continue

        # --------------------------------------------------
        # Monthly Revenue Trend
        # --------------------------------------------------

        if tool_name == "get_monthly_sales_trend":

            months = [
                row.get("month")
                for row in result
                if row.get("month") is not None
            ]

            revenue = [
                row.get("revenue", 0)
                for row in result
            ]

            if months and revenue:

                return {
                    "type": "line",
                    "title": "Monthly Revenue",
                    "x": months,
                    "y": revenue,
                }

        # --------------------------------------------------
        # Revenue By Region
        # --------------------------------------------------

        if tool_name == "get_sales_by_region":

            regions = [
                row.get("region")
                for row in result
                if row.get("region") is not None
            ]

            revenue = [
                row.get("revenue", 0)
                for row in result
            ]

            if regions and revenue:

                return {
                    "type": "bar",
                    "title": "Revenue by Region",
                    "x": regions,
                    "y": revenue,
                }

        # --------------------------------------------------
        # Top Products
        # --------------------------------------------------

        if tool_name == "get_top_products":

            products = [
                row.get("product_name")
                for row in result
                if row.get("product_name") is not None
            ]

            revenue = [
                row.get("revenue", 0)
                for row in result
            ]

            if products and revenue:

                return {
                    "type": "bar",
                    "title": "Top Products by Revenue",
                    "x": products,
                    "y": revenue,
                }

        # --------------------------------------------------
        # Category Performance
        # --------------------------------------------------

        if tool_name == "get_sales_by_category":

            categories = [
                row.get("category")
                for row in result
                if row.get("category") is not None
            ]

            revenue = [
                row.get("revenue", 0)
                for row in result
            ]

            if categories and revenue:

                return {
                    "type": "bar",
                    "title": "Revenue by Category",
                    "x": categories,
                    "y": revenue,
                }

    return None