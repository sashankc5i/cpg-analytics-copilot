from app.database.connection import get_connection


def get_stockout_rate():
    connection = get_connection()

    try:
        query = """
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
        """

        results = connection.execute(query).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()