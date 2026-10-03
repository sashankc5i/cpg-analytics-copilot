from app.database.repositories.promotion_repository import (
    get_promotion_impact_data,
)


def get_promotion_impact(
    filters: dict | None = None,
):
    return get_promotion_impact_data(
        filters=filters
    )