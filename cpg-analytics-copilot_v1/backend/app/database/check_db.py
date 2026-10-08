from app.database.connection import get_connection


def check_tables():
    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        for table in tables:
            print(table["name"])

    finally:
        connection.close()


if __name__ == "__main__":
    check_tables()