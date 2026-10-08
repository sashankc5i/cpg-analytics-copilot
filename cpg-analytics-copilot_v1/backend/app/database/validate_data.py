from app.database.connection import get_connection


def validate():

    connection = get_connection()

    try:

        tables = [
            "customers",
            "products",
            "stores",
            "promotions",
            "inventory",
            "sales",
        ]

        print("\n=== RECORD COUNTS ===")

        for table in tables:

            result = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()

            print(
                f"{table:<15} {result['count']:,}"
            )

        print("\n=== SALES SUMMARY ===")

        result = connection.execute("""
            SELECT
                COUNT(*) AS transactions,
                SUM(quantity) AS units,
                ROUND(SUM(sales_amount), 2) AS revenue,
                ROUND(AVG(sales_amount), 2) AS avg_transaction
            FROM sales
        """).fetchone()

        print(
            f"Transactions : {result['transactions']:,}"
        )

        print(
            f"Units        : {result['units']:,}"
        )

        print(
            f"Revenue      : ₹{result['revenue']:,.2f}"
        )

        print(
            f"Avg Basket   : ₹{result['avg_transaction']:,.2f}"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    validate()