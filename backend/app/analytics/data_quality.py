from datetime import datetime, timezone

from app.database.connection import get_connection
from app.database.repositories.base import execute_repository_operation


QUALITY_TABLES = (
    "customers",
    "products",
    "stores",
    "sales",
    "promotions",
    "inventory",
)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1;
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def _get_columns(connection, table_name: str) -> list[dict]:
    rows = connection.execute(
        f"PRAGMA table_info({_quote_identifier(table_name)});"
    ).fetchall()

    return [
        {
            "name": row["name"],
            "pk": row["pk"],
        }
        for row in rows
    ]


def _null_counts(
    connection,
    table_name: str,
    columns: list[dict],
) -> dict:
    if not columns:
        return {}

    expressions = ", ".join(
        (
            f"SUM(CASE WHEN {_quote_identifier(column['name'])} "
            f"IS NULL THEN 1 ELSE 0 END) "
            f"AS {_quote_identifier(column['name'])}"
        )
        for column in columns
    )

    row = connection.execute(
        f"""
        SELECT {expressions}
        FROM {_quote_identifier(table_name)};
        """
    ).fetchone()

    return {
        column["name"]: int(row[column["name"]] or 0)
        for column in columns
        if int(row[column["name"]] or 0) > 0
    }


def _duplicate_count(
    connection,
    table_name: str,
    columns: list[dict],
) -> int:
    primary_keys = [
        column["name"]
        for column in columns
        if column["pk"]
    ]

    if not primary_keys:
        return 0

    key_sql = ", ".join(
        _quote_identifier(column)
        for column in primary_keys
    )

    row = connection.execute(
        f"""
        SELECT COALESCE(
            SUM(duplicate_count - 1),
            0
        ) AS duplicate_rows
        FROM (
            SELECT
                COUNT(*) AS duplicate_count
            FROM {_quote_identifier(table_name)}
            GROUP BY {key_sql}
            HAVING COUNT(*) > 1
        );
        """
    ).fetchone()

    return int(row["duplicate_rows"] or 0)


def _sales_integrity_checks(connection) -> list[dict]:
    required_tables = {
        "sales",
        "stores",
        "products",
        "customers",
    }

    if not all(
        _table_exists(connection, table)
        for table in required_tables
    ):
        return []

    checks = (
        (
            "orphan_store_references",
            """
            SELECT COUNT(*) AS count
            FROM sales s
            LEFT JOIN stores st
                ON s.store_id = st.store_id
            WHERE st.store_id IS NULL;
            """,
        ),
        (
            "orphan_product_references",
            """
            SELECT COUNT(*) AS count
            FROM sales s
            LEFT JOIN products p
                ON s.product_id = p.product_id
            WHERE p.product_id IS NULL;
            """,
        ),
        (
            "orphan_customer_references",
            """
            SELECT COUNT(*) AS count
            FROM sales s
            LEFT JOIN customers c
                ON s.customer_id = c.customer_id
            WHERE c.customer_id IS NULL;
            """,
        ),
    )

    results = []

    for name, query in checks:
        row = connection.execute(query).fetchone()
        count = int(row["count"] or 0)

        results.append(
            {
                "indicator": name,
                "count": count,
                "status": "healthy" if count == 0 else "issue",
            }
        )

    return results


def _invalid_value_checks(connection) -> list[dict]:
    if not _table_exists(connection, "sales"):
        return []

    checks = (
        (
            "negative_quantity",
            """
            SELECT COUNT(*) AS count
            FROM sales
            WHERE quantity < 0;
            """,
        ),
        (
            "negative_revenue",
            """
            SELECT COUNT(*) AS count
            FROM sales
            WHERE sales_amount < 0;
            """,
        ),
    )

    results = []

    for name, query in checks:
        row = connection.execute(query).fetchone()
        count = int(row["count"] or 0)

        results.append(
            {
                "indicator": name,
                "count": count,
                "status": "healthy" if count == 0 else "issue",
            }
        )

    return results


def get_data_quality_indicators() -> dict:
    """
    Calculate deterministic data-quality indicators across the
    synthetic CPG data model.

    The checks cover:
    - missing values
    - duplicate primary-key rows
    - sales referential integrity
    - invalid negative sales values

    The function intentionally reports indicators rather than
    allowing the LLM to decide whether data is trustworthy.
    """

    connection = get_connection()

    try:
        table_results = []
        issue_count = 0

        for table_name in QUALITY_TABLES:
            if not _table_exists(
                connection,
                table_name,
            ):
                continue

            columns = _get_columns(
                connection,
                table_name,
            )

            row_count = connection.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM {_quote_identifier(table_name)};
                """
            ).fetchone()["count"]

            null_counts = _null_counts(
                connection,
                table_name,
                columns,
            )

            duplicate_rows = _duplicate_count(
                connection,
                table_name,
                columns,
            )

            if null_counts:
                issue_count += sum(
                    null_counts.values()
                )

            issue_count += duplicate_rows

            table_results.append(
                {
                    "table": table_name,
                    "row_count": int(row_count),
                    "null_counts": null_counts,
                    "duplicate_primary_key_rows": duplicate_rows,
                }
            )

        integrity_results = _sales_integrity_checks(
            connection
        )

        invalid_results = _invalid_value_checks(
            connection
        )

        issue_count += sum(
            item["count"]
            for item in integrity_results
        )

        issue_count += sum(
            item["count"]
            for item in invalid_results
        )

        if issue_count == 0:
            overall_status = "healthy"
        else:
            overall_status = "issue"

        return {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "overall_status": overall_status,
            "issue_count": issue_count,
            "tables": table_results,
            "referential_integrity": integrity_results,
            "invalid_values": invalid_results,
        }

    finally:
        connection.close()
