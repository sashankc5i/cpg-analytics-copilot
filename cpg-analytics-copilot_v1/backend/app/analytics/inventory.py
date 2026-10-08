from app.database.repositories.inventory_repository import (
    get_stockout_rate_data,
)


def get_stockout_rate():
    return get_stockout_rate_data()