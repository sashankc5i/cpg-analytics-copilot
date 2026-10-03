from app.database.connection import get_connection
from app.database.repositories.base import (
    execute_repository_operation,
)
from app.analytics.filters import (
    build_sales_filter_sql,
)


def get_promotion_impact_data(
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
                CASE
                    WHEN s.discount > 0
                    THEN 'Promotion'
                    ELSE 'No Promotion'
                END AS promotion_status,
                COUNT(*) AS transactions,
                SUM(s.quantity) AS units_sold,
                ROUND(
                    AVG(s.quantity),
                    2
                ) AS average_quantity,
                ROUND(
                    SUM(s.sales_amount),
                    2
                ) AS revenue,
                ROUND(
                    AVG(s.sales_amount),
                    2
                ) AS average_transaction_value
            FROM sales s
            {joins}
            {filter_sql}
            GROUP BY promotion_status;
        """

        results = execute_repository_operation(
            "get_promotion_impact_data",
            lambda: connection.execute(
                query,
                params,
            ).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()