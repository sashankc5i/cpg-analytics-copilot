from app.database.connection import get_connection


def get_customer_segment_performance():
    connection = get_connection()

    try:
        query = """
            SELECT
                c.customer_segment,
                COUNT(*) AS transactions,
                COUNT(DISTINCT c.customer_id)
                    AS customers,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2)
                    AS revenue,
                ROUND(AVG(s.sales_amount), 2)
                    AS average_transaction_value
            FROM sales s
            JOIN customers c
                ON s.customer_id = c.customer_id
            GROUP BY c.customer_segment
            ORDER BY revenue DESC;
        """

        results = connection.execute(query).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()