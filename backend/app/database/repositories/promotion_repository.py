from app.database.connection import get_connection
from app.database.repositories.base import (
    execute_repository_operation,
)


def get_promotion_impact_data() -> list[dict]:
    connection = get_connection()

    try:
        query = """
            SELECT
                CASE
                    WHEN discount > 0
                    THEN 'Promotion'
                    ELSE 'No Promotion'
                END AS promotion_status,
                COUNT(*) AS transactions,
                SUM(quantity) AS units_sold,
                ROUND(
                    AVG(quantity),
                    2
                ) AS average_quantity,
                ROUND(
                    SUM(sales_amount),
                    2
                ) AS revenue,
                ROUND(
                    AVG(sales_amount),
                    2
                ) AS average_transaction_value
            FROM sales
            GROUP BY promotion_status;
        """

        results = execute_repository_operation(
            "get_promotion_impact_data",
            lambda: connection.execute(query).fetchall(),
        )

        return [dict(row) for row in results]

    finally:
        connection.close()