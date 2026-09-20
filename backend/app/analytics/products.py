from app.database.connection import get_connection


def get_top_products(limit: int = 10):
    connection = get_connection()

    try:
        query = """
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                p.brand,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2) AS revenue
            FROM sales s
            JOIN products p
                ON s.product_id = p.product_id
            GROUP BY
                p.product_id,
                p.product_name,
                p.category,
                p.brand
            ORDER BY revenue DESC
            LIMIT ?;
        """

        results = connection.execute(
            query,
            (limit,),
        ).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()


def get_sales_by_category():
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

        results = connection.execute(query).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()