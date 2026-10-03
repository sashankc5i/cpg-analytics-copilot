from multiprocessing.dummy import connection

from httpx2 import query

from app.database.connection import get_connection
from app.database.repositories.base import (
    execute_repository_operation,
)
from app.analytics.filters import (
    build_sales_filter_sql,
)


def get_overall_sales_data(
    filters: dict | None = None,
) -> dict:
    connection = get_connection()

    try:
        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(filters)

        joins = ""

        if needs_store_join:
            joins += """
                JOIN stores st
                    ON s.store_id = st.store_id
            """

        if needs_product_join:
            joins += """
                JOIN products p
                    ON s.product_id = p.product_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        query = f"""
            SELECT
                COUNT(*) AS transactions,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2) AS revenue,
                ROUND(
                    AVG(s.sales_amount),
                    2
                ) AS average_transaction_value
            FROM sales s
            {joins}
            {filter_sql};
        """

        result = execute_repository_operation(
            "get_overall_sales_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchone(),
        )

        return dict(result)

    finally:
        connection.close()


def get_latest_sales_date(
    filters: dict | None = None,
) -> str | None:
    """
    Return the latest available transaction date.

    Non-date analytical filters are preserved. Existing date filters
    are removed because this function determines the latest available
    date rather than querying an already-selected period.

    Returns:
        Latest transaction date as YYYY-MM-DD, or None when no
        matching sales records exist.
    """

    connection = get_connection()

    try:
        normalized_filters = dict(filters or {})

        normalized_filters.pop(
            "start_date",
            None,
        )

        normalized_filters.pop(
            "end_date",
            None,
        )

        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(
            normalized_filters
        )

        joins = ""

        if needs_store_join:
            joins += """
                JOIN stores st
                    ON s.store_id = st.store_id
            """

        if needs_product_join:
            joins += """
                JOIN products p
                    ON s.product_id = p.product_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        query = f"""
            SELECT
                MAX(s.transaction_date) AS latest_sales_date
            FROM sales s
            {joins}
            {filter_sql};
        """

        result = execute_repository_operation(
            "get_latest_sales_date",
            lambda: connection.execute(
                query,
                params,
            ).fetchone(),
        )

        if not result:
            return None

        return result["latest_sales_date"]

    finally:
        connection.close()


def get_sales_by_region_data(
    filters: dict | None = None,
) -> list[dict]:
    connection = get_connection()

    try:
        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(filters)

        joins = """
            JOIN stores st
                ON s.store_id = st.store_id
        """

        if needs_product_join:
            joins += """
                JOIN products p
                    ON s.product_id = p.product_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        query = f"""
            SELECT
                st.region,
                COUNT(*) AS transactions,
                SUM(s.quantity) AS units_sold,
                ROUND(
                    SUM(s.sales_amount),
                    2
                ) AS revenue
            FROM sales s
            {joins}
            {filter_sql}
            GROUP BY st.region
            ORDER BY revenue DESC;
        """

        results = execute_repository_operation(
            "get_sales_by_region_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()


def get_monthly_sales_trend_data(
    filters: dict | None = None,
) -> list[dict]:
    connection = get_connection()

    try:
        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(filters)

        joins = ""

        if needs_store_join:
            joins += """
                JOIN stores st
                    ON s.store_id = st.store_id
            """

        if needs_product_join:
            joins += """
                JOIN products p
                    ON s.product_id = p.product_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        query = f"""
            SELECT
                strftime(
                    '%Y-%m',
                    s.transaction_date
                ) AS month,
                COUNT(*) AS transactions,
                SUM(s.quantity) AS units_sold,
                ROUND(
                    SUM(s.sales_amount),
                    2
                ) AS revenue
            FROM sales s
            {joins}
            {filter_sql}
            GROUP BY month
            ORDER BY month;
        """

        results = execute_repository_operation(
            "get_monthly_sales_trend_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()


def get_monthly_revenue_data(
    filters: dict | None = None,
) -> list[dict]:
    connection = get_connection()

    try:
        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(filters)

        joins = ""

        if needs_store_join:
            joins += """
                JOIN stores st
                    ON s.store_id = st.store_id
            """

        if needs_product_join:
            joins += """
                JOIN products p
                    ON s.product_id = p.product_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        query = f"""
            SELECT
                strftime(
                    '%Y-%m',
                    s.transaction_date
                ) AS period,
                ROUND(
                    SUM(s.sales_amount),
                    2
                ) AS actual_revenue
            FROM sales s
            {joins}
            {filter_sql}
            GROUP BY period
            ORDER BY period;
        """

        rows = execute_repository_operation(
            "get_monthly_revenue_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchall(),
        )

        return [
            {
                "period": row["period"],
                "actual_revenue": float(
                    row["actual_revenue"] or 0
                ),
            }
            for row in rows
        ]

    finally:
        connection.close()


def get_top_products_data(
    limit: int = 10,
    filters: dict | None = None,
) -> list[dict]:
    if not isinstance(limit, int):
        raise ValueError(
            "Product limit must be an integer."
        )

    if limit < 1 or limit > 50:
        raise ValueError(
            "Product limit must be between 1 and 50."
        )

    connection = get_connection()

    try:
        (
            filter_sql,
            params,
            needs_store_join,
            needs_product_join,
            needs_customer_join,
        ) = build_sales_filter_sql(filters)

        # products are always required by this query.
        joins = """
            JOIN products p
                ON s.product_id = p.product_id
        """

        if needs_store_join:
            joins += """
                JOIN stores st
                    ON s.store_id = st.store_id
            """

        if needs_customer_join:
            joins += """
                JOIN customers c
                    ON s.customer_id = c.customer_id
            """

        # build_sales_filter_sql() may report that products
        # are needed because of category/brand filters.
        # The products join is already present above.
        _ = needs_product_join

        query = f"""
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                p.brand,
                SUM(s.quantity) AS units_sold,
                ROUND(
                    SUM(s.sales_amount),
                    2
                ) AS revenue
            FROM sales s
            {joins}
            {filter_sql}
            GROUP BY
                p.product_id,
                p.product_name,
                p.category,
                p.brand
            ORDER BY revenue DESC
            LIMIT ?;
        """

        query_params = (
            *params,
            limit,
        )

        results = execute_repository_operation(
            "get_top_products_data",
            lambda: connection.execute(
                query,
                query_params,
            ).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()