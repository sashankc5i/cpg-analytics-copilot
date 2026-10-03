from app.database.repositories.product_repository import (
    get_sales_by_category_data,
)
from app.database.repositories.sales_repository import (
    get_top_products_data,
)


def get_top_products(
    limit: int = 10,
    filters: dict | None = None,
):
    return get_top_products_data(
        limit=limit,
        filters=filters,
    )


def get_sales_by_category(
    filters: dict | None = None,
):
    return get_sales_by_category_data(
        filters=filters
    )