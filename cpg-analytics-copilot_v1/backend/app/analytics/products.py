from app.database.repositories.product_repository import (
    get_sales_by_category_data,
)
from app.database.repositories.sales_repository import (
    get_top_products_data,
)


def get_top_products(limit: int = 10):
    return get_top_products_data(limit=limit)


def get_sales_by_category():
    return get_sales_by_category_data()