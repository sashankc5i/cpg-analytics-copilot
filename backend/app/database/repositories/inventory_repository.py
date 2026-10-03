from app.database.connection import get_connection
from app.database.repositories.base import (
    execute_repository_operation,
)
from app.analytics.filters import (
    normalize_filters,
)


def get_stockout_rate_data(
    filters: dict | None = None,
) -> list[dict]:
    normalized_filters = normalize_filters(
        filters
    )

    unsupported_filters = {
        key
        for key in normalized_filters
        if key != "region"
    }

    if unsupported_filters:
        raise ValueError(
            "Stockout rate does not currently support "
            "these filters: "
            + ", ".join(
                sorted(unsupported_filters)
            )
        )

    connection = get_connection()

    try:
        params: list[str] = []
        where_clause = ""

        regions = normalized_filters.get(
            "region"
        )

        if regions:
            placeholders = ", ".join(
                "?" for _ in regions
            )

            where_clause = (
                f"WHERE st.region IN ({placeholders})"
            )

            params.extend(regions)

        query = f"""
            SELECT
                st.region,
                COUNT(*) AS inventory_records,
                SUM(i.stockout_flag) AS stockout_events,
                ROUND(
                    100.0
                    * SUM(i.stockout_flag)
                    / COUNT(*),
                    2
                ) AS stockout_rate
            FROM inventory i
            JOIN stores st
                ON i.store_id = st.store_id
            {where_clause}
            GROUP BY st.region
            ORDER BY stockout_rate DESC;
        """

        results = execute_repository_operation(
            "get_stockout_rate_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()