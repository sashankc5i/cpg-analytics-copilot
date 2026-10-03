import sqlite3
from unittest.mock import patch

from app.analytics.freshness import (
    get_data_freshness,
)


def _connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE sales (
            transaction_id INTEGER PRIMARY KEY,
            transaction_date TEXT
        );

        CREATE TABLE inventory (
            inventory_id INTEGER PRIMARY KEY,
            inventory_date TEXT
        );

        INSERT INTO sales VALUES
            (1, '2026-09-29'),
            (2, '2026-09-30');

        INSERT INTO inventory VALUES
            (1, '2026-09-30');
        """
    )

    return connection


@patch(
    "app.analytics.freshness.get_connection"
)
def test_freshness_returns_latest_source_dates(
    mock_get_connection,
):
    connection = _connection()
    mock_get_connection.return_value = connection

    result = get_data_freshness()

    assert result["reference_latest_data_date"] == (
        "2026-09-30"
    )

    sales = next(
        item
        for item in result["sources"]
        if item["source"] == "sales"
    )

    inventory = next(
        item
        for item in result["sources"]
        if item["source"] == "inventory"
    )

    assert sales["latest_data_date"] == "2026-09-30"
    assert sales["date_column"] == "transaction_date"
    assert sales["status"] == "current"

    assert inventory["latest_data_date"] == "2026-09-30"
    assert inventory["date_column"] == "inventory_date"
    assert inventory["status"] == "current"


@patch(
    "app.analytics.freshness.get_connection"
)
def test_freshness_identifies_lagging_source(
    mock_get_connection,
):
    connection = _connection()

    connection.execute(
        """
        UPDATE inventory
        SET inventory_date = '2026-09-25';
        """
    )

    connection.commit()

    mock_get_connection.return_value = connection

    result = get_data_freshness()

    inventory = next(
        item
        for item in result["sources"]
        if item["source"] == "inventory"
    )

    assert inventory["latest_data_date"] == "2026-09-25"
    assert inventory["lag_days"] == 5
    assert inventory["status"] == "lagging"


@patch(
    "app.analytics.freshness.get_connection"
)
def test_freshness_handles_source_without_date_columns(
    mock_get_connection,
):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY
        );
        """
    )

    mock_get_connection.return_value = connection

    result = get_data_freshness()

    products = next(
        item
        for item in result["sources"]
        if item["source"] == "products"
    )

    assert products["latest_data_date"] is None
    assert products["date_column"] is None
    assert products["status"] == "unknown"


@patch(
    "app.analytics.freshness.get_connection"
)
def test_freshness_ignores_unrelated_date_columns(
    mock_get_connection,
):
    """
    A date-like column that does not represent data coverage must
    not redefine source freshness.
    """
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            birth_date TEXT,
            signup_date TEXT
        );

        INSERT INTO customers VALUES
            (1, '2026-12-28', '2026-09-15'),
            (2, '2026-11-20', '2026-09-20');
        """
    )

    mock_get_connection.return_value = connection

    result = get_data_freshness()

    customers = next(
        item
        for item in result["sources"]
        if item["source"] == "customers"
    )

    assert customers["latest_data_date"] is None
    assert customers["date_column"] is None
    assert customers["status"] == "unknown"


@patch(
    "app.analytics.freshness.get_connection"
)
def test_freshness_uses_governed_sales_date_column(
    mock_get_connection,
):
    """
    Only transaction_date should determine sales freshness.
    """
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE sales (
            transaction_id INTEGER PRIMARY KEY,
            transaction_date TEXT,
            future_event_date TEXT
        );

        INSERT INTO sales VALUES
            (1, '2026-09-29', '2026-12-31'),
            (2, '2026-09-30', '2027-01-15');
        """
    )

    mock_get_connection.return_value = connection

    result = get_data_freshness()

    sales = next(
        item
        for item in result["sources"]
        if item["source"] == "sales"
    )

    assert sales["latest_data_date"] == "2026-09-30"
    assert sales["date_column"] == "transaction_date"