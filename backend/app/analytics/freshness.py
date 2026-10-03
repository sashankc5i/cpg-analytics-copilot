from datetime import date, datetime, timezone

from app.database.connection import get_connection


FRESHNESS_TABLES = (
    "customers",
    "products",
    "stores",
    "sales",
    "promotions",
    "inventory",
)

# Only columns that represent actual business-data coverage should
# participate in freshness calculations.
#
# We intentionally do not automatically treat every column containing
# "date" or "time" as a freshness column because some dates may
# represent future events, effective dates, expiry dates, birthdays,
# or other business attributes rather than source-data coverage.
FRESHNESS_DATE_COLUMNS = {
    "sales": ("transaction_date",),
    "inventory": ("inventory_date",),
    "promotions": ("promotion_date",),
    "customers": (),
    "products": (),
    "stores": (),
}


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


def _available_freshness_columns(
    connection,
    table_name: str,
) -> list[str]:
    """
    Return only explicitly governed freshness columns that actually
    exist in the table.
    """
    configured_columns = FRESHNESS_DATE_COLUMNS.get(
        table_name,
        (),
    )

    if not configured_columns:
        return []

    rows = connection.execute(
        f"PRAGMA table_info({_quote_identifier(table_name)});"
    ).fetchall()

    available_columns = {
        row["name"]
        for row in rows
    }

    return [
        column_name
        for column_name in configured_columns
        if column_name in available_columns
    ]


def _latest_value(
    connection,
    table_name: str,
    column_name: str,
):
    row = connection.execute(
        f"""
        SELECT MAX({_quote_identifier(column_name)}) AS latest_value
        FROM {_quote_identifier(table_name)};
        """
    ).fetchone()

    return row["latest_value"]


def _parse_date(value) -> date | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return date.fromisoformat(
            text[:10]
        )
    except ValueError:
        return None


def get_data_freshness() -> dict:
    """
    Return deterministic freshness metadata based on governed
    business-data coverage dates.

    This application does not currently maintain physical ingestion
    timestamps, so freshness is based on the latest available business
    data date rather than a claim about source-system refresh time.

    Only explicitly configured freshness columns are considered.
    """

    connection = get_connection()

    try:
        sources = []

        for table_name in FRESHNESS_TABLES:
            if not _table_exists(
                connection,
                table_name,
            ):
                continue

            date_columns = _available_freshness_columns(
                connection,
                table_name,
            )

            candidates = []

            for column_name in date_columns:
                latest_value = _latest_value(
                    connection,
                    table_name,
                    column_name,
                )

                parsed = _parse_date(
                    latest_value
                )

                if parsed:
                    candidates.append(
                        (
                            parsed,
                            column_name,
                        )
                    )

            if not candidates:
                sources.append(
                    {
                        "source": table_name,
                        "latest_data_date": None,
                        "date_column": None,
                        "status": "unknown",
                    }
                )
                continue

            latest_date, date_column = max(
                candidates,
                key=lambda item: item[0],
            )

            sources.append(
                {
                    "source": table_name,
                    "latest_data_date": latest_date.isoformat(),
                    "date_column": date_column,
                    "status": "pending",
                }
            )

        available_dates = [
            date.fromisoformat(
                source["latest_data_date"]
            )
            for source in sources
            if source["latest_data_date"]
        ]

        reference_date = (
            max(available_dates)
            if available_dates
            else None
        )

        for source in sources:
            if not source["latest_data_date"]:
                continue

            source_date = date.fromisoformat(
                source["latest_data_date"]
            )

            lag_days = (
                reference_date - source_date
            ).days

            source["lag_days"] = lag_days
            source["status"] = (
                "current"
                if lag_days == 0
                else "lagging"
            )

        return {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "reference_latest_data_date": (
                reference_date.isoformat()
                if reference_date
                else None
            ),
            "freshness_basis": (
                "latest available business data date; "
                "ingestion/refresh timestamps are "
                "not currently stored"
            ),
            "sources": sources,
        }

    finally:
        connection.close()