from app.database.connection import get_connection


def get_overall_sales():
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


def get_sales_by_region():
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


def get_monthly_sales_trend():
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