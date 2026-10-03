from app.database.repositories.customer_repository import (
    get_customer_segment_performance_data,
)


def get_customer_segment_performance(
    filters: dict | None = None,
):
    return get_customer_segment_performance_data(
        filters=filters
    )