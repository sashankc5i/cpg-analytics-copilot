from app.database.connection import get_connection


def get_overall_sales_data() -> dict:
    connection = get_connection()

    try:
        query = """
            SELECT
                COUNT(*) AS transactions,
                SUM(quantity) AS units_sold,
                ROUND(SUM(sales_amount), 2) AS revenue,
                ROUND(AVG(sales_amount), 2)
                    AS average_transaction_value
            FROM sales;
        """

        result = connection.execute(query).fetchone()

        return dict(result)

    finally:
        connection.close()


def get_sales_by_region_data() -> list[dict]:
    connection = get_connection()

    try:
        query = """
            SELECT
                st.region,
                COUNT(*) AS transactions,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2) AS revenue
            FROM sales s
            JOIN stores st
                ON s.store_id = st.store_id
            GROUP BY st.region
            ORDER BY revenue DESC;
        """

        results = connection.execute(query).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()


def get_monthly_sales_trend_data() -> list[dict]:
    connection = get_connection()

    try:
        query = """
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                COUNT(*) AS transactions,
                SUM(quantity) AS units_sold,
                ROUND(SUM(sales_amount), 2) AS revenue
            FROM sales
            GROUP BY month
            ORDER BY month;
        """

        results = connection.execute(query).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()


def get_monthly_revenue_data() -> list[dict]:
    connection = get_connection()

    try:
        query = """
            SELECT
                strftime('%Y-%m', transaction_date) AS period,
                ROUND(SUM(sales_amount), 2) AS actual_revenue
            FROM sales
            GROUP BY period
            ORDER BY period;
        """

        rows = connection.execute(query).fetchall()

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


def get_top_products_data(limit: int = 10) -> list[dict]:
    if not isinstance(limit, int):
        raise ValueError("Product limit must be an integer.")

    if limit < 1 or limit > 50:
        raise ValueError(
            "Product limit must be between 1 and 50."
        )

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