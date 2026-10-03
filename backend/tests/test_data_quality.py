import sqlite3
from unittest.mock import patch

from app.analytics.data_quality import (
    get_data_quality_indicators,
)


def _connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript(
        """
        CREATE TABLE stores (
            store_id INTEGER PRIMARY KEY
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY
        );

        CREATE TABLE sales (
            transaction_id INTEGER PRIMARY KEY,
            store_id INTEGER,
            product_id INTEGER,
            customer_id INTEGER,
            quantity INTEGER,
            sales_amount REAL
        );

        CREATE TABLE promotions (
            promotion_id INTEGER PRIMARY KEY
        );

        CREATE TABLE inventory (
            inventory_id INTEGER PRIMARY KEY
        );

        INSERT INTO stores VALUES (1);
        INSERT INTO products VALUES (1);
        INSERT INTO customers VALUES (1);

        INSERT INTO sales VALUES
            (1, 1, 1, 1, 2, 100.0),
            (2, 1, 1, 1, 3, 150.0);
        """
    )

    return connection


@patch(
    "app.analytics.data_quality.get_connection"
)
def test_healthy_dataset(mock_get_connection):
    connection = _connection()
    mock_get_connection.return_value = connection

    result = get_data_quality_indicators()

    assert result["overall_status"] == "healthy"
    assert result["issue_count"] == 0

    sales = next(
        item
        for item in result["tables"]
        if item["table"] == "sales"
    )

    assert sales["row_count"] == 2
    assert sales["null_counts"] == {}
    assert sales["duplicate_primary_key_rows"] == 0


@patch(
    "app.analytics.data_quality.get_connection"
)
def test_quality_indicators_detect_orphans_and_invalid_values(
    mock_get_connection,
):
    connection = _connection()

    connection.execute(
        """
        INSERT INTO sales
        VALUES (3, 999, 999, 999, -2, -50.0);
        """
    )
    connection.commit()

    mock_get_connection.return_value = connection

    result = get_data_quality_indicators()

    assert result["overall_status"] == "issue"

    integrity = {
        item["indicator"]: item["count"]
        for item in result["referential_integrity"]
    }

    invalid = {
        item["indicator"]: item["count"]
        for item in result["invalid_values"]
    }

    assert integrity["orphan_store_references"] == 1
    assert integrity["orphan_product_references"] == 1
    assert integrity["orphan_customer_references"] == 1

    assert invalid["negative_quantity"] == 1
    assert invalid["negative_revenue"] == 1


@patch(
    "app.analytics.data_quality.get_connection"
)
def test_quality_indicators_detect_nulls(
    mock_get_connection,
):
    connection = _connection()

    connection.execute(
        """
        INSERT INTO sales
        VALUES (3, NULL, 1, 1, 1, 50.0);
        """
    )
    connection.commit()

    mock_get_connection.return_value = connection

    result = get_data_quality_indicators()

    sales = next(
        item
        for item in result["tables"]
        if item["table"] == "sales"
    )

    assert sales["null_counts"]["store_id"] == 1
