from unittest.mock import MagicMock, patch

import pytest
import sqlite3
from app.database.repositories.base import (
    RepositoryError,
    execute_repository_operation,
)
from app.database.repositories.base import RepositoryError

from app.database.repositories.customer_repository import (
    get_customer_segment_performance_data,
)
from app.database.repositories.inventory_repository import (
    get_stockout_rate_data,
)
from app.database.repositories.product_repository import (
    get_sales_by_category_data,
)
from app.database.repositories.promotion_repository import (
    get_promotion_impact_data,
)
from app.database.repositories.sales_repository import (
    get_monthly_revenue_data,
    get_monthly_sales_trend_data,
    get_overall_sales_data,
    get_sales_by_region_data,
    get_top_products_data,
)


def create_mock_connection(
    fetchone_result=None,
    fetchall_result=None,
):
    connection = MagicMock()

    if fetchone_result is not None:
        connection.execute.return_value.fetchone.return_value = (
            fetchone_result
        )

    if fetchall_result is not None:
        connection.execute.return_value.fetchall.return_value = (
            fetchall_result
        )

    return connection


def test_get_overall_sales_data_returns_dict():
    mock_row = {
        "transactions": 100,
        "units_sold": 250,
        "revenue": 50000.0,
        "average_transaction_value": 500.0,
    }

    connection = create_mock_connection(
        fetchone_result=mock_row,
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        result = get_overall_sales_data()

    assert result == mock_row
    connection.close.assert_called_once()


def test_get_sales_by_region_data_returns_rows():
    mock_rows = [
        {
            "region": "South",
            "transactions": 100,
            "units_sold": 250,
            "revenue": 50000.0,
        },
        {
            "region": "West",
            "transactions": 80,
            "units_sold": 200,
            "revenue": 40000.0,
        },
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        result = get_sales_by_region_data()

    assert result == mock_rows
    connection.close.assert_called_once()


def test_get_monthly_sales_trend_data_returns_rows():
    mock_rows = [
        {
            "month": "2026-01",
            "transactions": 100,
            "units_sold": 250,
            "revenue": 50000.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        result = get_monthly_sales_trend_data()

    assert result == mock_rows
    connection.close.assert_called_once()


def test_get_monthly_revenue_data_normalizes_revenue():
    mock_rows = [
        {
            "period": "2026-01",
            "actual_revenue": 50000,
        },
        {
            "period": "2026-02",
            "actual_revenue": None,
        },
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        result = get_monthly_revenue_data()

    assert result == [
        {
            "period": "2026-01",
            "actual_revenue": 50000.0,
        },
        {
            "period": "2026-02",
            "actual_revenue": 0.0,
        },
    ]

    connection.close.assert_called_once()


def test_get_top_products_data_rejects_non_integer_limit():
    with pytest.raises(
        ValueError,
        match="Product limit must be an integer.",
    ):
        get_top_products_data("10")


def test_get_top_products_data_rejects_invalid_limit():
    with pytest.raises(
        ValueError,
        match="Product limit must be between 1 and 50.",
    ):
        get_top_products_data(51)


def test_get_top_products_data_passes_valid_limit_to_database():
    mock_rows = [
        {
            "product_id": 1,
            "product_name": "Product 1",
            "category": "Food & Beverages",
            "brand": "Nexa",
            "units_sold": 100,
            "revenue": 10000.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        result = get_top_products_data(5)

    assert result == mock_rows

    connection.execute.assert_called_once()

    call_args = connection.execute.call_args

    assert call_args.args[1] == (5,)
    connection.close.assert_called_once()


def test_get_customer_segment_performance_data_returns_rows():
    mock_rows = [
        {
            "customer_segment": "Premium",
            "transactions": 100,
            "customers": 50,
            "units_sold": 200,
            "revenue": 50000.0,
            "average_transaction_value": 500.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        (
            "app.database.repositories."
            "customer_repository.get_connection"
        ),
        return_value=connection,
    ):
        result = get_customer_segment_performance_data()

    assert result == mock_rows
    connection.close.assert_called_once()


def test_get_sales_by_category_data_returns_rows():
    mock_rows = [
        {
            "category": "Food & Beverages",
            "units_sold": 500,
            "revenue": 100000.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        (
            "app.database.repositories."
            "product_repository.get_connection"
        ),
        return_value=connection,
    ):
        result = get_sales_by_category_data()

    assert result == mock_rows
    connection.close.assert_called_once()


def test_get_promotion_impact_data_returns_rows():
    mock_rows = [
        {
            "promotion_status": "Promotion",
            "transactions": 100,
            "units_sold": 250,
            "average_quantity": 2.5,
            "revenue": 50000.0,
            "average_transaction_value": 500.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        (
            "app.database.repositories."
            "promotion_repository.get_connection"
        ),
        return_value=connection,
    ):
        result = get_promotion_impact_data()

    assert result == mock_rows
    connection.close.assert_called_once()


def test_get_stockout_rate_data_returns_rows():
    mock_rows = [
        {
            "region": "South",
            "inventory_records": 1000,
            "stockout_events": 50,
            "stockout_rate": 5.0,
        }
    ]

    connection = create_mock_connection(
        fetchall_result=mock_rows,
    )

    with patch(
        (
            "app.database.repositories."
            "inventory_repository.get_connection"
        ),
        return_value=connection,
    ):
        result = get_stockout_rate_data()

    assert result == mock_rows
    connection.close.assert_called_once()
def test_sales_repository_wraps_database_error():
    connection = MagicMock()

    connection.execute.side_effect = sqlite3.OperationalError(
        "database is unavailable"
    )

    with patch(
        "app.database.repositories.sales_repository.get_connection",
        return_value=connection,
    ):
        with pytest.raises(
            RepositoryError,
            match="Repository operation failed: "
            "get_sales_by_region_data.",
        ) as error:
            get_sales_by_region_data()

    assert isinstance(
        error.value.__cause__,
        sqlite3.OperationalError,
    )

    connection.close.assert_called_once()
def test_execute_repository_operation_returns_callback_result():
    result = execute_repository_operation(
        "test_operation",
        lambda: {"value": 123},
    )

    assert result == {"value": 123}


def test_execute_repository_operation_wraps_sqlite_error():
    original_error = sqlite3.OperationalError(
        "database unavailable"
    )

    def failing_operation():
        raise original_error

    with pytest.raises(
        RepositoryError,
        match="Repository operation failed: test_operation.",
    ) as error:
        execute_repository_operation(
            "test_operation",
            failing_operation,
        )

    assert error.value.__cause__ is original_error
def test_customer_repository_wraps_database_error():
    connection = MagicMock()

    connection.execute.side_effect = sqlite3.OperationalError(
        "database unavailable"
    )

    with patch(
        (
            "app.database.repositories."
            "customer_repository.get_connection"
        ),
        return_value=connection,
    ):
        with pytest.raises(
            RepositoryError,
            match=(
                "Repository operation failed: "
                "get_customer_segment_performance_data."
            ),
        ) as error:
            get_customer_segment_performance_data()

    assert isinstance(
        error.value.__cause__,
        sqlite3.OperationalError,
    )

    connection.close.assert_called_once()


def test_product_repository_wraps_database_error():
    connection = MagicMock()

    connection.execute.side_effect = sqlite3.OperationalError(
        "database unavailable"
    )

    with patch(
        (
            "app.database.repositories."
            "product_repository.get_connection"
        ),
        return_value=connection,
    ):
        with pytest.raises(
            RepositoryError,
            match=(
                "Repository operation failed: "
                "get_sales_by_category_data."
            ),
        ) as error:
            get_sales_by_category_data()

    assert isinstance(
        error.value.__cause__,
        sqlite3.OperationalError,
    )

    connection.close.assert_called_once()


def test_promotion_repository_wraps_database_error():
    connection = MagicMock()

    connection.execute.side_effect = sqlite3.OperationalError(
        "database unavailable"
    )

    with patch(
        (
            "app.database.repositories."
            "promotion_repository.get_connection"
        ),
        return_value=connection,
    ):
        with pytest.raises(
            RepositoryError,
            match=(
                "Repository operation failed: "
                "get_promotion_impact_data."
            ),
        ) as error:
            get_promotion_impact_data()

    assert isinstance(
        error.value.__cause__,
        sqlite3.OperationalError,
    )

    connection.close.assert_called_once()


def test_inventory_repository_wraps_database_error():
    connection = MagicMock()

    connection.execute.side_effect = sqlite3.OperationalError(
        "database unavailable"
    )

    with patch(
        (
            "app.database.repositories."
            "inventory_repository.get_connection"
        ),
        return_value=connection,
    ):
        with pytest.raises(
            RepositoryError,
            match=(
                "Repository operation failed: "
                "get_stockout_rate_data."
            ),
        ) as error:
            get_stockout_rate_data()

    assert isinstance(
        error.value.__cause__,
        sqlite3.OperationalError,
    )

    connection.close.assert_called_once()