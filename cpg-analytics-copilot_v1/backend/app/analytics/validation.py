from app.database.connection import get_connection


def run_query(connection, query):
    cursor = connection.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def print_section(title, rows):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    for row in rows:
        print(row)


def main():

    connection = get_connection()

    try:

        # 1. Record counts
        rows = run_query(
            connection,
            """
            SELECT 'customers' AS table_name, COUNT(*) AS count
            FROM customers

            UNION ALL

            SELECT 'products', COUNT(*)
            FROM products

            UNION ALL

            SELECT 'stores', COUNT(*)
            FROM stores

            UNION ALL

            SELECT 'promotions', COUNT(*)
            FROM promotions

            UNION ALL

            SELECT 'inventory', COUNT(*)
            FROM inventory

            UNION ALL

            SELECT 'sales', COUNT(*)
            FROM sales;
            """,
        )

        print_section("RECORD COUNTS", rows)

        # 2. Overall sales
        rows = run_query(
            connection,
            """
            SELECT
                COUNT(*) AS transactions,
                SUM(quantity) AS units_sold,
                ROUND(SUM(sales_amount), 2) AS revenue,
                ROUND(AVG(sales_amount), 2)
                    AS average_transaction_value
            FROM sales;
            """,
        )

        print_section("OVERALL SALES", rows)

        # 3. Revenue by region
        rows = run_query(
            connection,
            """
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
            """,
        )

        print_section("REVENUE BY REGION", rows)

        # 4. Top products
        rows = run_query(
            connection,
            """
            SELECT
                p.product_name,
                p.category,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.sales_amount), 2) AS revenue
            FROM sales s
            JOIN products p
                ON s.product_id = p.product_id
            GROUP BY
                p.product_id,
                p.product_name,
                p.category
            ORDER BY revenue DESC
            LIMIT 10;
            """,
        )

        print_section("TOP 10 PRODUCTS", rows)

        # 5. Monthly trend
        rows = run_query(
            connection,
            """
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                COUNT(*) AS transactions,
                SUM(quantity) AS units_sold,
                ROUND(SUM(sales_amount), 2) AS revenue
            FROM sales
            GROUP BY month
            ORDER BY month;
            """,
        )

        print_section("MONTHLY SALES TREND", rows)

        # 6. Customer segments
        rows = run_query(
            connection,
            """
            SELECT
                c.customer_segment,
                COUNT(*) AS transactions,
                COUNT(DISTINCT c.customer_id) AS customers,
                ROUND(SUM(s.sales_amount), 2) AS revenue,
                ROUND(AVG(s.sales_amount), 2)
                    AS avg_transaction
            FROM sales s
            JOIN customers c
                ON s.customer_id = c.customer_id
            GROUP BY c.customer_segment
            ORDER BY revenue DESC;
            """,
        )

        print_section("CUSTOMER SEGMENT PERFORMANCE", rows)

        # 7. Promotion impact
        rows = run_query(
            connection,
            """
            SELECT
                CASE
                    WHEN discount > 0
                    THEN 'Promotion'
                    ELSE 'No Promotion'
                END AS promotion_status,

                COUNT(*) AS transactions,

                SUM(quantity) AS units_sold,

                ROUND(AVG(quantity), 2)
                    AS avg_quantity,

                ROUND(SUM(sales_amount), 2)
                    AS revenue,

                ROUND(AVG(sales_amount), 2)
                    AS avg_transaction

            FROM sales

            GROUP BY promotion_status;
            """,
        )

        print_section("PROMOTION IMPACT", rows)

        # 8. Stockout rate
        rows = run_query(
            connection,
            """
            SELECT
                st.region,

                COUNT(*) AS inventory_records,

                SUM(i.stockout_flag)
                    AS stockout_events,

                ROUND(
                    100.0 * SUM(i.stockout_flag)
                    / COUNT(*),
                    2
                ) AS stockout_rate

            FROM inventory i

            JOIN stores st
                ON i.store_id = st.store_id

            GROUP BY st.region

            ORDER BY stockout_rate DESC;
            """,
        )

        print_section("STOCKOUT ANALYSIS", rows)

    finally:
        connection.close()


if __name__ == "__main__":
    main()