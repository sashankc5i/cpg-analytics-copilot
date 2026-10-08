from app.database.connection import get_connection
from app.database.repositories.base import (
    execute_repository_operation,
)


def get_sales_by_category_data() -> list[dict]:
    connection = get_connection()

    try:
        query = """
            SELECT
                p.category,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2) AS revenue
            FROM sales s
            JOIN products p
                ON s.product_id = p.product_id
            GROUP BY p.category
            ORDER BY revenue DESC;
        """

        results = execute_repository_operation(
            "get_sales_by_category_data",
            lambda: connection.execute(query).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()