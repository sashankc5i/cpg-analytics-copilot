from __future__ import annotations

from datetime import date
from typing import Any


FILTER_KEYS = (
    "start_date",
    "end_date",
    "region",
    "category",
    "brand",
    "customer_segment",
)

MAX_FILTER_VALUES = 10


def _normalize_value(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []

    values = value if isinstance(value, list) else [value]

    if len(values) > MAX_FILTER_VALUES:
        raise ValueError(
            f"Filter '{field_name}' supports at most "
            f"{MAX_FILTER_VALUES} values."
        )

    normalized = []

    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Filter '{field_name}' must contain non-empty strings."
            )

        normalized.append(item.strip())

    return normalized


def normalize_filters(filters: dict | None) -> dict[str, Any]:
    """Validate and normalize the supported natural-language filter contract."""

    if filters is None:
        return {}

    if not isinstance(filters, dict):
        raise ValueError("Filters must be a JSON object.")

    unknown = set(filters) - set(FILTER_KEYS)

    if unknown:
        raise ValueError(
            "Unsupported filters: "
            + ", ".join(sorted(unknown))
        )

    normalized: dict[str, Any] = {}

    for field in FILTER_KEYS:

        if field not in filters:
            continue

        if field in {"start_date", "end_date"}:

            value = filters[field]

            if value is None:
                continue

            if not isinstance(value, str):
                raise ValueError(
                    f"Filter '{field}' must be a YYYY-MM-DD string."
                )

            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    f"Filter '{field}' must be a valid YYYY-MM-DD date."
                ) from exc

            normalized[field] = value
            continue

        values = _normalize_value(
            filters[field],
            field,
        )

        if values:
            normalized[field] = values

    start_date = normalized.get("start_date")
    end_date = normalized.get("end_date")

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "Filter 'start_date' must be on or before 'end_date'."
        )

    return normalized


def build_sales_filter_sql(
    filters: dict | None,
    *,
    sales_alias: str = "s",
    store_alias: str = "st",
    product_alias: str = "p",
    customer_alias: str = "c",
    date_column: str | None = None,
) -> tuple[str, list[Any], bool, bool, bool]:

    """Build a safe WHERE clause for filters over the sales star schema."""

    normalized = normalize_filters(filters)

    clauses: list[str] = []
    params: list[Any] = []

    date_expression = (
        date_column
        or f"{sales_alias}.transaction_date"
    )

    if "start_date" in normalized:
        clauses.append(
            f"DATE({date_expression}) >= DATE(?)"
        )
        params.append(
            normalized["start_date"]
        )

    if "end_date" in normalized:
        clauses.append(
            f"DATE({date_expression}) <= DATE(?)"
        )
        params.append(
            normalized["end_date"]
        )

    needs_store_join = "region" in normalized

    needs_product_join = bool(
        {"category", "brand"} & normalized.keys()
    )

    needs_customer_join = (
        "customer_segment" in normalized
    )

    for field, alias in (
        ("region", store_alias),
        ("category", product_alias),
        ("brand", product_alias),
        ("customer_segment", customer_alias),
    ):

        values = normalized.get(field)

        if not values:
            continue

        placeholders = ", ".join(
            "?" for _ in values
        )

        clauses.append(
            f"{alias}.{field} IN ({placeholders})"
        )

        params.extend(values)

    if not clauses:
        return (
            "",
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        )

    return (
        "WHERE " + " AND ".join(clauses),
        params,
        needs_store_join,
        needs_product_join,
        needs_customer_join,
    )